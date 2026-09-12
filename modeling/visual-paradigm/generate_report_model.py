"""Generate the Visual Paradigm model that mirrors Figures 1-6 and 14-21.

The report is the diagram inventory.  This generator deliberately does not
produce a separate architecture atlas.  It reuses the current code-derived
views where they answer the same report question and adds the missing Agile,
use-case, package, pipeline, communication, validator, and scheduler views.
"""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from pathlib import Path

from generate_model import (
    DRAWINGS,
    OUT,
    PALETTE,
    PREVIEWS,
    SOURCES,
    Boundary,
    Canvas,
    Edge,
    Node,
    build_xmi,
    domain_contracts,
    deployment,
    manifest,
    master_system,
    render_svg,
    render_vdx,
    sequence,
    service_architecture,
    state_machine,
    validate_routes,
    plantuml_for,
)
from omnitrade.engine.catalog import NODE_CATALOG
from omnitrade.sample_workflow import defense_workflow


ROOT = Path(__file__).resolve().parents[2]


def canvas(name: str, title: str, width: int, height: int, subtitle: str) -> Canvas:
    return Canvas(name=name, title=title, width=width, height=height, subtitle=subtitle)


def route(c: Canvas, key: str, points: list[tuple[float, float]], label: str = "", *, color: str | None = None, dashed: bool = False, label_at: tuple[float, float] | None = None) -> None:
    c.edge(key, points, label, color or PALETTE["gray"], dashed, True, label_at)


def rename(c: Canvas, name: str, title: str, subtitle: str) -> Canvas:
    c.name = name
    c.title = title
    c.subtitle = subtitle
    return c


def use_case() -> Canvas:
    c = canvas(
        "F01_Expanded_Use_Case",
        "Figure 1 - Expanded use-case model of the implemented product boundary",
        2700,
        1660,
        "Latest UI/API behavior, profile defaults, investor-policy risk controls, provider/model connections, validation, pause/recovery, lineage, export, and explicit no-broker boundary.",
    )
    c.boundary("OmniTrade AI - explainable financial decision support", 360, 35, 1870, 1435, PALETTE["blue"], "#FBFCFF")

    user = c.node("actor_user", "Registered analyst", ["Owns profile, workflows, runs, reports"], 30, 270, 250, 105, PALETTE["blue_fill"], PALETTE["blue"], "actor")
    maint = c.node("actor_maint", "Student maintainer / operator", ["Deploys, verifies, diagnoses, resumes"], 30, 790, 250, 115, PALETTE["purple_fill"], PALETTE["purple"], "actor")
    professor = c.node("actor_professor", "Professor / reviewer", ["Evaluates process, owned complexity, evidence"], 30, 1250, 250, 105, PALETTE["amber_fill"], PALETTE["amber"], "actor")
    data_provider = c.node("actor_data", "Market / news / macro providers", ["yfinance, Alpha Vantage, Finnhub", "FRED, Polygon, NewsAPI, Frankfurter"], 2320, 300, 330, 125, PALETTE["green_fill"], PALETTE["green"], "actor")
    model_provider = c.node("actor_model", "Model API providers", ["AWS Bedrock, Anthropic, OpenAI-compatible", "User connection selects approved model"], 2320, 760, 330, 125, PALETTE["purple_fill"], PALETTE["purple"], "actor")
    no_broker = c.note("no_broker", "OUT OF SCOPE", ["No broker orders", "No account control", "No autonomous execution"], 2320, 1230, 330, 130, PALETTE["red_fill"], PALETTE["red"], "constraint")

    auth = c.node("uc_auth", "Authenticate and maintain session", ["Login/logout", "Ownership-scoped requests"], 440, 220, 390, 105, PALETTE["blue_fill"], PALETTE["blue"], "usecase")
    profile = c.node("uc_profile", "Manage profile", ["Analysis defaults and investor policy", "Name/email are identity only"], 440, 390, 390, 115, PALETTE["blue_fill"], PALETTE["blue"], "usecase")
    connections = c.node("uc_connections", "Configure provider and model connections", ["Provider chains and credentials", "Model/provider routing policy"], 440, 575, 390, 115, PALETTE["green_fill"], PALETTE["green"], "usecase")
    analysis = c.node("uc_analysis", "Configure a new analysis", ["Ticker/date/analysts/depth", "risk/report/reasoning/currency", "budgets, retries, freshness, concurrency"], 440, 770, 390, 135, PALETTE["cyan_fill"], PALETTE["cyan"], "usecase")
    workflow = c.node("uc_workflow", "Design workflow in Workflow Lab", ["Edit typed 31-node catalog graph", "Validate, publish immutable version"], 440, 985, 390, 120, PALETTE["purple_fill"], PALETTE["purple"], "usecase")
    ops = c.node("uc_ops", "Deploy and verify release", ["Compose health, migrations, tests", "Deterministic providers/models in CI"], 440, 1200, 390, 115, PALETTE["amber_fill"], PALETTE["amber"], "usecase")

    validate = c.node("uc_validate", "Validate configuration and graph", ["Pydantic bounds and enum matrix", "types, ports, reachability, cycles", "declared loops, joins, side effects, budget"], 970, 250, 430, 140, PALETTE["amber_fill"], PALETTE["amber"], "usecase")
    run = c.node("uc_run", "Create and start an analysis run", ["Persist owner/config/version snapshot", "Clear fixture fallback for live providers"], 970, 500, 430, 120, PALETTE["blue_fill"], PALETTE["blue"], "usecase")
    monitor = c.node("uc_monitor", "Use Run History and Agent Room", ["Observe, pause, cancel, or resume", "Checkpoint restores completed outputs"], 970, 735, 430, 120, PALETTE["purple_fill"], PALETTE["purple"], "usecase")
    report = c.node("uc_report", "Review explainable decision report", ["Decision, confidence, warnings", "specialists, debate, risk views"], 970, 970, 430, 120, PALETTE["green_fill"], PALETTE["green"], "usecase")
    lineage = c.node("uc_lineage", "Inspect lineage and export output", ["Evidence IDs, citations, hashes", "JSON / HTML / PDF artifacts"], 970, 1205, 430, 120, PALETTE["teal_fill"], PALETTE["teal"], "usecase")

    evidence = c.node("uc_evidence", "Acquire and normalize live evidence", ["Real-provider fallback chains", "HTTP/connection failure classification", "schema, time guard, quality, FX"], 1570, 260, 500, 145, PALETTE["green_fill"], PALETTE["green"], "usecase")
    agents = c.node("uc_agents", "Execute specialist and debate agents", ["Market/fundamental/news/sentiment", "bull/bear bounded debate", "control node repeats; agents are not multiplied"], 1570, 515, 500, 145, PALETTE["purple_fill"], PALETTE["purple"], "usecase")
    risk = c.node("uc_risk", "Apply risk policy and decision validation", ["Aggressive/balanced/conservative views", "protected fields and deterministic checks"], 1570, 775, 500, 130, PALETTE["orange_fill"], PALETTE["orange"], "usecase")
    assemble = c.node("uc_assemble", "Assemble report and archive trace", ["Claim-to-evidence lineage", "warnings/limitations and run identifiers", "decision support only"], 1570, 1020, 500, 140, PALETTE["teal_fill"], PALETTE["teal"], "usecase")

    policy = c.node("uc_policy", "Define investment policy", ["horizon + experience", "max loss + max position", "excluded sectors"], 900, 55, 430, 130, PALETTE["orange_fill"], PALETTE["orange"], "usecase")
    model_defaults = c.node("uc_model_defaults", "Select default AI models", ["verified provider", "quick model + deep model", "prefills New Analysis"], 1500, 55, 430, 130, PALETTE["purple_fill"], PALETTE["purple"], "usecase")

    # Actor links use reserved outer corridors and enter their nearest use cases.
    route(c, "u_auth", [user.right, (330, user.right[1]), (330, auth.left[1]), auth.left], "session", color=PALETTE["blue"], label_at=(305, 238))
    route(c, "u_profile", [user.right, (315, user.right[1]), (315, profile.left[1]), profile.left], "defaults/policy", color=PALETTE["blue"], label_at=(290, 410))
    route(c, "u_analysis", [user.right, (300, user.right[1]), (300, analysis.left[1]), analysis.left], "analysis request", color=PALETTE["blue"], label_at=(280, 785))
    route(c, "m_workflow", [maint.right, (325, maint.right[1]), (325, workflow.left[1]), workflow.left], "owned graph", color=PALETTE["purple"], label_at=(300, 1000))
    route(c, "m_ops", [maint.right, (310, maint.right[1]), (310, ops.left[1]), ops.left], "release evidence", color=PALETTE["purple"], label_at=(285, 1220))
    route(c, "p_report", [professor.right, (320, professor.right[1]), (320, 1390), (920, 1390), (920, report.left[1]), report.left], "inspect result", color=PALETTE["amber"], label_at=(835, 1360))
    route(c, "p_lineage", [professor.right, (300, professor.right[1]), (300, 1415), (900, 1415), (900, lineage.left[1]), lineage.left], "audit evidence", color=PALETTE["amber"], label_at=(815, 1390))
    route(c, "dp_evidence", [data_provider.left, (2180, data_provider.left[1]), (2180, evidence.right[1]), evidence.right], "typed HTTP responses", color=PALETTE["green"], label_at=(2070, 285))
    route(c, "mp_agents", [model_provider.left, (2160, model_provider.left[1]), (2160, agents.right[1]), agents.right], "prompt / structured draft", color=PALETTE["purple"], label_at=(2050, 735))
    route(c, "out_scope", [assemble.right, (2260, assemble.right[1]), (2260, no_broker.left[1]), no_broker.left], "no interface", color=PALETTE["red"], dashed=True, label_at=(2180, 1178))

    # Include/extend relations stay inside horizontal/vertical gutters.
    route(c, "analysis_validate", [analysis.right, (900, analysis.right[1]), (900, validate.left[1]), validate.left], "<<include>> validation", dashed=True, color=PALETTE["cyan"], label_at=(845, 690))
    route(c, "workflow_validate", [workflow.right, (880, workflow.right[1]), (880, validate.left[1]), validate.left], "<<include>> publish checks", dashed=True, color=PALETTE["purple"], label_at=(835, 930))
    route(c, "validate_run", [validate.bottom, (validate.bottom[0], 445), (run.top[0], 445), run.top], "accepted snapshot", color=PALETTE["amber"], label_at=(1140, 420))
    route(c, "run_evidence", [run.right, (1490, run.right[1]), (1490, evidence.left[1]), evidence.left], "RunConfig + trace_id", color=PALETTE["blue"], label_at=(1415, 475))
    route(c, "evidence_agents", [evidence.bottom, (evidence.bottom[0], 465), (agents.top[0], 465), agents.top], "EvidenceBundle", color=PALETTE["green"], label_at=(1790, 438))
    route(c, "agents_risk", [agents.bottom, (agents.bottom[0], 720), (risk.top[0], 720), risk.top], "proposal + debate", color=PALETTE["purple"], label_at=(1790, 690))
    route(c, "risk_assemble", [risk.bottom, (risk.bottom[0], 965), (assemble.top[0], 965), assemble.top], "validated decision", color=PALETTE["orange"], label_at=(1785, 935))
    route(c, "run_monitor", [run.bottom, (run.bottom[0], 680), (monitor.top[0], 680), monitor.top], "events/checkpoints", color=PALETTE["blue"], label_at=(1135, 653))
    route(c, "assemble_report", [assemble.left, (1490, assemble.left[1]), (1490, report.right[1]), report.right], "Report + artifacts", color=PALETTE["teal"], label_at=(1410, 1000))
    route(c, "report_lineage", [report.bottom, (report.bottom[0], 1150), (lineage.top[0], 1150), lineage.top], "<<include>>", dashed=True, color=PALETTE["teal"], label_at=(1160, 1125))
    route(c, "monitor_resume", [monitor.left, (900, monitor.left[1]), (900, 1145), (workflow.bottom[0], 1145), workflow.bottom], "<<extend>> resume failed/interrupted", dashed=True, color=PALETTE["purple"], label_at=(705, 1115))
    route(c, "profile_policy", [profile.right, (860, profile.right[1]), (860, 205), (policy.left[0] - 35, 205), (policy.left[0] - 35, policy.left[1]), policy.left], "<<include>>", dashed=True, color=PALETTE["orange"], label_at=(800, 185))
    route(c, "profile_models", [profile.right, (850, profile.right[1]), (850, 205), (model_defaults.left[0] - 35, 205), (model_defaults.left[0] - 35, model_defaults.left[1]), model_defaults.left], "<<include>>", dashed=True, color=PALETTE["purple"], label_at=(1370, 185))
    route(c, "connections_models", [connections.right, (880, connections.right[1]), (880, 220), (model_defaults.left[0] - 55, 220), (model_defaults.left[0] - 55, model_defaults.left[1]), model_defaults.left], "verified models", dashed=True, color=PALETTE["green"], label_at=(1325, 220))
    route(c, "policy_risk", [policy.right, (1450, policy.right[1]), (1450, risk.left[1]), risk.left], "deep-copied into run; used by risk agents", dashed=True, color=PALETTE["orange"], label_at=(1420, 730))
    route(c, "defaults_analysis", [model_defaults.bottom, (model_defaults.bottom[0], 205), (1450, 205), (1450, 940), (analysis.right[0] + 40, 940), (analysis.right[0] + 40, analysis.right[1]), analysis.right], "prefill; user may override", dashed=True, color=PALETTE["purple"], label_at=(1380, 920))
    return c


