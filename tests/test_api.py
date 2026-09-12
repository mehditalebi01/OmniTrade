from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from omnitrade.api import _configured_definition, _recover_run_from_events, app
from omnitrade.contracts import NodeRun, NodeStatus, Run, RunConfiguration, RunEvent, RunStatus
from omnitrade.engine.catalog import NODE_CATALOG
from omnitrade.sample_workflow import defense_workflow
from omnitrade.storage import store


def auth(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": "demo", "password": "demo"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_model_node_timeout_allows_configured_retries() -> None:
    run = Run(
        workflow_version_id=uuid4(),
        owner_id=uuid4(),
        ticker="AAPL",
        as_of=datetime.now(UTC),
        configuration=RunConfiguration(model_max_retries=2),
    )

    configured = _configured_definition(defense_workflow(), run)

    model_nodes = [node for node in configured.nodes if NODE_CATALOG[node.type].model_cost]
    assert model_nodes
    assert all(node.timeout_seconds == 300 for node in model_nodes)


def test_complete_browser_api_scenario() -> None:
    store.workflows.clear()
    store.versions.clear()
    store.runs.clear()
    store.run_events.clear()
    store.run_results.clear()
    with TestClient(app) as client:
        headers = auth(client)
        workflow = client.post("/api/v1/workflows/sample", headers=headers).json()
        checked = client.post(
            f"/api/v1/workflows/{workflow['id']}/validate", headers=headers
        ).json()
        assert checked["valid"] is True
        version = client.post(f"/api/v1/workflows/{workflow['id']}/publish", headers=headers).json()
        run_response = client.post(
            "/api/v1/runs",
            headers=headers,
            json={
                "workflow_version_id": version["id"],
                "ticker": "MSFT",
                "as_of": "2026-01-01T10:00:00Z",
                "configuration": {"data_mode": "recorded"},
            },
        )
        assert run_response.status_code == 202
        run_id = run_response.json()["id"]
        run = client.get(f"/api/v1/runs/{run_id}", headers=headers).json()
        assert run["status"] == "succeeded"
        lineage = client.get(f"/api/v1/runs/{run_id}/lineage", headers=headers).json()
        assert lineage["complete"] is True
        assert lineage["events"] > 30
        report = client.get(f"/api/v1/reports/{run_id}", headers=headers).json()
        assert report["ticker"] == "MSFT"
        assert report["lineage_complete"] is True
        assert len(report["agent_analyses"]) == 4
        assert len(report["risk_analyses"]) == 3
        assert report["research_debate"]["bull_case"]["key_points"]
        assert report["workflow_summary"]["trace_id"]


def test_workflow_draft_can_reset_without_replacing_published_version() -> None:
    with TestClient(app) as client:
        headers = auth(client)
        workflow = client.post("/api/v1/workflows/sample", headers=headers).json()
        version = client.post(f"/api/v1/workflows/{workflow['id']}/publish", headers=headers).json()
        changed = workflow["definition"]
        changed["nodes"][0]["name"] = "Custom start"
        changed["nodes"][0]["config"]["ui_color"] = "#123456"
        assert (
            client.put(
                f"/api/v1/workflows/{workflow['id']}", headers=headers, json=changed
            ).status_code
            == 200
        )

        reset = client.post(
            f"/api/v1/workflows/{workflow['id']}/reset-default", headers=headers
        ).json()

        assert reset["definition"] == defense_workflow().model_dump(mode="json")
        assert reset["published_version_id"] == version["id"]


def test_completed_worker_events_recover_late_non_aapl_report() -> None:
    run = Run(
        workflow_version_id=uuid4(),
        owner_id=uuid4(),
        ticker="NVDA",
        as_of=datetime.now(UTC),
        status=RunStatus.INTERRUPTED,
    )
    started_at = datetime.now(UTC) - timedelta(seconds=240)
    report_state = NodeRun(
        run_id=run.id,
        node_id="report",
        status=NodeStatus.SUCCEEDED,
        output={"ticker": "NVDA", "decision": {"action": "HOLD", "confidence": 0.6}},
    )
    events = [
        RunEvent(
            event_type="run.started", run_id=run.id, trace_id=run.trace_id, occurred_at=started_at
        ),
        RunEvent(
            event_type="run.checkpointed",
            run_id=run.id,
            trace_id=run.trace_id,
            payload={
                "sequence": 1,
                "node_states": {"report": report_state.model_dump(mode="json")},
            },
        ),
        RunEvent(
            event_type="run.completed",
            run_id=run.id,
            trace_id=run.trace_id,
            payload={"status": "succeeded"},
        ),
    ]
    store.save_run(run)

    assert _recover_run_from_events(run, events) is True
    assert store.runs[run.id].status == RunStatus.DEGRADED
    assert store.run_results[run.id]["report"]["ticker"] == "NVDA"


def test_pause_and_old_run_resume_are_exposed_by_api(monkeypatch) -> None:
    async def do_not_execute(_run_id):
        return None

    monkeypatch.setattr("omnitrade.api._execute_run", do_not_execute)
    with TestClient(app) as client:
        headers = auth(client)
        workflow = client.post("/api/v1/workflows/sample", headers=headers).json()
        version = client.post(f"/api/v1/workflows/{workflow['id']}/publish", headers=headers).json()
        owner_id = next(
            value["owner_id"]
            for value in store.workflows.values()
            if str(value["id"]) == workflow["id"]
        )
        active = Run(
            workflow_version_id=version["id"],
            owner_id=owner_id,
            ticker="AMD",
            as_of=datetime.now(UTC),
            status=RunStatus.RUNNING,
            configuration=RunConfiguration(data_mode="recorded"),
        )
        store.save_run(active)

        paused = client.post(f"/api/v1/runs/{active.id}/pause", headers=headers)
        assert paused.status_code == 202
        assert paused.json()["status"] == "pausing"
        assert any(
            event.event_type == "run.pause_requested" for event in store.run_events[active.id]
        )

        active.status = RunStatus.PAUSED
        active.created_at = datetime.now(UTC) - timedelta(days=4)
        store.save_run(active)
        resumed = client.post(f"/api/v1/runs/{active.id}/resume", headers=headers)
        assert resumed.status_code == 202
        assert resumed.json()["status"] == "queued"
        assert any(
            event.event_type == "run.resume_requested" for event in store.run_events[active.id]
        )


def test_catalog_suggestions_and_input_options_are_backend_contracts() -> None:
    with TestClient(app) as client:
        headers = auth(client)
        options = client.get("/api/v1/analysis-options", headers=headers).json()
        assert "AAPL" in options["tickers"]
        assert options["quick_models"] == ["deterministic-fixture"]
        catalog = client.get("/api/v1/catalog", headers=headers).json()["nodes"]
        assert catalog["market_analyst"]["description"].startswith("Explains price trends")
        suggestions = catalog["fetch_market"]["suggested_targets"]
        assert any(item["node_type"] == "normalize_market" for item in suggestions)
        assert all(item["source_port"] and item["target_port"] for item in suggestions)


def test_connection_credentials_are_write_only() -> None:
    with TestClient(app) as client:
        headers = auth(client)
        catalog = client.get("/api/v1/connections/catalog", headers=headers)
        assert catalog.status_code == 200
        assert "openai" in catalog.json()["providers"]
        providers = catalog.json()["providers"]
        assert providers["yfinance"]["auto_connect"] is True
        assert providers["stocktwits"]["auto_connect"] is False
        assert providers["reddit"]["availability_note"]
        assert "API key" in providers["alpha_vantage"]["credential_note"]
        saved = client.put(
            "/api/v1/connections/openai",
            headers=headers,
            json={"provider": "openai", "api_key": "secret-value", "test_model": "gpt-5.4-mini"},
        )
        assert saved.status_code == 200
        assert "secret-value" not in saved.text
        listed = client.get("/api/v1/connections", headers=headers)
        assert "secret-value" not in listed.text
        bedrock = client.put(
            "/api/v1/connections/bedrock",
            headers=headers,
            json={
                "provider": "bedrock",
                "aws_bearer_token_bedrock": "private-bedrock-token",
                "region": "us-east-1",
                "test_model": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
                "model_ids": [
                    "us.anthropic.claude-haiku-4-5-20251001-v1:0",
                    "us.anthropic.claude-sonnet-4-6",
                ],
            },
        )
        assert bedrock.status_code == 200
        assert "private-bedrock-token" not in bedrock.text
        assert len(bedrock.json()["models"]) == 2


def test_failed_optional_public_feed_is_removed_and_error_is_short(monkeypatch) -> None:
    async def blocked(_value):
        request = httpx.Request("GET", "https://provider.example/private-path")
        response = httpx.Response(429, request=request)
        raise httpx.HTTPStatusError("rate limited", request=request, response=response)

    monkeypatch.setattr("omnitrade.api.verify_connection", blocked)
    with TestClient(app) as client:
        headers = auth(client)
        saved = client.put(
            "/api/v1/connections/reddit",
            headers=headers,
            json={"provider": "reddit"},
        )
        assert saved.status_code == 200
        failed = client.post("/api/v1/connections/reddit/verify", headers=headers)
        assert failed.status_code == 422
        assert "HTTP 429" in failed.json()["detail"]
        assert "private-path" not in failed.text
        statuses = client.get("/api/v1/connections", headers=headers).json()
        reddit = next(item for item in statuses if item["provider"] == "reddit")
        assert reddit["configured"] is False


def test_verified_data_provider_labels_and_roles_reach_analysis(monkeypatch) -> None:
    async def ready(_value):
        return "Data connection verified"

    monkeypatch.setattr("omnitrade.api.verify_connection", ready)
    with TestClient(app) as client:
        headers = auth(client)
        for provider in ("fred", "polymarket"):
            client.put(
                f"/api/v1/connections/{provider}",
                headers=headers,
                json={"provider": provider},
            )
            assert (
                client.post(f"/api/v1/connections/{provider}/verify", headers=headers).status_code
                == 200
            )
        options = client.get("/api/v1/analysis-options", headers=headers).json()
        assert options["data_provider_labels"]["fred"] == "FRED"
        assert options["data_provider_labels"]["polymarket"] == "Polymarket"
        assert options["data_provider_capabilities"]["fred"] == ["macro"]
        assert "macro" in options["data_provider_capabilities"]["polymarket"]
        for provider in ("fred", "polymarket"):
            client.delete(f"/api/v1/connections/{provider}", headers=headers)


def test_sample_workflow_creation_is_idempotent() -> None:
    store.workflows.clear()
    store.versions.clear()
    with TestClient(app) as client:
        headers = auth(client)
        first = client.post("/api/v1/workflows/sample", headers=headers).json()
        second = client.post("/api/v1/workflows/sample", headers=headers).json()
        assert second["id"] == first["id"]
        assert len(client.get("/api/v1/workflows", headers=headers).json()) == 1


def test_user_cannot_read_another_users_workflow() -> None:
    with TestClient(app) as client:
        demo_headers = auth(client)
        workflow = client.post("/api/v1/workflows/sample", headers=demo_headers).json()
        other_login = client.post(
            "/api/v1/auth/login",
            json={"username": "mehdi", "password": "omnitrade"},
        ).json()
        other_headers = {"Authorization": f"Bearer {other_login['access_token']}"}
        response = client.get(f"/api/v1/workflows/{workflow['id']}", headers=other_headers)
        assert response.status_code == 404


def test_profile_and_report_history_are_durable_api_features() -> None:
    with TestClient(app) as client:
        headers = auth(client)
        profile = client.get("/api/v1/profile", headers=headers).json()
        profile["display_name"] = "Demo Student"
        saved = client.put("/api/v1/profile", headers=headers, json=profile)
        assert saved.status_code == 200
        assert saved.json()["display_name"] == "Demo Student"
        assert client.get("/api/v1/runs", headers=headers).status_code == 200
        assert client.get("/api/v1/report-history", headers=headers).status_code == 200


def test_run_settings_are_validated_before_queueing() -> None:
    store.workflows.clear()
    store.versions.clear()
    with TestClient(app) as client:
        headers = auth(client)
        workflow = client.post("/api/v1/workflows/sample", headers=headers).json()
        version = client.post(f"/api/v1/workflows/{workflow['id']}/publish", headers=headers).json()
        response = client.post(
            "/api/v1/runs",
            headers=headers,
            json={
                "workflow_version_id": version["id"],
                "ticker": "AAPL",
                "as_of": "2026-01-01T10:00:00Z",
                "configuration": {"data_mode": "recorded"},
                "budget_override": {
                    "max_runtime_seconds": 180,
                    "max_model_calls": 1,
                    "max_provider_calls": 30,
                    "max_tokens": 40000,
                    "max_parallel_nodes": 8,
                },
            },
        )
        assert response.status_code == 422
        assert response.json()["detail"]["message"] == "Run settings make this workflow invalid"


def test_selected_analysts_change_the_executed_workflow() -> None:
    store.workflows.clear()
    store.versions.clear()
    store.runs.clear()
    store.run_results.clear()
    with TestClient(app) as client:
        headers = auth(client)
        workflow = client.post("/api/v1/workflows/sample", headers=headers).json()
        version = client.post(f"/api/v1/workflows/{workflow['id']}/publish", headers=headers).json()
        response = client.post(
            "/api/v1/runs",
            headers=headers,
            json={
                "workflow_version_id": version["id"],
                "ticker": "AAPL",
                "as_of": "2026-01-01T10:00:00Z",
                "configuration": {"data_mode": "recorded", "analysts": ["market"]},
            },
        )
        assert response.status_code == 202
        lineage = client.get(
            f"/api/v1/runs/{response.json()['id']}/lineage", headers=headers
        ).json()
        assert "market_analyst" in lineage["nodes"]
        assert "fundamental_analyst" not in lineage["nodes"]
        assert "news_analyst" not in lineage["nodes"]
        assert "sentiment_analyst" not in lineage["nodes"]


def test_live_only_mode_is_rejected_when_not_configured() -> None:
    store.workflows.clear()
    store.versions.clear()
    with TestClient(app) as client:
        headers = auth(client)
        workflow = client.post("/api/v1/workflows/sample", headers=headers).json()
        version = client.post(f"/api/v1/workflows/{workflow['id']}/publish", headers=headers).json()
        response = client.post(
            "/api/v1/runs",
            headers=headers,
            json={
                "workflow_version_id": version["id"],
                "ticker": "AAPL",
                "as_of": "2026-01-01T10:00:00Z",
                "configuration": {"data_mode": "live"},
            },
        )
        assert response.status_code == 422
