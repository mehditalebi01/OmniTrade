from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from omnitrade.auth import LoginRequest, User, authenticate, current_user, issue_token
from omnitrade.config import get_settings
from omnitrade.connections import (
    MODEL_PROVIDERS,
    PROVIDER_CATALOG,
    ConnectionInput,
    connections,
    discover_models,
    verification_error_message,
    verify_connection,
)
from omnitrade.contracts import (
    Checkpoint,
    FailurePolicy,
    NodeRun,
    NodeStatus,
    Run,
    RunEvent,
    RunRequest,
    RunStatus,
    UserProfile,
    WorkflowDefinition,
)
from omnitrade.engine.catalog import NODE_CATALOG
from omnitrade.engine.executors import deterministic_executors
from omnitrade.engine.runtime import WorkflowRuntime
from omnitrade.engine.validator import WorkflowValidator
from omnitrade.infrastructure.events import RedisStreamEventBus
from omnitrade.reporting import build_detailed_report, render_pdf
from omnitrade.sample_workflow import defense_workflow
from omnitrade.storage import NotFoundError, store

app = FastAPI(title="OmniTrade AI API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.post("/api/v1/auth/login")
def login(request: LoginRequest) -> dict[str, str]:
    user = authenticate(request)
    return {"access_token": issue_token(user), "token_type": "bearer"}


@app.get("/api/v1/profile")
def get_profile(user: User = Depends(current_user)) -> dict[str, object]:
    return store.get_profile(user.id).model_dump(mode="json")


@app.put("/api/v1/profile")
def update_profile(profile: UserProfile, user: User = Depends(current_user)) -> dict[str, object]:
    return store.save_profile(user.id, profile).model_dump(mode="json")


@app.get("/api/v1/catalog")
def catalog(_: User = Depends(current_user)) -> dict[str, object]:
    from omnitrade.engine.catalog import NODE_CATALOG, NODE_DESCRIPTIONS, ports_compatible

    return {
        "count": len(NODE_CATALOG),
        "nodes": {
            name: {
                "group": spec.group,
                "description": NODE_DESCRIPTIONS[name],
                "inputs": spec.inputs,
                "outputs": spec.outputs,
                "suggested_targets": [
                    {
                        "node_type": target_name,
                        "source_port": source_port,
                        "target_port": target_port,
                        "data_type": str(source_type),
                    }
                    for target_name, target_spec in NODE_CATALOG.items()
                    for source_port, source_type in spec.outputs.items()
                    for target_port, target_type in target_spec.inputs.items()
                    if target_name != name and ports_compatible(source_type, target_type)
                ],
            }
            for name, spec in NODE_CATALOG.items()
        },
    }


@app.get("/api/v1/connections/catalog")
def connection_catalog(_: User = Depends(current_user)) -> dict[str, object]:
    return {
        "providers": {
            name: {
                "label": spec["label"],
                "category": spec["category"],
                "base_url": spec.get("base_url"),
                "key_optional": spec.get("key_optional", False),
                "auto_connect": spec.get("auto_connect"),
                "availability_note": spec.get("availability_note"),
                "credential_note": spec.get("credential_note"),
                "models": spec.get("models", []),
                "capabilities": spec.get("capabilities", []),
            }
            for name, spec in PROVIDER_CATALOG.items()
        }
    }


@app.get("/api/v1/connections")
def list_connections(user: User = Depends(current_user)) -> list[dict[str, object]]:
    return [item.model_dump(mode="json") for item in connections.statuses(user.id)]


@app.put("/api/v1/connections/{provider}")
def save_connection(
    provider: str, value: ConnectionInput, user: User = Depends(current_user)
) -> dict[str, object]:
    if provider not in PROVIDER_CATALOG or value.provider != provider:
        raise HTTPException(status_code=400, detail="Unknown or mismatched provider")
    return connections.put(user.id, value).model_dump(mode="json")


@app.post("/api/v1/connections/{provider}/verify")
async def verify_saved_connection(
    provider: str, user: User = Depends(current_user)
) -> dict[str, object]:
    value = connections.get(user.id, provider)
    if not value:
        raise HTTPException(status_code=404, detail="Save this connection before verification")
    try:
        message = await verify_connection(value)
    except Exception as exc:
        message = verification_error_message(provider, exc)
        spec = PROVIDER_CATALOG[provider]
        if (
            spec["category"] == "data"
            and spec.get("key_optional")
            and spec.get("auto_connect") is False
        ):
            connections.delete(user.id, provider)
        else:
            connections.mark_verified(user.id, provider, False, message)
        raise HTTPException(status_code=422, detail=f"Connection failed: {message}") from exc
    connections.mark_verified(user.id, provider, True, message)
    return connections.status(user.id, provider).model_dump(mode="json")


@app.get("/api/v1/connections/{provider}/models")
async def connection_models(provider: str, user: User = Depends(current_user)) -> dict[str, object]:
    value = connections.get(user.id, provider)
    if not value:
        raise HTTPException(status_code=404, detail="Save this connection before loading models")
    try:
        models = await discover_models(value)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not load models: {exc}") from exc
    connections.save_models(user.id, provider, models)
    return {"provider": provider, "models": models}


@app.delete("/api/v1/connections/{provider}", status_code=204)
def delete_connection(provider: str, user: User = Depends(current_user)) -> Response:
    connections.delete(user.id, provider)
    return Response(status_code=204)


@app.get("/api/v1/analysis-options")
def analysis_options(user: User = Depends(current_user)) -> dict[str, object]:
    settings = get_settings()
    verified = connections.runtime_connections(user.id)
    verified_models = {
        name: (
            connections.models(user.id, name)
            or ([value["test_model"]] if value.get("test_model") else [])
        )
        for name, value in verified.items()
        if name in MODEL_PROVIDERS
    }
    quick_models = sorted({model for models in verified_models.values() for model in models})
    return {
        "tickers": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD"],
        "quick_models": quick_models
        or (["deterministic-fixture"] if settings.fixture_mode else []),
        "deep_models": quick_models or (["deterministic-fixture"] if settings.fixture_mode else []),
        "model_providers": sorted(name for name in verified if name in MODEL_PROVIDERS),
        "provider_models": verified_models,
        "data_providers": sorted(
            name for name in verified if PROVIDER_CATALOG[name]["category"] == "data"
        ),
        "data_provider_labels": {
            name: PROVIDER_CATALOG[name]["label"]
            for name in verified
            if PROVIDER_CATALOG[name]["category"] == "data"
        },
        "data_provider_capabilities": {
            name: PROVIDER_CATALOG[name].get("capabilities", [])
            for name in verified
            if PROVIDER_CATALOG[name]["category"] == "data"
        },
        "languages": [
            "English",
            "Italian",
            "Chinese",
            "Japanese",
            "Korean",
            "Hindi",
            "Spanish",
            "Portuguese",
            "French",
            "German",
            "Arabic",
            "Russian",
        ],
        "currencies": ["USD", "EUR", "GBP", "JPY"],
        "data_modes": ["recorded", "live"] if settings.fixture_mode else ["live"],
    }


@app.get("/api/v1/workflows")
def list_workflows(user: User = Depends(current_user)) -> list[dict[str, object]]:
    return [_workflow_response(item) for item in store.list_workflows(user.id)]


@app.post("/api/v1/workflows", status_code=201)
def create_workflow(
    definition: WorkflowDefinition, user: User = Depends(current_user)
) -> dict[str, object]:
    return _workflow_response(store.create_workflow(user.id, definition))


@app.post("/api/v1/workflows/sample", status_code=201)
def create_sample(user: User = Depends(current_user)) -> dict[str, object]:
    sample = defense_workflow()
    existing = next(
        (record for record in store.list_workflows(user.id) if record["definition"] == sample),
        None,
    )
    return _workflow_response(existing or store.create_workflow(user.id, sample))


@app.get("/api/v1/workflows/{workflow_id}")
def get_workflow(workflow_id: UUID, user: User = Depends(current_user)) -> dict[str, object]:
    try:
        return _workflow_response(store.get_workflow(workflow_id, user.id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail="Workflow not found") from exc


@app.put("/api/v1/workflows/{workflow_id}")
def update_workflow(
    workflow_id: UUID, definition: WorkflowDefinition, user: User = Depends(current_user)
) -> dict[str, object]:
    try:
        return _workflow_response(store.update_workflow(workflow_id, user.id, definition))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail="Workflow not found") from exc


@app.post("/api/v1/workflows/{workflow_id}/reset-default")
def reset_workflow_default(
    workflow_id: UUID, user: User = Depends(current_user)
) -> dict[str, object]:
    """Reset only the draft; published versions and old run reports stay unchanged."""

    try:
        store.get_workflow(workflow_id, user.id)
        return _workflow_response(store.update_workflow(workflow_id, user.id, defense_workflow()))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail="Workflow not found") from exc