def agile_cycle() -> Canvas:
    c = canvas("F02_Agile_Incremental_Cycle", "Figure 2 - Agile incremental cycle with XP engineering practices", 2500, 820, "Agile governs value and adaptation; XP supplies the engineering practices inside each small increment.")
    stages = [
        ("select", "Select value", ["story + acceptance criteria", "planning game"], PALETTE["blue_fill"], PALETTE["blue"]),
        ("analyze", "Analyze and design", ["simple typed contract", "spike only for uncertainty"], PALETTE["gray_fill"], PALETTE["gray"]),
        ("implement", "Implement", ["small change", "lead + reviewer rotation"], PALETTE["gray_fill"], PALETTE["gray"]),
        ("verify", "Verify", ["tests + static checks", "fake models / recorded providers"], PALETTE["green_fill"], PALETTE["green"]),
        ("integrate", "Integrate", ["working main baseline", "continuous integration"], PALETTE["gray_fill"], PALETTE["gray"]),
        ("review", "Review", ["user + professor feedback", "demonstrate evidence"], PALETTE["amber_fill"], PALETTE["amber"]),
        ("reflect", "Reflect", ["limits + improvements", "refactor without behavior drift"], PALETTE["purple_fill"], PALETTE["purple"]),
        ("adapt", "Adapt next increment", ["reprioritize story", "keep acceptance boundary"], PALETTE["blue_fill"], PALETTE["blue"]),
    ]
    nodes: list[Node] = []
    for idx, (key, title, lines, fill, stroke) in enumerate(stages):
        nodes.append(c.node(key, title, lines, 80 + idx * 300, 110, 250, 125, fill, stroke, "activity"))
    for idx in range(len(nodes) - 1):
        route(c, f"flow_{idx}", [nodes[idx].right, nodes[idx + 1].left], "")
    route(c, "feedback", [nodes[-1].bottom, (nodes[-1].bottom[0], 350), (nodes[0].bottom[0], 350), nodes[0].bottom], "feedback changes the next story; it never bypasses verification", color=PALETTE["blue"], label_at=(920, 325))
    values = [
        ("communication", "Communication", "shared contracts + daily review"),
        ("simplicity", "Simplicity", "small typed slices; no speculative services"),
        ("feedback_v", "Feedback", "tests, UI evidence, demonstrations"),
        ("courage", "Courage", "expose gaps and refactor"),
        ("respect", "Respect", "collective ownership and review"),
    ]
    for idx, (key, title, text) in enumerate(values):
        c.node(key, title, [text], 175 + idx * 465, 430, 360, 90, PALETTE["white"], PALETTE["line"], "note")
    c.note("agile_note", "Implemented process boundary", ["Eight cumulative increments; stories and acceptance conditions drive work.", "XP is the chosen engineering framework inside the Agile incremental process."], 460, 620, 1580, 100, PALETTE["cyan_fill"], PALETTE["cyan"], "note")
    return c


def ci_pipeline() -> Canvas:
    c = canvas("F03_XP_CI_Pipeline", "Figure 3 - XP verification and Continuous Integration pipeline", 2200, 1120, "Compact two-row pipeline: fast feedback before integration and inspectable evidence after a green main branch.")
    stages = [
        ("story", "Story + acceptance", ["observable behavior", "contract impact"]),
        ("pair", "Lead + reviewer", ["small change", "shared ownership"]),
        ("unit", "Unit + contract tests", ["validator, runtime, providers", "reports and configuration matrix"]),
        ("static", "Static checks", ["Ruff + mypy", "TypeScript checks"]),
        ("integration", "Integration tests", ["API, storage, events", "checkpoint recovery"]),
        ("frontend", "Frontend verification", ["Vitest + production build", "Playwright smoke path"]),
        ("container", "Container checks", ["Compose configuration", "health + migration startup"]),
        ("baseline", "Integrated baseline", ["review evidence", "next story feedback"]),
    ]
    nodes: list[Node] = []
    positions = [(100, 100), (590, 100), (1080, 100), (1570, 100), (1570, 330), (1080, 330), (590, 330), (100, 330)]
    for idx, ((key, title, lines), (x, y)) in enumerate(zip(stages, positions)):
        fill = PALETTE["blue_fill"] if idx in (0, 7) else PALETTE["white"]
        stroke = PALETTE["blue"] if idx in (0, 7) else PALETTE["gray"]
        nodes.append(c.node(key, title, lines, x, y, 390, 135, fill, stroke, "activity"))
    for idx in range(3):
        route(c, f"ci_top_{idx}", [nodes[idx].right, nodes[idx + 1].left])
    route(c, "ci_turn", [nodes[3].bottom, nodes[4].top])
    for idx in range(4, 7):
        route(c, f"ci_bottom_{idx}", [nodes[idx].left, nodes[idx + 1].right])
    c.boundary("Verification gates", 80, 550, 2040, 280, PALETTE["gray"], "#FCFCFD")
    gates = [
        ("fast", "Fast feedback", ["Unit or contract failure", "stops the change."]),
        ("deterministic", "Deterministic boundary", ["Recorded providers + fake models", "remove live-service variance."]),
        ("regression", "Regression control", ["Configuration matrix covers", "options and provider chains."]),
        ("release", "Release evidence", ["Build, containers, migrations,", "and scenario artifacts stay inspectable."]),
    ]
    gate_positions = [(130, 630), (650, 630), (1170, 630), (1690, 630)]
    for (key, title, lines), (x, y) in zip(gates, gate_positions):
        c.node(key, title, lines, x, y, 380, 110, PALETTE["white"], PALETTE["line"], "note")
    route(c, "ci_feedback", [nodes[-1].left, (45, nodes[-1].left[1]), (45, 45), (nodes[0].top[0], 45), nodes[0].top], "failed gate returns to the smallest responsible change; green baseline informs the next story", color=PALETTE["blue"], label_at=(760, 30))
    c.note("ci_boundary", "Evidence boundary", ["The repository proves automated checks and reproducible configuration.", "It does not claim that every historical decision was test-first."], 330, 920, 1540, 100, PALETTE["gray_fill"], PALETTE["gray"], "note")
    return c


