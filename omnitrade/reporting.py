from __future__ import annotations

from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from omnitrade.contracts import Run

ANALYSTS = {
    "market_analyst": "Market Analyst",
    "fundamental_analyst": "Fundamental Analyst",
    "news_analyst": "News Analyst",
    "sentiment_analyst": "Sentiment Analyst",
}
RISKS = {
    "aggressive": "Aggressive Risk Analyst",
    "balanced": "Balanced Risk Analyst",
    "conservative": "Conservative Risk Analyst",
}


def build_detailed_report(
    base_report: dict[str, Any], nodes: dict[str, Any], run: Run
) -> dict[str, Any]:
    """Build the audit report from outputs produced by the executed workflow."""
    report = dict(base_report)
    analyst_views: list[dict[str, Any]] = []
    for node_id, name in ANALYSTS.items():
        output = _output(nodes, node_id)
        if not output:
            continue
        analyst_views.append(
            {
                "node_id": node_id,
                "agent": name,
                "viewpoint": output.get("viewpoint", "NEUTRAL"),
                "confidence": output.get("confidence", 0),
                "summary": output.get("summary", "No summary was produced."),
                "key_points": output.get("key_points", []),
                "risks": output.get("risks", []),
                "evidence_refs": output.get("evidence_refs", []),
            }
        )

    bull = _output(nodes, "bull")
    bear = _output(nodes, "bear")
    manager = _output(nodes, "research")
    proposal = _output(nodes, "proposal")
    risk_views: list[dict[str, Any]] = []
    for node_id, name in RISKS.items():
        output = _output(nodes, node_id)
        if output:
            risk_views.append(
                {
                    "node_id": node_id,
                    "agent": name,
                    "stance": output.get("stance", "NEUTRAL"),
                    "confidence": output.get("confidence", 0),
                    "summary": output.get("summary", "No summary was produced."),
                    "impact": output.get("impact", "No impact statement was produced."),
                    "key_points": output.get("key_points", []),
                }
            )

    evidence_items: list[dict[str, Any]] = []
    for node_id in ("market", "fundamentals", "news", "macro", "sentiment"):
        output = _output(nodes, node_id)
        if output:
            evidence_items.append(
                {
                    "source": node_id,
                    "status": str(nodes[node_id].get("status", "unknown")),
                    "summary": f"{output.get('provider', 'unknown')} evidence observed at {output.get('observed_at', 'unknown')}",
                    "content_hashes": _content_hashes(output),
                }
            )

    statuses = [
        str(item.get("status", "unknown")) for item in nodes.values() if isinstance(item, dict)
    ]
    report.update(
        {
            "agent_analyses": analyst_views,
            "research_debate": {
                "round_limit": run.configuration.research_depth,
                "bull_case": _case(bull, "Positive catalysts and upside evidence."),
                "bear_case": _case(bear, "Downside risks and uncertainty."),
                "manager_conclusion": manager.get(
                    "summary", "The research manager combined both cases."
                ),
                "agreement": manager.get("agreement", "Mixed evidence"),
            },
            "trading_proposal": {
                "action": proposal.get(
                    "action", report.get("decision", {}).get("action", "NO_DECISION")
                ),
                "confidence": proposal.get("confidence", 0),
                "summary": proposal.get("summary", "No proposal summary was produced."),
                "conditions": proposal.get("conditions", []),
            },
            "risk_analyses": risk_views,
            "evidence_overview": evidence_items,
            "workflow_summary": {
                "workflow_version_id": str(run.workflow_version_id),
                "trace_id": str(run.trace_id),
                "node_statuses": {
                    node_id: str(state.get("status", "unknown"))
                    for node_id, state in nodes.items()
                    if isinstance(state, dict)
                },
                "completed_nodes": statuses.count("succeeded"),
                "degraded_nodes": statuses.count("degraded"),
                "failed_nodes": statuses.count("failed"),
                "selected_agents": run.configuration.analysts,
            },
        }
    )
    return report


def _output(nodes: dict[str, Any], node_id: str) -> dict[str, Any]:
    state = nodes.get(node_id, {})
    output = state.get("output", {}) if isinstance(state, dict) else {}
    return output if isinstance(output, dict) else {}


def _case(output: dict[str, Any], fallback: str) -> dict[str, Any]:
    return {
        "agent": output.get("agent", "Research Agent"),
        "stance": output.get("stance", output.get("viewpoint", "NEUTRAL")),
        "summary": output.get("summary", fallback),
        "support": output.get("strength", output.get("confidence", 0)),
        "confidence": output.get("confidence", 0),
        "key_points": output.get("key_points", []),
        "counterpoints": output.get("risks_or_counters", []),
    }


