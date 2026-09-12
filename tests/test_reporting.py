import asyncio
from datetime import UTC, datetime, timedelta
from io import BytesIO
from uuid import uuid4

from pypdf import PdfReader

from omnitrade.contracts import Run
from omnitrade.engine.executors import deterministic_executors
from omnitrade.engine.runtime import WorkflowRuntime
from omnitrade.reporting import build_detailed_report, render_pdf
from omnitrade.sample_workflow import defense_workflow


def test_pdf_report_contains_every_agent_stage() -> None:
    async def scenario():
        run = Run(
            workflow_version_id=uuid4(),
            owner_id=uuid4(),
            ticker="AAPL",
            as_of=datetime.now(UTC) - timedelta(minutes=1),
        )
        result = await WorkflowRuntime(deterministic_executors()).execute(defense_workflow(), run)
        nodes = {
            node_id: {"status": state.status.value, "output": state.output}
            for node_id, state in result.node_runs.items()
        }
        return build_detailed_report(nodes["report"]["output"], nodes, result.run)

    report = asyncio.run(scenario())
    assert len(report["agent_analyses"]) == 4
    assert len(report["risk_analyses"]) == 3
    assert report["research_debate"]["bull_case"]["key_points"]
    bull = report["research_debate"]["bull_case"]
    bear = report["research_debate"]["bear_case"]
    assert bull["support"] + bear["support"] == 1
    body = render_pdf(report)
    assert body.startswith(b"%PDF")
    assert len(body) > 5_000
    text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(body)).pages)
    assert "Specialist Analyst Views" in text
    assert "Bull and Bear Research Debate" in text
    assert "Support:" in text
    assert "Evidence confidence:" in text
    assert "Risk Team Views" in text