def timing_model() -> Canvas:
    c = canvas("F04_Increment_Timing_Model", "Figure 4 - Reconstructed function-point timing model", 2400, 1200, "Planning estimate only: 200 planned hours / 100 relative function points = 2.00 planned hours per relative FP.")
    items = [
        ("i1", "I1 Walking skeleton", ["20 planned hours", "10 relative FP", "2.00 h / relative FP"]),
        ("i2", "I2 Safe workflow design", ["28 planned hours", "16 relative FP", "1.75 h / relative FP"]),
        ("i3", "I3 Event execution", ["34 planned hours", "18 relative FP", "1.89 h / relative FP"]),
        ("i4", "I4 Trusted evidence", ["28 planned hours", "14 relative FP", "2.00 h / relative FP"]),
        ("i5", "I5 Typed analysis", ["24 planned hours", "12 relative FP", "2.00 h / relative FP"]),
        ("i6", "I6 Decision workflow", ["28 planned hours", "15 relative FP", "1.87 h / relative FP"]),
        ("i7", "I7 Explainable product", ["22 planned hours", "10 relative FP", "2.20 h / relative FP"]),
        ("i8", "I8 Release evidence", ["16 planned hours", "5 relative FP", "3.20 h / relative FP"]),
    ]
    nodes: list[Node] = []
    positions = [(100, 220), (650, 220), (1200, 220), (1750, 220), (1750, 500), (1200, 500), (650, 500), (100, 500)]
    for (key, title, lines), (x, y) in zip(items, positions):
        fill = PALETTE["blue_fill"] if key in ("i1", "i8") else PALETTE["white"]
        nodes.append(c.node(key, title, lines, x, y, 420, 150, fill, PALETTE["blue"] if key in ("i1", "i8") else PALETTE["gray"], "component"))
    for idx in range(3):
        route(c, f"top_{idx}", [nodes[idx].right, nodes[idx + 1].left])
    route(c, "down", [nodes[3].bottom, nodes[4].top])
    for idx in range(4, 7):
        route(c, f"bottom_{idx}", [nodes[idx].left, nodes[idx + 1].right])
    c.boundary("Function-point interpretation", 90, 780, 2220, 300, PALETTE["gray"], "#FCFCFD")
    groups = [
        ("ei", "External interaction", ["inputs, outputs, and inquiries through UI and API"]),
        ("data", "Data functions", ["workflows, versions, runs, events, evidence, reports, artifacts"]),
        ("interfaces", "External interfaces", ["providers, model gateway, PostgreSQL and Redis"]),
        ("complexity", "Owned control complexity", ["validation, scheduling, joins, failure, checkpoint, lineage"]),
    ]
    for idx, (key, title, lines) in enumerate(groups):
        c.node(key, title, lines, 150 + idx * 545, 850, 480, 130, PALETTE["white"], PALETTE["line"], "note")
    return c


def package_dependencies() -> Canvas:
    c = canvas("F14_Package_Dependencies", "Figure 14 - Package and module dependency model", 2600, 1450, "Arrows show compile-time or call-level use. The browser stays behind the typed API; runtime logic stays behind service and contract boundaries.")
    c.boundary("frontend/src", 80, 160, 580, 1120, PALETTE["blue"], "#FBFCFF")
    c.boundary("omnitrade application", 760, 160, 1750, 1120, PALETTE["purple"], "#FDFCFF")
    c.boundary("engine", 1410, 470, 1010, 670, PALETTE["orange"], "#FFFCF8")
    login = c.node("p_pages", "React pages and components", ["Login, Overview, New Analysis", "Agent Room, Reports, Workflow Lab", "Profile, Connections"], 150, 260, 430, 145, PALETTE["blue_fill"], PALETTE["blue"], "package")
    api_ts = c.node("p_api_ts", "api.ts", ["typed HTTP methods", "nested backend error formatting"], 150, 540, 430, 120, PALETTE["blue_fill"], PALETTE["blue"], "package")
    types_ts = c.node("p_types_ts", "types.ts", ["request/response and UI view types"], 150, 820, 430, 105, PALETTE["blue_fill"], PALETTE["blue"], "package")
    rf = c.node("p_react_flow", "React Flow workflow canvas", ["catalog palette + typed graph lifecycle"], 150, 1060, 430, 105, PALETTE["blue_fill"], PALETTE["blue"], "package")

    api = c.node("p_api", "api.py", ["authentication, ownership, public /api/v1 routes", "RunConfig validation and live fallback clearing"], 830, 245, 460, 135, PALETTE["purple_fill"], PALETTE["purple"], "package")
    services = c.node("p_services", "services.py", ["workflow/run/evidence/model/report orchestration", "ProviderError -> safe HTTP 502"], 830, 500, 460, 125, PALETTE["purple_fill"], PALETTE["purple"], "package")
    contracts = c.node("p_contracts", "contracts.py", ["Pydantic domain and boundary contracts"], 830, 760, 460, 110, PALETTE["amber_fill"], PALETTE["amber"], "package")
    storage = c.node("p_storage", "storage.py + db.py + migrations", ["owner-scoped repositories", "PostgreSQL persistence and immutable versions"], 830, 1010, 460, 125, PALETTE["teal_fill"], PALETTE["teal"], "package")

    runtime = c.node("p_runtime", "engine/runtime.py", ["stable ready set, bounded parallel batch", "retry/fallback, failure, checkpoint, resume"], 1480, 540, 390, 135, PALETTE["orange_fill"], PALETTE["orange"], "package")
    validator = c.node("p_validator", "engine/validator.py", ["types, ports, reachability, cycle/loop", "joins, side effects, evidence, actual model-call budget"], 1960, 540, 390, 145, PALETTE["orange_fill"], PALETTE["orange"], "package")
    catalog = c.node("p_catalog", "engine/catalog.py", [f"{len(NODE_CATALOG)} node types", "groups, ports, required config, side effects"], 1480, 815, 390, 125, PALETTE["orange_fill"], PALETTE["orange"], "package")
    executors = c.node("p_executors", "engine/executors.py", ["node dispatch and typed executor boundary"], 1960, 815, 390, 105, PALETTE["orange_fill"], PALETTE["orange"], "package")
    providers = c.node("p_providers", "providers.py + connections.py", ["real-provider chains, no fixture live", "classification, normalization, Frankfurter FX"], 1480, 245, 390, 135, PALETTE["green_fill"], PALETTE["green"], "package")
    model = c.node("p_model", "model_gateway.py + remote_executor.py", ["approved model routing, structured draft", "downstream error detail preserved"], 1960, 245, 390, 135, PALETTE["purple_fill"], PALETTE["purple"], "package")
    reporting = c.node("p_reporting", "reporting.py", ["JSON/HTML/PDF assembly", "warnings, evidence, lineage, artifacts"], 1480, 1010, 870, 115, PALETTE["teal_fill"], PALETTE["teal"], "package")

    route(c, "pages_api", [login.bottom, (login.bottom[0], 470), (api_ts.top[0], 470), api_ts.top], "calls")
    route(c, "api_types", [api_ts.bottom, (api_ts.bottom[0], 740), (types_ts.top[0], 740), types_ts.top], "uses")
    route(c, "flow_api", [rf.left, (90, rf.left[1]), (90, api_ts.left[1]), api_ts.left], "workflow API", label_at=(105, 980))
    route(c, "http", [api_ts.right, (710, api_ts.right[1]), (710, api.left[1]), api.left], "/api/v1 JSON", color=PALETTE["blue"], label_at=(660, 430))
    route(c, "api_services", [api.bottom, (api.bottom[0], 440), (services.top[0], 440), services.top], "delegates", color=PALETTE["purple"])
    route(c, "api_contracts", [api.right, (1340, api.right[1]), (1340, contracts.top[1] - 60), (contracts.top[0], contracts.top[1] - 60), contracts.top], "validates request", color=PALETTE["amber"], label_at=(1210, 670))
    route(c, "services_storage", [services.right, (1360, services.right[1]), (1360, storage.right[1]), storage.right], "repositories", label_at=(1285, 900))
    route(c, "services_runtime", [services.right, (1360, services.right[1]), (1360, runtime.left[1]), runtime.left], "execute")
    route(c, "services_provider", [services.top, (services.top[0], 430), (providers.left[0] - 60, 430), (providers.left[0] - 60, providers.left[1]), providers.left], "evidence request", color=PALETTE["green"], label_at=(1300, 400))
    route(c, "services_model", [api.top, (api.top[0], 110), (model.top[0], 110), model.top], "connection/model routing", color=PALETTE["purple"], label_at=(1450, 80))
    route(c, "runtime_validator", [runtime.right, (1915, runtime.right[1]), (1915, validator.left[1]), validator.left], "validate before schedule", color=PALETTE["orange"])
    route(c, "runtime_catalog", [runtime.bottom, (runtime.bottom[0], 750), (catalog.top[0], 750), catalog.top], "node definitions")
    route(c, "runtime_executors", [runtime.right, (1915, runtime.right[1]), (1915, executors.top[1] - 50), (executors.top[0], executors.top[1] - 50), executors.top], "dispatch")
    route(c, "validator_catalog", [validator.bottom, (validator.bottom[0], 760), (catalog.right[0] + 45, 760), (catalog.right[0] + 45, catalog.right[1]), catalog.right], "catalog rules")
    route(c, "executors_provider", [executors.right, (2480, executors.right[1]), (2480, 120), (providers.top[0], 120), providers.top], "adapter call", color=PALETTE["green"], label_at=(1550, 90))
    route(c, "executors_model", [executors.right, (2460, executors.right[1]), (2460, model.right[1]), model.right], "model call", color=PALETTE["purple"], label_at=(2370, 410))
    route(c, "services_reporting", [services.right, (1370, services.right[1]), (1370, reporting.left[1]), reporting.left], "assemble output", color=PALETTE["teal"], label_at=(1300, 950))
    route(c, "report_storage", [reporting.left, (1370, reporting.left[1]), (1370, storage.right[1]), storage.right], "persist artifacts", color=PALETTE["teal"], label_at=(1300, 1080))
    return c


