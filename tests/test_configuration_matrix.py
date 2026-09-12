import asyncio
from datetime import UTC, datetime, timedelta
from itertools import chain, combinations
from typing import Any
from uuid import uuid4

import pytest

from omnitrade.api import _configured_definition
from omnitrade.contracts import Run, RunConfiguration, RunStatus
from omnitrade.engine.executors import deterministic_executors
from omnitrade.engine.runtime import WorkflowRuntime
from omnitrade.engine.validator import WorkflowValidator
from omnitrade.sample_workflow import defense_workflow


def configured_run(**values: Any) -> Run:
    configuration = RunConfiguration(data_mode="recorded", **values)
    return Run(
        workflow_version_id=uuid4(),
        owner_id=uuid4(),
        ticker="AMD",
        as_of=datetime.now(UTC) - timedelta(minutes=1),
        configuration=configuration,
    )


@pytest.mark.parametrize("depth", range(1, 6))
def test_every_research_depth_is_valid_and_executes_its_bound(depth: int) -> None:
    run = configured_run(research_depth=depth)
    workflow = _configured_definition(defense_workflow(), run)

    assert WorkflowValidator().validate(workflow).valid is True
    result = asyncio.run(WorkflowRuntime(deterministic_executors()).execute(workflow, run))

    assert result.run.status == RunStatus.SUCCEEDED
    assert result.node_runs["debate"].iteration == depth
    assert sum(event.event_type == "node.loop_iteration" for event in result.events) == depth


ANALYSTS = ("market", "fundamentals", "news", "sentiment")
ANALYST_NODES = {
    "market": "market_analyst",
    "fundamentals": "fundamental_analyst",
    "news": "news_analyst",
    "sentiment": "sentiment_analyst",
}
ANALYST_COMBINATIONS = list(
    chain.from_iterable(combinations(ANALYSTS, size) for size in range(1, len(ANALYSTS) + 1))
)


@pytest.mark.parametrize("analysts", ANALYST_COMBINATIONS)
def test_every_non_empty_analyst_selection_builds_a_valid_graph(
    analysts: tuple[str, ...],
) -> None:
    run = configured_run(analysts=list(analysts))
    workflow = _configured_definition(defense_workflow(), run)

    assert WorkflowValidator().validate(workflow).valid is True
    present = {node.id for node in workflow.nodes}
    for analyst in ANALYSTS:
        node_id = ANALYST_NODES[analyst]
        assert (node_id in present) is (analyst in analysts)


@pytest.mark.parametrize("risk_profile", ["conservative", "balanced", "aggressive"])
@pytest.mark.parametrize("report_detail", ["summary", "standard", "detailed"])
@pytest.mark.parametrize("reasoning_effort", ["low", "medium", "high"])
def test_report_model_and_risk_options_complete_together(
    risk_profile: str, report_detail: str, reasoning_effort: str
) -> None:
    run = configured_run(
        risk_profile=risk_profile,
        report_detail=report_detail,
        reasoning_effort=reasoning_effort,
        temperature=0.2,
        model_max_retries=3,
    )
    workflow = _configured_definition(defense_workflow(), run)
    result = asyncio.run(WorkflowRuntime(deterministic_executors()).execute(workflow, run))

    assert result.run.status == RunStatus.SUCCEEDED
    report = result.node_runs["report"].output
    assert report["analysis_settings"]["risk_profile"] == risk_profile
    assert report["analysis_settings"]["report_detail"] == report_detail
    assert report["analysis_settings"]["reasoning_effort"] == reasoning_effort
    assert report["analysis_settings"]["temperature"] == 0.2
    assert report["analysis_settings"]["model_max_retries"] == 3


@pytest.mark.parametrize("currency", ["USD", "EUR", "GBP", "JPY"])
@pytest.mark.parametrize(
    "language",
    [
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
)
def test_every_offered_language_and_currency_is_a_valid_configuration(
    currency: str, language: str
) -> None:
    run = configured_run(base_currency=currency, output_language=language)
    workflow = _configured_definition(defense_workflow(), run)

    assert WorkflowValidator().validate(workflow).valid is True
    assert run.configuration.base_currency == currency
    assert run.configuration.output_language == language


@pytest.mark.parametrize("temperature", [None, 0.0, 0.2, 1.0, 2.0])
@pytest.mark.parametrize("model_max_retries", range(0, 6))
@pytest.mark.parametrize("allow_degraded", [False, True])
def test_every_model_control_value_builds_a_valid_workflow(
    temperature: float | None, model_max_retries: int, allow_degraded: bool
) -> None:
    run = configured_run(
        temperature=temperature,
        model_max_retries=model_max_retries,
        allow_degraded=allow_degraded,
    )
    workflow = _configured_definition(defense_workflow(), run)

    assert WorkflowValidator().validate(workflow).valid is True
    assert run.configuration.temperature == temperature
    assert run.configuration.model_max_retries == model_max_retries
    expected_policy = "required" if not allow_degraded else None
    if expected_policy:
        assert all(node.failure_policy == expected_policy for node in workflow.nodes)


@pytest.mark.parametrize(
    ("field", "providers"),
    [
        ("market_providers", ["yfinance", "alpha_vantage"]),
        ("fundamental_providers", ["alpha_vantage", "yfinance"]),
        ("news_providers", ["yfinance", "alpha_vantage"]),
        ("sentiment_providers", ["stocktwits", "reddit", "yfinance"]),
        ("macro_providers", ["fred", "polymarket", "alpha_vantage"]),
    ],
)
def test_every_provider_chain_offered_by_the_ui_is_accepted(
    field: str, providers: list[str]
) -> None:
    run = configured_run(**{field: providers})

    assert getattr(run.configuration, field) == providers
    assert WorkflowValidator().validate(_configured_definition(defense_workflow(), run)).valid


def test_live_fetch_nodes_never_use_a_fixture_fallback() -> None:
    graph = defense_workflow()
    next(node for node in graph.nodes if node.id == "market").retry.fallback_provider = "fixture"

    configured = _configured_definition(graph, configured_run())

    assert all(
        node.retry.fallback_provider is None
        for node in configured.nodes
        if node.type.startswith("fetch_")
    )