def _content_hashes(value: Any) -> list[str]:
    if isinstance(value, dict):
        direct = value.get("content_hash")
        hashes = [str(direct)] if direct else []
        for child in value.values():
            hashes.extend(_content_hashes(child))
        return list(dict.fromkeys(hashes))
    if isinstance(value, list):
        list_hashes: list[str] = []
        for child in value:
            list_hashes.extend(_content_hashes(child))
        return list(dict.fromkeys(list_hashes))
    return []


def render_pdf(report: dict[str, Any]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="OmniTrade AI decision-support report",
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            parent=styles["Title"],
            fontSize=25,
            leading=30,
            textColor=colors.HexColor("#17233D"),
            alignment=TA_CENTER,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Section",
            parent=styles["Heading1"],
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#3F39A8"),
            spaceBefore=12,
            spaceAfter=8,
            keepWithNext=True,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Agent",
            parent=styles["Heading2"],
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#17233D"),
            spaceBefore=7,
            spaceAfter=4,
            keepWithNext=True,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["BodyText"],
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#536078"),
        )
    )
    story: list[Any] = []
    decision = report.get("decision", {})
    story.extend(
        [
            Spacer(1, 16 * mm),
            Paragraph("OmniTrade AI", styles["CoverTitle"]),
            Paragraph("Multi-Agent Financial Decision-Support Report", styles["Heading2"]),
            Spacer(1, 8 * mm),
            _summary_table(report, decision),
            Spacer(1, 8 * mm),
            Paragraph(
                _safe(report.get("executive_summary", "No executive summary.")), styles["BodyText"]
            ),
            Spacer(1, 4 * mm),
            Paragraph("Decision support only. No broker order is created.", styles["Small"]),
            PageBreak(),
            Paragraph("1. Final Decision", styles["Section"]),
            Paragraph(
                f"<b>Action:</b> {_safe(decision.get('action', 'NO_DECISION'))} &nbsp;&nbsp; <b>Confidence:</b> {_percent(decision.get('confidence', 0))}",
                styles["BodyText"],
            ),
            Paragraph(
                f"<b>Rationale:</b> {_safe(decision.get('rationale', 'No rationale.'))}",
                styles["BodyText"],
            ),
            _bullet_block("Key factors", decision.get("key_factors", []), styles),
            Paragraph("2. Specialist Analyst Views", styles["Section"]),
        ]
    )
    for agent in report.get("agent_analyses", []):
        story.extend(_agent_block(agent, styles))

    debate = report.get("research_debate", {})
    story.extend(
        [
            Paragraph("3. Bull and Bear Research Debate", styles["Section"]),
            _case_block(
                "Bull Researcher", debate.get("bull_case", {}), colors.HexColor("#E8F7ED"), styles
            ),
            _case_block(
                "Bear Researcher", debate.get("bear_case", {}), colors.HexColor("#FCEBEC"), styles
            ),
            Paragraph(
                f"<b>Research Manager:</b> {_safe(debate.get('manager_conclusion', 'No conclusion.'))}",
                styles["BodyText"],
            ),
        ]
    )

    proposal = report.get("trading_proposal", {})
    story.extend(
        [
            Paragraph("4. Trading Proposal", styles["Section"]),
            Paragraph(
                f"<b>{_safe(proposal.get('action', 'NO_DECISION'))}</b> ({_percent(proposal.get('confidence', 0))}) - {_safe(proposal.get('summary', 'No summary.'))}",
                styles["BodyText"],
            ),
            _bullet_block("Conditions", proposal.get("conditions", []), styles),
            Paragraph("5. Risk Team Views", styles["Section"]),
        ]
    )
    for risk in report.get("risk_analyses", []):
        story.extend(_risk_block(risk, styles))

    story.extend(
        [
            Paragraph("6. Evidence and Traceability", styles["Section"]),
            _evidence_table(report.get("evidence_overview", []), styles),
            Paragraph("7. Analysis Settings", styles["Section"]),
            _settings_table(report.get("analysis_settings", {}), styles),
            Spacer(1, 5 * mm),
            Paragraph(
                _safe(report.get("disclaimer", "Financial decision support only.")), styles["Small"]
            ),
        ]
    )
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def _summary_table(report: dict[str, Any], decision: dict[str, Any]) -> Table:
    data = [
        ["Ticker", _safe(report.get("ticker", "-")), "As of", _safe(report.get("as_of", "-"))],
        [
            "Decision",
            _safe(decision.get("action", "NO_DECISION")),
            "Confidence",
            _percent(decision.get("confidence", 0)),
        ],
    ]
    table = Table(data, colWidths=[28 * mm, 48 * mm, 28 * mm, 60 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F5FA")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#17233D")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8DEEA")),
                ("PADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def _agent_block(agent: dict[str, Any], styles: Any) -> list[Any]:
    content: list[Any] = [
        Paragraph(
            f"{_safe(agent.get('agent', 'Analyst'))} - {_safe(agent.get('viewpoint', 'NEUTRAL'))} ({_percent(agent.get('confidence', 0))})",
            styles["Agent"],
        ),
        Paragraph(_safe(agent.get("summary", "No summary.")), styles["BodyText"]),
        _bullet_block("Key points", agent.get("key_points", []), styles),
        _bullet_block("Risks", agent.get("risks", []), styles),
    ]
    return content


def _case_block(title: str, case: dict[str, Any], background: colors.Color, styles: Any) -> Table:
    support = case.get("support", case.get("confidence", 0))
    body = [
        Paragraph(
            f"<b>{_safe(title)}</b> - Support: {_percent(support)} | Evidence confidence: {_percent(case.get('confidence', 0))}",
            styles["BodyText"],
        ),
        Paragraph(_safe(case.get("summary", "No summary.")), styles["BodyText"]),
    ]
    for item in case.get("key_points", []):
        body.append(Paragraph(f"- {_safe(item)}", styles["Small"]))
    table = Table([[body]], colWidths=[164 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#CBD4E2")),
                ("PADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _risk_block(risk: dict[str, Any], styles: Any) -> list[Any]:
    return [
        Paragraph(
            f"{_safe(risk.get('agent', 'Risk Analyst'))} - {_safe(risk.get('stance', 'NEUTRAL'))} ({_percent(risk.get('confidence', 0))})",
            styles["Agent"],
        ),
        Paragraph(_safe(risk.get("summary", "No summary.")), styles["BodyText"]),
        Paragraph(
            f"<b>Impact on decision:</b> {_safe(risk.get('impact', 'No impact statement.'))}",
            styles["Small"],
        ),
    ]


def _bullet_block(title: str, values: Any, styles: Any) -> Any:
    items = values if isinstance(values, list) else []
    if not items:
        return Spacer(1, 1)
    return KeepTogether(
        [
            Paragraph(f"<b>{_safe(title)}:</b>", styles["Small"]),
            *[Paragraph(f"- {_safe(item)}", styles["Small"]) for item in items],
        ]
    )


def _evidence_table(items: list[dict[str, Any]], styles: Any) -> Table:
    data: list[list[Any]] = [["Source", "Status", "Evidence summary", "Content hash"]]
    for item in items:
        hashes = item.get("content_hashes", [])
        data.append(
            [
                _safe(item.get("source", "-")),
                _safe(item.get("status", "-")),
                Paragraph(_safe(item.get("summary", "-")), styles["Small"]),
                Paragraph(_safe(hashes[0] if hashes else "-")[:18] + "...", styles["Small"]),
            ]
        )
    table = Table(data, colWidths=[25 * mm, 38 * mm, 55 * mm, 46 * mm], repeatRows=1)
    table.setStyle(_table_style())
    return table


def _settings_table(settings: dict[str, Any], styles: Any) -> Table:
    data = [
        [
            Paragraph(f"<b>{_safe(key.replace('_', ' ').title())}</b>", styles["Small"]),
            Paragraph(
                _safe(", ".join(value) if isinstance(value, list) else value), styles["Small"]
            ),
        ]
        for key, value in settings.items()
    ]
    table = Table(data or [["Settings", "Unavailable"]], colWidths=[58 * mm, 106 * mm])
    table.setStyle(_table_style(header=False))
    return table


def _table_style(header: bool = True) -> TableStyle:
    commands: list[tuple[Any, ...]] = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D8DEEA")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3F39A8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    return TableStyle(commands)


def _footer(canvas: Any, doc: Any) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D8DEEA"))
    canvas.line(18 * mm, 12 * mm, 192 * mm, 12 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#667085"))
    canvas.drawString(18 * mm, 8 * mm, "OmniTrade AI - Decision support only")
    canvas.drawRightString(192 * mm, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _safe(value: Any) -> str:
    return escape(str(value))


def _percent(value: Any) -> str:
    try:
        return f"{float(value):.0%}"
    except (TypeError, ValueError):
        return "0%"