def analysis_pipeline() -> Canvas:
    c = canvas("F16_Analysis_Pipeline", "Figure 16 - Analysis pipeline: stages, gates, parallelism, and recovery", 3000, 1550, "A stage advances only when contracts and policy gates pass; current configuration and provider semantics are explicit.")
    stages = [
        ("configure", "1. Configure", ["ticker/date/roles/depth", "risk/report/reasoning/currency", "budgets/retries/freshness/concurrency"]),
        ("validate", "2. Validate", ["Pydantic bounds + enum matrix", "types/ports/reachability/cycles", "loops/joins/side effects/budget"]),
        ("publish", "3. Publish", ["immutable workflow version", "catalog snapshot + content hash"]),
        ("create", "4. Create run", ["owner + RunConfig snapshot", "900 s default; bounded values", "clear fixture fallback for live"]),
        ("collect", "5. Collect evidence", ["parallel real-provider chains", "classify HTTP/network failures", "normalize + time guard + Frankfurter FX"]),
        ("analyze", "6. Analyze", ["selected specialist agents", "typed EvidenceBundle inputs", "structured, protected outputs"]),
        ("debate", "7. Debate", ["bull/bear/rebuttal/proposal", "bounded control loop only", "upstream agents not multiplied"]),
        ("risk", "8. Risk", ["three risk views", "policy limits + deterministic fields"]),
        ("decide", "9. Decide", ["decision validation", "confidence + warnings + limitations"]),
        ("report", "10. Report", ["views + lineage", "JSON/HTML/PDF artifacts", "decision support; no broker"]),
    ]
    nodes: list[Node] = []
    for idx, (key, title, lines) in enumerate(stages):
        nodes.append(c.node(key, title, lines, 45 + idx * 290, 190, 255, 160, PALETTE["blue_fill"] if idx in (0, 9) else PALETTE["white"], PALETTE["blue"] if idx in (0, 9) else PALETTE["gray"], "activity"))
    for idx in range(len(nodes) - 1):
        route(c, f"pipe_{idx}", [nodes[idx].right, nodes[idx + 1].left], "")
    gates = ["Configuration accepted", "Graph valid", "Version frozen", "Run owned", "Evidence usable", "Roles complete", "Loop bound reached", "Risk set complete", "Decision valid", "Archive written"]
    for idx, text in enumerate(gates):
        gate = c.node(f"gate_{idx}", text, [], 70 + idx * 290, 430, 205, 75, PALETTE["gray_fill"], PALETTE["line"], "decision")
        route(c, f"gate_link_{idx}", [nodes[idx].bottom, gate.top], "", dashed=True)
    c.boundary("Cross-cutting owned execution controls", 110, 620, 2780, 330, PALETTE["gray"], "#FCFCFD")
    controls = [
        ("ready", "Stable ready-set scheduler", ["sorted node IDs; max_parallel_nodes"]),
        ("event", "Monotonic event protocol", ["sequence, run/node IDs, status, trace"]),
        ("checkpoint", "Checkpoint writer", ["completed outputs + loop state"]),
        ("failure", "Failure classifier", ["retry / fallback / degraded / failed"]),
        ("resume", "Resume planner", ["skip completed; recompute remaining"]),
    ]
    for idx, (key, title, lines) in enumerate(controls):
        c.node(key, title, lines, 170 + idx * 545, 720, 460, 130, PALETTE["white"], PALETTE["line"], "component")
    recoverable = c.node("recoverable", "RECOVERABLE", ["Transient provider/model error -> bounded retry", "Provider chain -> next real provider", "Optional node -> degraded run + warning"], 120, 1110, 810, 180, PALETTE["red_fill"], PALETTE["red"], "state")
    resumable = c.node("resumable", "RESUMABLE", ["Persist checkpoint -> restore completed outputs", "Reset incomplete nodes to pending", "Resume readiness -> continue remaining nodes"], 1095, 1110, 810, 180, PALETTE["blue_fill"], PALETTE["blue"], "state")
    terminal = c.node("terminal", "TERMINAL", ["Required node failure -> FAILED", "Safe-point cancellation -> CANCELLED", "All required paths -> COMPLETED / DEGRADED"], 2070, 1110, 810, 180, PALETTE["gray_fill"], PALETTE["gray"], "state")
    route(c, "control_recover", [c.by_key("failure").bottom, (c.by_key("failure").bottom[0], 1030), (recoverable.top[0], 1030), recoverable.top], "classified failure", color=PALETTE["red"], label_at=(480, 1002))
    route(c, "control_resume", [c.by_key("resume").bottom, (c.by_key("resume").bottom[0], 1030), (resumable.top[0], 1030), resumable.top], "checkpoint/recovery", color=PALETTE["blue"], label_at=(1380, 1010))
    route(c, "control_terminal", [c.by_key("ready").bottom, (c.by_key("ready").bottom[0], 1010), (terminal.top[0], 1010), terminal.top], "terminal selection", color=PALETTE["gray"], label_at=(2290, 990))
    return c


def communication() -> Canvas:
    c = canvas("F17_Communication_Collaboration", "Figure 17 - UML communication diagram for one analysis run", 2750, 1550, "Numbered messages show responsibility allocation; object links use reserved gutters and never pass through another object.")
    ui = c.node("comm_ui", ":New Analysis UI", ["bounded form + readable API errors"], 100, 190, 360, 110, PALETTE["blue_fill"], PALETTE["blue"], "lifeline")
    api = c.node("comm_api", ":API / RunService", ["ownership + RunConfig validation"], 620, 190, 360, 110, PALETTE["purple_fill"], PALETTE["purple"], "lifeline")
    validator = c.node("comm_validator", ":Catalog + WorkflowValidator", ["configuration, graph, budget"], 1140, 190, 410, 110, PALETTE["amber_fill"], PALETTE["amber"], "lifeline")
    repo = c.node("comm_repo", ":Repository + EventLog", ["run/version/event/checkpoint"], 1770, 190, 410, 110, PALETTE["teal_fill"], PALETTE["teal"], "lifeline")
    room = c.node("comm_room", ":Agent Room / Reports", ["events, state, report, lineage"], 100, 650, 360, 110, PALETTE["blue_fill"], PALETTE["blue"], "lifeline")
    scheduler = c.node("comm_scheduler", ":Readiness Scheduler", ["stable ready set + bounded batch"], 620, 650, 360, 110, PALETTE["orange_fill"], PALETTE["orange"], "lifeline")
    evidence = c.node("comm_evidence", ":Evidence Gateway", ["real provider chains + FX + quality"], 1140, 650, 410, 110, PALETTE["green_fill"], PALETTE["green"], "lifeline")
    specialists = c.node("comm_specialists", ":Specialist Pool", ["market/fundamental/news/sentiment"], 1770, 650, 410, 110, PALETTE["purple_fill"], PALETTE["purple"], "lifeline")
    debate = c.node("comm_debate", ":Debate + Proposal", ["bounded control loop; protected draft"], 1770, 1080, 410, 110, PALETTE["purple_fill"], PALETTE["purple"], "lifeline")
    risk = c.node("comm_risk", ":Risk + Decision", ["three views + deterministic validation"], 1140, 1080, 410, 110, PALETTE["orange_fill"], PALETTE["orange"], "lifeline")
    report = c.node("comm_report", ":Report Builder", ["explanation + evidence lineage + artifacts"], 620, 1080, 360, 110, PALETTE["teal_fill"], PALETTE["teal"], "lifeline")

    route(c, "m1", [ui.right, api.left], "1 createRun(config, workflowVersion)", color=PALETTE["blue"], label_at=(470, 160))
    route(c, "m11", [api.right, validator.left], "1.1 validate(config, graph, policy)", color=PALETTE["amber"], label_at=(990, 160))
    route(c, "m12", [validator.right, repo.left], "1.2 persist snapshot + initial event", color=PALETTE["teal"], label_at=(1565, 160))
    route(c, "m2", [api.bottom, (api.bottom[0], 510), (scheduler.top[0], 510), scheduler.top], "2 scheduleReady(run)", color=PALETTE["orange"], label_at=(1040, 480))
    route(c, "m21", [scheduler.right, evidence.left], "2.1 collect and normalize evidence", color=PALETTE["green"], label_at=(995, 620))
    route(c, "m22", [evidence.right, specialists.left], "2.2 execute selected specialists", color=PALETTE["purple"], label_at=(1560, 620))
    route(c, "m23", [evidence.top, (evidence.top[0], 470), (repo.bottom[0] - 80, 470), (repo.bottom[0] - 80, repo.bottom[1]), repo.bottom], "2.3 append ordered events + checkpoint", color=PALETTE["teal"], label_at=(1300, 440))
    route(c, "m3", [specialists.bottom, (specialists.bottom[0], 930), (debate.top[0], 930), debate.top], "3 bounded debate + proposal", color=PALETTE["purple"], label_at=(2200, 900))
    route(c, "m4", [debate.left, risk.right], "4 apply risk policy + validate", color=PALETTE["orange"], label_at=(1545, 1050))
    route(c, "m5", [risk.left, report.right], "5 assemble report + trace", color=PALETTE["teal"], label_at=(995, 1050))
    route(c, "m51", [risk.top, (risk.top[0], 980), (repo.right[0] + 90, 980), (repo.right[0] + 90, repo.bottom[1] + 40), (repo.bottom[0], repo.bottom[1] + 40), repo.bottom], "5.1 persist report/artifacts/checkpoint", color=PALETTE["teal"], label_at=(1800, 950))
    route(c, "m6", [report.left, (520, report.left[1]), (520, room.right[1]), room.right], "6 expose report, lineage, activity", color=PALETTE["blue"], label_at=(760, 1000))
    route(c, "m61", [room.top, (room.top[0], 430), (ui.bottom[0], 430), ui.bottom], "6.1 poll/stream visible state", color=PALETTE["blue"], label_at=(470, 400))
    c.note("comm_note", "Message contract", ["Every exchange carries owner_id, run_id, workflow_version_id, node/event identity, trace_id, and typed payload where applicable.", "No communication creates a brokerage order."], 350, 1320, 1950, 115, PALETTE["gray_fill"], PALETTE["gray"], "note")
    return c


