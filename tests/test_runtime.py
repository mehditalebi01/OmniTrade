import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from omnitrade.contracts import NodeStatus, Run, RunStatus
from omnitrade.engine.executors import _research_case, deterministic_executors
from omnitrade.engine.runtime import WorkflowRuntime
from omnitrade.sample_workflow import defense_workflow


def make_run():
    return Run(
        workflow_version_id=uuid4(),
        owner_id=uuid4(),
        ticker="AAPL",
        as_of=datetime.now(UTC) - timedelta(minutes=1),
    )


def test_bull_and_bear_support_and_confidence_are_independent() -> None:
    reports = {
        "specialists": [
            {"specialist": "market_analyst", "signal_score": 0.8, "confidence": 0.9},
            {"specialist": "fundamental_analyst", "signal_score": 0.7, "confidence": 0.8},
            {"specialist": "news_analyst", "signal_score": 0.4, "confidence": 0.6},
        ]
    }

    bull = _research_case(True, reports)
    bear = _research_case(False, reports)

    assert bull["strength"] + bear["strength"] == pytest.approx(1)
    assert bull["strength"] != bear["strength"]
    assert bull["confidence"] != bear["confidence"]
    assert bull["confidence"] > bear["confidence"]
    assert all(0 <= case[key] <= 1 for case in (bull, bear) for key in ("strength", "confidence"))


def test_research_case_without_evidence_reports_no_confidence() -> None:
    bull = _research_case(True, {})
    bear = _research_case(False, {})

    assert bull["strength"] == bear["strength"] == 0.5
    assert bull["confidence"] == bear["confidence"] == 0


def test_runtime_completes_and_is_deterministic():
    async def scenario():
        graph = defense_workflow()
        result = await WorkflowRuntime(deterministic_executors()).execute(graph, make_run())
        assert result.run.status == RunStatus.SUCCEEDED
        assert all(n.status.value == "succeeded" for n in result.node_runs.values())
        assert any(e.event_type == "node.loop_iteration" for e in result.events)
        assert result.checkpoints

    asyncio.run(scenario())


def test_different_tickers_produce_different_analysis_values():
    async def scenario():
        first = await WorkflowRuntime(deterministic_executors()).execute(
            defense_workflow(), make_run()
        )
        second_run = make_run()
        second_run.ticker = "MSFT"
        second = await WorkflowRuntime(deterministic_executors()).execute(
            defense_workflow(), second_run
        )
        first_market = first.node_runs["market_analyst"].output
        second_market = second.node_runs["market_analyst"].output
        assert first_market["signal_score"] != second_market["signal_score"]
        assert first_market["key_points"] != second_market["key_points"]

    asyncio.run(scenario())


def test_investor_loss_limit_changes_risk_policy() -> None:
    async def scenario():
        normal_run = make_run()
        strict_run = make_run()
        strict_run.investor_policy.maximum_loss_percent = 5
        normal = await WorkflowRuntime(deterministic_executors()).execute(
            defense_workflow(), normal_run
        )
        strict = await WorkflowRuntime(deterministic_executors()).execute(
            defense_workflow(), strict_run
        )
        assert (
            normal.node_runs["balanced"].output["summary"]
            != strict.node_runs["balanced"].output["summary"]
        )

    asyncio.run(scenario())


def test_optional_failure_degrades_run():
    async def scenario():
        graph = defense_workflow()
        node = next(n for n in graph.nodes if n.id == "sentiment")
        node.config["simulate"] = "failure"
        result = await WorkflowRuntime(deterministic_executors()).execute(graph, make_run())
        assert result.run.status == RunStatus.DEGRADED
        assert result.node_runs["sentiment"].status.value == "degraded"

    asyncio.run(scenario())


def test_required_failure_stops_run():
    async def scenario():
        graph = defense_workflow()
        next(n for n in graph.nodes if n.id == "market").config["simulate"] = "failure"
        result = await WorkflowRuntime(deterministic_executors()).execute(graph, make_run())
        assert result.run.status == RunStatus.FAILED
        assert any(n.status.value == "skipped" for n in result.node_runs.values())

    asyncio.run(scenario())


