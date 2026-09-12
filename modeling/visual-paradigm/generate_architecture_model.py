"""Generate the architecture views that extend the user's Visual Paradigm Atlas.

The views use the implemented OmniTrade code as their source of truth.  The
course architecture material is used only to keep the distinction between an
architectural style, an architectural pattern, and a local design mechanism.
All authored connectors are orthogonal and are validated against unrelated
node interiors before the Visual Paradigm exchange is written.
"""

from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path

from generate_model import (
    PALETTE,
    Canvas,
    Node,
    render_svg,
    validate_routes,
)
from omnitrade.engine.catalog import NODE_CATALOG
from omnitrade.sample_workflow import defense_workflow


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PREVIEWS = OUT / "architecture-previews"
EXCHANGE = OUT / "vp-architecture.tsv"
MANIFEST = OUT / "architecture-model-manifest.json"


def canvas(name: str, title: str, width: int, height: int, subtitle: str) -> Canvas:
    return Canvas(name=name, title=title, width=width, height=height, subtitle=subtitle)


def component(
    c: Canvas,
    key: str,
    title: str,
    lines: list[str],
    x: float,
    y: float,
    w: float,
    h: float,
    fill: str,
    stroke: str,
) -> Node:
    return c.node(key, title, lines, x, y, w, h, fill, stroke, "component")


def dependency(
    c: Canvas,
    key: str,
    source: Node,
    target: Node,
    *,
    color: str = PALETTE["gray"],
    dashed: bool = False,
    via: list[tuple[float, float]] | None = None,
) -> None:
    points = [source.right, *(via or []), target.left]
    c.edge(key, points, "", color, dashed, True, None)


def down(
    c: Canvas,
    key: str,
    source: Node,
    target: Node,
    *,
    color: str = PALETTE["gray"],
    dashed: bool = False,
    corridor: float | None = None,
) -> None:
    y = corridor if corridor is not None else (source.bottom[1] + target.top[1]) / 2
    c.edge(
        key,
        [source.bottom, (source.bottom[0], y), (target.top[0], y), target.top],
        "",
        color,
        dashed,
        True,
        None,
    )