def validator_activity() -> Canvas:
    c = canvas("F19_Validator_Activity", "Figure 19 - Validator activity for publication and run preparation", 2400, 1650, "Stable issue IDs are returned without executing the workflow. Latest configuration and corrected budget rules are included.")
    start = c.node("v_start", "Start", [], 80, 180, 80, 80, PALETTE["navy"], PALETTE["navy"], "start")
    steps = [
        ("load", "Load WorkflowDefinition", ["index nodes; normalize reverse adjacency"]),
        ("boundary", "Check graph boundary", ["exactly one start and one end"]),
        ("config", "Validate analysis configuration", ["all analyst/depth/risk/report/reasoning", "language/currency/provider-chain combinations", "clamped numeric ranges and required connection fields"]),
        ("catalog", "Validate catalog and node config", [f"known type from {len(NODE_CATALOG)}-node catalog", "required per-node configuration"]),
        ("ports", "Check typed ports", ["source/target compatibility", "required input cardinality"]),
        ("reach", "Check reachability", ["every required node reachable from start"]),
        ("cycle", "Check cycles and declared loops", ["Kahn cycle check", "only declared bounded control loops accepted"]),
        ("joins", "Check joins and side effects", ["join completeness", "effect restrictions + idempotency"]),
        ("budget", "Check budgets and evidence policy", ["actual model nodes x retry allowance", "research depth does not multiply whole graph", "live fetch has no fixture fallback"]),
    ]
    positions = [(260, 150), (720, 150), (1180, 150), (1730, 150), (1730, 480), (1260, 480), (790, 480), (320, 480), (790, 820)]
    nodes: list[Node] = []
    for (key, title, lines), (x, y) in zip(steps, positions):
        nodes.append(c.node(key, title, lines, x, y, 390 if key != "config" else 480, 145 if key != "config" else 175, PALETTE["white"], PALETTE["gray"], "activity"))
    route(c, "vs", [start.right, (210, start.right[1]), (210, nodes[0].left[1]), nodes[0].left])
    route(c, "v1", [nodes[0].right, nodes[1].left])
    route(c, "v2", [nodes[1].right, (1145, nodes[1].right[1]), (1145, nodes[2].left[1]), nodes[2].left])
    route(c, "v3", [nodes[2].right, (1695, nodes[2].right[1]), (1695, nodes[3].left[1]), nodes[3].left])
    route(c, "v4", [nodes[3].bottom, (nodes[3].bottom[0], 420), (nodes[4].top[0], 420), nodes[4].top])
    route(c, "v5", [nodes[4].left, nodes[5].right])
    route(c, "v6", [nodes[5].left, nodes[6].right])
    route(c, "v7", [nodes[6].left, nodes[7].right])
    route(c, "v8", [nodes[7].bottom, (nodes[7].bottom[0], 740), (nodes[8].left[0] - 80, 740), (nodes[8].left[0] - 80, nodes[8].left[1]), nodes[8].left])
    decision = c.node("issues", "Issues?", ["ordered by stable issue ID"], 1320, 870, 260, 110, PALETTE["amber_fill"], PALETTE["amber"], "decision")
    invalid = c.node("invalid", "Invalid definition", ["return ordered errors and warnings", "do not persist publication or create run"], 700, 1130, 470, 145, PALETTE["red_fill"], PALETTE["red"], "state")
    valid = c.node("valid", "Valid definition", ["allow immutable publication", "allow run snapshot only after request validation"], 1600, 1130, 470, 145, PALETTE["blue_fill"], PALETTE["blue"], "state")
    end_bad = c.node("end_bad", "End", [], 900, 1390, 80, 80, PALETTE["navy"], PALETTE["navy"], "end")
    end_ok = c.node("end_ok", "End", [], 1800, 1390, 80, 80, PALETTE["navy"], PALETTE["navy"], "end")
    route(c, "v9", [nodes[8].right, (1230, nodes[8].right[1]), (1230, decision.left[1]), decision.left])
    route(c, "yes", [decision.left, (1220, decision.left[1]), (1220, invalid.top[1] - 60), (invalid.top[0], invalid.top[1] - 60), invalid.top], "yes", color=PALETTE["red"], label_at=(1130, 1015))
    route(c, "no", [decision.right, (1660, decision.right[1]), (1660, valid.top[1] - 60), (valid.top[0], valid.top[1] - 60), valid.top], "no", color=PALETTE["blue"], label_at=(1625, 1015))
    route(c, "bad_end", [invalid.bottom, (invalid.bottom[0], 1340), (end_bad.top[0], 1340), end_bad.top])
    route(c, "ok_end", [valid.bottom, (valid.bottom[0], 1340), (end_ok.top[0], 1340), end_ok.top])
    return c


def scheduler_activity() -> Canvas:
    c = canvas("F20_Readiness_Scheduler_Activity", "Figure 20 - Deterministic readiness scheduler activity", 2450, 1700, "Sorted readiness, bounded parallel batches, classified failure, monotonic events, checkpointing, cancellation, completion, and resume.")
    start = c.node("s_start", "Start / Resume", [], 80, 120, 100, 80, PALETTE["navy"], PALETTE["navy"], "start")
    steps = [
        ("restore", "Create or restore NodeRun states", ["completed outputs remain immutable", "load loop state and latest checkpoint"]),
        ("cancel_check", "Check cancellation signal", ["before each batch and after each completion"]),
        ("ready", "Compute ready set", ["pending nodes whose required predecessors are acceptable"]),
        ("sort", "Sort and cap batch", ["stable node identifier", "max_parallel_nodes"]),
        ("inputs", "Assemble typed inputs", ["stable edge order + execution context"]),
        ("execute", "Execute batch", ["async gather with timeout", "bounded retry and real-provider fallback"]),
        ("classify", "Classify results", ["succeeded / degraded / failed / interrupted"]),
        ("persist", "Persist events + checkpoint", ["monotonic sequence", "completed outputs + loop state"]),
    ]
    nodes: list[Node] = []
    for idx, (key, title, lines) in enumerate(steps):
        nodes.append(c.node(key, title, lines, 300, 100 + idx * 175, 520, 125, PALETTE["white"], PALETTE["gray"], "activity"))
    route(c, "ss", [start.right, (240, start.right[1]), (240, nodes[0].left[1]), nodes[0].left])
    for idx in range(len(nodes) - 1):
        route(c, f"sf_{idx}", [nodes[idx].bottom, (nodes[idx].bottom[0], nodes[idx + 1].top[1] - 25), (nodes[idx + 1].top[0], nodes[idx + 1].top[1] - 25), nodes[idx + 1].top])
    cancel_dec = c.node("cancel", "Cancel requested?", [], 1050, 280, 280, 100, PALETTE["amber_fill"], PALETTE["amber"], "decision")
    ready_dec = c.node("ready_empty", "Ready set empty?", [], 1050, 590, 280, 100, PALETTE["amber_fill"], PALETTE["amber"], "decision")
    terminal_dec = c.node("terminal_dec", "Terminal?", [], 1050, 1230, 280, 100, PALETTE["amber_fill"], PALETTE["amber"], "decision")
    cancelled = c.node("cancelled", "CANCELLED", ["safe cancellation point", "checkpoint remains resumable"], 1580, 220, 560, 145, PALETTE["blue_fill"], PALETTE["blue"], "state")
    interrupted = c.node("interrupted", "FAILED / INTERRUPTED", ["required failure or recovery process stop", "stable reason and trace retained"], 1580, 545, 560, 145, PALETTE["red_fill"], PALETTE["red"], "state")
    completed = c.node("completed", "COMPLETED / DEGRADED", ["all required paths terminal", "optional failure may remain with warning"], 1580, 1160, 560, 145, PALETTE["green_fill"], PALETTE["green"], "state")
    end = c.node("s_end", "End", [], 2210, 1185, 80, 80, PALETTE["navy"], PALETTE["navy"], "end")
    route(c, "to_cancel", [nodes[1].right, (930, nodes[1].right[1]), (930, cancel_dec.left[1]), cancel_dec.left])
    route(c, "cancel_yes", [cancel_dec.right, (1450, cancel_dec.right[1]), (1450, cancelled.left[1]), cancelled.left], "yes", color=PALETTE["blue"], label_at=(1390, 265))
    route(c, "cancel_no", [cancel_dec.bottom, (cancel_dec.bottom[0], 500), (nodes[2].right[0] + 90, 500), (nodes[2].right[0] + 90, nodes[2].right[1]), nodes[2].right], "no", color=PALETTE["gray"], label_at=(940, 470))
    route(c, "to_ready", [nodes[2].right, (930, nodes[2].right[1]), (930, ready_dec.left[1]), ready_dec.left])
    route(c, "deadlock", [ready_dec.right, (1460, ready_dec.right[1]), (1460, interrupted.left[1]), interrupted.left], "yes: deadlock or required failure", color=PALETTE["red"], label_at=(1370, 555))
    route(c, "ready_no", [ready_dec.bottom, (ready_dec.bottom[0], 750), (nodes[3].right[0] + 90, 750), (nodes[3].right[0] + 90, nodes[3].right[1]), nodes[3].right], "no", label_at=(940, 720))
    route(c, "to_terminal", [nodes[-1].right, (950, nodes[-1].right[1]), (950, terminal_dec.left[1]), terminal_dec.left])
    route(c, "terminal_yes", [terminal_dec.right, (1460, terminal_dec.right[1]), (1460, completed.left[1]), completed.left], "yes", color=PALETTE["green"], label_at=(1410, 1190))
    route(c, "terminal_no", [terminal_dec.top, (terminal_dec.top[0], 1110), (880, 1110), (880, nodes[2].top[1] - 45), (nodes[2].top[0], nodes[2].top[1] - 45), nodes[2].top], "no - recompute readiness", color=PALETTE["gray"], label_at=(850, 1070))
    route(c, "cancel_end", [cancelled.right, (2220, cancelled.right[1]), (2220, end.top[1] - 80), (end.top[0], end.top[1] - 80), end.top])
    route(c, "interrupt_end", [interrupted.right, (2240, interrupted.right[1]), (2240, end.top[1] - 60), (end.top[0], end.top[1] - 60), end.top])
    route(c, "complete_end", [completed.right, (2175, completed.right[1]), (2175, end.left[1]), end.left])
    c.note("resume_note", "Resume invariant", ["Resume loads the latest checkpoint, keeps completed outputs, resets incomplete states to pending, and re-enters readiness.", "Declared loop state is restored; completed nodes are not repeated."], 1280, 1430, 950, 130, PALETTE["gray_fill"], PALETTE["gray"], "note")
    return c


