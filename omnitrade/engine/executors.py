from __future__ import annotations

import asyncio
import hashlib
import json
import math
import statistics
from datetime import UTC, datetime, timedelta
from typing import Any

from omnitrade.contracts import NodeDefinition
from omnitrade.engine.catalog import NODE_CATALOG
from omnitrade.engine.runtime import ExecutionContext, NodeExecutor


async def deterministic_executor(
    node: NodeDefinition, inputs: dict[str, Any], context: ExecutionContext
) -> Any:
    """Fixture executor used in CI and the defense scenario."""
    delay_ms = int(node.config.get("delay_ms", 0))
    if delay_ms:
        await asyncio.sleep(min(delay_ms, 10_000) / 1000)
    if node.config.get("simulate") == "timeout" and "_fallback_provider" not in inputs:
        raise TimeoutError("primary provider timed out")
    if node.config.get("simulate") == "failure":
        raise RuntimeError("simulated optional source failure")

    spec = NODE_CATALOG[node.type]
    if spec.provider_cost:
        context.spend_provider_call()
        await asyncio.sleep(0.05)
    if spec.model_cost:
        context.spend_model_call(tokens=250)
        await asyncio.sleep(0.12)

    if node.type == "start":
        return {"started": True}
    if node.type == "resolve_instrument":
        return {"ticker": context.run.ticker, "exchange": "NASDAQ", "currency": "USD"}
    if node.type.startswith("fetch_"):
        return fixture_provider_payload(node.type, context.run.ticker, context.run.as_of)
    if node.type.startswith("normalize_"):
        raw = inputs.get("raw", inputs)
        return (
            {**raw, "normalized": True}
            if isinstance(raw, dict)
            else {"data": raw, "normalized": True}
        )
    if node.type == "join":
        return {"items": inputs.get("items", []), "joined": True}
    if node.type == "time_guard":
        evidence, warnings = _guard_evidence_time(
            inputs,
            context.run.as_of,
            int(node.config["max_age_hours"]),
            context.run.configuration.allow_degraded,
        )
        return {
            "items": evidence,
            "time_validated": True,
            "quality_warnings": warnings,
        }
    if node.type == "parallel_split":
        return {"split": True}
    if node.type == "technical_indicators":
        return _technical_indicators(inputs)
    if node.type == "fundamental_ratios":
        return _fundamental_ratios(inputs)
    if node.type.endswith("_analyst"):
        return _analyst_output(node.type, inputs, context.run.ticker)
    if node.type in {"bull_researcher", "bear_researcher"}:
        return _research_case(node.type == "bull_researcher", inputs)
    if node.type == "research_manager":
        bull_score = _position_score(inputs, "bull")
        bear_score = _position_score(inputs, "bear")
        return {
            "round": 1,
            "cases": inputs,
            "stopped": abs(bull_score - bear_score) >= 0.12,
            "agreement": f"Bull strength {bull_score:.2f}; bear strength {bear_score:.2f}.",
            "summary": "The research manager compares independent positive and negative evidence before a proposal is created.",
        }
    if node.type == "bounded_loop":
        previous = inputs.get("previous", {})
        previous_round = int(previous.get("round", 0)) if isinstance(previous, dict) else 0
        round_number = previous_round + 1
        return {
            "round": round_number,
            "cases": inputs.get("cases", inputs),
            "stopped": round_number >= int(node.config["max_iterations"]),
            "termination_reason": "configured debate bound reached"
            if round_number >= int(node.config["max_iterations"])
            else "another bounded comparison is allowed",
        }
    if node.type == "proposal_builder":
        bull_score = _position_score(inputs, "bull")
        bear_score = _position_score(inputs, "bear")
        net_score = max(0.0, min(1.0, 0.5 + (bull_score - bear_score) / 2))
        action = "BUY" if net_score >= 0.62 else "SELL" if net_score <= 0.38 else "HOLD"
        return {
            "action": action,
            "signal_score": round(net_score, 4),
            "confidence": round(min(0.92, 0.55 + abs(net_score - 0.5)), 4),
            "summary": f"The research evidence produces a {action} proposal with a combined signal of {net_score:.2f}.",
            "conditions": [
                "Reassess when prices, filings, or material news change.",
                "Do not treat this decision-support output as guaranteed performance.",
            ],
            "basis": inputs,
        }
    if node.type.endswith("_risk"):
        risk_profile = node.type.removesuffix("_risk")
        proposal = _find_first(inputs, "signal_score") or {}
        signal = float(proposal.get("signal_score", 0.5))
        thresholds = {
            "aggressive": (0.58, 0.42),
            "balanced": (0.62, 0.38),
            "conservative": (0.68, 0.32),
        }
        buy_at, sell_at = thresholds[risk_profile]
        policy = context.run.investor_policy
        if policy.maximum_loss_percent < 8:
            buy_at += 0.04
            sell_at -= 0.04
        if policy.investment_horizon == "long":
            buy_at -= 0.02
        elif policy.investment_horizon == "short":
            buy_at += 0.02
        stance = "ACCEPT" if signal >= buy_at or signal <= sell_at else "CAUTIOUS"
        return {
            "profile": risk_profile,
            "stance": stance,
            "confidence": round(0.55 + abs(signal - 0.5), 4),
            "summary": f"The {risk_profile} policy for a {policy.investment_horizon}-term investor requires BUY >= {buy_at:.2f} or SELL <= {sell_at:.2f}; the proposal signal is {signal:.2f}.",
            "impact": "The risk threshold can keep a weak directional proposal at HOLD.",
            "key_points": [f"Signal: {signal:.2f}", f"Policy range: {sell_at:.2f} to {buy_at:.2f}"],
            "proposal": inputs,
        }
    if node.type == "risk_join":
        return {"views": inputs}
    if node.type == "decision_validator":
        selected = context.run.configuration.risk_profile
        selected_view = next(
            (item for item in _all_dicts(inputs) if item.get("profile") == selected),
            {},
        )
        proposal = _find_first(inputs, "signal_score") or {}
        proposed_action = str(proposal.get("action", "HOLD"))
        action = proposed_action if selected_view.get("stance") == "ACCEPT" else "HOLD"
        signal = float(proposal.get("signal_score", 0.5))
        sector_item = _find_first(inputs, "sector") or {}
        sector = str(sector_item.get("sector") or "")
        excluded = {value.casefold() for value in context.run.investor_policy.excluded_sectors}
        sector_blocked = bool(sector and sector.casefold() in excluded)
        if sector_blocked:
            action = "HOLD"
        return {
            "action": action,
            "confidence": round(float(proposal.get("confidence", 0.5)), 4),
            "signal_score": round(signal, 4),
            "rationale": f"The {selected} user policy {'blocks the sector' if sector_blocked else 'accepts' if action == proposed_action else 'limits'} for the {proposed_action} proposal produced from live evidence.",
            "key_factors": [
                f"combined signal {signal:.2f}",
                f"selected risk policy {selected}",
                f"maximum position {context.run.investor_policy.maximum_position_percent:.0f}%",
                "bounded bull-bear research",
            ],
            "warnings": [
                "Financial decision support only",
                "Market data and model outputs can be incomplete or wrong",
            ]
            + ([f"Sector {sector} is excluded by the user policy"] if sector_blocked else []),
            "inputs": inputs,
        }
    if node.type == "report_renderer":
        decision = inputs.get("decision", inputs)
        if isinstance(decision, dict) and isinstance(decision.get("decision"), dict):
            decision = decision["decision"]
        configuration = context.run.configuration
        return {
            "report_version": "1.0",
            "title": f"OmniTrade report for {context.run.ticker}",
            "ticker": context.run.ticker,
            "as_of": context.run.as_of.isoformat(),
            "generated_at": datetime.now(UTC).isoformat(),
            "executive_summary": (
                f"OmniTrade recommends {decision.get('action', 'NO_DECISION')} with "
                f"{float(decision.get('confidence', 0)):.0%} confidence after parallel evidence, "
                "research debate, and three risk views."
            ),
            "decision": {
                "action": decision.get("action", "NO_DECISION"),
                "confidence": decision.get("confidence", 0),
                "rationale": decision.get("rationale", "No rationale was produced."),
                "key_factors": decision.get("key_factors", []),
                "warnings": decision.get("warnings", []),
            },
            "sections": [
                {
                    "title": "Market and technical analysis",
                    "summary": "Price evidence and technical indicators were normalized and reviewed.",
                },
                {
                    "title": "Fundamental analysis",
                    "summary": "Company data and financial ratios were checked as a separate evidence branch.",
                },
                {
                    "title": "News and sentiment",
                    "summary": "Text evidence was compared with market evidence when the selected analysts were enabled.",
                },
                {
                    "title": "Research debate",
                    "summary": f"Bull and bear cases used a bounded debate of up to {configuration.research_depth} rounds.",
                },
                {
                    "title": "Risk review",
                    "summary": f"Aggressive, neutral, and conservative views were merged for a {configuration.risk_profile} user profile.",
                },
            ],
            "analysis_settings": configuration.model_dump(mode="json"),
            "investor_policy": context.run.investor_policy.model_dump(mode="json"),
            "lineage_complete": True,
            "disclaimer": "Financial decision support only. OmniTrade does not execute trades.",
        }
    if node.type == "end":
        return inputs.get("report")
    return inputs