def main_architecture() -> Canvas:
    c = canvas(
        "A01_Main_Web_Information_System_Architecture",
        "Architecture 1 - OmniTrade main web information system architecture",
        4000,
        2210,
        "Enhanced Atlas: user configuration enters three owned CONTROL subsystems; typed execution services produce a durable, explainable decision-support report.",
    )

    c.boundary("A. Web client and user configuration", 50, 95, 620, 1460, PALETTE["blue"], "#F8FAFF")
    c.boundary("CONTROL 1. Request and run composition", 730, 95, 760, 1460, PALETTE["cyan"], "#F4FBFF")
    c.boundary("CONTROL 2. Workflow orchestration kernel", 1550, 95, 860, 1460, PALETTE["orange"], "#FFF9F5")
    c.boundary("D. Typed execution plane", 2470, 95, 900, 1460, PALETTE["green"], "#F5FCF7")
    c.boundary("CONTROL 3. Decision governance", 3430, 95, 520, 1460, PALETTE["red"], "#FFF7F8")
    c.boundary("E. Durable state, events, observability, and output", 730, 1630, 3220, 490, PALETTE["purple"], "#FAF8FF")

    browser = component(c, "browser", "React web application", ["pages: profile, connections, workflow, analysis", "commands: start / pause / resume / cancel", "source: frontend/src/App.tsx"], 90, 155, 540, 155, PALETTE["blue_fill"], PALETTE["blue"])
    profile = component(c, "profile", "Profile inputs", ["defaults: quick/deep model + provider", "policy: horizon, loss, position, sectors", "source: ProfilePage.tsx"], 90, 380, 540, 155, PALETTE["blue_fill"], PALETTE["blue"])
    connections = component(c, "connections", "Connection inputs", ["provider credentials + endpoints", "discover models; verify before use", "credentials remain session-only"], 90, 605, 540, 155, PALETTE["green_fill"], PALETTE["green"])
    workflow_lab = component(c, "workflow_lab", "Workflow graph editor", ["31 typed node kinds; 33-node default graph", "edit, validate, publish immutable version", "source: WorkflowStudio.tsx"], 90, 830, 540, 155, PALETTE["purple_fill"], PALETTE["purple"])
    analysis = component(c, "analysis", "Run configuration panel", ["ticker/date, agents, depth, providers", "models, budgets, retries, freshness", "source: AnalysisPage.tsx"], 90, 1055, 540, 165, PALETTE["cyan_fill"], PALETTE["cyan"])
    controls = component(c, "run_controls", "Run History and Agent Room", ["observe ordered events and node effects", "safe pause, cancel, checkpoint resume", "sources: RunsPage + AgentRoom"], 90, 1290, 540, 165, PALETTE["purple_fill"], PALETTE["purple"])

    api = component(c, "api_boundary", "Request API boundary", ["JWT ownership and request DTO validation", "profile, connection, workflow, run routes", "source: omnitrade/api.py"], 790, 155, 640, 155, PALETTE["cyan_fill"], PALETTE["cyan"])
    connection_scope = component(c, "connection_scope", "Session connection verifier", ["verify provider; discover model IDs", "pass only selected credentials to a task", "source: connections.py"], 790, 380, 640, 155, PALETTE["green_fill"], PALETTE["green"])
    config_resolver = component(c, "config_resolver", "Configuration resolver", ["merge profile defaults with run overrides", "validate enum/range/configuration matrix", "source: contracts.py + api.py"], 790, 605, 640, 155, PALETTE["blue_fill"], PALETTE["blue"])
    snapshot = component(c, "snapshot", "Published workflow snapshot", ["published WorkflowVersion + content hash", "copy graph, ports, failure policies, budget", "source: storage.py"], 790, 830, 640, 155, PALETTE["purple_fill"], PALETTE["purple"])
    composer = component(c, "composer", "Composition: create Run", ["bind ticker/as-of, policy, configuration", "create owner-scoped Run and trace_id", "source: create_run()"], 790, 1055, 640, 155, PALETTE["cyan_fill"], PALETTE["cyan"])
    run_context = component(c, "run_context", "Execution context and trace", ["immutable version + scoped connections", "provider/model/token/runtime counters", "source: ExecutionContext"], 790, 1290, 640, 165, PALETTE["teal_fill"], PALETTE["teal"])

    validator = component(c, "validator", "Graph invariant validator", ["ports, reachability, loops, joins", "required inputs, side effects, call budgets", "source: engine/validator.py"], 1640, 155, 680, 155, PALETTE["amber_fill"], PALETTE["amber"])
    index = component(c, "graph_index", "Graph index and readiness resolver", ["build incoming/outgoing adjacency", "parent states determine READY set", "source: WorkflowRuntime.execute"], 1640, 380, 680, 155, PALETTE["orange_fill"], PALETTE["orange"])
    scheduler = component(c, "scheduler", "Stable parallel-wave scheduler", ["sort ready IDs; cap max_parallel_nodes", "asyncio.gather one deterministic wave", "source: _ready_nodes()"], 1640, 605, 680, 155, PALETTE["orange_fill"], PALETTE["orange"])
    dispatcher = component(c, "dispatcher", "Typed node dispatcher", ["NodeDefinition + typed inputs -> NodeTask", "route catalog group to owned service", "source: distributed_executors()"], 1640, 830, 680, 155, PALETTE["cyan_fill"], PALETTE["cyan"])
    policy = component(c, "execution_policy", "Budget, retry, and failure policy", ["provider/model/token limits; timeout/backoff", "required fails; optional degrades", "source: _execute_node()"], 1640, 1055, 680, 155, PALETTE["red_fill"], PALETTE["red"])
    recovery = component(c, "recovery", "Checkpoint and recovery controller", ["snapshot node outputs + consumed event IDs", "resume resets unfinished nodes only", "source: _checkpoint() + resume_run()"], 1640, 1290, 680, 165, PALETTE["purple_fill"], PALETTE["purple"])

    data_apis = component(c, "data_apis", "Live data provider networks", ["Yahoo / Alpha Vantage / FRED", "Polymarket / StockTwits / Reddit", "Frankfurter historical FX"], 2510, 155, 390, 170, PALETTE["green_fill"], PALETTE["green"])
    model_apis = component(c, "model_apis", "LLM provider networks", ["OpenAI-compatible / Anthropic / Gemini", "Azure OpenAI / AWS Bedrock", "user-selected verified model"], 2940, 155, 390, 170, PALETTE["purple_fill"], PALETTE["purple"])
    provider_router = component(c, "provider_router", "Provider-chain adapter", ["role/capability routing in user order", "fallback on classified provider failure", "source: fetch_from_chain()"], 2510, 405, 390, 170, PALETTE["green_fill"], PALETTE["green"])
    model_gateway = component(c, "model_gateway", "Model JSON contract gateway", ["provider-specific HTTP client", "JSON extraction, retry, schema-safe merge", "source: model_gateway.py"], 2940, 405, 390, 170, PALETTE["purple_fill"], PALETTE["purple"])
    evidence = component(c, "evidence_service", "Evidence acquisition and processing", ["5 parallel fetches -> normalization", "technical indicators + fundamental ratios", "time/quality/FX policy"], 2510, 680, 390, 205, PALETTE["teal_fill"], PALETTE["teal"])
    specialists = component(c, "specialists", "Specialist analysis agent pool", ["market / fundamental / news / sentiment", "grounded deterministic draft + model narrative", "each returns typed AgentReport"], 2940, 680, 390, 205, PALETTE["cyan_fill"], PALETTE["cyan"])
    lineage = component(c, "lineage", "Claim-to-evidence lineage ledger", ["provider, URL, time, quality, content hash", "claim evidence_refs survive every stage", "source: EvidenceItem + Claim"], 2510, 1010, 390, 190, PALETTE["teal_fill"], PALETTE["teal"])
    research = component(c, "research", "Bull/Bear research and bounded debate", ["parallel positive/negative cases", "manager compares conflict and agreement", "explicit max_iterations loop"], 2940, 1010, 390, 190, PALETTE["purple_fill"], PALETTE["purple"])
    event_control = component(c, "event_control", "Runtime event coordinator", ["versioned RunEvent with trace + node IDs", "publish progress after every state change", "source: RedisStreamEventBus"], 2725, 1305, 390, 150, PALETTE["purple_fill"], PALETTE["purple"])

    proposal = component(c, "proposal", "Governed proposal builder", ["combine bounded research cases", "deterministic BUY / HOLD / SELL draft", "confidence + conditions"], 3490, 405, 400, 170, PALETTE["green_fill"], PALETTE["green"])
    risk = component(c, "risk", "Three parallel risk views", ["aggressive / balanced / conservative", "apply immutable InvestorPolicy", "reward, loss, uncertainty"], 3490, 680, 400, 205, PALETTE["red_fill"], PALETTE["red"])
    decision = component(c, "decision", "Deterministic decision gate", ["join 3 views; evidence/consistency checks", "max loss, position, excluded-sector limits", "protected action and confidence"], 3490, 1010, 400, 190, PALETTE["red_fill"], PALETTE["red"])
    report = component(c, "report", "Report assembler", ["specialists + debate + risk + lineage", "JSON/PDF + disclaimer + limitations", "source: reporting.py"], 3490, 1305, 400, 150, PALETTE["teal_fill"], PALETTE["teal"])

    postgres = component(c, "postgres", "Durable PostgreSQL repository", ["users, profiles, workflow versions, runs", "events, evidence, calls, reports, artifacts", "durable ownership and recovery"], 800, 1735, 560, 235, PALETTE["blue_fill"], PALETTE["blue"])
    redis = component(c, "redis", "Run-event Redis stream", ["at-least-once run-event transport", "pause/cancel flags and progress feed", "consumer-group service isolation"], 1450, 1735, 560, 235, PALETTE["purple_fill"], PALETTE["purple"])
    artifacts = component(c, "artifacts", "Hashed artifact volume", ["JSON and PDF report files", "SHA-256 metadata and stable paths", "source: artifacts.py"], 2100, 1735, 560, 235, PALETTE["teal_fill"], PALETTE["teal"])
    agent_room = component(c, "agent_room", "Agent Room / SSE", ["ordered node/run events", "agent output and impact details", "observable execution, not hidden chain"], 2750, 1735, 500, 235, PALETTE["purple_fill"], PALETTE["purple"])
    reports_ui = component(c, "reports_ui", "Reports and Run History", ["decision, evidence, warnings, agent views", "calendar, lineage, JSON/PDF export", "decision support only - no broker"], 3340, 1735, 550, 235, PALETTE["green_fill"], PALETTE["green"])

    # User-input influence.  Each route uses the corridor between the client and CONTROL 1.
    dependency(c, "browser_api", browser, api, color=PALETTE["blue"])
    dependency(c, "profile_config", profile, config_resolver, color=PALETTE["blue"], via=[(700, profile.right[1]), (700, config_resolver.left[1])])
    dependency(c, "connection_verify", connections, connection_scope, color=PALETTE["green"], via=[(700, connections.right[1]), (700, connection_scope.left[1])])
    dependency(c, "workflow_snapshot", workflow_lab, snapshot, color=PALETTE["purple"])
    dependency(c, "analysis_config", analysis, composer, color=PALETTE["cyan"], via=[(700, analysis.right[1]), (700, composer.left[1])])
    dependency(c, "run_control", controls, recovery, color=PALETTE["purple"], dashed=True, via=[(700, controls.right[1]), (700, 1585), (1515, 1585), (1515, recovery.left[1])])

    # CONTROL 1 composition sequence.
    down(c, "api_scope", api, connection_scope, color=PALETTE["cyan"])
    down(c, "scope_config", connection_scope, config_resolver, color=PALETTE["green"])
    down(c, "config_snapshot", config_resolver, snapshot, color=PALETTE["blue"])
    down(c, "snapshot_composer", snapshot, composer, color=PALETTE["purple"])
    down(c, "composer_context", composer, run_context, color=PALETTE["cyan"])

    # CONTROL 2 algorithm.
    dependency(c, "context_validator", run_context, validator, color=PALETTE["orange"], via=[(1520, run_context.right[1]), (1520, validator.left[1])])
    down(c, "validate_index", validator, index, color=PALETTE["amber"])
    down(c, "index_scheduler", index, scheduler, color=PALETTE["orange"])
    down(c, "scheduler_dispatcher", scheduler, dispatcher, color=PALETTE["orange"])
    down(c, "dispatcher_policy", dispatcher, policy, color=PALETTE["cyan"])
    down(c, "policy_recovery", policy, recovery, color=PALETTE["red"])

    # Typed execution plane and governance.  Cross-boundary routes stay in reserved gutters.
    dependency(c, "dispatch_provider", dispatcher, provider_router, color=PALETTE["green"], via=[(2440, dispatcher.right[1]), (2440, provider_router.left[1])])
    dependency(c, "dispatch_model", dispatcher, model_gateway, color=PALETTE["purple"], via=[(2445, dispatcher.right[1]), (2445, 620), (2915, 620), (2915, model_gateway.left[1])])
    down(c, "data_to_router", data_apis, provider_router, color=PALETTE["green"])
    down(c, "models_to_gateway", model_apis, model_gateway, color=PALETTE["purple"])
    down(c, "router_evidence", provider_router, evidence, color=PALETTE["green"])
    down(c, "gateway_specialists", model_gateway, specialists, color=PALETTE["purple"])
    dependency(c, "evidence_specialists", evidence, specialists, color=PALETTE["teal"])
    down(c, "evidence_lineage", evidence, lineage, color=PALETTE["teal"])
    down(c, "specialists_research", specialists, research, color=PALETTE["purple"])
    dependency(c, "lineage_research", lineage, research, color=PALETTE["teal"])
    dependency(c, "research_proposal", research, proposal, color=PALETTE["green"], via=[(3400, research.right[1]), (3400, proposal.left[1])])
    down(c, "proposal_risk", proposal, risk, color=PALETTE["red"])
    down(c, "risk_decision", risk, decision, color=PALETTE["red"])
    down(c, "decision_report", decision, report, color=PALETTE["teal"])

    # Runtime events and durable outcomes use the bottom corridor above persistence.
    dependency(c, "recovery_events", recovery, event_control, color=PALETTE["purple"], dashed=True, via=[(2435, recovery.right[1]), (2435, event_control.left[1])])
    c.edge("recovery_postgres", [recovery.bottom, (recovery.bottom[0], 1590), (postgres.top[0], 1590), postgres.top], "", PALETTE["blue"], True, True, None)
    c.edge("event_redis", [event_control.bottom, (event_control.bottom[0], 1590), (redis.top[0], 1590), redis.top], "", PALETTE["purple"], True, True, None)
    c.edge("report_artifacts", [report.bottom, (report.bottom[0], 1595), (artifacts.top[0], 1595), artifacts.top], "", PALETTE["teal"], True, True, None)
    dependency(c, "redis_agentroom", redis, agent_room, color=PALETTE["purple"], dashed=True, via=[(2050, redis.right[1]), (2050, 2050), (2700, 2050), (2700, agent_room.left[1])])
    dependency(c, "artifacts_reports", artifacts, reports_ui, color=PALETTE["teal"], via=[(2710, artifacts.right[1]), (2710, 2020), (3300, 2020), (3300, reports_ui.left[1])])
    dependency(c, "agentroom_reports", agent_room, reports_ui, color=PALETTE["purple"])
    return c