@app.delete("/api/v1/workflows/{workflow_id}", status_code=204)
def delete_workflow(workflow_id: UUID, user: User = Depends(current_user)) -> Response:
    try:
        store.delete_workflow(workflow_id, user.id)
        return Response(status_code=204)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail="Workflow not found") from exc


@app.post("/api/v1/workflows/{workflow_id}/validate")
def validate_workflow(workflow_id: UUID, user: User = Depends(current_user)) -> dict[str, object]:
    try:
        result = WorkflowValidator().validate(
            store.get_workflow(workflow_id, user.id)["definition"]
        )
        return result.model_dump(mode="json")
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail="Workflow not found") from exc


@app.post("/api/v1/workflows/{workflow_id}/publish")
def publish_workflow(workflow_id: UUID, user: User = Depends(current_user)) -> dict[str, object]:
    try:
        record = store.get_workflow(workflow_id, user.id)
        result = WorkflowValidator().validate(record["definition"])
        if not result.valid:
            raise HTTPException(status_code=422, detail=result.model_dump(mode="json"))
        return store.publish(workflow_id, user.id).model_dump(mode="json")
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail="Workflow not found") from exc


@app.post("/api/v1/runs", status_code=202)
def create_run(
    request: RunRequest, background: BackgroundTasks, user: User = Depends(current_user)
) -> dict[str, object]:
    version = store.versions.get(request.workflow_version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Workflow version not found")
    workflow = store.workflows.get(version.workflow_id)
    if not workflow or workflow["owner_id"] != user.id:
        raise HTTPException(status_code=404, detail="Workflow version not found")
    run = Run(
        workflow_version_id=version.id,
        owner_id=user.id,
        ticker=request.ticker,
        as_of=request.as_of,
        configuration=request.configuration,
        investor_policy=store.get_profile(user.id).investor_policy.model_copy(deep=True),
        budget_override=request.budget_override,
    )
    if not get_settings().fixture_mode and request.configuration.data_mode == "recorded":
        raise HTTPException(
            status_code=422,
            detail="Recorded evidence is for automated tests only. Configure verified real providers.",
        )
    _ensure_run_connections(run)
    configured = _configured_definition(version.definition, run)
    validation = WorkflowValidator().validate(configured)
    if not validation.valid:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Run settings make this workflow invalid",
                "validation": validation.model_dump(mode="json"),
            },
        )
    store.save_run(run)
    background.add_task(_execute_run, run.id)
    return run.model_dump(mode="json")


