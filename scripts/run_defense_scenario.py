from __future__ import annotations

import asyncio
import json
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from omnitrade.contracts import Run
from omnitrade.engine.executors import deterministic_executors
from omnitrade.engine.runtime import WorkerCrash, WorkflowRuntime
from omnitrade.sample_workflow import defense_workflow


async def main() -> None:
    graph = defense_workflow()
    next(node for node in graph.nodes if node.id == "market").config["simulate"] = "timeout"
    next(node for node in graph.nodes if node.id == "sentiment").config["simulate"] = "failure"
    run = Run(
        workflow_version_id=uuid4(),
        owner_id=uuid4(),
        ticker="AAPL",
        as_of=datetime.now(UTC) - timedelta(minutes=1),
    )
    executors = deterministic_executors()
    normal_proposal = executors["proposal_builder"]
    crash_once = True

    async def proposal_with_crash(node, inputs, context):
        nonlocal crash_once
        if crash_once:
            crash_once = False
            raise WorkerCrash("simulated workflow worker crash")
        return await normal_proposal(node, inputs, context)

    executors["proposal_builder"] = proposal_with_crash
    first = WorkflowRuntime(executors)
    with suppress(WorkerCrash):
        await first.execute(graph, run)
    checkpoint = first._checkpoints[-1]
    first_events = list(first._events)
    resumed = WorkflowRuntime(executors)
    result = await resumed.execute(graph, run, restored=checkpoint)
    events = first_events + result.events
    output = Path("artifacts/defense")
    output.mkdir(parents=True, exist_ok=True)
    (output / "runtime-events.json").write_text(
        json.dumps([event.model_dump(mode="json") for event in events], indent=2, default=str),
        encoding="utf-8",
    )
    (output / "sequence.mmd").write_text(sequence(events), encoding="utf-8")
    summary = {
        "status": result.run.status,
        "events": len(events),
        "checkpoints": checkpoint.sequence + len(result.checkpoints),
        "degraded_reasons": result.run.degraded_reasons,
        "resumed_from": checkpoint.sequence,
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, default=str))


def sequence(events) -> str:
    lines = [
        "sequenceDiagram",
        "  autonumber",
        "  actor User",
        "  participant GUI",
        "  participant API",
        "  participant Workflow",
        "  participant Evidence",
        "  participant Model",
        "  participant Report",
        "  User->>GUI: Start AAPL analysis",
        "  GUI->>API: POST run",
        "  API->>Workflow: run.requested",
    ]
    for event in events:
        if event.event_type == "run.interrupted":
            lines.append("  Note over Workflow,API: worker crash; latest checkpoint stays durable")
            continue
        if (
            event.event_type == "run.started"
            and any("worker crash" in line for line in lines)
            and not any("resume from checkpoint" in line for line in lines)
        ):
            lines.append("  Note over API,Workflow: resume from checkpoint")
            continue
        if not event.node_id or event.event_type not in {
            "node.started",
            "node.succeeded",
            "node.degraded",
            "node.failed",
            "provider.fallback",
            "node.loop_iteration",
        }:
            continue
        target = service_for(event.node_id)
        label = f"{event.event_type}: {event.node_id}"
        if event.event_type == "node.started":
            lines.append(f"  Workflow->>+{target}: {label}")
        elif event.event_type in {"node.succeeded", "node.degraded", "node.failed"}:
            lines.append(f"  {target}-->>-Workflow: {label}")
        else:
            lines.append(f"  Note over Workflow,{target}: {label}")
    lines += [
        "  Workflow-->>API: final event",
        "  API-->>GUI: SSE update",
        "  GUI-->>User: report and lineage",
    ]
    return "\n".join(lines) + "\n"


def service_for(node_id: str) -> str:
    if node_id.startswith(
        (
            "fetch",
            "norm",
            "time",
            "technical",
            "ratios",
            "instrument",
            "market",
            "fundamentals",
            "news",
            "macro",
            "sentiment",
        )
    ):
        return "Evidence"
    if node_id in {"report", "end"}:
        return "Report"
    if "analyst" in node_id or node_id in {
        "bull",
        "bear",
        "research",
        "debate",
        "proposal",
        "aggressive",
        "balanced",
        "conservative",
        "risk_join",
        "decision",
    }:
        return "Model"
    return "Workflow"


if __name__ == "__main__":
    asyncio.run(main())