def control_decomposition() -> Canvas:
    c = canvas(
        "A02_Control_Subsystem_Decomposition",
        "Architecture 2 - Decomposition of the three CONTROL subsystems",
        3800,
        2050,
        "Lowest-level responsibility view: composition creates an executable snapshot, orchestration advances it deterministically, and governance constrains the decision and report.",
    )
    c.boundary("CONTROL 1. Composition algorithm", 60, 100, 1150, 1800, PALETTE["cyan"], "#F4FBFF")
    c.boundary("CONTROL 2. Orchestration algorithm", 1325, 100, 1150, 1800, PALETTE["orange"], "#FFF9F5")
    c.boundary("CONTROL 3. Governance algorithm", 2590, 100, 1150, 1800, PALETTE["red"], "#FFF7F8")

    def column(prefix: str, x: int, specs: list[tuple[str, str, list[str], str, str]]) -> list[Node]:
        nodes: list[Node] = []
        for index, (key, title, lines, fill, stroke) in enumerate(specs):
            nodes.append(component(c, f"{prefix}_{key}", title, lines, x, 175 + index * 255, 890, 175, fill, stroke))
        for index in range(len(nodes) - 1):
            down(c, f"{prefix}_flow_{index}", nodes[index], nodes[index + 1], color=nodes[index].stroke)
        return nodes

    composition = column("c1", 190, [
        ("accept", "1. Accept owned command", ["authenticate user; validate request DTO", "load profile, connections, published workflow", "api.py + auth.py"], PALETTE["blue_fill"], PALETTE["blue"]),
        ("merge", "2. Resolve effective configuration", ["profile defaults < explicit run overrides", "validate analysts/providers/models/ranges", "RunConfiguration validators"], PALETTE["cyan_fill"], PALETTE["cyan"]),
        ("scope", "3. Scope verified connections", ["select only providers/models used by this run", "never persist keys in DB/events/artifacts", "SessionConnectionStore"], PALETTE["green_fill"], PALETTE["green"]),
        ("version", "4. Freeze executable graph", ["copy immutable published WorkflowVersion", "bind node configs, failure policy, retry, budget", "_configured_definition()"], PALETTE["purple_fill"], PALETTE["purple"]),
        ("persist", "5. Create run and trace", ["owner_id + workflow_version_id + trace_id", "persist QUEUED before background execution", "create_run() + PostgresStore"], PALETTE["teal_fill"], PALETTE["teal"]),
        ("handoff", "6. Handoff typed WorkflowTask", ["workflow + run + checkpoint? + scoped connections", "HTTP to workflow service :8001", "_execute_run()"], PALETTE["amber_fill"], PALETTE["amber"]),
    ])
    orchestration = column("c2", 1455, [
        ("validate", "1. Validate graph invariants", ["known node types; typed ports; reachability", "declared loops; join/fan-in; side effects; budgets", "WorkflowValidator.validate()"], PALETTE["amber_fill"], PALETTE["amber"]),
        ("restore", "2. Restore or initialize NodeRuns", ["checkpoint copies successful/degraded outputs", "unfinished nodes return to PENDING", "WorkflowRuntime.execute()"], PALETTE["purple_fill"], PALETTE["purple"]),
        ("ready", "3. Compute deterministic ready set", ["all non-loop parents must be terminal-acceptable", "stable node-ID sort prevents race-dependent order", "_ready_nodes()"], PALETTE["orange_fill"], PALETTE["orange"]),
        ("wave", "4. Execute bounded parallel wave", ["cap by max_parallel_nodes", "gather typed tasks; aggregate inputs by port", "asyncio.gather() + _execute_node()"], PALETTE["cyan_fill"], PALETTE["cyan"]),
        ("classify", "5. Apply execution policy", ["timeout/retry/backoff and call counters", "required -> FAILED; optional -> DEGRADED", "FailurePolicy + RetryPolicy"], PALETTE["red_fill"], PALETTE["red"]),
        ("checkpoint", "6. Emit event and checkpoint", ["save node states, outputs, sequence, consumed IDs", "pause only between waves; cancel cooperatively", "_emit() + _checkpoint()"], PALETTE["teal_fill"], PALETTE["teal"]),
    ])
    governance = column("c3", 2720, [
        ("guard", "1. Admit trustworthy evidence", ["reject future/stale core evidence", "optional stale branches may degrade when allowed", "validate_evidence() + time_guard"], PALETTE["teal_fill"], PALETTE["teal"]),
        ("ground", "2. Ground agent computation", ["deterministic draft defines facts and shape", "model edits narrative; protected fields stay owned", "merge_model_narrative()"], PALETTE["purple_fill"], PALETTE["purple"]),
        ("debate", "3. Bound research collaboration", ["Bull/Bear cases; manager comparison", "declared loop count prevents unbounded agents", "research_manager + bounded_loop"], PALETTE["green_fill"], PALETTE["green"]),
        ("risk", "4. Apply three risk perspectives", ["parallel aggressive/balanced/conservative review", "each receives frozen InvestorPolicy", "risk nodes + risk_join"], PALETTE["red_fill"], PALETTE["red"]),
        ("decide", "5. Validate the decision", ["evidence consistency + confidence limits", "max loss/position/excluded-sector constraints", "decision_validator"], PALETTE["red_fill"], PALETTE["red"]),
        ("report", "6. Assemble auditable output", ["agent views + evidence refs + settings + warning", "JSON/PDF, hash, disclaimer; never execute trades", "reporting.py + artifacts.py"], PALETTE["teal_fill"], PALETTE["teal"]),
    ])

    dependency(c, "c1_c2", composition[-1], orchestration[0], color=PALETTE["orange"], via=[(1265, composition[-1].right[1]), (1265, orchestration[0].left[1])])
    dependency(c, "c2_c3", orchestration[-1], governance[0], color=PALETTE["red"], via=[(2530, orchestration[-1].right[1]), (2530, governance[0].left[1])])
    return c