@app.get("/api/v1/runs")
async def list_runs(user: User = Depends(current_user)) -> list[dict[str, object]]:
    await _reconcile_completed_runs(user.id)
    return [run.model_dump(mode="json") for run in store.list_runs(user.id)]


@app.get("/api/v1/runs/{run_id}")
async def get_run(run_id: UUID, user: User = Depends(current_user)) -> dict[str, object]:
    run = _owned_run(run_id, user)
    await _reconcile_completed_run(run.id)
    return run.model_dump(mode="json")


@app.post("/api/v1/runs/{run_id}/cancel", status_code=202)
async def cancel_run(run_id: UUID, user: User = Depends(current_user)) -> dict[str, object]:
    run = _owned_run(run_id, user)
    if run.status not in {
        RunStatus.QUEUED,
        RunStatus.RUNNING,
        RunStatus.PAUSING,
        RunStatus.PAUSED,
    }:
        raise HTTPException(status_code=409, detail="Run cannot be cancelled in its current state")
    if run.status == RunStatus.PAUSED:
        run.status = RunStatus.CANCELLED
        run.updated_at = datetime.now(UTC)
        store.save_run(run)
        await _record_control_event(run, "run.cancelled")
        if get_settings().env == "compose":
            await RedisStreamEventBus(get_settings().redis_url).clear_pause(run_id)
        return run.model_dump(mode="json")
    run.status = RunStatus.CANCELLING
    run.updated_at = datetime.now(UTC)
    store.save_run(run)
    await _record_control_event(run, "run.cancel_requested")
    if get_settings().env == "compose":
        await RedisStreamEventBus(get_settings().redis_url).request_cancel(run_id)
    return run.model_dump(mode="json")


