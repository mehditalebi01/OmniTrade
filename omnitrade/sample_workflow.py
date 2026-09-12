from typing import Any

from omnitrade.contracts import (
    Budget,
    EdgeDefinition,
    FailurePolicy,
    NodeDefinition,
    WorkflowDefinition,
)


def defense_workflow() -> WorkflowDefinition:
    nodes = [
        n("start", "start"),
        n("split", "parallel_split"),
        n("instrument", "resolve_instrument"),
        n("market", "fetch_market", retry={"max_attempts": 2}),
        n("fundamentals", "fetch_fundamentals"),
        n("news", "fetch_news"),
        n("macro", "fetch_macro", optional=True),
        n("sentiment", "fetch_sentiment", optional=True),
        n("norm_market", "normalize_market"),
        n("norm_fund", "normalize_fundamentals"),
        n("norm_news", "normalize_text"),
        n("norm_macro", "normalize_text", optional=True),
        n("norm_sentiment", "normalize_text", optional=True),
        n("technical", "technical_indicators"),
        n("ratios", "fundamental_ratios"),
        n("evidence_join", "join", config={"join_policy": "required"}),
        n("time_guard", "time_guard", config={"max_age_hours": 72}),
        n("market_analyst", "market_analyst"),
        n("fundamental_analyst", "fundamental_analyst"),
        n("news_analyst", "news_analyst"),
        n("sentiment_analyst", "sentiment_analyst", optional=True),
        n("bull", "bull_researcher"),
        n("bear", "bear_researcher"),
        n("research", "research_manager"),
        n("debate", "bounded_loop", config={"max_iterations": 2}),
        n("proposal", "proposal_builder"),
        n("aggressive", "aggressive_risk"),
        n("balanced", "balanced_risk"),
        n("conservative", "conservative_risk"),
        n("risk_join", "risk_join"),
        n("decision", "decision_validator"),
        n("report", "report_renderer"),
        n("end", "end"),
    ]
    edges: list[EdgeDefinition] = []

    def e(source: str, source_port: str, target: str, target_port: str, loop: bool = False) -> None:
        edges.append(
            EdgeDefinition(
                id=f"e{len(edges) + 1}",
                source=source,
                source_port=source_port,
                target=target,
                target_port=target_port,
                loop=loop,
            )
        )

    e("start", "control", "split", "in")
    e("split", "out", "instrument", "control")
    for target in ("market", "fundamentals", "news", "macro", "sentiment"):
        e("instrument", "instrument", target, "instrument")
    e("market", "raw", "norm_market", "raw")
    e("fundamentals", "raw", "norm_fund", "raw")
    e("news", "raw", "norm_news", "raw")
    e("macro", "raw", "norm_macro", "raw")
    e("sentiment", "raw", "norm_sentiment", "raw")
    e("norm_market", "data", "technical", "data")
    e("norm_fund", "data", "ratios", "data")
    for source, port in (
        ("norm_market", "data"),
        ("norm_fund", "data"),
        ("norm_news", "data"),
        ("norm_macro", "data"),
        ("norm_sentiment", "data"),
        ("technical", "evidence"),
        ("ratios", "evidence"),
    ):
        e(source, port, "evidence_join", "items")
    e("evidence_join", "joined", "time_guard", "items")
    for analyst in ("market_analyst", "fundamental_analyst", "news_analyst", "sentiment_analyst"):
        e("time_guard", "evidence", analyst, "evidence")
    for analyst in ("market_analyst", "fundamental_analyst", "news_analyst", "sentiment_analyst"):
        e(analyst, "report", "bull", "reports")
        e(analyst, "report", "bear", "reports")
    e("bull", "case", "research", "cases")
    e("bear", "case", "research", "cases")
    e("research", "cases", "debate", "cases")
    e("debate", "cases", "research", "cases", loop=True)
    e("debate", "cases", "proposal", "cases")
    for risk in ("aggressive", "balanced", "conservative"):
        e("proposal", "proposal", risk, "proposal")
        e(risk, "view", "risk_join", "views")
    e("risk_join", "views", "decision", "views")
    e("decision", "decision", "report", "decision")
    e("report", "report", "end", "report")
    return WorkflowDefinition(
        name="Complete stock decision workflow",
        description="Defense workflow with parallel evidence, bounded debate, three risk views, recovery and lineage.",
        nodes=nodes,
        edges=edges,
        budget=Budget(max_model_calls=40, max_provider_calls=30, max_parallel_nodes=8),
    )


def n(
    node_id: str,
    node_type: str,
    *,
    config: dict[str, Any] | None = None,
    optional: bool = False,
    retry: dict[str, Any] | None = None,
) -> NodeDefinition:
    return NodeDefinition(
        id=node_id,
        type=node_type,
        name=node_id.replace("_", " ").title(),
        config=config or {},
        failure_policy=FailurePolicy.OPTIONAL if optional else FailurePolicy.REQUIRED,
        retry=retry or {},
    )