def architecture_style() -> Canvas:
    c = canvas(
        "A03_Architecture_Style",
        "Architecture 3 - Dominant and supporting architectural styles",
        3400,
        1830,
        "Dominant style: layered web information system. Supporting styles refine distribution, workflow computation, event observation, and durable information ownership.",
    )
    c.boundary("Dominant style: Layered web information system", 60, 105, 2180, 1620, PALETTE["blue"], "#F8FAFF")
    c.boundary("Supporting styles - scoped, not competing main architectures", 2350, 105, 990, 1620, PALETTE["purple"], "#FAF8FF")

    layers = [
        component(c, "layer_ui", "Layer 1 - User interface", ["React pages and workflow canvas", "renders commands, progress, reports", "client/browser responsibility"], 170, 190, 1940, 190, PALETTE["blue_fill"], PALETTE["blue"]),
        component(c, "layer_comm", "Layer 2 - User communications and access", ["Nginx + FastAPI REST/SSE", "JWT ownership; DTO and connection checks", "network-facing boundary"], 170, 455, 1940, 190, PALETTE["cyan_fill"], PALETTE["cyan"]),
        component(c, "layer_app", "Layer 3 - Application and CONTROL services", ["run composition + workflow scheduling + governance", "API, workflow, evidence, model, report services", "application-specific coordination"], 170, 720, 1940, 190, PALETTE["orange_fill"], PALETTE["orange"]),
        component(c, "layer_domain", "Layer 4 - Information retrieval and domain processing", ["provider adapters, normalization, calculations", "specialists, bounded research, risk, decision", "typed pipeline transformations"], 170, 985, 1940, 190, PALETTE["green_fill"], PALETTE["green"]),
        component(c, "layer_data", "Layer 5 - Durable information management", ["PostgreSQL + Redis Streams + artifacts", "versioned workflows, runs, events, evidence, reports", "repository and recovery state"], 170, 1250, 1940, 190, PALETTE["purple_fill"], PALETTE["purple"]),
    ]
    for index in range(len(layers) - 1):
        down(c, f"layer_{index}", layers[index], layers[index + 1], color=PALETTE["blue"])

    supporting = [
        component(c, "style_client_server", "Client-server", ["browser client -> HTTP/SSE servers", "Docker services may share one host", "scope: distribution and communication"], 2470, 190, 750, 190, PALETTE["cyan_fill"], PALETTE["cyan"]),
        component(c, "style_service", "Service-oriented", ["five cohesive backend services", "versioned DTOs; internal HTTP contracts", "scope: application responsibility"], 2470, 455, 750, 190, PALETTE["blue_fill"], PALETTE["blue"]),
        component(c, "style_pipeline", "Pipes and filters", ["typed DAG nodes transform port values", "parallel branches, joins, bounded loop", "scope: analysis computation"], 2470, 720, 750, 190, PALETTE["green_fill"], PALETTE["green"]),
        component(c, "style_event", "Event-driven / implicit invocation", ["runtime publishes versioned RunEvents", "UI and recovery observe without owning schedule", "scope: progress and control signals"], 2470, 985, 750, 190, PALETTE["orange_fill"], PALETTE["orange"]),
        component(c, "style_repository", "Repository", ["durable shared facts in PostgreSQL", "Redis event log + hashed artifact archive", "scope: state, audit, recovery"], 2470, 1250, 750, 190, PALETTE["purple_fill"], PALETTE["purple"]),
    ]

    # Horizontal, same-row mappings keep the classification readable.
    dependency(c, "map_client", layers[0], supporting[0], color=PALETTE["cyan"])
    dependency(c, "map_service", layers[1], supporting[1], color=PALETTE["blue"])
    dependency(c, "map_pipeline", layers[2], supporting[2], color=PALETTE["green"])
    dependency(c, "map_event", layers[3], supporting[3], color=PALETTE["orange"])
    dependency(c, "map_repository", layers[4], supporting[4], color=PALETTE["purple"])
    return c