@app.post("/api/v1/runs/{run_id}/pause", status_code=202)
async def pause_run(run_id: UUID, user: User = Depends(current_user)) -> dict[str, object]:
    run = _owned_run(run_id, user)
    if run.status not in {RunStatus.QUEUED, RunStatus.RUNNING}:
        raise HTTPException(status_code=409, detail="Only an active run can be paused")
    run.status = RunStatus.PAUSING
    run.updated_at = datetime.now(UTC)
    store.save_run(run)
    await _record_control_event(run, "run.pause_requested")
    if get_settings().env == "compose":
        await RedisStreamEventBus(get_settings().redis_url).request_pause(run_id)
    return run.model_dump(mode="json")


@app.post("/api/v1/runs/{run_id}/resume", status_code=202)
async def resume_run(
    run_id: UUID, background: BackgroundTasks, user: User = Depends(current_user)
) -> dict[str, object]:
    run = _owned_run(run_id, user)
    await _reconcile_completed_run(run.id)
    if run.status not in {RunStatus.INTERRUPTED, RunStatus.FAILED, RunStatus.PAUSED}:
        raise HTTPException(
            status_code=409, detail="Only paused, interrupted, or failed runs can resume"
        )
    _ensure_run_connections(run)
    if get_settings().env == "compose":
        bus = RedisStreamEventBus(get_settings().redis_url)
        await bus.clear_pause(run_id)
        await bus.clear_cancel(run_id)
    run.status = RunStatus.QUEUED
    run.updated_at = datetime.now(UTC)
    store.save_run(run)
    await _record_control_event(run, "run.resume_requested")
    background.add_task(_execute_run, run.id)
    return run.model_dump(mode="json")


@app.get("/api/v1/runs/{run_id}/events")
def run_events(run_id: UUID, user: User = Depends(current_user)) -> StreamingResponse:
    _owned_run(run_id, user)

    async def stream() -> AsyncIterator[str]:
        sent = 0
        seen: set[UUID] = set()
        redis_bus = (
            RedisStreamEventBus(get_settings().redis_url)
            if get_settings().env == "compose"
            else None
        )
        while True:
            if redis_bus:
                events = [
                    event async for event in redis_bus.stream(run_id) if event.event_id not in seen
                ]
            else:
                events = store.run_events[run_id][sent:]
            for event in events:
                seen.add(event.event_id)
                sent += 1
                yield f"id: {sent}\nevent: {event.event_type}\ndata: {event.model_dump_json()}\n\n"
            run = store.runs[run_id]
            if run.status in {
                RunStatus.SUCCEEDED,
                RunStatus.DEGRADED,
                RunStatus.FAILED,
                RunStatus.PAUSED,
                RunStatus.CANCELLED,
                RunStatus.INTERRUPTED,
            } and (redis_bus is not None or sent >= len(store.run_events[run_id])):
                break
            await asyncio.sleep(0.1)

    return StreamingResponse(
        stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"}
    )