def object_snapshot() -> Canvas:
    c = canvas("U22_Runtime_Object_Snapshot", "Supplement 22 - Object diagram: one paused analysis snapshot", 2200, 1320, "Concrete instances show what is persisted at a durable pause and what is restored on resume.")
    objects = [
        ("u", "user17: User", ["id = user-17", "owns run/profile/workflow"]),
        ("p", "activeProfile: UserProfile", ["default model = bedrock/claude", "risk profile = balanced"]),
        ("ip", "runPolicy: InvestorPolicy", ["maxLoss = 12%", "maxPosition = 20%", "excluded = tobacco"]),
        ("wv", "workflowV7: WorkflowVersion", ["version = 7", "immutable content hash"]),
        ("r", "nvdaRun: Run", ["status = PAUSED", "ticker = NVDA", "trace_id = ..."]),
        ("cp", "checkpoint84: Checkpoint", ["sequence = 84", "completed outputs retained", "loop state retained"]),
        ("nr", "marketAgentRun: NodeRun", ["status = SUCCEEDED", "attempt = 1", "output hash = ..."]),
        ("ev", "pauseEvent84: RunEvent", ["type = run.paused", "monotonic sequence = 84"]),
        ("rep", "decisionReport: Report", ["not yet available", "requires SUCCEEDED/DEGRADED"]),
    ]
    positions = [(90, 170), (610, 170), (1130, 170), (1650, 170), (90, 560), (610, 560), (1130, 560), (1650, 560), (870, 970)]
    nodes: dict[str, Node] = {}
    for (key, title, lines), (x, y) in zip(objects, positions):
        nodes[key] = c.node(key, title, lines, x, y, 430, 155, PALETTE["white"], PALETTE["blue"] if key in {"u", "r"} else PALETTE["gray"], "object")
    route(c, "u_p", [nodes["u"].right, nodes["p"].left], "1 owns")
    route(c, "p_ip", [nodes["p"].right, nodes["ip"].left], "1 contains")
    route(c, "ip_r", [nodes["ip"].bottom, (nodes["ip"].bottom[0], 475), (nodes["r"].right[0] + 70, 475), (nodes["r"].right[0] + 70, nodes["r"].right[1]), nodes["r"].right], "deep-copied at run creation", color=PALETTE["orange"], label_at=(1040, 450))
    route(c, "wv_r", [nodes["wv"].bottom, (nodes["wv"].bottom[0], 470), (nodes["r"].left[0] - 45, 470), (nodes["r"].left[0] - 45, nodes["r"].left[1]), nodes["r"].left], "snapshotted version", color=PALETTE["purple"], label_at=(1700, 445))
    route(c, "r_cp", [nodes["r"].right, nodes["cp"].left], "latest 1")
    route(c, "cp_nr", [nodes["cp"].right, nodes["nr"].left], "restores state")
    route(c, "nr_ev", [nodes["nr"].right, nodes["ev"].left], "produces ordered events")
    route(c, "cp_rep", [nodes["cp"].bottom, (nodes["cp"].bottom[0], 870), (nodes["rep"].top[0], 870), nodes["rep"].top], "resume continues before report", dashed=True, label_at=(905, 845))
    return c


def composite_structure() -> Canvas:
    c = canvas("U23_Runtime_Composite_Structure", "Supplement 23 - Composite structure: WorkflowRuntime internals", 2300, 1420, "Ports and parts expose the owned orchestration kernel instead of treating WorkflowRuntime as a black box.")
    c.boundary("structured classifier: WorkflowRuntime", 90, 110, 2120, 1180, PALETTE["orange"], "#FFFCF8")
    ingress = c.node("ingress", "runTaskPort", ["WorkflowTask", "runtime connections", "pause/cancel probes"], 65, 250, 50, 50, PALETTE["blue_fill"], PALETTE["blue"], "port")
    validator = c.node("validator", "validator: WorkflowValidator", ["config + graph + budget", "stable issues"], 650, 190, 430, 145, PALETTE["white"], PALETTE["amber"], "part")
    planner = c.node("planner", "planner: ReadinessResolver", ["restore/init NodeRuns", "stable ready set", "bounded parallel wave"], 1300, 190, 430, 155, PALETTE["white"], PALETTE["orange"], "part")
    executor = c.node("executor", "executor: NodeDispatcher", ["typed inputs", "timeout/retry", "provider/model/report adapters"], 650, 540, 430, 165, PALETTE["white"], PALETTE["purple"], "part")
    policy = c.node("policy", "policy: FailureAndPauseController", ["required/optional failure", "PAUSING -> checkpoint -> PAUSED", "cancel and interruption"], 1300, 540, 430, 175, PALETTE["white"], PALETTE["red"], "part")
    checkpoint = c.node("checkpoint", "checkpoint: CheckpointWriter", ["node outputs + loop state", "event IDs + sequence", "resume skips completed nodes"], 650, 900, 430, 165, PALETTE["white"], PALETTE["teal"], "part")
    egress = c.node("egress", "resultEventPort", ["RunResult", "Postgres events/checkpoint", "Redis progress events"], 2185, 950, 50, 50, PALETTE["green_fill"], PALETTE["green"], "port")
    route(c, "i_v", [ingress.right, (570, ingress.right[1]), (570, validator.left[1]), validator.left], "validate(task)", color=PALETTE["blue"])
    route(c, "v_p", [validator.right, (1190, validator.right[1]), (1190, planner.left[1]), planner.left], "accepted definition", color=PALETTE["amber"])
    route(c, "p_e", [planner.bottom, (planner.bottom[0], 460), (executor.top[0], 460), executor.top], "NodeTask[]", color=PALETTE["orange"])
    route(c, "e_pol", [executor.right, (1190, executor.right[1]), (1190, policy.left[1]), policy.left], "ExecutionResult[]", color=PALETTE["purple"])
    route(c, "pol_cp", [policy.bottom, (policy.bottom[0], 820), (checkpoint.right[0] + 80, 820), (checkpoint.right[0] + 80, checkpoint.right[1]), checkpoint.right], "wave outcome / pause", color=PALETTE["red"])
    route(c, "cp_plan", [checkpoint.left, (560, checkpoint.left[1]), (560, 430), (planner.left[0] - 70, 430), (planner.left[0] - 70, planner.left[1]), planner.left], "next wave or restored state", dashed=True, color=PALETTE["teal"], label_at=(820, 405))
    route(c, "cp_out", [checkpoint.right, (1550, checkpoint.right[1]), (1550, egress.left[1]), egress.left], "checkpoint + events", color=PALETTE["teal"])
    route(c, "pol_out", [policy.right, (1860, policy.right[1]), (1860, egress.top[1] - 50), (egress.top[0], egress.top[1] - 50), egress.top], "terminal / paused result", color=PALETTE["green"], label_at=(1860, 805))
    return c