def architecture_patterns() -> Canvas:
    c = canvas(
        "A04_Architecture_Pattern_Realization",
        "Architecture 4 - Architectural pattern realization map",
        3650,
        2060,
        "Each lane states the architecture problem, the selected pattern, its concrete OmniTrade realization, and the resulting trade-off.",
    )
    lanes = [
        ("Three-tier client-server", "Separate browser interaction from domain work and durable state", "React/Nginx | FastAPI + services | PostgreSQL/Redis/artifacts", "clear deployment boundary; network and service failure must be handled", PALETTE["blue"], PALETTE["blue_fill"]),
        ("Modular service decomposition", "Keep scheduling, provider failure, model variation, and reporting cohesive", "API :8000 | workflow :8001 | evidence :8002 | model :8003 | report :8004", "independent ownership/testing; more contracts and operational links", PALETTE["cyan"], PALETTE["cyan_fill"]),
        ("Typed workflow pipeline", "Execute a configurable, non-linear analysis without black-box orchestration", "31 NodeSpecs + typed ports + DAG + parallel waves + joins + bounded loop", "visible owned complexity; validator and recovery logic are required", PALETTE["green"], PALETTE["green_fill"]),
        ("Ports, adapters, and strategy selection", "Replace volatile data/model vendors without changing domain control", "Provider/NodeProvider + ModelClient protocols; user-ordered provider chain", "vendor substitution and test seams; adapters must normalize failures and schemas", PALETTE["purple"], PALETTE["purple_fill"]),
        ("Event log plus repository checkpoint", "Observe progress and recover without replaying completed side effects", "RunEvent/Redis Streams + Postgres rows + Checkpoint consumed IDs", "traceability and resume; at-least-once delivery needs idempotent effects", PALETTE["orange"], PALETTE["orange_fill"]),
    ]
    for index, (pattern, problem, realization, consequence, stroke, fill) in enumerate(lanes):
        y = 105 + index * 380
        c.boundary(f"Pattern {index + 1}", 50, y, 3550, 320, stroke, "#FFFFFF")
        problem_node = component(c, f"p{index}_problem", f"P{index + 1} architecture problem", [problem], 110, y + 65, 720, 190, PALETTE["gray_fill"], PALETTE["gray"])
        pattern_node = component(c, f"p{index}_pattern", pattern, ["selected architectural pattern", "system-wide structural effect"], 940, y + 65, 640, 190, fill, stroke)
        realization_node = component(c, f"p{index}_realization", f"P{index + 1} OmniTrade realization", [realization, "verified in code and docker-compose.yml"], 1690, y + 65, 970, 190, fill, stroke)
        consequence_node = component(c, f"p{index}_consequence", f"P{index + 1} consequence / trade-off", [consequence], 2770, y + 65, 720, 190, PALETTE["gray_fill"], PALETTE["gray"])
        dependency(c, f"p{index}_a", problem_node, pattern_node, color=stroke)
        dependency(c, f"p{index}_b", pattern_node, realization_node, color=stroke)
        dependency(c, f"p{index}_c", realization_node, consequence_node, color=stroke)
    return c