def fixture_provider_payload(kind: str, ticker: str, as_of: datetime) -> dict[str, Any]:
    ticker_bias = (sum(ord(char) for char in ticker) % 17 - 8) / 100
    base = 100 + sum(ord(char) for char in ticker) % 70
    payload = {
        "kind": kind,
        "ticker": ticker,
        "observed_at": (as_of - timedelta(hours=1)).astimezone(UTC).isoformat(),
        "retrieved_at": datetime.now(UTC).isoformat(),
        "provider": "omnitrade-fixture-v1",
        "currency": "USD",
        "unit": "provider-specific",
        "values": [round(base * (1 + ticker_bias * step / 20), 2) for step in range(30)],
    }
    payload["content_hash"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()
    return payload


def deterministic_executors() -> dict[str, NodeExecutor]:
    return {node_type: deterministic_executor for node_type in NODE_CATALOG}


def _content_hashes(value: Any) -> list[str]:
    found: list[str] = []

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            content_hash = item.get("content_hash")
            if isinstance(content_hash, str) and content_hash not in found:
                found.append(content_hash)
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return found


def _all_dicts(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            found.append(item)
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return found


def _find_first(value: Any, key: str) -> dict[str, Any] | None:
    return next((item for item in _all_dicts(value) if key in item), None)


def _validate_evidence_time(value: Any, as_of: datetime, max_age_hours: int) -> None:
    cutoff = as_of.astimezone(UTC)
    for item in _all_dicts(value):
        observed = item.get("observed_at")
        if not isinstance(observed, str):
            continue
        try:
            timestamp = datetime.fromisoformat(observed.replace("Z", "+00:00")).astimezone(UTC)
        except ValueError as exc:
            raise ValueError(f"Invalid evidence time: {observed}") from exc
        if timestamp > cutoff + timedelta(minutes=5):
            raise ValueError("Evidence is newer than the analysis time")
        kind = str(item.get("kind", ""))
        allowed_age = max_age_hours
        if kind == "fetch_fundamentals":
            allowed_age = max(allowed_age, 24 * 190)
        elif kind == "fetch_macro":
            allowed_age = max(allowed_age, 24 * 14)
        if cutoff - timestamp > timedelta(hours=allowed_age):
            raise ValueError(
                f"{kind or 'Evidence'} is older than its {allowed_age}-hour freshness rule"
            )


def _guard_evidence_time(
    inputs: dict[str, Any],
    as_of: datetime,
    max_age_hours: int,
    allow_degraded: bool,
) -> tuple[Any, list[str]]:
    """Reject unsafe core evidence and omit stale optional text evidence."""

    evidence = inputs.get("items", inputs)
    if not isinstance(evidence, dict) or not isinstance(evidence.get("items"), list):
        _validate_evidence_time(evidence, as_of, max_age_hours)
        return evidence, []

    kept: list[Any] = []
    warnings: list[str] = []
    degradable_kinds = {"fetch_news", "fetch_sentiment", "fetch_macro"}
    for branch in evidence["items"]:
        try:
            _validate_evidence_time(branch, as_of, max_age_hours)
        except ValueError as exc:
            kind_item = _find_first(branch, "kind")
            kind = str(kind_item.get("kind", "Evidence")) if kind_item else "Evidence"
            stale = "older than" in str(exc)
            if allow_degraded and stale and kind in degradable_kinds:
                warnings.append(f"{kind} was excluded because it is stale")
                continue
            raise
        kept.append(branch)
    return {**evidence, "items": kept}, warnings


def _technical_indicators(inputs: dict[str, Any]) -> dict[str, Any]:
    market = _find_first(inputs, "bars")
    if market:
        bars = market["bars"]
        closes = [float(item["close"]) for item in bars]
        volumes = [int(item["volume"]) for item in bars]
    else:
        values = _find_first(inputs, "values") or {}
        closes = [float(value) for value in values.get("values", [])]
        volumes = []
    if len(closes) < 2:
        raise ValueError("At least two prices are needed for technical analysis")
    returns = [
        current / previous - 1 for previous, current in zip(closes, closes[1:], strict=False)
    ]
    momentum = closes[-1] / closes[max(0, len(closes) - 21)] - 1
    sma20 = statistics.fmean(closes[-20:])
    sma50 = statistics.fmean(closes[-50:])
    gains = [max(value, 0) for value in returns[-14:]]
    losses = [max(-value, 0) for value in returns[-14:]]
    avg_gain = statistics.fmean(gains) if gains else 0
    avg_loss = statistics.fmean(losses) if losses else 0
    rsi = 100 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    volatility = statistics.pstdev(returns) * math.sqrt(252) if len(returns) > 1 else 0
    score = 0.5 + max(-0.2, min(0.2, momentum * 2))
    score += 0.1 if closes[-1] > sma20 else -0.1
    score += 0.05 if sma20 > sma50 else -0.05
    score += -0.05 if rsi > 75 else 0.05 if rsi < 30 else 0
    score = max(0.0, min(1.0, score))
    return {
        "kind": "technical_indicators",
        "signal_score": round(score, 4),
        "last_close": closes[-1],
        "momentum_20d": round(momentum, 4),
        "sma_20": round(sma20, 4),
        "sma_50": round(sma50, 4),
        "rsi_14": round(rsi, 2),
        "annualized_volatility": round(volatility, 4),
        "average_volume_20d": round(statistics.fmean(volumes[-20:]), 2) if volumes else None,
        "observations": len(closes),
        "source": inputs,
    }


def _fundamental_ratios(inputs: dict[str, Any]) -> dict[str, Any]:
    source = _find_first(inputs, "company")
    if not source:
        return {
            "kind": "fundamental_ratios",
            "signal_score": 0.5,
            "available_metrics": 0,
            "source": inputs,
        }
    company = source["company"]

    def number(name: str) -> float | None:
        try:
            value = company.get(name)
            return None if value in {None, "None", "-"} else float(value)
        except (TypeError, ValueError):
            return None

    pe = number("PERatio")
    margin = number("ProfitMargin")
    roe = number("ReturnOnEquityTTM")
    revenue_growth = number("RevenueGrowthTTM")
    earnings_growth = number("QuarterlyEarningsGrowthYOY")
    score_parts = [
        0.65 if pe is not None and 0 < pe <= 25 else 0.4 if pe is not None else 0.5,
        0.7
        if margin is not None and margin >= 0.15
        else 0.4
        if margin is not None and margin < 0
        else 0.5,
        0.7 if roe is not None and roe >= 0.15 else 0.45 if roe is not None else 0.5,
        0.7
        if revenue_growth is not None and revenue_growth > 0.08
        else 0.4
        if revenue_growth is not None and revenue_growth < 0
        else 0.5,
        0.7
        if earnings_growth is not None and earnings_growth > 0.08
        else 0.4
        if earnings_growth is not None and earnings_growth < 0
        else 0.5,
    ]
    metrics = {
        "pe_ratio": pe,
        "profit_margin": margin,
        "return_on_equity": roe,
        "revenue_growth": revenue_growth,
        "earnings_growth": earnings_growth,
    }
    return {
        "kind": "fundamental_ratios",
        "signal_score": round(statistics.fmean(score_parts), 4),
        "company_name": company.get("Name"),
        "sector": company.get("Sector"),
        "metrics": metrics,
        "available_metrics": sum(value is not None for value in metrics.values()),
        "source": inputs,
    }


def _analyst_output(node_type: str, inputs: dict[str, Any], ticker: str) -> dict[str, Any]:
    if node_type == "market_analyst":
        evidence = _find_first(inputs, "momentum_20d") or {}
        score = float(evidence.get("signal_score", 0.5))
        points = [
            f"20-day momentum: {float(evidence.get('momentum_20d', 0)):.2%}",
            f"RSI(14): {float(evidence.get('rsi_14', 50)):.1f}",
            f"Annualized volatility: {float(evidence.get('annualized_volatility', 0)):.2%}",
        ]
        risks = ["Price trends can reverse and historical volatility can change."]
    elif node_type == "fundamental_analyst":
        evidence = _find_first(inputs, "available_metrics") or {}
        score = float(evidence.get("signal_score", 0.5))
        metrics = evidence.get("metrics", {})
        points = [
            f"Sector: {evidence.get('sector')}",
            f"P/E ratio: {metrics.get('pe_ratio')}",
            f"Profit margin: {metrics.get('profit_margin')}",
            f"Revenue growth: {metrics.get('revenue_growth')}",
        ]
        risks = ["Current overview data may not include every filing or sector comparison."]
    else:
        evidence = _find_first(inputs, "articles") or {}
        articles = evidence.get("articles", [])
        scores = [
            float(item["sentiment_score"])
            for item in articles
            if item.get("sentiment_score") is not None
        ]
        average = statistics.fmean(scores) if scores else 0
        score = max(0.0, min(1.0, 0.5 + average / 2))
        points = [
            f"Articles reviewed: {len(articles)}",
            f"Average provider sentiment: {average:.3f}",
        ]
        points.extend(str(item.get("title")) for item in articles[:2])
        risks = ["News sentiment is noisy, time-sensitive, and may repeat the same event."]
    label = "BULLISH" if score >= 0.62 else "BEARISH" if score <= 0.38 else "NEUTRAL"
    confidence = min(0.9, 0.58 + abs(score - 0.5))
    summary = f"The {node_type.replace('_', ' ')} rates {ticker} as {label.lower()} from its available evidence, with a signal score of {score:.2f}."
    hashes = _content_hashes(inputs)
    result = {
        "specialist": node_type,
        "viewpoint": label,
        "signal_score": round(score, 4),
        "confidence": round(confidence, 4),
        "summary": summary,
        "key_points": points,
        "risks": risks,
        "evidence_refs": hashes,
        "claims": [
            {"text": point, "confidence": round(confidence, 4), "evidence_refs": hashes}
            for point in points
        ],
    }
    if node_type == "fundamental_analyst":
        result["sector"] = evidence.get("sector")
    return result


def _research_case(bull: bool, inputs: dict[str, Any]) -> dict[str, Any]:
    reports = [
        item for item in _all_dicts(inputs) if "specialist" in item and "signal_score" in item
    ]
    scores = [float(report["signal_score"]) for report in reports]
    mean_signal = statistics.fmean(scores) if scores else 0.5
    strength = mean_signal if bull else 1 - mean_signal
    directional_weights = [
        max(0.0, (score - 0.5) * 2) if bull else max(0.0, (0.5 - score) * 2) for score in scores
    ]
    weight_total = sum(directional_weights)
    if not reports:
        confidence = 0.0
    elif weight_total == 0:
        confidence = 0.2
    else:
        weighted_quality = (
            sum(
                weight * max(0.0, min(1.0, float(report.get("confidence", 0.5))))
                for report, weight in zip(reports, directional_weights, strict=True)
            )
            / weight_total
        )
        coverage = sum(weight > 0 for weight in directional_weights) / len(reports)
        directional_mass = weight_total / len(reports)
        confidence = min(
            0.95,
            0.5 * weighted_quality + 0.25 * coverage + 0.25 * directional_mass,
        )
    direction = "positive" if bull else "negative"
    ranked = sorted(reports, key=lambda item: float(item["signal_score"]), reverse=bull)
    points = [
        f"{item['specialist'].replace('_', ' ')}: {float(item['signal_score']):.2f}"
        for item in ranked[:3]
    ]
    return {
        "position": "bull" if bull else "bear",
        "strength": round(strength, 4),
        "confidence": round(confidence, 4),
        "summary": f"The {direction} case has support {strength:.2f} and evidence confidence {confidence:.2f} after comparing {len(reports)} specialist views.",
        "key_points": points or ["No specialist evidence was available."],
        "risks_or_counters": ["The opposing case must remain visible in the final decision."],
    }


def _position_score(inputs: dict[str, Any], position: str) -> float:
    case = next((item for item in _all_dicts(inputs) if item.get("position") == position), None)
    return float(case.get("strength", 0.5)) if case else 0.5