@app.get("/api/v1/runs/{run_id}/lineage")
async def lineage(run_id: UUID, user: User = Depends(current_user)) -> dict[str, object]:
    _owned_run(run_id, user)
    result = store.run_results.get(run_id, {})
    nodes = result.get("nodes", {})
    events = store.run_events[run_id]
    if get_settings().env == "compose":
        events = await _combined_run_events(run_id)
    if not nodes:
        nodes = _nodes_from_events(events)
    return {
        "run_id": run_id,
        "nodes": nodes,
        "events": len(events),
        "complete": bool(result),
    }


@app.get("/api/v1/runs/{run_id}/activity")
async def run_activity(run_id: UUID, user: User = Depends(current_user)) -> dict[str, object]:
    run = _owned_run(run_id, user)
    await _reconcile_completed_run(run.id)
    events = await _combined_run_events(run_id)
    nodes = store.run_results.get(run_id, {}).get("nodes", {})
    if not nodes:
        nodes = _nodes_from_events(events)
    return {
        "run": run.model_dump(mode="json"),
        "events": [event.model_dump(mode="json") for event in events],
        "nodes": nodes,
    }


@app.get("/api/v1/reports/{run_id}")
async def report(run_id: UUID, user: User = Depends(current_user)) -> dict[str, object]:
    run = _owned_run(run_id, user)
    await _reconcile_completed_run(run.id)
    result = store.run_results.get(run_id)
    if not result:
        raise HTTPException(status_code=409, detail="Report is not ready")
    return cast(dict[str, object], result.get("report", {}))


@app.get("/api/v1/report-history")
async def list_reports(user: User = Depends(current_user)) -> list[dict[str, object]]:
    await _reconcile_completed_runs(user.id)
    reports: list[dict[str, object]] = []
    for run in store.list_runs(user.id):
        result = store.run_results.get(run.id)
        if not result or not result.get("report"):
            continue
        report_data = cast(dict[str, object], result["report"])
        decision_value = report_data.get("decision")
        decision = (
            cast(dict[str, object], decision_value) if isinstance(decision_value, dict) else {}
        )
        reports.append(
            {
                "run_id": run.id,
                "ticker": run.ticker,
                "as_of": run.as_of,
                "created_at": run.created_at,
                "status": run.status,
                "action": decision.get("action", "NO_DECISION"),
                "confidence": decision.get("confidence", 0),
            }
        )
    return reports


@app.get("/api/v1/reports/{run_id}/export/{format}")
async def export_report(run_id: UUID, format: str, user: User = Depends(current_user)) -> Response:
    data = await report(run_id, user)
    if format == "json":
        return Response(json.dumps(data, indent=2, default=str), media_type="application/json")
    if format == "html":
        body = f"<html><body><h1>OmniTrade AI report</h1><pre>{json.dumps(data, indent=2, default=str)}</pre><p>Decision support only.</p></body></html>"
        return Response(body, media_type="text/html")
    if format == "pdf":
        return Response(
            render_pdf(data),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="omnitrade-{run_id}.pdf"'},
        )
    raise HTTPException(status_code=400, detail="Supported formats: json, html, pdf")