def runtime_timing() -> Canvas:
    c = canvas("U24_Run_Timing", "Supplement 24 - Timing diagram: run, node, event, and UI state", 2400, 720, "Relative time only. The diagram shows the observable ordering contract for execution, durable pause, resume, and report availability.")
    c.boundary("time ->", 220, 80, 2070, 430, PALETTE["gray"], "#FCFCFD")
    lanes = [
        ("run", "RunStatus", ["QUEUED", "RUNNING / wave 1", "PAUSING", "PAUSED", "RUNNING / resumed", "SUCCEEDED"]),
        ("node", "NodeRun", ["PENDING / wave 1", "RUNNING / wave 1", "SUCCEEDED / wave 1", "retained immutable", "PENDING / remaining", "SUCCEEDED / remaining"]),
        ("checkpoint", "Checkpoint", ["none", "wave 1", "pause-safe", "stable", "restored", "final"]),
        ("events", "Visible events", ["queued", "started", "pausing", "paused", "resumed", "completed"]),
        ("ui", "Run History / Report", ["queued", "live / wave 1", "pausing", "paused", "live / resumed", "report ready"]),
    ]
    xs = [300, 620, 940, 1260, 1580, 1900]
    for lane_index, (key, title, values) in enumerate(lanes):
        y = 190 + lane_index * 185
        c.node(f"label_{key}", title, [], 20, y, 180, 90, PALETTE["gray_fill"], PALETTE["gray"], "lifeline")
        for index, (x, value) in enumerate(zip(xs, values)):
            c.node(f"{key}_{index}", value, [], x, y, 250, 90, PALETTE["white"], PALETTE["blue"] if key in {"run", "ui"} else PALETTE["teal"], "timingstate")
    c.note("timing_note", "Ordering constraints", ["pause acknowledgement follows a checkpoint; resume rechecks session-only connections before work restarts", "completed node outputs remain immutable; report is exposed only after SUCCEEDED or DEGRADED"], 420, 555, 1580, 110, PALETTE["amber_fill"], PALETTE["amber"], "constraint")
    return c


def interaction_overview() -> Canvas:
    c = canvas("U25_Interaction_Overview", "Supplement 25 - Interaction overview: end-to-end analysis control", 2250, 1500, "Each interaction occurrence expands into the corresponding sequence, communication, activity, or timing diagram.")
    start = c.node("start", "Start", [], 80, 165, 80, 80, PALETTE["navy"], PALETTE["navy"], "start")
    profile = c.node("profile", "ref Profile + Connections", ["load defaults/policy", "verify provider/model session"], 300, 130, 430, 140, PALETTE["blue_fill"], PALETTE["blue"], "interaction")
    configure = c.node("configure", "ref Configure + Validate", ["new analysis + workflow version", "typed request and graph gates"], 900, 130, 430, 140, PALETTE["amber_fill"], PALETTE["amber"], "interaction")
    execute = c.node("execute", "ref Execute ready waves", ["evidence, specialists, debate", "risk, checkpoints, events"], 1500, 130, 430, 150, PALETTE["purple_fill"], PALETTE["purple"], "interaction")
    pause = c.node("pause", "Pause requested?", [], 980, 500, 290, 110, PALETTE["amber_fill"], PALETTE["amber"], "decision")
    durable = c.node("durable", "ref Durable pause", ["PAUSING", "checkpoint", "PAUSED"], 350, 720, 430, 145, PALETTE["teal_fill"], PALETTE["teal"], "interaction")
    resume = c.node("resume", "Resume?", [], 980, 735, 290, 110, PALETTE["amber_fill"], PALETTE["amber"], "decision")
    complete = c.node("complete", "Terminal analysis?", [], 1550, 500, 320, 110, PALETTE["amber_fill"], PALETTE["amber"], "decision")
    report = c.node("report", "ref Report + Run History", ["separate confidence/support", "lineage + artifacts", "merged durable/live events"], 1450, 975, 500, 160, PALETTE["green_fill"], PALETTE["green"], "interaction")
    end = c.node("end", "End", [], 2040, 1020, 80, 80, PALETTE["navy"], PALETTE["navy"], "end")
    route(c, "a", [start.right, (230, start.right[1]), (230, profile.left[1]), profile.left])
    route(c, "b", [profile.right, configure.left])
    route(c, "c", [configure.right, (1410, configure.right[1]), (1410, execute.left[1]), execute.left])
    route(c, "d", [execute.bottom, (execute.bottom[0], 420), (pause.right[0] + 70, 420), (pause.right[0] + 70, pause.right[1]), pause.right])
    route(c, "e", [pause.left, (850, pause.left[1]), (850, durable.top[1] - 45), (durable.top[0], durable.top[1] - 45), durable.top], "yes", color=PALETTE["teal"], label_at=(820, 650))
    route(c, "f", [durable.right, (875, durable.right[1]), (875, resume.left[1]), resume.left])
    route(c, "g", [resume.top, (resume.top[0], 660), (execute.left[0] - 65, 660), (execute.left[0] - 65, execute.bottom[1] + 30), (execute.bottom[0], execute.bottom[1] + 30), execute.bottom], "yes: recheck + restore", dashed=True, color=PALETTE["blue"], label_at=(1300, 635))
    route(c, "h", [pause.right, complete.left], "no")
    route(c, "i", [complete.top, (complete.top[0], 420), (execute.right[0] + 70, 420), (execute.right[0] + 70, execute.right[1]), execute.right], "no: next ready wave", dashed=True, label_at=(2010, 390))
    route(c, "j", [complete.bottom, (complete.bottom[0], 900), (report.top[0], 900), report.top], "yes", color=PALETTE["green"], label_at=(1680, 875))
    route(c, "k", [report.right, (1995, report.right[1]), (1995, end.left[1]), end.left])
    return c


def deployment_topology() -> Canvas:
    c = rename(deployment(), "U26_Deployment_Topology", "Supplement 26 - Deployment diagram: Docker Compose topology", "Current containers, ports, health dependencies, data volumes, event stores, and external provider trust boundaries.")
    return c


def latest_run_state_machine() -> Canvas:
    c = canvas("F21_Run_State_Machine", "Figure 21 - Run lifecycle and resumable outcomes", 2300, 1380, "Current run and node states, including durable PAUSING/PAUSED behavior, cancellation, interruption, retry, and checkpoint resume.")
    c.boundary("RunStatus", 40, 100, 1030, 1160, PALETTE["blue"], "#FBFCFF")
    c.boundary("NodeStatus", 1110, 100, 1140, 1160, PALETTE["teal"], "#FAFFFE")
    q = c.node("queued", "QUEUED", ["accepted; background task pending"], 100, 175, 230, 95, PALETTE["blue_fill"], PALETTE["blue"], "state")
    r = c.node("running", "RUNNING", ["validated; ready waves execute", "pause/cancel probes active"], 430, 165, 270, 115, PALETTE["blue_fill"], PALETTE["blue"], "state")
    d = c.node("degraded", "DEGRADED", ["optional failure or limit warning", "report remains available"], 80, 420, 265, 115, PALETTE["amber_fill"], PALETTE["amber"], "state")
    s = c.node("succeeded", "SUCCEEDED", ["required paths complete", "report available"], 400, 420, 250, 110, PALETTE["green_fill"], PALETTE["green"], "state")
    f = c.node("failed", "FAILED", ["validation, required failure", "or deadlock"], 735, 420, 245, 110, PALETTE["red_fill"], PALETTE["red"], "state")
    pg = c.node("pausing", "PAUSING", ["pause accepted", "finish safe point + checkpoint"], 80, 700, 260, 115, PALETTE["orange_fill"], PALETTE["orange"], "state")
    pd = c.node("paused", "PAUSED", ["durable checkpoint stable", "resume rechecks connections"], 410, 700, 260, 115, PALETTE["teal_fill"], PALETTE["teal"], "state")
    cg = c.node("cancelling", "CANCELLING", ["cancel requested"], 740, 700, 240, 100, PALETTE["orange_fill"], PALETTE["orange"], "state")
    cd = c.node("cancelled", "CANCELLED", ["cancellation probe observed"], 110, 1010, 250, 100, PALETTE["gray_fill"], PALETTE["gray"], "state")
    it = c.node("interrupted", "INTERRUPTED", ["worker/process loss", "resume from checkpoint"], 650, 1010, 270, 110, PALETTE["gray_fill"], PALETTE["gray"], "state")
    route(c, "q_r", [q.right, r.left], "background execution starts", color=PALETTE["blue"], label_at=(380, 140))
    route(c, "r_d", [r.left, (375, r.left[1]), (375, 370), (d.top[0], 370), d.top], "optional failure", color=PALETTE["amber"], label_at=(260, 345))
    route(c, "r_s", [r.bottom, (r.bottom[0], 365), (s.top[0], 365), s.top], "required success", color=PALETTE["green"], label_at=(525, 340))
    route(c, "r_f", [r.right, (715, r.right[1]), (715, 365), (f.top[0], 365), f.top], "required failure / deadlock", color=PALETTE["red"], label_at=(810, 340))
    route(c, "r_pg", [r.left, (370, r.left[1]), (370, 630), (pg.top[0], 630), pg.top], "pause requested", color=PALETTE["orange"], label_at=(275, 605))
    route(c, "pg_pd", [pg.right, pd.left], "safe checkpoint written", color=PALETTE["teal"], label_at=(375, 665))
    route(c, "pd_r", [pd.top, (pd.top[0], 610), (1025, 610), (1025, 125), (r.top[0], 125), r.top], "resume: recheck + restore", dashed=True, color=PALETTE["blue"], label_at=(850, 75))
    route(c, "r_cg", [r.right, (1010, r.right[1]), (1010, cg.right[1]), cg.right], "cancel requested", color=PALETTE["orange"], label_at=(980, 620))
    route(c, "cg_cd", [cg.bottom, (cg.bottom[0], 930), (cd.right[0] + 65, 930), (cd.right[0] + 65, cd.right[1]), cd.right], "probe observed", color=PALETTE["gray"], label_at=(610, 900))
    route(c, "r_it", [r.right, (1000, r.right[1]), (1000, 955), (it.top[0], 955), it.top], "worker/process loss", dashed=True, color=PALETTE["gray"], label_at=(890, 930))
    route(c, "it_r", [it.right, (1030, it.right[1]), (1030, 120), (r.top[0], 120), r.top], "resume after interruption", dashed=True, color=PALETTE["blue"], label_at=(680, 45))

    pending = c.node("pending", "PENDING", ["not yet eligible"], 1180, 180, 210, 90, PALETTE["teal_fill"], PALETTE["teal"], "state")
    ready = c.node("ready", "READY", ["parents terminal", "inputs available"], 1510, 175, 220, 100, PALETTE["teal_fill"], PALETTE["teal"], "state")
    nr = c.node("nrun", "RUNNING", ["attempt + timeout active"], 1880, 180, 250, 90, PALETTE["teal_fill"], PALETTE["teal"], "state")
    ns = c.node("nsucc", "SUCCEEDED", ["typed output emitted"], 1180, 500, 220, 95, PALETTE["green_fill"], PALETTE["green"], "state")
    nd = c.node("ndeg", "DEGRADED", ["optional failure", "warning output"], 1510, 500, 220, 105, PALETTE["amber_fill"], PALETTE["amber"], "state")
    nf = c.node("nfail", "FAILED", ["attempts exhausted", "required may fail run"], 1880, 500, 250, 110, PALETTE["red_fill"], PALETTE["red"], "state")
    sk = c.node("skipped", "SKIPPED", ["unselected or removed by policy"], 1220, 900, 260, 105, PALETTE["gray_fill"], PALETTE["gray"], "state")
    nc = c.node("ncancel", "CANCELLED", ["run cancellation probe"], 1850, 900, 270, 100, PALETTE["gray_fill"], PALETTE["gray"], "state")
    route(c, "p_ready", [pending.right, ready.left], "parents terminal", label_at=(1450, 135))
    route(c, "ready_run", [ready.right, nr.left], "selected in bounded wave", label_at=(1800, 135))
    route(c, "nr_s", [nr.left, (1810, nr.left[1]), (1810, 430), (ns.top[0], 430), ns.top], "valid typed output", color=PALETTE["green"], label_at=(1450, 405))
    route(c, "nr_d", [nr.bottom, (nr.bottom[0], 430), (nd.top[0], 430), nd.top], "optional failure", color=PALETTE["amber"], label_at=(1740, 405))
    route(c, "nr_f", [nr.bottom, (nr.bottom[0], 430), (nf.top[0], 430), nf.top], "attempts exhausted", color=PALETTE["red"], label_at=(2030, 405))
    route(c, "retry", [nf.right, (2180, nf.right[1]), (2180, 140), (nr.top[0], 140), nr.top], "retry below max_attempts", dashed=True, color=PALETTE["orange"], label_at=(2150, 350))
    route(c, "skip", [pending.left, (1145, pending.left[1]), (1145, sk.left[1]), sk.left], "configuration removes node")
    route(c, "cancel_node", [nr.right, (2195, nr.right[1]), (2195, nc.right[1]), nc.right], "cancellation probe")
    return c