def architecture_principles() -> Canvas:
    c = canvas(
        "A05_Architecture_Principles",
        "Architecture 5 - Architecture principles and quality-attribute traceability",
        3600,
        2020,
        "Principles are expressed as enforceable implementation rules, not slogans; each group ends in the quality attributes it protects.",
    )
    groups = [
        ("Structure and evolvability", PALETTE["blue"], PALETTE["blue_fill"], [
            ("Separation of concerns", "five services + catalog groups own distinct work", "docs/adr/0002-modular-services.md"),
            ("High cohesion, low coupling", "versioned NodeTask/RunEvent contracts cross boundaries", "services.py + contracts.py"),
            ("Dependency inversion", "Provider and ModelClient protocols isolate vendors", "providers.py + model_gateway.py"),
        ], "Maintainability | replaceability | testability"),
        ("Correctness and determinism", PALETTE["green"], PALETTE["green_fill"], [
            ("Explicit contracts", "Pydantic models + typed ports reject invalid graphs/data", "contracts.py + validator.py"),
            ("Deterministic control", "stable ready-set ordering and owned decision checks", "runtime.py + executors.py"),
            ("Immutable execution context", "published version and InvestorPolicy copied into Run", "storage.py + api.py"),
        ], "Consistency | reproducibility | auditability"),
        ("Resilience and operations", PALETTE["orange"], PALETTE["orange_fill"], [
            ("Bound every resource", "timeouts, retries, budgets, parallel and loop limits", "Budget + RetryPolicy + bounded_loop"),
            ("Fail explicitly and degrade safely", "required failure stops; optional failure records warning", "FailurePolicy + WorkflowRuntime"),
            ("Make progress resumable", "events + checkpoints + consumed IDs avoid duplicate work", "_checkpoint() + resume_run()"),
        ], "Availability | recoverability | predictable cost"),
        ("Trust, safety, and explanation", PALETTE["red"], PALETTE["red_fill"], [
            ("Least-privilege secrets", "verified credentials stay in memory and are task-scoped", "SessionConnectionStore + remote_executor"),
            ("Ground and protect decisions", "models cannot overwrite evidence/action/confidence fields", "merge_model_narrative()"),
            ("Preserve safety boundary", "decision support, lineage, disclaimer; no broker interface", "reporting.py + architecture ADRs"),
        ], "Security | explainability | controlled financial risk"),
    ]

    for index, (title, stroke, fill, principles, outcome) in enumerate(groups):
        x = 60 + index * 885
        c.boundary(title, x, 105, 815, 1810, stroke, "#FFFFFF")
        nodes: list[Node] = []
        for p_index, (principle, mechanism, source) in enumerate(principles):
            nodes.append(component(c, f"g{index}_p{p_index}", principle, [mechanism, f"source: {source}"], x + 70, 215 + p_index * 420, 675, 240, fill, stroke))
        outcome_node = component(c, f"g{index}_outcome", f"{title} quality outcomes", [outcome, "verified by tests, events, and artifacts"], x + 70, 1510, 675, 245, PALETTE["gray_fill"], PALETTE["gray"])
        for p_index, node in enumerate(nodes):
            corridor = 520 + p_index * 420
            c.edge(
                f"g{index}_trace{p_index}",
                [node.bottom, (node.bottom[0], corridor), (x + 35, corridor), (x + 35, outcome_node.left[1]), outcome_node.left],
                "",
                stroke,
                True,
                True,
                None,
            )
    return c