async def _execute_run(run_id: UUID) -> None:
    run = store.runs[run_id]
    if run.status == RunStatus.QUEUED:
        run.status = RunStatus.RUNNING
        run.updated_at = datetime.now(UTC)
        store.save_run(run)
    version = store.versions[run.workflow_version_id]
    checkpoint = await _latest_checkpoint(run_id)
    definition = _configured_definition(version.definition, run)
    if get_settings().env == "compose":
        try:
            # The workflow budget is a domain limit. The transport gets a grace
            # period so a finished report is not discarded during final return.
            async with httpx.AsyncClient(
                timeout=definition.budget.max_runtime_seconds + 300
            ) as client:
                response = await client.post(
                    "http://workflow:8001/internal/runs/execute",
                    json={
                        "workflow": definition.model_dump(mode="json"),
                        "run": run.model_dump(mode="json"),
                        "checkpoint": checkpoint.model_dump(mode="json") if checkpoint else None,
                        "connections": connections.runtime_connections(run.owner_id),
                    },
                )
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPError:
            if not await _reconcile_completed_run(run_id):
                run.status = RunStatus.INTERRUPTED
                run.updated_at = datetime.now(UTC)
                store.save_run(run)
            return
        updated = Run.model_validate(body["run"])
        events = [RunEvent.model_validate(event_data) for event_data in body["events"]]
        _apply_runtime_budget(updated, events, definition.budget.max_runtime_seconds)
        store.save_run(updated)
        for event in events:
            store.add_event(event)
        if updated.status == RunStatus.PAUSED:
            return
        detailed_report = build_detailed_report(body["report"], body["nodes"], updated)
        store.save_result(run_id, {"nodes": body["nodes"], "report": detailed_report})
        return
    if run.configuration.data_mode == "recorded":
        local_executors = deterministic_executors()
    else:
        from omnitrade.engine.catalog import NODE_CATALOG
        from omnitrade.services import NodeTask, execute_task, model_execute, report_execute

        async def local_execute(node: Any, inputs: dict[str, Any], context: Any) -> Any:
            all_connections = connections.runtime_connections(run.owner_id)
            if node.type.startswith("fetch_"):
                config = run.configuration
                selected = set(
                    config.market_providers
                    + config.fundamental_providers
                    + config.news_providers
                    + config.sentiment_providers
                    + config.macro_providers
                )
            elif NODE_CATALOG[node.type].group in {"specialist", "research", "risk", "output"}:
                selected = {run.configuration.model_provider}
            else:
                selected = set()
            task = NodeTask(
                node=node,
                inputs=inputs,
                run=context.run,
                connections={
                    name: value for name, value in all_connections.items() if name in selected
                },
            )
            if NODE_CATALOG[node.type].group in {"specialist", "research", "risk"}:
                return (await model_execute(task)).output
            if NODE_CATALOG[node.type].group == "output":
                return (await report_execute(task)).output
            return (await execute_task(task)).output

        local_executors = {name: local_execute for name in NODE_CATALOG}
    runtime = WorkflowRuntime(
        local_executors,
        listener=_event_listener,
        cancellation_probe=_local_cancellation_probe,
        pause_probe=_local_pause_probe,
        connections=connections.runtime_connections(run.owner_id),
    )
    result = await runtime.execute(definition, run, restored=checkpoint)
    report_node: Any = next(
        (
            state.output
            for node_id, state in result.node_runs.items()
            if definition.nodes and node_id == "report"
        ),
        {},
    )
    store.save_run(result.run)
    node_data = {key: value.model_dump(mode="json") for key, value in result.node_runs.items()}
    if result.run.status == RunStatus.PAUSED:
        return
    store.save_result(
        run.id,
        {
            "nodes": node_data,
            "report": build_detailed_report(report_node or {}, node_data, result.run),
        },
    )


async def _reconcile_completed_runs(owner_id: UUID) -> None:
    if get_settings().env != "compose":
        return
    for run in store.list_runs(owner_id):
        if run.status == RunStatus.INTERRUPTED and run.id not in store.run_results:
            await _reconcile_completed_run(run.id)


async def _reconcile_completed_run(run_id: UUID) -> bool:
    """Recover a worker result that completed after the API transport timed out."""

    run = store.runs.get(run_id)
    if not run or run_id in store.run_results or get_settings().env != "compose":
        return False
    events = await _combined_run_events(run_id)
    for event in events:
        store.add_event(event)
    return _recover_run_from_events(run, events)