def test_timeout_does_not_use_an_unselected_fake_fallback():
    async def scenario():
        graph = defense_workflow()
        next(n for n in graph.nodes if n.id == "market").config["simulate"] = "timeout"
        result = await WorkflowRuntime(deterministic_executors()).execute(graph, make_run())
        assert result.run.status == RunStatus.FAILED
        assert not any(e.event_type == "provider.fallback" for e in result.events)

    asyncio.run(scenario())


def test_cancellation_probe_stops_pending_nodes():
    async def scenario():
        async def cancelled(_run_id):
            return True

        result = await WorkflowRuntime(
            deterministic_executors(), cancellation_probe=cancelled
        ).execute(defense_workflow(), make_run())
        assert result.run.status == RunStatus.CANCELLED
        assert all(state.status.value == "cancelled" for state in result.node_runs.values())

    asyncio.run(scenario())


def test_failed_run_resumes_from_checkpoint_without_repeating_successes():
    async def scenario():
        graph = defense_workflow()
        next(node for node in graph.nodes if node.id == "market").config["simulate"] = "failure"
        first = await WorkflowRuntime(deterministic_executors()).execute(graph, make_run())
        checkpoint = first.checkpoints[-1]
        completed_before = {
            node_id
            for node_id, state in checkpoint.node_states.items()
            if state.status.value == "succeeded"
        }
        for state in checkpoint.node_states.values():
            if state.status.value == "failed":
                state.status = NodeStatus.PENDING
                state.error = None
        next(node for node in graph.nodes if node.id == "market").config.pop("simulate")
        second = await WorkflowRuntime(deterministic_executors()).execute(
            graph, first.run, restored=checkpoint
        )
        assert second.run.status == RunStatus.SUCCEEDED
        restarted = {event.node_id for event in second.events if event.event_type == "node.started"}
        assert completed_before.isdisjoint(restarted)

    asyncio.run(scenario())


def test_paused_run_resumes_without_repeating_completed_nodes():
    async def scenario():
        probes = 0

        async def pause_after_first_batch(_run_id):
            nonlocal probes
            probes += 1
            return probes > 1

        graph = defense_workflow()
        first = await WorkflowRuntime(
            deterministic_executors(), pause_probe=pause_after_first_batch
        ).execute(graph, make_run())
        assert first.run.status == RunStatus.PAUSED
        assert first.checkpoints
        checkpoint = first.checkpoints[-1]
        completed_before = {
            node_id
            for node_id, state in checkpoint.node_states.items()
            if state.status in {NodeStatus.SUCCEEDED, NodeStatus.DEGRADED}
        }
        assert completed_before

        second = await WorkflowRuntime(deterministic_executors()).execute(
            graph, first.run, restored=checkpoint
        )

        assert second.run.status == RunStatus.SUCCEEDED
        restarted = {event.node_id for event in second.events if event.event_type == "node.started"}
        assert completed_before.isdisjoint(restarted)

    asyncio.run(scenario())


def test_stale_optional_news_degrades_without_stopping_report():
    async def scenario():
        graph = defense_workflow()
        run = make_run()
        executors = deterministic_executors()

        async def stale_news(node, inputs, context):
            output = await deterministic_executors()["fetch_news"](node, inputs, context)
            output["observed_at"] = (run.as_of - timedelta(days=7)).isoformat()
            return output

        executors["fetch_news"] = stale_news
        result = await WorkflowRuntime(executors).execute(graph, run)

        assert result.run.status == RunStatus.DEGRADED
        assert result.node_runs["time_guard"].status == NodeStatus.DEGRADED
        assert result.node_runs["report"].status == NodeStatus.SUCCEEDED
        assert any("fetch_news was excluded" in reason for reason in result.run.degraded_reasons)

    asyncio.run(scenario())


def test_stale_news_stays_fatal_when_degraded_mode_is_disabled():
    async def scenario():
        graph = defense_workflow()
        run = make_run()
        run.configuration.allow_degraded = False
        executors = deterministic_executors()

        async def stale_news(node, inputs, context):
            output = await deterministic_executors()["fetch_news"](node, inputs, context)
            output["observed_at"] = (run.as_of - timedelta(days=7)).isoformat()
            return output

        executors["fetch_news"] = stale_news
        result = await WorkflowRuntime(executors).execute(graph, run)

        assert result.run.status == RunStatus.FAILED
        assert result.node_runs["time_guard"].status == NodeStatus.FAILED

    asyncio.run(scenario())
