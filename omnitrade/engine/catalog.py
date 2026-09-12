from dataclasses import dataclass

from omnitrade.contracts import PortType


@dataclass(frozen=True)
class NodeSpec:
    group: str
    inputs: dict[str, PortType]
    outputs: dict[str, PortType]
    provider_cost: int = 0
    model_cost: int = 0
    side_effect: bool = False
    required_config: tuple[str, ...] = ()


def _spec(
    group: str, ins: dict[str, PortType], outs: dict[str, PortType], **kwargs: object
) -> NodeSpec:
    return NodeSpec(group, ins, outs, **kwargs)  # type: ignore[arg-type]


NODE_CATALOG: dict[str, NodeSpec] = {
    # Control (5)
    "start": _spec("control", {}, {"control": PortType.CONTROL}),
    "end": _spec("control", {"report": PortType.REPORT}, {}),
    "parallel_split": _spec("control", {"in": PortType.CONTROL}, {"out": PortType.CONTROL}),
    "join": _spec(
        "control",
        {"items": PortType.EVIDENCE_SET},
        {"joined": PortType.EVIDENCE_SET},
        required_config=("join_policy",),
    ),
    "bounded_loop": _spec(
        "control",
        {"cases": PortType.RESEARCH_CASES},
        {"cases": PortType.RESEARCH_CASES},
        required_config=("max_iterations",),
    ),
    # Evidence (6)
    "resolve_instrument": _spec(
        "evidence", {"control": PortType.CONTROL}, {"instrument": PortType.INSTRUMENT}
    ),
    "fetch_market": _spec(
        "evidence",
        {"instrument": PortType.INSTRUMENT},
        {"raw": PortType.RAW_MARKET},
        provider_cost=1,
    ),
    "fetch_fundamentals": _spec(
        "evidence",
        {"instrument": PortType.INSTRUMENT},
        {"raw": PortType.RAW_FUNDAMENTALS},
        provider_cost=1,
    ),
    "fetch_news": _spec(
        "evidence", {"instrument": PortType.INSTRUMENT}, {"raw": PortType.RAW_TEXT}, provider_cost=1
    ),
    "fetch_macro": _spec(
        "evidence", {"instrument": PortType.INSTRUMENT}, {"raw": PortType.RAW_TEXT}, provider_cost=1
    ),
    "fetch_sentiment": _spec(
        "evidence", {"instrument": PortType.INSTRUMENT}, {"raw": PortType.RAW_TEXT}, provider_cost=1
    ),
    # Normalization/calculation (6)
    "normalize_market": _spec(
        "normalization", {"raw": PortType.RAW_MARKET}, {"data": PortType.NORMALIZED_MARKET}
    ),
    "normalize_fundamentals": _spec(
        "normalization",
        {"raw": PortType.RAW_FUNDAMENTALS},
        {"data": PortType.NORMALIZED_FUNDAMENTALS},
    ),
    "normalize_text": _spec(
        "normalization", {"raw": PortType.RAW_TEXT}, {"data": PortType.NORMALIZED_TEXT}
    ),
    "time_guard": _spec(
        "normalization",
        {"items": PortType.EVIDENCE_SET},
        {"evidence": PortType.EVIDENCE_SET},
        required_config=("max_age_hours",),
    ),
    "technical_indicators": _spec(
        "calculation", {"data": PortType.NORMALIZED_MARKET}, {"evidence": PortType.EVIDENCE}
    ),
    "fundamental_ratios": _spec(
        "calculation", {"data": PortType.NORMALIZED_FUNDAMENTALS}, {"evidence": PortType.EVIDENCE}
    ),
    # Specialist analysis (4)
    "market_analyst": _spec(
        "specialist",
        {"evidence": PortType.EVIDENCE_SET},
        {"report": PortType.SPECIALIST_REPORT},
        model_cost=1,
    ),
    "fundamental_analyst": _spec(
        "specialist",
        {"evidence": PortType.EVIDENCE_SET},
        {"report": PortType.SPECIALIST_REPORT},
        model_cost=1,
    ),
    "news_analyst": _spec(
        "specialist",
        {"evidence": PortType.EVIDENCE_SET},
        {"report": PortType.SPECIALIST_REPORT},
        model_cost=1,
    ),
    "sentiment_analyst": _spec(
        "specialist",
        {"evidence": PortType.EVIDENCE_SET},
        {"report": PortType.SPECIALIST_REPORT},
        model_cost=1,
    ),
    # Research (4)
    "bull_researcher": _spec(
        "research",
        {"reports": PortType.SPECIALIST_REPORTS},
        {"case": PortType.RESEARCH_CASE},
        model_cost=1,
    ),
    "bear_researcher": _spec(
        "research",
        {"reports": PortType.SPECIALIST_REPORTS},
        {"case": PortType.RESEARCH_CASE},
        model_cost=1,
    ),
    "research_manager": _spec(
        "research",
        {"cases": PortType.RESEARCH_CASES},
        {"cases": PortType.RESEARCH_CASES},
        model_cost=1,
    ),
    "proposal_builder": _spec(
        "research",
        {"cases": PortType.RESEARCH_CASES},
        {"proposal": PortType.PROPOSAL},
        model_cost=1,
    ),
    # Risk (5)
    "aggressive_risk": _spec(
        "risk", {"proposal": PortType.PROPOSAL}, {"view": PortType.RISK_VIEW}, model_cost=1
    ),
    "balanced_risk": _spec(
        "risk", {"proposal": PortType.PROPOSAL}, {"view": PortType.RISK_VIEW}, model_cost=1
    ),
    "conservative_risk": _spec(
        "risk", {"proposal": PortType.PROPOSAL}, {"view": PortType.RISK_VIEW}, model_cost=1
    ),
    "risk_join": _spec("risk", {"views": PortType.RISK_VIEWS}, {"views": PortType.RISK_VIEWS}),
    "decision_validator": _spec(
        "risk", {"views": PortType.RISK_VIEWS}, {"decision": PortType.DECISION}
    ),
    # Output (1)
    "report_renderer": _spec(
        "output",
        {"decision": PortType.DECISION},
        {"report": PortType.REPORT},
        model_cost=1,
        side_effect=True,
    ),
}