def report_canvases() -> list[Canvas]:
    high = rename(master_system(), "F05_High_Level_As_Built_Architecture", "Figure 5 - OmniTrade high-level as-built architecture", "Expanded from TradingAgents into the implemented UI, API, workflow runtime, evidence, bounded agents, risk, report, persistence, and no-broker boundary.")
    component = rename(service_architecture(), "F06_Integrated_Component_Architecture", "Figure 6 - Integrated component architecture", "Expanded responsibilities for browser, API, services, runtime, providers/models, persistence, events, reporting, and deployment boundaries.")
    domain = rename(domain_contracts(), "F15_Domain_Class_Model", "Figure 15 - Domain and class model", "Persistent concepts, typed runtime contracts, ownership/version relations, evidence lineage, reports, artifacts, and recovery state.")
    seq = rename(sequence(), "F18_End_to_End_Sequence", "Figure 18 - End-to-end execution sequence", "Latest profile defaults and investor policy, connection recheck, request validation, provider/model routing, durable pause/resume, risk/report stages, events, and checkpoints.")
    state = latest_run_state_machine()
    return [
        use_case(), agile_cycle(), ci_pipeline(), timing_model(), high, component,
        package_dependencies(), domain, analysis_pipeline(), communication(), seq,
        validator_activity(), scheduler_activity(), state,
        object_snapshot(), composite_structure(), runtime_timing(), interaction_overview(), deployment_topology(),
    ]


DIAGRAM_TYPES = {
    "F01": "USE_CASE",
    "F02": "ACTIVITY",
    "F03": "ACTIVITY",
    "F04": "OVERVIEW",
    "F05": "COMPONENT",
    "F06": "COMPONENT",
    "F14": "PACKAGE",
    "F15": "CLASS",
    "F16": "ACTIVITY",
    "F17": "COMMUNICATION",
    "F18": "SEQUENCE",
    "F19": "ACTIVITY",
    "F20": "ACTIVITY",
    "F21": "STATE",
    "U22": "OBJECT",
    "U23": "COMPOSITE",
    "U24": "TIMING",
    "U25": "INTERACTION_OVERVIEW",
    "U26": "DEPLOYMENT",
}


def b64(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def source_revision() -> str:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def write_vp_exchange(canvases: list[Canvas]) -> None:
    """Write a compact exchange file consumed by the native VP OpenAPI plugin."""
    rows = ["# OmniTrade Visual Paradigm OpenAPI exchange v1"]
    for c in canvases:
        prefix = c.name.split("_", 1)[0]
        rows.append("\t".join(["D", b64(c.name), b64(c.title), DIAGRAM_TYPES[prefix], str(c.width), str(c.height), b64(c.subtitle)]))
        for idx, boundary in enumerate(c.boundaries):
            rows.append("\t".join(["B", b64(c.name), b64(f"boundary_{idx}"), b64(boundary.title), str(boundary.x), str(boundary.y), str(boundary.w), str(boundary.h), boundary.fill, boundary.stroke]))
        for node in [*c.nodes, *c.notes]:
            rows.append("\t".join(["N", b64(c.name), b64(node.key), b64(node.stereotype), b64(node.title), b64("\n".join(node.lines)), str(node.x), str(node.y), str(node.w), str(node.h), node.fill, node.stroke]))
        for edge in c.edges:
            points = ";".join(f"{int(x)},{int(y)}" for x, y in edge.points)
            label_x, label_y = edge.label_at or edge.points[len(edge.points) // 2]
            rows.append("\t".join(["E", b64(c.name), b64(edge.key), b64(edge.label), b64(points), edge.color, "1" if edge.dashed else "0", "1" if edge.arrow else "0", str(int(label_x)), str(int(label_y))]))
    (OUT / "vp-diagrams.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    for directory in (OUT, DRAWINGS, PREVIEWS, SOURCES):
        directory.mkdir(parents=True, exist_ok=True)
    canvases = report_canvases()
    validate_routes(canvases)
    for directory in (DRAWINGS, PREVIEWS, SOURCES):
        for pattern in (("F*.vdx", "U*.vdx") if directory == DRAWINGS else ("F*.svg", "U*.svg") if directory == PREVIEWS else ("F*.puml", "U*.puml")):
            for path in directory.glob(pattern):
                path.unlink()
    for c in canvases:
        (PREVIEWS / f"{c.name}.svg").write_text(render_svg(c), encoding="utf-8")
        (DRAWINGS / f"{c.name}.vdx").write_text(render_vdx(c), encoding="utf-8")
        (SOURCES / f"{c.name}.puml").write_text(plantuml_for(c), encoding="utf-8")
    (OUT / "OmniTradeAI-Report-UML-2.1.xmi").write_text(build_xmi(canvases), encoding="utf-8")
    write_vp_exchange(canvases)
    data = manifest(canvases)
    data["source_revision"] = source_revision()
    data["report_source"] = "C:/Users/SefroyeK/OneDrive/Desktop/omnitrade_v5.6_final.pdf"
    data["report_figures"] = ["1", "2", "3", "4", "5", "6", "14", "15", "16", "17", "18", "19", "20", "21"]
    data["supplemental_uml"] = ["object", "composite structure", "timing", "interaction overview", "deployment"]
    data["facts"]["catalog_node_types"] = len(NODE_CATALOG)
    data["facts"]["default_workflow_nodes"] = len(defense_workflow().nodes)
    data["facts"]["default_workflow_edges"] = len(defense_workflow().edges)
    data["checksums"] = {
        str(path.relative_to(OUT)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
        for directory in (DRAWINGS, PREVIEWS, SOURCES)
        for pattern in ("F*", "U*")
        for path in sorted(directory.glob(pattern))
    }
    (OUT / "report-model-manifest.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(json.dumps({"diagrams": len(canvases), "revision": data["source_revision"], "catalog_nodes": len(NODE_CATALOG), "workflow_nodes": len(defense_workflow().nodes), "workflow_edges": len(defense_workflow().edges)}, indent=2))


if __name__ == "__main__":
    main()