def _recover_run_from_events(run: Run, events: list[RunEvent]) -> bool:
    completed = next(
        (event for event in reversed(events) if event.event_type == "run.completed"),
        None,
    )
    checkpoint_event = next(
        (event for event in reversed(events) if event.event_type == "run.checkpointed"),
        None,
    )
    if not completed or not checkpoint_event:
        return False
    raw_states = checkpoint_event.payload.get("node_states")
    if not isinstance(raw_states, dict):
        return False
    states = {node_id: NodeRun.model_validate(value) for node_id, value in raw_states.items()}
    report_state = states.get("report")
    if (
        not report_state
        or report_state.status != NodeStatus.SUCCEEDED
        or not isinstance(report_state.output, dict)
    ):
        return False

    run.status = RunStatus(completed.payload.get("status", RunStatus.SUCCEEDED))
    run.updated_at = completed.occurred_at
    version = store.versions.get(run.workflow_version_id)
    runtime_limit = (
        run.budget_override.max_runtime_seconds
        if run.budget_override
        else version.definition.budget.max_runtime_seconds
        if version
        else 180
    )
    _apply_runtime_budget(run, events, runtime_limit)
    node_data = {node_id: state.model_dump(mode="json") for node_id, state in states.items()}
    store.save_run(run)
    for event in events:
        store.add_event(event)
    store.save_result(
        run.id,
        {
            "nodes": node_data,
            "report": build_detailed_report(report_state.output, node_data, run),
        },
    )
    return True


def _apply_runtime_budget(run: Run, events: list[RunEvent], runtime_limit: int) -> None:
    started = next((event for event in events if event.event_type == "run.started"), None)
    completed = next(
        (event for event in reversed(events) if event.event_type == "run.completed"),
        None,
    )
    if not started or not completed:
        return
    elapsed = (completed.occurred_at - started.occurred_at).total_seconds()
    if elapsed <= runtime_limit:
        return
    reason = f"Runtime budget exceeded: {elapsed:.1f}s used, {runtime_limit}s allowed"
    if reason not in run.degraded_reasons:
        run.degraded_reasons.append(reason)
    run.status = RunStatus.DEGRADED


async def _event_listener(event: RunEvent) -> None:
    store.add_event(event)


async def _record_control_event(run: Run, event_type: str) -> None:
    """Write user control commands to durable history and the live event stream."""

    event = RunEvent(
        event_type=event_type,
        run_id=run.id,
        trace_id=run.trace_id,
        payload={"status": run.status},
    )
    store.add_event(event)
    if get_settings().env == "compose":
        await RedisStreamEventBus(get_settings().redis_url).publish(event)


def _ensure_run_connections(run: Run) -> None:
    """Recheck session-only credentials before a new or resumed live run."""

    if run.configuration.data_mode == "recorded":
        return
    available = connections.runtime_connections(run.owner_id)
    selected_data = set(
        run.configuration.market_providers
        + run.configuration.fundamental_providers
        + run.configuration.news_providers
        + run.configuration.sentiment_providers
        + run.configuration.macro_providers
    )
    missing = sorted(selected_data - available.keys())
    if missing:
        raise HTTPException(
            status_code=422,
            detail=(
                "Reconnect and verify the data providers required by this run: "
                + ", ".join(missing)
            ),
        )
    provider = run.configuration.model_provider
    if provider not in available:
        raise HTTPException(
            status_code=422,
            detail=f"Reconnect and verify the model provider required by this run: {provider}",
        )
    fallback_model = available[provider].get("test_model")
    allowed_models = connections.models(run.owner_id, provider) or (
        [fallback_model] if fallback_model else []
    )
    selected_models = {run.configuration.quick_model, run.configuration.deep_model}
    if not selected_models.issubset(allowed_models):
        raise HTTPException(
            status_code=422,
            detail="Reconnect the model provider and load the models saved by this run",
        )