assert len(NODE_CATALOG) == 31


NODE_DESCRIPTIONS: dict[str, str] = {
    "start": "Starts the workflow and sends the first control signal.",
    "end": "Closes the workflow after the final report is ready.",
    "parallel_split": "Opens several branches so data tasks can run at the same time.",
    "join": "Waits for connected evidence branches and combines their results.",
    "bounded_loop": "Repeats the research debate, but stops at the configured round limit.",
    "resolve_instrument": "Checks the stock ticker and creates one verified instrument identity.",
    "fetch_market": "Collects raw price and volume data for the selected stock.",
    "fetch_fundamentals": "Collects company statements and financial values.",
    "fetch_news": "Collects recent company and market news from available providers.",
    "fetch_macro": "Collects economic information that may affect the stock or its sector.",
    "fetch_sentiment": "Collects public sentiment signals about the selected stock.",
    "normalize_market": "Converts market data into one clean and consistent format.",
    "normalize_fundamentals": "Cleans financial values and makes their units and currency consistent.",
    "normalize_text": "Cleans text evidence and gives news, macro, or sentiment a common format.",
    "time_guard": "Rejects future or stale evidence before it reaches the analyst agents.",
    "technical_indicators": "Calculates technical signals from normalized market data.",
    "fundamental_ratios": "Calculates financial ratios used to study company quality and value.",
    "market_analyst": "Explains price trends, technical signals, uncertainty, and market risks.",
    "fundamental_analyst": "Explains the company's financial strength, value, and weaknesses.",
    "news_analyst": "Explains how recent news and economic events may affect the stock.",
    "sentiment_analyst": "Explains public mood and warns when sentiment evidence is weak or noisy.",
    "bull_researcher": "Builds the positive case using analyst reports and possible growth factors.",
    "bear_researcher": "Builds the negative case using risks, weak evidence, and downside factors.",
    "research_manager": "Compares both research cases and records their agreement and conflicts.",
    "proposal_builder": "Turns the research result into a clear BUY, HOLD, or SELL proposal.",
    "aggressive_risk": "Reviews the proposal for a user who accepts higher risk for higher reward.",
    "balanced_risk": "Reviews the proposal by balancing possible reward and possible loss.",
    "conservative_risk": "Reviews the proposal with strong focus on loss prevention and uncertainty.",
    "risk_join": "Combines the three risk views before the final decision check.",
    "decision_validator": "Checks that the decision agrees with evidence, risk rules, and confidence limits.",
    "report_renderer": "Builds the final readable report with agent views and evidence links.",
}

assert NODE_DESCRIPTIONS.keys() == NODE_CATALOG.keys()


COLLECTION_COMPATIBILITY: set[tuple[PortType, PortType]] = {
    (PortType.EVIDENCE, PortType.EVIDENCE_SET),
    (PortType.NORMALIZED_MARKET, PortType.EVIDENCE_SET),
    (PortType.NORMALIZED_FUNDAMENTALS, PortType.EVIDENCE_SET),
    (PortType.NORMALIZED_TEXT, PortType.EVIDENCE_SET),
    (PortType.SPECIALIST_REPORT, PortType.SPECIALIST_REPORTS),
    (PortType.RESEARCH_CASE, PortType.RESEARCH_CASES),
    (PortType.RISK_VIEW, PortType.RISK_VIEWS),
}


def ports_compatible(source: PortType, target: PortType) -> bool:
    return source == target or (source, target) in COLLECTION_COMPATIBILITY