def b64(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def write_exchange(canvases: list[Canvas]) -> None:
    rows = ["# OmniTrade architecture Visual Paradigm OpenAPI exchange v1"]
    for c in canvases:
        rows.append("\t".join(["D", b64(c.name), b64(c.title), "COMPONENT", str(c.width), str(c.height), b64(c.subtitle)]))
        for index, boundary in enumerate(c.boundaries):
            rows.append("\t".join(["B", b64(c.name), b64(f"boundary_{index}"), b64(boundary.title), str(int(boundary.x)), str(int(boundary.y)), str(int(boundary.w)), str(int(boundary.h)), boundary.fill, boundary.stroke]))
        for node in [*c.nodes, *c.notes]:
            rows.append("\t".join(["N", b64(c.name), b64(node.key), b64(node.stereotype), b64(node.title), b64("\n".join(node.lines)), str(int(node.x)), str(int(node.y)), str(int(node.w)), str(int(node.h)), node.fill, node.stroke]))
        for edge in c.edges:
            points = ";".join(f"{int(x)},{int(y)}" for x, y in edge.points)
            label_x, label_y = edge.label_at or edge.points[len(edge.points) // 2]
            rows.append("\t".join(["E", b64(c.name), b64(edge.key), b64(edge.label), b64(points), edge.color, "1" if edge.dashed else "0", "1" if edge.arrow else "0", str(int(label_x)), str(int(label_y))]))
    EXCHANGE.write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    canvases = [
        main_architecture(),
        control_decomposition(),
        architecture_style(),
        architecture_patterns(),
        architecture_principles(),
    ]
    validate_routes(canvases)
    for old in PREVIEWS.glob("A*.svg"):
        old.unlink()
    for item in canvases:
        (PREVIEWS / f"{item.name}.svg").write_text(render_svg(item), encoding="utf-8")
    write_exchange(canvases)
    workflow = defense_workflow()
    MANIFEST.write_text(
        json.dumps(
            {
                "source_revision": revision(),
                "source_system": "web-based information system",
                "dominant_style": "layered web information system",
                "supporting_styles": ["client-server", "service-oriented", "pipes-and-filters", "event-driven", "repository"],
                "catalog_node_types": len(NODE_CATALOG),
                "default_workflow_nodes": len(workflow.nodes),
                "default_workflow_edges": len(workflow.edges),
                "diagrams": [{"id": item.name, "title": item.title, "nodes": len(item.nodes), "edges": len(item.edges)} for item in canvases],
                "reference_note": "Course PDF was used for terminology and classification only; implementation claims come from the current repository.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"diagrams": len(canvases), "revision": revision(), "exchange": str(EXCHANGE)}, indent=2))


if __name__ == "__main__":
    main()