def _nodes_from_events(events: list[RunEvent]) -> dict[str, object]:
    checkpoint = next(
        (event for event in reversed(events) if event.event_type == "run.checkpointed"),
        None,
    )
    if not checkpoint:
        return {}
    states = checkpoint.payload.get("node_states", {})
    return cast(dict[str, object], states) if isinstance(states, dict) else {}


async def _local_cancellation_probe(run_id: UUID) -> bool:
    return store.runs[run_id].status == RunStatus.CANCELLING


async def _local_pause_probe(run_id: UUID) -> bool:
    return store.runs[run_id].status == RunStatus.PAUSING


async def _latest_checkpoint(run_id: UUID) -> Checkpoint | None:
    events = await _combined_run_events(run_id)
    candidates = [event for event in events if event.event_type == "run.checkpointed"]
    if not candidates:
        return None
    event = max(candidates, key=lambda item: int(item.payload["sequence"]))
    states = {
        node_id: NodeRun.model_validate(state)
        for node_id, state in event.payload["node_states"].items()
    }
    for state in states.values():
        if state.status in {
            NodeStatus.FAILED,
            NodeStatus.SKIPPED,
            NodeStatus.CANCELLED,
            NodeStatus.RUNNING,
            NodeStatus.READY,
        }:
            state.status = NodeStatus.PENDING
            state.error = None
    return Checkpoint(
        run_id=run_id,
        sequence=int(event.payload["sequence"]),
        node_states=states,
    )


async def _combined_run_events(run_id: UUID) -> list[RunEvent]:
    """Merge durable database history with the current Redis stream."""

    by_id = {event.event_id: event for event in store.run_events[run_id]}
    if get_settings().env == "compose":
        redis_events = [
            event async for event in RedisStreamEventBus(get_settings().redis_url).stream(run_id)
        ]
        by_id.update({event.event_id: event for event in redis_events})
    return sorted(by_id.values(), key=lambda event: event.occurred_at)


def _owned_run(run_id: UUID, user: User) -> Run:
    run = store.runs.get(run_id)
    if not run or run.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


def _configured_definition(definition: WorkflowDefinition, run: Run) -> WorkflowDefinition:
    configured = definition.model_copy(deep=True)
    if run.budget_override:
        configured.budget = run.budget_override
    for node in configured.nodes:
        if node.type.startswith("fetch_"):
            # Real provider fallback is controlled by the selected provider
            # chain. Old workflow drafts may still contain a fixture fallback,
            # which must never be used or shown for a live run.
            node.retry.fallback_provider = None
        if NODE_CATALOG[node.type].model_cost:
            retry_timeout = 100 * (run.configuration.model_max_retries + 1)
            node.timeout_seconds = max(node.timeout_seconds, min(300, retry_timeout))
        if node.type == "bounded_loop":
            node.config["max_iterations"] = run.configuration.research_depth
        elif node.type == "time_guard":
            node.config["max_age_hours"] = run.configuration.evidence_freshness_hours
        if not run.configuration.allow_degraded:
            node.failure_policy = FailurePolicy.REQUIRED
    analyst_nodes = {
        "market": "market_analyst",
        "fundamentals": "fundamental_analyst",
        "news": "news_analyst",
        "sentiment": "sentiment_analyst",
    }
    removed = {
        node_id
        for analyst, node_id in analyst_nodes.items()
        if analyst not in run.configuration.analysts
    }
    configured.nodes = [node for node in configured.nodes if node.id not in removed]
    configured.edges = [
        edge
        for edge in configured.edges
        if edge.source not in removed and edge.target not in removed
    ]
    return configured


def _workflow_response(record: dict[str, object]) -> dict[str, object]:
    return {
        "id": record["id"],
        "owner_id": record["owner_id"],
        "definition": record["definition"],
        "version": record["version"],
        "published_version_id": record["published_version_id"],
    }
