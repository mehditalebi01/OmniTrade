"""Generate OmniTrade UML model sources and routed Visual Paradigm drawings.

The generator reads the live node catalog and default workflow.  It produces:
* UML 2.1 XMI for semantic elements and dependencies;
* Visio 2003 XML drawings for editable Visual Paradigm import;
* SVG previews for fast visual verification;
* PlantUML source for portable review and future regeneration.

Coordinates are deliberate.  Orthogonal routes stay in reserved corridors and
do not cross component boxes.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Iterable
from uuid import NAMESPACE_URL, uuid5

from omnitrade.engine.catalog import NODE_CATALOG, NODE_DESCRIPTIONS
from omnitrade.sample_workflow import defense_workflow


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DRAWINGS = OUT / "drawings"
PREVIEWS = OUT / "previews"
SOURCES = OUT / "plantuml"


PALETTE = {
    "navy": "#15233A",
    "blue": "#4361EE",
    "blue_fill": "#E9EEFF",
    "cyan": "#2D9CDB",
    "cyan_fill": "#E8F7FF",
    "teal": "#1AAE9F",
    "teal_fill": "#E5F8F5",
    "green": "#1E9E59",
    "green_fill": "#EAF8EF",
    "amber": "#E59A16",
    "amber_fill": "#FFF4D8",
    "orange": "#E76F51",
    "orange_fill": "#FFF0EB",
    "purple": "#7B61C9",
    "purple_fill": "#F2EDFF",
    "red": "#D95367",
    "red_fill": "#FFECEF",
    "gray": "#667085",
    "gray_fill": "#F2F4F7",
    "white": "#FFFFFF",
    "ink": "#172033",
    "muted": "#475467",
    "line": "#98A2B3",
}


def slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_").lower()


def stable_id(kind: str, name: str) -> str:
    return "id_" + uuid5(NAMESPACE_URL, f"omnitrade:{kind}:{name}").hex


@dataclass
class Node:
    key: str
    title: str
    lines: list[str]
    x: float
    y: float
    w: float
    h: float
    fill: str = PALETTE["gray_fill"]
    stroke: str = PALETTE["gray"]
    stereotype: str = "component"

    @property
    def left(self) -> tuple[float, float]:
        return self.x, self.y + self.h / 2

    @property
    def right(self) -> tuple[float, float]:
        return self.x + self.w, self.y + self.h / 2

    @property
    def top(self) -> tuple[float, float]:
        return self.x + self.w / 2, self.y

    @property
    def bottom(self) -> tuple[float, float]:
        return self.x + self.w / 2, self.y + self.h


@dataclass
class Boundary:
    title: str
    x: float
    y: float
    w: float
    h: float
    stroke: str
    fill: str = "#FFFFFF"
    dashed: bool = False


@dataclass
class Edge:
    key: str
    points: list[tuple[float, float]]
    label: str = ""
    color: str = PALETTE["gray"]
    dashed: bool = False
    arrow: bool = True
    label_at: tuple[float, float] | None = None


@dataclass
class Canvas:
    name: str
    title: str
    width: int
    height: int
    subtitle: str = ""
    nodes: list[Node] = field(default_factory=list)
    boundaries: list[Boundary] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    notes: list[Node] = field(default_factory=list)

    def node(self, *args: object, **kwargs: object) -> Node:
        value = Node(*args, **kwargs)
        self.nodes.append(value)
        return value

    def note(self, *args: object, **kwargs: object) -> Node:
        value = Node(*args, **kwargs)
        self.notes.append(value)
        return value

    def boundary(self, *args: object, **kwargs: object) -> Boundary:
        value = Boundary(*args, **kwargs)
        self.boundaries.append(value)
        return value

    def edge(self, *args: object, **kwargs: object) -> Edge:
        value = Edge(*args, **kwargs)
        self.edges.append(value)
        return value

    def by_key(self, key: str) -> Node:
        return next(node for node in self.nodes if node.key == key)


def lr(canvas: Canvas, key: str, source: Node, target: Node, label: str = "", *, corridor: float | None = None, color: str = PALETTE["gray"], dashed: bool = False, label_at: tuple[float, float] | None = None) -> None:
    mid = corridor if corridor is not None else (source.right[0] + target.left[0]) / 2
    points = [source.right, (mid, source.right[1]), (mid, target.left[1]), target.left]
    canvas.edge(key, points, label, color, dashed, True, label_at)


def tb(canvas: Canvas, key: str, source: Node, target: Node, label: str = "", *, corridor: float | None = None, color: str = PALETTE["gray"], dashed: bool = False, label_at: tuple[float, float] | None = None) -> None:
    mid = corridor if corridor is not None else (source.bottom[1] + target.top[1]) / 2
    points = [source.bottom, (source.bottom[0], mid), (target.top[0], mid), target.top]
    canvas.edge(key, points, label, color, dashed, True, label_at)


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]


def svg_text(lines: Iterable[str], x: float, y: float, width: float, *, title: bool = False, color: str = PALETTE["ink"], size: int = 14) -> str:
    rows = list(lines)
    if not rows:
        return ""
    chunks: list[str] = []
    for index, line in enumerate(rows):
        weight = 700 if title or index == 0 else 430
        line_size = size + 1 if index == 0 else size
        chunks.append(
            f'<text x="{x + width / 2:.1f}" y="{y + 22 + index * (size + 7):.1f}" '
            f'text-anchor="middle" font-family="Inter,Segoe UI,Arial" font-size="{line_size}" '
            f'font-weight="{weight}" fill="{color}">{escape(line)}</text>'
        )
    return "".join(chunks)


def render_svg(canvas: Canvas) -> str:
    marker = """
    <defs>
      <marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto" markerUnits="strokeWidth">
        <path d="M0,0 L10,4 L0,8 z" fill="context-stroke"/>
      </marker>
      <filter id="shadow" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.12"/></filter>
    </defs>"""
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas.width}" height="{canvas.height}" viewBox="0 0 {canvas.width} {canvas.height}">',
        marker,
        '<rect width="100%" height="100%" fill="#FFFFFF"/>',
        f'<text x="32" y="38" font-family="Inter,Segoe UI,Arial" font-size="24" font-weight="800" fill="{PALETTE["navy"]}">{escape(canvas.title)}</text>',
    ]
    if canvas.subtitle:
        parts.append(f'<text x="32" y="62" font-family="Inter,Segoe UI,Arial" font-size="13" fill="{PALETTE["muted"]}">{escape(canvas.subtitle)}</text>')
    for item in canvas.boundaries:
        dash = ' stroke-dasharray="8 6"' if item.dashed else ""
        parts.append(f'<rect x="{item.x}" y="{item.y}" width="{item.w}" height="{item.h}" rx="14" fill="{item.fill}" fill-opacity="0.42" stroke="{item.stroke}" stroke-width="2"{dash}/>')
        parts.append(f'<rect x="{item.x + 14}" y="{item.y - 13}" width="{max(130, len(item.title) * 8.2)}" height="26" rx="6" fill="#FFFFFF" stroke="{item.stroke}"/>')
        parts.append(f'<text x="{item.x + 24}" y="{item.y + 5}" font-family="Inter,Segoe UI,Arial" font-size="14" font-weight="750" fill="{item.stroke}">{escape(item.title)}</text>')
    for edge in canvas.edges:
        path = " ".join(("M" if index == 0 else "L") + f" {x:.1f} {y:.1f}" for index, (x, y) in enumerate(edge.points))
        dash = ' stroke-dasharray="7 5"' if edge.dashed else ""
        arrow = ' marker-end="url(#arrow)"' if edge.arrow else ""
        parts.append(f'<path d="{path}" fill="none" stroke="{edge.color}" stroke-width="2.2" stroke-linejoin="round"{dash}{arrow}/>')
        if edge.label:
            lx, ly = edge.label_at or edge.points[len(edge.points) // 2]
            label_lines = edge.label.split("\n")
            label_width = max(95, max(len(line) for line in label_lines) * 6.6 + 18)
            label_height = len(label_lines) * 16 + 10
            parts.append(f'<rect x="{lx - label_width/2:.1f}" y="{ly - label_height/2:.1f}" width="{label_width:.1f}" height="{label_height}" rx="5" fill="#FFFFFF" stroke="#D0D5DD"/>')
            for index, line in enumerate(label_lines):
                parts.append(f'<text x="{lx:.1f}" y="{ly - (len(label_lines)-1)*8 + index*16 + 4:.1f}" text-anchor="middle" font-family="Inter,Segoe UI,Arial" font-size="11" fill="{PALETTE["muted"]}">{escape(line)}</text>')
    for node in [*canvas.nodes, *canvas.notes]:
        dash = ' stroke-dasharray="6 4"' if node.stereotype == "note" else ""
        parts.append(f'<rect x="{node.x}" y="{node.y}" width="{node.w}" height="{node.h}" rx="11" fill="{node.fill}" stroke="{node.stroke}" stroke-width="2"{dash} filter="url(#shadow)"/>')
        if node.stereotype and node.stereotype not in {"note", "plain"}:
            parts.append(f'<text x="{node.x + 12}" y="{node.y + 18}" font-family="Inter,Segoe UI,Arial" font-size="10" fill="{node.stroke}">«{escape(node.stereotype)}»</text>')
            y0 = node.y + 16
        else:
            y0 = node.y + 4
        parts.append(svg_text([node.title, *node.lines], node.x, y0, node.w, size=12 if node.w < 230 else 13))
    parts.append('</svg>')
    return "".join(parts)


def vdx_shape(node: Node, shape_id: int, page_height: float) -> str:
    scale = 100.0
    x = node.x / scale
    y = (page_height - node.y - node.h) / scale
    w = node.w / scale
    h = node.h / scale
    pin_x = x + w / 2
    pin_y = y + h / 2
    sr, sg, sb = hex_to_rgb(node.stroke)
    fr, fg, fb = hex_to_rgb(node.fill)
    text = "&#10;".join(escape(value) for value in ([f"«{node.stereotype}»", node.title, *node.lines] if node.stereotype not in {"plain", "note", ""} else [node.title, *node.lines]))
    dashed = "2" if node.stereotype == "note" else "1"
    return f"""<Shape ID="{shape_id}" NameU="{escape(node.key)}" Type="Shape">
      <XForm><PinX>{pin_x:.4f}</PinX><PinY>{pin_y:.4f}</PinY><Width>{w:.4f}</Width><Height>{h:.4f}</Height><LocPinX>{w/2:.4f}</LocPinX><LocPinY>{h/2:.4f}</LocPinY><Angle>0</Angle></XForm>
      <Line><LineWeight>0.018</LineWeight><LineColor>RGB({sr},{sg},{sb})</LineColor><LinePattern>{dashed}</LinePattern></Line>
      <Fill><FillForegnd>RGB({fr},{fg},{fb})</FillForegnd><FillPattern>1</FillPattern></Fill>
      <Char IX="0"><Font>0</Font><Color>RGB(23,32,51)</Color><Size>0.115</Size></Char><Para IX="0"><HorzAlign>1</HorzAlign><SpBefore>0</SpBefore><SpAfter>0</SpAfter></Para>
      <Text>{text}</Text>
      <Geom IX="0"><MoveTo IX="1"><X>0</X><Y>0</Y></MoveTo><LineTo IX="2"><X>{w:.4f}</X><Y>0</Y></LineTo><LineTo IX="3"><X>{w:.4f}</X><Y>{h:.4f}</Y></LineTo><LineTo IX="4"><X>0</X><Y>{h:.4f}</Y></LineTo><LineTo IX="5"><X>0</X><Y>0</Y></LineTo></Geom>
    </Shape>"""


def vdx_boundary(item: Boundary, shape_id: int, page_height: float) -> str:
    node = Node(f"boundary_{shape_id}", item.title, [], item.x, item.y, item.w, item.h, item.fill, item.stroke, "plain")
    raw = vdx_shape(node, shape_id, page_height)
    if item.dashed:
        raw = raw.replace("<LinePattern>1</LinePattern>", "<LinePattern>2</LinePattern>")
    return raw


def vdx_edge(edge: Edge, shape_id: int, page_height: float) -> str:
    scale = 100.0
    xs = [p[0] for p in edge.points]
    ys = [page_height - p[1] for p in edge.points]
    x0, y0 = min(xs) / scale, min(ys) / scale
    w, h = max((max(xs) - min(xs)) / scale, 0.001), max((max(ys) - min(ys)) / scale, 0.001)
    r, g, b = hex_to_rgb(edge.color)
    geom = []
    for index, (px, py) in enumerate(zip(xs, ys), start=1):
        tag = "MoveTo" if index == 1 else "LineTo"
        geom.append(f'<{tag} IX="{index}"><X>{px/scale-x0:.4f}</X><Y>{py/scale-y0:.4f}</Y></{tag}>')
    arrow = "4" if edge.arrow else "0"
    pattern = "2" if edge.dashed else "1"
    return f"""<Shape ID="{shape_id}" NameU="{escape(edge.key)}" Type="Shape">
      <XForm><PinX>{x0+w/2:.4f}</PinX><PinY>{y0+h/2:.4f}</PinY><Width>{w:.4f}</Width><Height>{h:.4f}</Height><LocPinX>{w/2:.4f}</LocPinX><LocPinY>{h/2:.4f}</LocPinY><Angle>0</Angle></XForm>
      <Line><LineWeight>0.014</LineWeight><LineColor>RGB({r},{g},{b})</LineColor><LinePattern>{pattern}</LinePattern><EndArrow>{arrow}</EndArrow><EndArrowSize>2</EndArrowSize></Line>
      <Fill><FillPattern>0</FillPattern></Fill><Geom IX="0"><NoFill>1</NoFill>{''.join(geom)}</Geom>
    </Shape>"""


def vdx_label(edge: Edge, shape_id: int, page_height: float) -> str:
    lx, ly = edge.label_at or edge.points[len(edge.points) // 2]
    lines = edge.label.split("\n")
    width = max(100, max(len(line) for line in lines) * 7 + 20)
    height = len(lines) * 18 + 10
    return vdx_shape(Node(f"label_{edge.key}", lines[0], lines[1:], lx - width/2, ly - height/2, width, height, "#FFFFFF", "#D0D5DD", "plain"), shape_id, page_height)


def render_vdx(canvas: Canvas) -> str:
    shapes: list[str] = []
    shape_id = 1
    for item in canvas.boundaries:
        shapes.append(vdx_boundary(item, shape_id, canvas.height)); shape_id += 1
    for edge in canvas.edges:
        shapes.append(vdx_edge(edge, shape_id, canvas.height)); shape_id += 1
        if edge.label:
            shapes.append(vdx_label(edge, shape_id, canvas.height)); shape_id += 1
    for node in [*canvas.nodes, *canvas.notes]:
        shapes.append(vdx_shape(node, shape_id, canvas.height)); shape_id += 1
    title = Node("diagram_title", canvas.title, [canvas.subtitle] if canvas.subtitle else [], 24, 12, canvas.width - 48, 58, "#FFFFFF", "#FFFFFF", "plain")
    shapes.append(vdx_shape(title, shape_id, canvas.height))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<VisioDocument xmlns="urn:schemas-microsoft-com:office:visio" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
 <DocumentProperties><Creator>OmniTradeAI</Creator><Title>{escape(canvas.title)}</Title></DocumentProperties>
 <DocumentSettings><DefaultLineStyle>0</DefaultLineStyle><DefaultFillStyle>0</DefaultFillStyle><DefaultTextStyle>0</DefaultTextStyle></DocumentSettings>
 <Colors/><StyleSheets/><Masters/>
 <Pages><Page ID="0" NameU="{escape(canvas.name)}" Name="{escape(canvas.title)}">
  <PageSheet><PageProps><PageWidth>{canvas.width/100:.4f}</PageWidth><PageHeight>{canvas.height/100:.4f}</PageHeight><PageScale>1</PageScale><DrawingScale>1</DrawingScale></PageProps></PageSheet>
  <Shapes>{''.join(shapes)}</Shapes><Connects/>
 </Page></Pages>
</VisioDocument>"""


def base_canvas(name: str, title: str, width: int, height: int, subtitle: str) -> Canvas:
    return Canvas(name, title, width, height, subtitle)


def domain_contracts() -> Canvas:
    c = base_canvas("D01_L3_Domain_Contracts", "D01 — L3 Domain contracts and traceability objects", 1900, 1080, "Current Pydantic contracts; arrows show ownership or typed reference direction.")
    c.boundary("Workflow definition", 30, 90, 570, 440, PALETTE["blue"], PALETTE["blue_fill"])
    c.boundary("Run lifecycle", 625, 90, 590, 620, PALETTE["teal"], PALETTE["teal_fill"])
    c.boundary("Evidence and decision", 1240, 90, 630, 620, PALETTE["purple"], PALETTE["purple_fill"])
    c.boundary("User-controlled policy", 30, 740, 1185, 300, PALETTE["amber"], PALETTE["amber_fill"])
    n = c.node
    workflow = n("workflow", "WorkflowDefinition", ["name, schema_version", "nodes[], edges[]", "budget"], 60, 140, 245, 130, PALETTE["blue_fill"], PALETTE["blue"], "entity")
    node_def = n("node_def", "NodeDefinition", ["typed node + config", "failure policy + timeout", "retry + position"], 340, 120, 230, 150, PALETTE["blue_fill"], PALETTE["blue"], "entity")
    edge_def = n("edge_def", "EdgeDefinition", ["source.port → target.port", "loop flag"], 340, 310, 230, 105, PALETTE["blue_fill"], PALETTE["blue"], "entity")
    workflow_ver = n("workflow_ver", "WorkflowVersion", ["immutable published snapshot", "content_hash + version"], 60, 340, 245, 120, PALETTE["blue_fill"], PALETTE["blue"], "entity")
    run = n("run", "Run", ["owner + workflow_version", "ticker + as_of + trace_id", "status + degraded reasons"], 660, 130, 240, 145, PALETTE["teal_fill"], PALETTE["teal"], "entity")
    node_run = n("node_run", "NodeRun", ["node status", "attempt + iteration", "output or error"], 940, 120, 235, 135, PALETTE["teal_fill"], PALETTE["teal"], "entity")
    event = n("event", "RunEvent", ["event_id + event_type", "run_id + node_id + trace", "timestamp + payload"], 660, 330, 240, 145, PALETTE["teal_fill"], PALETTE["teal"], "event")
    checkpoint = n("checkpoint", "Checkpoint", ["sequence", "node_states{}", "consumed_event_ids{}"], 940, 330, 235, 145, PALETTE["teal_fill"], PALETTE["teal"], "entity")
    artifact = n("artifact", "Artifact", ["report_id + format", "path + SHA-256"], 800, 535, 235, 105, PALETTE["gray_fill"], PALETTE["gray"], "entity")
    evidence = n("evidence", "EvidenceItem", ["value + type + unit/currency", "observed/retrieved timestamps", "provider + URL + hash + flags"], 1275, 130, 260, 155, PALETTE["purple_fill"], PALETTE["purple"], "entity")
    claim = n("claim", "Claim", ["text", "evidence_ids[]", "confidence 0..1"], 1580, 140, 250, 125, PALETTE["purple_fill"], PALETTE["purple"], "entity")
    agent_report = n("agent_report", "AgentReport", ["specialist + summary", "claims[] + risks[]"], 1275, 345, 260, 120, PALETTE["purple_fill"], PALETTE["purple"], "entity")
    decision = n("decision", "Decision", ["BUY | HOLD | SELL | NO_DECISION", "confidence + rationale", "claim_ids[] + warnings[]"], 1580, 335, 250, 145, PALETTE["red_fill"], PALETTE["red"], "entity")
    config = n("config", "RunConfiguration", ["agents, depth, providers", "models, retries, freshness", "currency, language, degradation"], 70, 800, 300, 165, PALETTE["amber_fill"], PALETTE["amber"], "value object")
    budget = n("budget", "Budget", ["runtime/model/provider/token caps", "max parallel nodes"], 430, 820, 280, 120, PALETTE["amber_fill"], PALETTE["amber"], "value object")
    policy = n("policy", "InvestorPolicy", ["horizon + experience", "loss + position limits", "excluded sectors"], 770, 800, 280, 150, PALETTE["amber_fill"], PALETTE["amber"], "value object")
    lr(c, "wf_nodes", workflow, node_def, "contains 1..*", corridor=322, color=PALETTE["blue"], label_at=(322, 175))
    lr(c, "wf_edges", workflow, edge_def, "contains 0..*", corridor=320, color=PALETTE["blue"], label_at=(322, 360))
    tb(c, "version_def", workflow_ver, workflow, "snapshots", corridor=305, color=PALETTE["blue"], label_at=(180, 305))
    lr(c, "run_nodes", run, node_run, "owns per node", corridor=918, color=PALETTE["teal"], label_at=(918, 176))
    tb(c, "run_events", run, event, "emits", corridor=302, color=PALETTE["teal"], label_at=(780, 302))
    lr(c, "checkpoint_state", checkpoint, node_run, "restores", corridor=1085, color=PALETTE["teal"], label_at=(1090, 296))
    tb(c, "event_checkpoint", event, checkpoint, "deduplicated by event_id", corridor=505, color=PALETTE["teal"], label_at=(920, 505))
    tb(c, "run_artifact", event, artifact, "final report event", corridor=505, color=PALETTE["gray"], label_at=(745, 542))
    lr(c, "claim_evidence", evidence, claim, "evidence_ids[]", corridor=1558, color=PALETTE["purple"], label_at=(1557, 190))
    tb(c, "report_claims", evidence, agent_report, "supports", corridor=315, color=PALETTE["purple"], label_at=(1405, 316))
    lr(c, "decision_claims", agent_report, decision, "claim_ids[]", corridor=1558, color=PALETTE["purple"], label_at=(1557, 395))
    c.edge("config_run", [config.top, (config.top[0], 720), (620, 720), (620, run.left[1]), run.left], "copied into run", PALETTE["amber"], False, True, (420, 720))
    c.edge("budget_workflow", [budget.top, (budget.top[0], 720), (15, 720), (15, workflow.left[1]), workflow.left], "default or override", PALETTE["amber"], False, True, (285, 720))
    c.edge("policy_run", [policy.top, (policy.top[0], 720), (1225, 720), (1225, 300), (run.bottom[0], 300), run.bottom], "risk constraints", PALETTE["amber"], False, True, (1080, 720))
    return c


def runtime_kernel() -> Canvas:
    c = base_canvas("D02_L3_Runtime_Kernel", "D02 — L3 workflow-engine kernel", 1900, 1080, "Owned complex logic: validation, readiness, bounded parallel scheduling, retry/fallback, failure classification, checkpoint recovery.")
    c.boundary("Definition gate", 35, 95, 500, 890, PALETTE["blue"], PALETTE["blue_fill"])
    c.boundary("Runtime scheduler", 565, 95, 780, 890, PALETTE["teal"], PALETTE["teal_fill"])
    c.boundary("Execution and recovery", 1375, 95, 490, 890, PALETTE["orange"], PALETTE["orange_fill"])
    n = c.node
    request = n("request", "WorkflowTask / Run", ["published workflow version", "configuration + budget", "trace + cancellation context"], 70, 145, 250, 145, PALETTE["blue_fill"], PALETTE["blue"], "input")
    catalog = n("catalog", "Node catalog (31 types)", ["typed input/output ports", "provider/model cost", "required config + side effects"], 70, 340, 250, 145, PALETTE["purple_fill"], PALETTE["purple"], "registry")
    validator = n("validator", "WorkflowValidator", ["single start/end", "known/reachable nodes", "port compatibility", "bounded loop + budget safety", "model budget = actual model nodes × retries", "depth does not multiply the full graph"], 250, 550, 250, 220, PALETTE["blue_fill"], PALETTE["blue"], "service")
    result = n("result", "ValidationResult", ["errors block execution", "warnings preserved"], 70, 820, 250, 100, PALETTE["gray_fill"], PALETTE["gray"], "contract")
    init = n("init", "Initialize / restore", ["load latest checkpoint", "or create pending NodeRuns", "recover consumed event IDs"], 610, 145, 260, 150, PALETTE["teal_fill"], PALETTE["teal"], "scheduler phase")
    ready = n("ready", "Readiness resolver", ["parents terminal?", "required inputs present?", "sort stable node IDs"], 610, 355, 260, 145, PALETTE["teal_fill"], PALETTE["teal"], "algorithm")
    wave = n("wave", "Bounded parallel wave", ["cap = max_parallel_nodes", "asyncio.gather", "independent branches only"], 1000, 350, 275, 145, PALETTE["teal_fill"], PALETTE["teal"], "algorithm")
    classify = n("classify", "Wave outcome classifier", ["required fail → run fail", "optional fail → degraded", "cancel → terminal cancel", "no progress → deadlock"], 805, 600, 285, 175, PALETTE["teal_fill"], PALETTE["teal"], "decision")
    checkpoint = n("checkpoint", "Checkpoint after each wave", ["sequence + node states", "consumed event IDs", "idempotent resume point"], 1000, 825, 275, 120, PALETTE["gray_fill"], PALETTE["gray"], "persistence")
    execute = n("execute", "Execute one node", ["timeout wrapper", "attempt loop 1..5", "budget debit before call"], 1415, 145, 280, 150, PALETTE["orange_fill"], PALETTE["orange"], "executor")
    retry = n("retry", "Retry / fallback policy", ["exponential backoff", "model/provider call limits", "live fetch: clear node fixture fallback", "real data fallback stays inside provider chain"], 1415, 350, 280, 165, PALETTE["orange_fill"], PALETTE["orange"], "policy")
    remote = n("remote", "Local or remote executor", ["deterministic fixture", "evidence :8002", "model gateway :8003", "report :8004"], 1415, 555, 280, 155, PALETTE["orange_fill"], PALETTE["orange"], "strategy")
    event = n("event", "Event + state update", ["node.started / succeeded", "degraded / failed", "trace_id propagated"], 1415, 790, 280, 135, PALETTE["orange_fill"], PALETTE["orange"], "observable")
    lr(c, "request_validate", request, validator, "definition + version", corridor=345, color=PALETTE["blue"], label_at=(350, 250))
    lr(c, "catalog_validate", catalog, validator, "NodeSpec + port rules", corridor=345, color=PALETTE["purple"], label_at=(350, 455))
    tb(c, "validator_result", validator, result, "valid / issues", corridor=790, color=PALETTE["blue"], label_at=(285, 790))
    lr(c, "validate_init", validator, init, "valid only", corridor=550, color=PALETTE["blue"], label_at=(550, 205))
    tb(c, "init_ready", init, ready, "node states", corridor=325, color=PALETTE["teal"], label_at=(740, 325))
    lr(c, "ready_wave", ready, wave, "ready[0:cap]", corridor=930, color=PALETTE["teal"], label_at=(930, 405))
    lr(c, "wave_execute", wave, execute, "NodeTask × N", corridor=1360, color=PALETTE["orange"], label_at=(1358, 300))
    tb(c, "execute_retry", execute, retry, "failure / timeout", corridor=323, color=PALETTE["orange"], label_at=(1555, 323))
    tb(c, "retry_remote", retry, remote, "attempt or fallback", corridor=523, color=PALETTE["orange"], label_at=(1555, 523))
    tb(c, "remote_event", remote, event, "output / error", corridor=748, color=PALETTE["orange"], label_at=(1555, 748))
    lr(c, "event_classify", event, classify, "ExecutionResult", corridor=1360, color=PALETTE["orange"], label_at=(1360, 750))
    tb(c, "classify_checkpoint", classify, checkpoint, "persist every wave", corridor=802, color=PALETTE["teal"], label_at=(940, 805))
    c.edge("next_wave", [checkpoint.right, (1325, checkpoint.right[1]), (1325, 520), (ready.bottom[0], 520), ready.bottom], "next wave until terminal", PALETTE["teal"], False, True, (1090, 520))
    c.edge("resume", [event.right, (1815, event.right[1]), (1815, 965), (550, 965), (550, init.left[1]), init.left], "restart: restore latest checkpoint + replay-safe events", PALETTE["orange"], True, True, (1270, 965))
    return c


def adapters() -> Canvas:
    c = base_canvas("D03_L3_Adapters", "D03 — L3 provider and model adapter contracts", 2100, 1080, "Third parties are replaceable adapters. OmniTrade owns routing, typed validation, retry, evidence policy, and deterministic protected fields.")
    c.boundary("Data-provider adapters", 30, 100, 900, 900, PALETTE["amber"], PALETTE["amber_fill"])
    c.boundary("Model-provider adapters", 970, 100, 1100, 900, PALETTE["purple"], PALETTE["purple_fill"])
    n = c.node
    provider_contract = n("provider_contract", "NodeProvider protocol", ["fetch_node(type,ticker,as_of)", "returns raw typed payload"], 330, 155, 300, 115, PALETTE["amber_fill"], PALETTE["amber"], "interface")
    router = n("router", "fetch_from_chain", ["capability-compatible real-provider chain", "first success; no fixture fallback in live mode", "classify HTTP status / connection / provider error", "collect safe failure reasons", "Frankfurter FX after market/fundamental fetch"], 330, 330, 300, 190, PALETTE["orange_fill"], PALETTE["orange"], "owned router")
    data_nodes = [
        ("yfinance", "Yahoo Finance", ["market OHLCV", "fundamentals", "news + sentiment"], 65, 610),
        ("alpha", "Alpha Vantage", ["market + fundamentals", "news/sentiment + macro", "API key"], 330, 610),
        ("fred", "FRED", ["macro: DGS10", "API key"], 595, 610),
        ("polymarket", "Polymarket", ["macro context", "prediction-market text"], 65, 810),
        ("stocktwits", "StockTwits", ["public sentiment", "optional/rate-limited"], 330, 810),
        ("reddit", "Reddit feeds", ["public sentiment", "optional/network-sensitive"], 595, 810),
    ]
    dn: list[Node] = []
    for key, title, lines, x, y in data_nodes:
        dn.append(n(key, title, lines, x, y, 235, 125, PALETTE["amber_fill"], PALETTE["amber"], "adapter"))
    provider_routes = [
        [router.left, (310, router.left[1]), (310, 560), (dn[0].top[0], 560), dn[0].top],
        [router.bottom, (router.bottom[0], 560), (dn[1].top[0], 560), dn[1].top],
        [router.right, (650, router.right[1]), (650, 560), (dn[2].top[0], 560), dn[2].top],
        [router.left, (40, router.left[1]), (40, 780), (dn[3].top[0], 780), dn[3].top],
        [router.left, (310, router.left[1]), (310, 780), (dn[4].top[0], 780), dn[4].top],
        [router.right, (850, router.right[1]), (850, 780), (dn[5].top[0], 780), dn[5].top],
    ]
    for index, (item, points) in enumerate(zip(dn, provider_routes)):
        c.edge(f"provider_{index}", points, "fetch_node", PALETTE["amber"], False, True, (item.top[0], 575 if index < 3 else 795))
    tb(c, "contract_router", provider_contract, router, "implemented by adapters", corridor=305, color=PALETTE["amber"], label_at=(480, 305))
    model_contract = n("model_contract", "ModelClient protocol", ["complete(prompt) → text"], 1340, 155, 300, 105, PALETTE["purple_fill"], PALETTE["purple"], "interface")
    gateway = n("gateway", "Typed model gateway", ["build client by provider", "prompt + JSON extraction", "Pydantic output validation", "retry invalid output", "merge narrative; protect facts"], 1340, 330, 300, 185, PALETTE["purple_fill"], PALETTE["purple"], "owned gateway")
    implementations = [
        ("openai_compat", "OpenAI-compatible", ["OpenAI, xAI, DeepSeek", "Qwen, GLM, MiniMax", "OpenRouter, Mistral, Kimi, Groq, NVIDIA, Ollama"], 1010, 610, 300),
        ("anthropic", "AnthropicClient", ["Claude Messages API"], 1340, 610, 250),
        ("gemini", "GeminiClient", ["Google generateContent"], 1620, 610, 250),
        ("azure", "AzureOpenAIClient", ["deployment + api-version"], 1100, 810, 270),
        ("bedrock", "BedrockClient", ["AWS region + credentials", "Anthropic models through AWS"], 1400, 810, 270),
        ("fixture", "DeterministicFakeModel", ["offline + CI", "repeatable typed output"], 1700, 810, 270),
    ]
    mn: list[Node] = []
    for key, title, lines, x, y, w in implementations:
        mn.append(n(key, title, lines, x, y, w, 130 if key != "openai_compat" else 155, PALETTE["purple_fill"], PALETTE["purple"], "adapter"))
    tb(c, "contract_gateway", model_contract, gateway, "client selected at runtime", corridor=295, color=PALETTE["purple"], label_at=(1490, 295))
    model_routes = [
        [gateway.left, (1325, gateway.left[1]), (1325, 560), (mn[0].top[0], 560), mn[0].top],
        [gateway.bottom, (gateway.bottom[0], 560), (mn[1].top[0], 560), mn[1].top],
        [gateway.right, (1660, gateway.right[1]), (1660, 560), (mn[2].top[0], 560), mn[2].top],
        [gateway.top, (gateway.top[0], 300), (950, 300), (950, 780), (mn[3].top[0], 780), mn[3].top],
        [gateway.left, (1325, gateway.left[1]), (1325, 780), (mn[4].top[0], 780), mn[4].top],
        [gateway.right, (2030, gateway.right[1]), (2030, 780), (mn[5].top[0], 780), mn[5].top],
    ]
    for index, (item, points) in enumerate(zip(mn, model_routes)):
        c.edge(f"model_{index}", points, "complete(prompt)", PALETTE["purple"], False, True, (item.top[0], 575 if index < 3 else 795))
    c.note("secret_note", "Connection boundary", ["Credentials are session-only", "Verified settings become runtime dictionaries", "Secrets do not enter DB, events, reports, or artifacts"], 990, 385, 305, 135, PALETTE["gray_fill"], PALETTE["gray"], "note")
    return c


def evidence_pipeline() -> Canvas:
    c = base_canvas("D04_L2_Evidence_Pipeline", "D04 — L2 evidence acquisition, normalization, calculation, and quality gate", 2450, 1160, "Five provider chains run in parallel; typed ports and the time guard define the evidence boundary.")
    c.boundary("External data sources", 25, 105, 390, 980, PALETTE["amber"], PALETTE["amber_fill"])
    c.boundary("Acquisition", 450, 105, 390, 980, PALETTE["orange"], PALETTE["orange_fill"])
    c.boundary("Normalization + calculation", 875, 105, 650, 980, PALETTE["cyan"], PALETTE["cyan_fill"])
    c.boundary("Evidence quality boundary", 1560, 105, 440, 980, PALETTE["teal"], PALETTE["teal_fill"])
    c.boundary("Specialist consumers", 2035, 105, 390, 980, PALETTE["purple"], PALETTE["purple_fill"])
    n=c.node
    providers = [
        n("p_market", "Market chain", ["Yahoo → Alpha Vantage", "OHLCV + timestamps"], 60, 180, 320, 115, PALETTE["amber_fill"], PALETTE["amber"], "providers"),
        n("p_fund", "Fundamental chain", ["Yahoo → Alpha Vantage", "statements + profile"], 60, 345, 320, 115, PALETTE["amber_fill"], PALETTE["amber"], "providers"),
        n("p_news", "News chain", ["Yahoo → Alpha Vantage", "articles + URLs + time"], 60, 510, 320, 115, PALETTE["amber_fill"], PALETTE["amber"], "providers"),
        n("p_macro", "Macro chain", ["FRED → Alpha Vantage → Polymarket", "rates + macro/prediction text"], 60, 675, 320, 130, PALETTE["amber_fill"], PALETTE["amber"], "providers"),
        n("p_sent", "Sentiment chain", ["Yahoo → Alpha Vantage", "→ StockTwits → Reddit", "scores + posts"], 60, 855, 320, 145, PALETTE["amber_fill"], PALETTE["amber"], "providers"),
    ]
    fetches=[]
    names=[("fetch_market","fetch_market",180),("fetch_fund","fetch_fundamentals",345),("fetch_news","fetch_news",510),("fetch_macro","fetch_macro",675),("fetch_sent","fetch_sentiment",855)]
    for key,title,y in names:
        fetches.append(n(key,title,["real-provider chain routing","no fixture fallback in live mode","provider call budget"],490,y,310,115,PALETTE["orange_fill"],PALETTE["orange"],"workflow node"))
    normalizers = [
        n("norm_market", "normalize_market", ["schema + numeric coercion", "common timestamps/currency"], 920, 165, 280, 125, PALETTE["cyan_fill"], PALETTE["cyan"], "workflow node"),
        n("technical", "technical_indicators", ["momentum + SMA20/SMA50", "RSI14 + annualized volatility", "deterministic signal score"], 1230, 165, 250, 145, PALETTE["teal_fill"], PALETTE["teal"], "algorithm"),
        n("norm_fund", "normalize_fundamentals", ["units + missing values", "base-currency conversion"], 920, 370, 280, 125, PALETTE["cyan_fill"], PALETTE["cyan"], "workflow node"),
        n("ratios", "fundamental_ratios", ["profit margin", "debt/equity + valuation", "quality/value evidence"], 1230, 370, 250, 140, PALETTE["teal_fill"], PALETTE["teal"], "algorithm"),
        n("norm_news", "normalize_text (news)", ["clean text + metadata", "URL + observed time"], 1005, 585, 300, 115, PALETTE["cyan_fill"], PALETTE["cyan"], "workflow node"),
        n("norm_macro", "normalize_text (macro)", ["common text evidence", "source + time + hash"], 1005, 750, 300, 115, PALETTE["cyan_fill"], PALETTE["cyan"], "workflow node"),
        n("norm_sent", "normalize_text (sentiment)", ["score/text normalization", "quality flags"], 1005, 915, 300, 115, PALETTE["cyan_fill"], PALETTE["cyan"], "workflow node"),
    ]
    join=n("join","evidence_join",["typed collection compatibility","required/optional branch policy","content hashes preserved"],1600,350,360,145,PALETTE["teal_fill"],PALETTE["teal"],"join")
    guard=n("guard","time_guard",["reject future evidence","reject stale > freshness hours","mark degraded when permitted","output EvidenceSet"],1600,610,360,165,PALETTE["teal_fill"],PALETTE["teal"],"quality gate")
    analysts=[
        n("a_market","Market Analyst",["technical + market evidence","report + claims + refs"],2075,190,310,120,PALETTE["purple_fill"],PALETTE["purple"],"agent"),
        n("a_fund","Fundamental Analyst",["ratios + company evidence","report + claims + refs"],2075,405,310,120,PALETTE["purple_fill"],PALETTE["purple"],"agent"),
        n("a_news","News Analyst",["news + macro context","report + claims + refs"],2075,620,310,120,PALETTE["purple_fill"],PALETTE["purple"],"agent"),
        n("a_sent","Sentiment Analyst",["sentiment + quality flags","report + claims + refs"],2075,835,310,120,PALETTE["purple_fill"],PALETTE["purple"],"agent"),
    ]
    for index,(p,f) in enumerate(zip(providers,fetches)):
        lr(c,f"chain_{index}",p,f,"request / response\nraw typed payload",corridor=430,color=PALETTE["amber"],label_at=(430,p.right[1]))
    pairs=[(fetches[0],normalizers[0]),(fetches[1],normalizers[2]),(fetches[2],normalizers[4]),(fetches[3],normalizers[5]),(fetches[4],normalizers[6])]
    for index,(source,target) in enumerate(pairs):
        lr(c,f"raw_{index}",source,target,"raw_* port\nJSON payload",corridor=855,color=PALETTE["orange"],label_at=(855,source.right[1]))
    lr(c,"tech",normalizers[0],normalizers[1],"normalized_market",corridor=1215,color=PALETTE["teal"],label_at=(1215,220))
    lr(c,"ratio",normalizers[2],normalizers[3],"normalized_fundamentals",corridor=1215,color=PALETTE["teal"],label_at=(1215,430))
    sources=[normalizers[0],normalizers[1],normalizers[2],normalizers[3],normalizers[4],normalizers[5],normalizers[6]]
    source_exits = [
        [normalizers[0].bottom, (normalizers[0].bottom[0], 320), (1538, 320)],
        [normalizers[1].right, (1538, normalizers[1].right[1])],
        [normalizers[2].bottom, (normalizers[2].bottom[0], 535), (1538, 535)],
        [normalizers[3].right, (1538, normalizers[3].right[1])],
        [normalizers[4].right, (1538, normalizers[4].right[1])],
        [normalizers[5].right, (1538, normalizers[5].right[1])],
        [normalizers[6].right, (1538, normalizers[6].right[1])],
    ]
    for index,(source,points) in enumerate(zip(sources,source_exits)):
        c.edge(f"join_{index}",[ *points, (1538, join.left[1]), join.left],"",PALETTE["cyan"],False,True)
    tb(c,"guard",join,guard,"EvidenceSet\nwith hashes + quality flags",corridor=550,color=PALETTE["teal"],label_at=(1780,550))
    for index,target in enumerate(analysts):
        c.edge(f"consume_{index}",[guard.right,(2018,guard.right[1]),(2018,target.left[1]),target.left],"typed EvidenceSet",PALETTE["purple"],False,True,(2018,target.left[1]-18))
    return c


def agent_collaboration() -> Canvas:
    c=base_canvas("D05_L2_Agent_Collaboration","D05 — L2 multi-agent collaboration and owned decision logic",2550,1200,"Agents are workflow components with typed contracts; deterministic drafts and protected fields prevent free-form model control.")
    c.boundary("Specialist analysis (parallel)",30,100,470,1030,PALETTE["purple"],PALETTE["purple_fill"])
    c.boundary("Adversarial research",540,100,740,1030,PALETTE["green"],PALETTE["green_fill"])
    c.boundary("Proposal + risk review",1320,100,760,1030,PALETTE["red"],PALETTE["red_fill"])
    c.boundary("Decision + explanation",2120,100,400,1030,PALETTE["blue"],PALETTE["blue_fill"])
    n=c.node
    specialists=[]
    for key,title,lines,y in [
        ("market","Market Analyst",["signal score + trends","claims reference evidence"],175),
        ("fund","Fundamental Analyst",["ratios + financial health","claims reference evidence"],390),
        ("news","News Analyst",["events + macro impact","claims reference evidence"],605),
        ("sent","Sentiment Analyst",["public mood + noise warning","claims reference evidence"],820),
    ]: specialists.append(n(key,title,lines,75,y,380,130,PALETTE["purple_fill"],PALETTE["purple"],"agent node"))
    merge=n("merge","Specialist-report fan-in",["SPECIALIST_REPORT → REPORTS","selected agents only","evidence_refs retained"],575,185,300,135,PALETTE["green_fill"],PALETTE["green"],"typed join")
    bull=n("bull","Bull Researcher",["growth factors + supporting claims","score positive case"],935,155,300,135,PALETTE["green_fill"],PALETTE["green"],"agent node")
    bear=n("bear","Bear Researcher",["weakness + downside factors","score negative case"],935,365,300,135,PALETTE["red_fill"],PALETTE["red"],"agent node")
    manager=n("manager","Research Manager",["compare agreement/conflicts","position scores","record round + stopped flag"],690,590,330,155,PALETTE["green_fill"],PALETTE["green"],"agent node")
    loop=n("loop","Bounded debate controller",["max_iterations = research_depth","explicit typed loop dependency","runtime repeats the control node only","upstream model agents are not multiplied","stop at limit or convergence"],690,830,330,190,PALETTE["orange_fill"],PALETTE["orange"],"owned algorithm")
    proposal=n("proposal","Proposal Builder",["BUY/HOLD/SELL thresholds","confidence from case balance","conditions + evidence lineage"],1360,270,320,160,PALETTE["red_fill"],PALETTE["red"],"owned algorithm + agent")
    risk_nodes=[]
    for key,title,lines,y in [
        ("aggr","Aggressive Risk",["higher reward tolerance","position/loss constraint view"],520),
        ("bal","Balanced Risk",["reward-loss trade-off","profile-consistent view"],715),
        ("cons","Conservative Risk",["loss prevention + uncertainty","strict constraint view"],910),
    ]: risk_nodes.append(n(key,title,lines,1730,y,305,130,PALETTE["red_fill"],PALETTE["red"],"agent node"))
    risk_join=n("risk_join","Risk-view join",["RISK_VIEW → RISK_VIEWS","all three perspectives"],1360,700,300,120,PALETTE["gray_fill"],PALETTE["gray"],"typed join")
    decision=n("decision","Decision Validator",["consistency with evidence","investor loss/position limits","confidence + warning rules","NO_DECISION when invalid"],2160,355,320,180,PALETTE["blue_fill"],PALETTE["blue"],"owned policy gate")
    report=n("report","Report Renderer",["executive summary","agent/debate/risk sections","evidence hashes + trace","PDF / JSON artifact"],2160,710,320,175,PALETTE["blue_fill"],PALETTE["blue"],"output node")
    for index,s in enumerate(specialists):
        c.edge(f"sp_{index}",[s.right,(520,s.right[1]),(520,merge.left[1]),merge.left],"SPECIALIST_REPORT",PALETTE["purple"],False,True,(520,s.right[1]-18))
    lr(c,"merge_bull",merge,bull,"reports[]",corridor=900,color=PALETTE["green"],label_at=(900,220))
    lr(c,"merge_bear",merge,bear,"reports[]",corridor=900,color=PALETTE["red"],label_at=(900,420))
    c.edge("bull_manager",[bull.left,(900,bull.left[1]),(900,540),(manager.top[0],540),manager.top],"bull case",PALETTE["green"],False,True,(930,540))
    c.edge("bear_manager",[bear.bottom,(1085,555),(855,555),manager.top],"bear case",PALETTE["red"],False,True,(1085,555))
    tb(c,"manager_loop",manager,loop,"RESEARCH_CASES\nround state",corridor=800,color=PALETTE["orange"],label_at=(855,800))
    c.edge("loop_back",[loop.left,(625,loop.left[1]),(625,560),(675,560),(675,manager.left[1]),manager.left],"loop=true\nnext round if not stopped",PALETTE["orange"],True,True,(625,755))
    c.edge("loop_proposal",[loop.right,(1300,loop.right[1]),(1300,proposal.left[1]),proposal.left],"final cases\nposition scores",PALETTE["green"],False,True,(1300,640))
    for index,risk in enumerate(risk_nodes):
        c.edge(f"proposal_risk_{index}",[proposal.right,(1705,proposal.right[1]),(1705,risk.left[1]),risk.left],"proposal + investor policy",PALETTE["red"],False,True,(1705,risk.left[1]-18))
        c.edge(f"risk_join_{index}",[risk.left,(1690,risk.left[1]),(1690,risk_join.right[1]),risk_join.right],"risk view",PALETTE["red"],False,True,(1688,risk.left[1]+18))
    c.edge("join_decision",[risk_join.bottom,(risk_join.bottom[0],900),(2100,900),(2100,decision.left[1]),decision.left],"RISK_VIEWS\n+ protected proposal fields",PALETTE["blue"],False,True,(2100,620))
    tb(c,"decision_report",decision,report,"Decision + claims + warnings",corridor=625,color=PALETTE["blue"],label_at=(2320,625))
    c.note("model_note","Model call boundary",["Quick/deep model receives prompt + typed input","Gateway requires JSON and retries invalid output","Narrative may improve; evidence refs, scores, action, confidence, loop state, lineage and disclaimer stay protected"],1060,950,580,145,PALETTE["gray_fill"],PALETTE["gray"],"note")
    return c


def service_architecture() -> Canvas:
    c=base_canvas("D06_L1_Service_Architecture","D06 — L1 application services, APIs, events, and data ownership",2300,1240,"Docker deployment services and request/event paths. Secret-bearing connection state remains inside the API process session store.")
    c.boundary("Presentation",30,100,390,1060,PALETTE["blue"],PALETTE["blue_fill"])
    c.boundary("Application services",455,100,1100,1060,PALETTE["teal"],PALETTE["teal_fill"])
    c.boundary("Infrastructure",1590,100,680,1060,PALETTE["gray"],PALETTE["gray_fill"])
    n=c.node
    ui=n("ui","React / Nginx frontend :5173",["Overview + New Analysis","Agent Room + Reports + Runs","Workflow Lab + Profile + Connections","numeric controls clamp contract ranges","api.ts formats nested validation errors"],70,180,310,205,PALETTE["blue_fill"],PALETTE["blue"],"container")
    api=n("api","FastAPI API :8000",["auth/profile/connections/catalog","workflow CRUD/validate/publish","run create/cancel/resume","SSE events/activity/lineage","report history/export"],500,160,330,220,PALETTE["teal_fill"],PALETTE["teal"],"container")
    session=n("session","SessionConnectionStore",["secret input + verification","runtime dictionaries only","not persisted"],500,455,330,140,PALETTE["orange_fill"],PALETTE["orange"],"in-process store")
    workflow=n("workflow","Workflow service :8001",["internal_validate","WorkflowRuntime.run","distributed executors","checkpoint + final status"],930,150,330,185,PALETTE["teal_fill"],PALETTE["teal"],"container")
    evidence=n("evidence","Evidence service :8002",["provider-chain routing","normalization/calculation","evidence time policy","ProviderError → safe HTTP 502 detail"],930,430,330,165,PALETTE["amber_fill"],PALETTE["amber"],"container")
    model=n("model","Model gateway :8003",["typed model client","JSON validation + retry","protected-field merge"],930,665,330,150,PALETTE["purple_fill"],PALETTE["purple"],"container")
    report=n("report","Report service :8004",["detailed report assembly","PDF/JSON artifact","SHA-256 metadata"],930,900,330,150,PALETTE["blue_fill"],PALETTE["blue"],"container")
    router=n("router","remote_executor routing",["31 NodeSpec types","evidence/model/report groups","NodeTask ↔ NodeResult","non-success detail → RuntimeError"],1320,455,195,185,PALETTE["gray_fill"],PALETTE["gray"],"adapter")
    postgres=n("postgres","PostgreSQL 16",["users + profiles","workflow/version + run","events + evidence + model calls","reports + artifacts"],1635,170,280,190,PALETTE["gray_fill"],PALETTE["gray"],"database")
    redis=n("redis","Redis Streams 7.4",["run event transport","consumer groups","progress + completion events"],1945,170,280,155,PALETTE["gray_fill"],PALETTE["gray"],"event bus")
    artifact=n("artifact","Artifact volume",["JSON/PDF report files","path + SHA-256"],1635,470,280,130,PALETTE["gray_fill"],PALETTE["gray"],"storage")
    providers=n("providers","External data APIs",["Yahoo, Alpha Vantage, FRED","Polymarket, StockTwits, Reddit","Frankfurter.dev historical FX"],1945,470,280,155,PALETTE["amber_fill"],PALETTE["amber"],"external")
    models=n("models","External model APIs",["OpenAI-compatible, Anthropic, Gemini","Azure OpenAI, AWS Bedrock","or deterministic fixture"],1945,725,280,155,PALETTE["purple_fill"],PALETTE["purple"],"external")
    migration=n("migration","Alembic migrate job",["upgrade head before services","Postgres health dependency"],1635,760,280,130,PALETTE["gray_fill"],PALETTE["gray"],"job")
    lr(c,"ui_api",ui,api,"HTTPS /api/v1\nJWT + JSON",corridor=440,color=PALETTE["blue"],label_at=(440,250))
    tb(c,"api_session",api,session,"credentials\nverification state",corridor=415,color=PALETTE["orange"],label_at=(665,415))
    lr(c,"api_workflow",api,workflow,"WorkflowTask\nHTTP JSON",corridor=880,color=PALETTE["teal"],label_at=(880,230))
    lr(c,"workflow_router",workflow,router,"NodeTask",corridor=1290,color=PALETTE["teal"],label_at=(1290,255))
    c.edge("router_evidence",[router.left,(1288,router.left[1]),(1288,evidence.right[1]),evidence.right],"evidence nodes :8002",PALETTE["amber"],False,True,(1288,470))
    c.edge("router_model",[router.left,(1300,router.left[1]),(1300,model.right[1]),model.right],"agent/model nodes :8003",PALETTE["purple"],False,True,(1300,735))
    c.edge("router_report",[router.left,(1312,router.left[1]),(1312,report.right[1]),report.right],"report node :8004",PALETTE["blue"],False,True,(1312,970))
    pg_routes = [
        [api.top, (api.top[0], 120), (1570, 120), (1570, postgres.left[1]), postgres.left],
        [workflow.right, (1570, workflow.right[1]), (1570, postgres.left[1]), postgres.left],
        [evidence.bottom, (evidence.bottom[0], 640), (1570, 640), (1570, postgres.left[1]), postgres.left],
        [model.right, (1570, model.right[1]), (1570, postgres.left[1]), postgres.left],
        [report.right, (1570, report.right[1]), (1570, postgres.left[1]), postgres.left],
    ]
    for index,points in enumerate(pg_routes):
        c.edge(f"pg_{index}",points,"repositories / transactions" if index == 0 else "",PALETTE["gray"],False,True,(1570,385))
    redis_routes = [
        [api.top, (api.top[0], 120), (1930, 120), (1930, redis.left[1]), redis.left],
        [workflow.top, (workflow.top[0], 120), (1930, 120), (1930, redis.left[1]), redis.left],
        [evidence.bottom, (evidence.bottom[0], 640), (1930, 640), (1930, redis.left[1]), redis.left],
        [model.right, (1930, model.right[1]), (1930, redis.left[1]), redis.left],
        [report.right, (1930, report.right[1]), (1930, redis.left[1]), redis.left],
    ]
    for index,points in enumerate(redis_routes):
        c.edge(f"redis_{index}",points,"RunEvent stream" if index == 0 else "",PALETTE["teal"],True,True,(1875,345))
    c.edge("evidence_external",[evidence.bottom,(evidence.bottom[0],640),(1930,640),(1930,providers.left[1]),providers.left],"HTTPS\nraw provider payload",PALETTE["amber"],False,True,(1930,555))
    c.edge("model_external",[model.right,(1930,model.right[1]),(1930,models.left[1]),models.left],"prompt → model text",PALETTE["purple"],False,True,(1930,760))
    lr(c,"report_artifact",report,artifact,"write + hash",corridor=1580,color=PALETTE["blue"],label_at=(1580,1020))
    c.edge("migrate_pg",[migration.left,(1600,migration.left[1]),(1600,postgres.left[1]),postgres.left],"schema before startup",PALETTE["gray"],False,True,(1600,675))
    c.note("secret","Trust boundary",["Only verified session settings are passed to runtime services.","API keys and AWS credentials are excluded from persisted rows, events, reports, and artifacts."],500,875,330,145,PALETTE["gray_fill"],PALETTE["gray"],"note")
    return c


def master_system() -> Canvas:
    c=base_canvas("D07_L0_Master_System","D07 — L0 OmniTrade master control/data/collaboration model",3400,2050,"Read left-to-right and top-to-bottom. Every connector names the message/data and the receiving responsibility; routes use reserved corridors.")
    c.boundary("A. User control plane",30,100,620,730,PALETTE["blue"],PALETTE["blue_fill"])
    c.boundary("B. API + run composition",690,100,660,730,PALETTE["teal"],PALETTE["teal_fill"])
    c.boundary("C. Owned workflow engine",1390,100,690,730,PALETTE["orange"],PALETTE["orange_fill"])
    c.boundary("D. Evidence subsystem",30,890,2050,1080,PALETTE["amber"],PALETTE["amber_fill"])
    c.boundary("E. Agent/research/risk subsystem",2120,100,1245,1350,PALETTE["purple"],PALETTE["purple_fill"])
    c.boundary("F. Output, observability, persistence",2120,1510,1245,460,PALETTE["gray"],PALETTE["gray_fill"])
    n=c.node
    profile=n("profile","Profile panel",["default ticker/model/providers","horizon + experience","max loss + position","excluded sectors"],70,170,250,165,PALETTE["blue_fill"],PALETTE["blue"],"user input")
    connections=n("connections","Connections panel",["data/model provider","key/URL/region/model IDs","verify + discover models","secrets session-only"],360,170,250,180,PALETTE["blue_fill"],PALETTE["blue"],"user input")
    workflow_lab=n("workflow_lab","Workflow Lab",["31 typed node types","ports + edges + loop flag","timeouts/retry/failure policy","budget + publish version"],70,445,250,190,PALETTE["blue_fill"],PALETTE["blue"],"user input")
    analysis=n("analysis","New Analysis",["ticker + as-of","analysts + depth + risk","5 provider chains","quick/deep models","freshness + output options","budget default 900s; ranges clamped"],360,445,250,220,PALETTE["blue_fill"],PALETTE["blue"],"user input")
    api=n("api","FastAPI boundary",["authenticate owner","validate request DTO","resolve published workflow","202 Accepted + run ID"],735,165,260,165,PALETTE["teal_fill"],PALETTE["teal"],"API :8000")
    composer=n("composer","Run composer",["Pydantic range/enum/chain validation","copy profile policy + run configuration","filter unselected analysts","override timeout/depth/freshness","clear fixture fallback on live fetch","bind verified connections"],1035,135,270,225,PALETTE["teal_fill"],PALETTE["teal"],"owned service")
    version=n("version","Immutable workflow snapshot",["definition + content hash","schema/version + budget","33 nodes / 48 edges default"],735,450,260,145,PALETTE["teal_fill"],PALETTE["teal"],"domain")
    run=n("run","Run + trace context",["configuration + investor policy","trace_id + status","runtime/provider/model budgets"],1035,470,270,155,PALETTE["teal_fill"],PALETTE["teal"],"domain")
    validator=n("validator","WorkflowValidator",["start/end + reachability","known nodes/config","typed ports + required inputs","bounded-cycle + budget safety","count actual model nodes × retries","do not multiply full graph by depth"],1430,145,275,220,PALETTE["orange_fill"],PALETTE["orange"],"owned algorithm")
    scheduler=n("scheduler","Wave scheduler",["parents terminal → READY","stable sort + parallel cap","async wave execution","cancel/deadlock detection"],1755,150,280,190,PALETTE["orange_fill"],PALETTE["orange"],"owned algorithm")
    executor=n("executor","Node execution policy",["typed input aggregation","timeout + retry/backoff","fallback provider","required/optional classification"],1430,470,275,190,PALETTE["orange_fill"],PALETTE["orange"],"owned algorithm")
    recovery=n("recovery","Checkpoint + recovery",["save after every wave","node states + event IDs","resume without duplicate work","reconcile late completion"],1755,470,280,190,PALETTE["orange_fill"],PALETTE["orange"],"owned algorithm")
    data_providers=n("data_providers","Data providers",["Yahoo: market/fund/news/sentiment","Alpha: market/fund/news/sent/macro","FRED: rates (DGS10)","Polymarket: macro/prediction text","StockTwits/Reddit: sentiment","Frankfurter.dev: historical FX conversion"],70,960,390,225,PALETTE["amber_fill"],PALETTE["amber"],"external systems")
    router=n("provider_router","Provider-chain router",["capability + user order","first real-provider success","classify HTTP / connection errors","no fixture fallback for live fetch","provider budget + historical FX"],510,970,300,205,PALETTE["orange_fill"],PALETTE["orange"],"owned adapter")
    fetch=n("fetch","Five fetch nodes (parallel)",["market → RAW_MARKET","fundamentals → RAW_FUNDAMENTALS","news/macro/sentiment → RAW_TEXT","timestamp + provider + source URL","provider failure becomes safe 502 detail"],860,960,350,215,PALETTE["amber_fill"],PALETTE["amber"],"workflow subsystem")
    normalize=n("normalize","Normalization",["numeric/schema coercion","units + base currency","text + metadata cleaning","content hash + quality flags"],1260,980,300,180,PALETTE["cyan_fill"],PALETTE["cyan"],"owned computation")
    calc=n("calc","Deterministic calculations",["momentum + SMA20/SMA50","RSI14 + annualized volatility","signal score","profit/debt/value ratios"],1610,970,390,190,PALETTE["teal_fill"],PALETTE["teal"],"owned algorithms")
    join=n("evidence_join","Evidence join",["collection port compatibility","required/optional branches","merge normalized + calculated items"],1050,1310,330,160,PALETTE["teal_fill"],PALETTE["teal"],"owned join")
    guard=n("time_guard","Evidence time/quality guard",["as_of reproducibility","reject future data","reject stale > configured hours","degrade only when allowed"],1500,1310,360,175,PALETTE["teal_fill"],PALETTE["teal"],"owned policy")
    evidence_store=n("evidence_store","Evidence lineage",["EvidenceItem + hash","provider + URL + timestamps","claim evidence_refs","quality flags"],1180,1670,360,165,PALETTE["gray_fill"],PALETTE["gray"],"persistent contract")
    model_providers=n("model_providers","Third-party model APIs",["OpenAI-compatible families","Anthropic / Gemini / Azure","AWS Bedrock (incl. Anthropic)","Ollama or deterministic fixture"],2160,175,300,185,PALETTE["purple_fill"],PALETTE["purple"],"external systems")
    model_gateway=n("model_gateway","Typed model gateway",["client routing + prompt","JSON extraction + validation","retry invalid output","merge narrative only","protect scores/action/lineage"],2500,165,300,205,PALETTE["purple_fill"],PALETTE["purple"],"owned boundary")
    analysts=n("analysts","Four specialist agents",["market / fundamental","news / sentiment","EvidenceSet → AgentReport","claims + risks + evidence refs"],2160,500,300,190,PALETTE["purple_fill"],PALETTE["purple"],"agent subsystem")
    research=n("research","Bull + Bear + Manager",["parallel positive/negative cases","compare conflicts + agreement","position scores","typed ResearchCase(s)"],2500,500,300,190,PALETTE["green_fill"],PALETTE["green"],"agent subsystem")
    debate=n("debate","Bounded debate",["round limit = research_depth","explicit typed loop dependency","repeat control node only","do not multiply all model agents","stop flag + convergence; never unbounded"],2840,490,300,215,PALETTE["orange_fill"],PALETTE["orange"],"owned algorithm")
    proposal=n("proposal","Proposal builder",["case-balance thresholds","BUY/HOLD/SELL","confidence + conditions","evidence lineage"],2160,840,300,185,PALETTE["red_fill"],PALETTE["red"],"agent + algorithm")
    risks=n("risks","Three risk agents",["aggressive / balanced / conservative","proposal + InvestorPolicy","reward/loss/uncertainty views"],2500,840,300,175,PALETTE["red_fill"],PALETTE["red"],"agent subsystem")
    decision=n("decision","Decision validator",["join 3 risk views","evidence/claim consistency","loss + position + sector limits","NO_DECISION + warnings when unsafe"],2840,840,300,205,PALETTE["blue_fill"],PALETTE["blue"],"owned policy gate")
    report=n("report","Report service",["decision + agents + debate + risk","settings + trace + node statuses","JSON/PDF + disclaimer"],2160,1580,300,175,PALETTE["blue_fill"],PALETTE["blue"],"output")
    events=n("events","Event stream / Agent Room",["node/run state events","Redis Streams + activity API","400 ms UI polling / SSE endpoint"],2500,1580,300,165,PALETTE["teal_fill"],PALETTE["teal"],"observability")
    persistence=n("persistence","PostgreSQL + artifacts",["run/event/evidence/model call rows","workflow/version/profile rows","artifact volume + SHA-256"],2840,1580,300,175,PALETTE["gray_fill"],PALETTE["gray"],"infrastructure")
    ui_output=n("ui_output","Reports / Runs UI",["final action + confidence","agent/debate/risk views","lineage + export","no brokerage execution"],2500,1810,300,135,PALETTE["blue_fill"],PALETTE["blue"],"user output")
    # Control-plane routes.
    c.edge("profile_composer",[profile.top,(profile.top[0],125),(composer.top[0],125),composer.top],"UserProfile\nInvestorPolicy + defaults",PALETTE["blue"],False,True,(740,125))
    c.edge("connections_composer",[connections.top,(connections.top[0],135),(composer.top[0],135),composer.top],"verified runtime settings\n(no secrets persisted)",PALETTE["blue"],False,True,(980,135))
    c.edge("lab_version",[workflow_lab.bottom,(workflow_lab.bottom[0],705),(version.bottom[0],705),version.bottom],"validate + publish\nWorkflowDefinition",PALETTE["blue"],False,True,(545,705))
    lr(c,"analysis_api",analysis,api,"POST /runs\nRunRequest JSON",corridor=670,color=PALETTE["blue"],label_at=(670,620))
    lr(c,"api_composer",api,composer,"owner + request",corridor=1015,color=PALETTE["teal"],label_at=(1015,230))
    tb(c,"version_run",version,run,"workflow_version_id",corridor=660,color=PALETTE["teal"],label_at=(900,660))
    lr(c,"composer_run",composer,run,"configured definition\n+ policy + budgets",corridor=1325,color=PALETTE["teal"],label_at=(1325,420))
    lr(c,"run_validator",run,validator,"definition + catalog",corridor=1370,color=PALETTE["orange"],label_at=(1370,555))
    lr(c,"validator_scheduler",validator,scheduler,"valid graph",corridor=1730,color=PALETTE["orange"],label_at=(1730,230))
    tb(c,"scheduler_executor",scheduler,executor,"ready node wave",corridor=410,color=PALETTE["orange"],label_at=(1885,410))
    lr(c,"executor_recovery",executor,recovery,"state + event after node",corridor=1730,color=PALETTE["orange"],label_at=(1730,560))
    c.edge("recovery_scheduler",[recovery.right,(2055,recovery.right[1]),(2055,390),(1895,390),scheduler.bottom],"checkpointed next wave / resume",PALETTE["orange"],True,True,(2055,390))
    # Evidence routes use the vertical gap at y 850 and internal horizontal corridors.
    c.edge("executor_fetch",[executor.bottom,(executor.bottom[0],850),(fetch.top[0],850),fetch.top],"NodeTask: fetch_*\nprovider chain + ticker + as_of",PALETTE["orange"],False,True,(1290,850))
    lr(c,"providers_router",data_providers,router,"HTTPS request / response\nprovider-native JSON",corridor=485,color=PALETTE["amber"],label_at=(485,1085))
    lr(c,"router_fetch",router,fetch,"first successful payload\nerrors retained for degradation",corridor=835,color=PALETTE["amber"],label_at=(835,1085))
    lr(c,"fetch_normalize",fetch,normalize,"RAW_* typed ports",corridor=1235,color=PALETTE["cyan"],label_at=(1235,1080))
    lr(c,"normalize_calc",normalize,calc,"normalized market/fundamentals",corridor=1585,color=PALETTE["teal"],label_at=(1585,1070))
    c.edge("normalize_join",[normalize.bottom,(1410,1260),(1215,1260),join.top],"normalized text/market/fundamentals",PALETTE["cyan"],False,True,(1335,1260))
    c.edge("calc_join",[calc.bottom,(1805,1240),(1440,1240),(1440,1390),join.right],"technical + ratio Evidence",PALETTE["teal"],False,True,(1600,1240))
    lr(c,"join_guard",join,guard,"EvidenceSet\nhashes + quality flags",corridor=1440,color=PALETTE["teal"],label_at=(1440,1390))
    tb(c,"guard_store",guard,evidence_store,"accepted evidence + lineage",corridor=1580,color=PALETTE["teal"],label_at=(1700,1580))
    c.edge("guard_analysts",[guard.right,(2100,guard.right[1]),(2100,analysts.left[1]),analysts.left],"EvidenceSet\nselected analyst nodes",PALETTE["purple"],False,True,(2100,1210))
    # Model and agent collaboration routes.
    lr(c,"models_gateway",model_providers,model_gateway,"prompt → text response\nprovider auth stays in gateway",corridor=2480,color=PALETTE["purple"],label_at=(2480,265))
    c.edge("gateway_agents",[model_gateway.bottom,(2650,430),(2310,430),analysts.top],"typed completion\nvalidated AgentReport",PALETTE["purple"],False,True,(2480,430))
    tb(c,"gateway_research",model_gateway,research,"typed research narrative",corridor=430,color=PALETTE["purple"],label_at=(2650,430))
    c.edge("gateway_debate",[model_gateway.right,(3170,model_gateway.right[1]),(3170,debate.right[1]),debate.right],"optional narrative help\nprotected loop state",PALETTE["purple"],True,True,(3170,460))
    lr(c,"analysts_research",analysts,research,"SPECIALIST_REPORTS\nclaims + evidence refs",corridor=2480,color=PALETTE["green"],label_at=(2480,595))
    lr(c,"research_debate",research,debate,"RESEARCH_CASES\nround + position scores",corridor=2820,color=PALETTE["orange"],label_at=(2820,595))
    c.edge("debate_back",[debate.bottom,(2990,760),(2650,760),research.bottom],"typed loop dependency\nruntime repeats control node only",PALETTE["orange"],True,True,(2820,760))
    c.edge("debate_proposal",[debate.left,(2820,debate.left[1]),(2820,790),(2310,790),proposal.top],"final cases",PALETTE["green"],False,True,(2550,790))
    lr(c,"proposal_risks",proposal,risks,"Proposal + InvestorPolicy",corridor=2480,color=PALETTE["red"],label_at=(2480,930))
    lr(c,"risks_decision",risks,decision,"RISK_VIEWS",corridor=2820,color=PALETTE["red"],label_at=(2820,930))
    # Output and observation routes.
    c.edge("decision_report",[decision.bottom,(2990,1490),(2310,1490),report.top],"Decision + claims + warnings",PALETTE["blue"],False,True,(2650,1490))
    c.edge("recovery_events",[recovery.right,(2100,recovery.right[1]),(2100,1480),(events.top[0],1480),events.top],"RunEvent stream\ntrace_id + node state",PALETTE["teal"],True,True,(2350,1480))
    lr(c,"report_events",report,events,"report.ready event",corridor=2480,color=PALETTE["teal"],label_at=(2480,1665))
    lr(c,"events_persist",events,persistence,"append events / status",corridor=2820,color=PALETTE["gray"],label_at=(2820,1660))
    c.edge("report_persist",[report.right,(2480,report.right[1]),(2480,1780),(2990,1780),persistence.bottom],"JSON/PDF artifact + SHA-256",PALETTE["gray"],False,True,(2730,1780))
    c.edge("output_ui",[report.bottom,(2310,1985),(2650,1985),ui_output.bottom],"GET report/history/export",PALETTE["blue"],False,True,(2480,1985))
    c.edge("events_ui",[events.bottom,ui_output.top],"activity polling / SSE",PALETTE["teal"],False,True,(2650,1780))
    return c


def sequence() -> Canvas:
    c=base_canvas("D08_L0_End_to_End_Sequence","D08 — L0 end-to-end new-analysis sequence",3000,2050,"One run from browser input to explainable report. Parallel and loop frames expose orchestration rather than treating agents as black boxes.")
    actors=[
        ("user","User",80,PALETTE["blue"]),("ui","React UI",360,PALETTE["blue"]),("api","API :8000",650,PALETTE["teal"]),("db","Postgres",940,PALETTE["gray"]),("wf","Workflow :8001",1230,PALETTE["orange"]),("ev","Evidence :8002",1520,PALETTE["amber"]),("data","Data APIs",1810,PALETTE["amber"]),("mg","Model gateway :8003",2100,PALETTE["purple"]),("models","Model APIs",2390,PALETTE["purple"]),("report","Report :8004",2680,PALETTE["blue"]),
    ]
    lifeline: dict[str,Node]={}
    for key,title,x,color in actors:
        lifeline[key]=c.node(key,title,[],x,95,220,70,"#FFFFFF",color,"lifeline")
        c.edge(f"life_{key}",[(x+110,165),(x+110,1970)],"",color,True,False)
    def msg(key:str,src:str,dst:str,y:float,label:str,color:str=PALETTE["gray"],dashed:bool=False)->None:
        a=lifeline[src].x+110;b=lifeline[dst].x+110
        if src == dst:
            c.edge(key,[(a,y),(a+95,y),(a+95,y+30),(a,y+30)],label,color,dashed,True,(a+48,y-22))
        else:
            start=(a,y);end=(b,y)
            c.edge(key,[start,end],label,color,dashed,True,((a+b)/2,y-22))
    # Frames are dashed boundaries; their routes remain horizontal between lifelines.
    c.boundary("1. Configure and accept",45,185,2860,310,PALETTE["blue"],"#FFFFFF",True)
    c.boundary("2. Validate, schedule, and acquire evidence (parallel)",45,525,2860,490,PALETTE["amber"],"#FFFFFF",True)
    c.boundary("3. Specialist agents + bounded research debate",45,1045,2860,480,PALETTE["purple"],"#FFFFFF",True)
    c.boundary("4. Risk validation, report, persistence, and observation",45,1555,2860,400,PALETTE["teal"],"#FFFFFF",True)
    msg("s1","user","ui",235,"1  Save profile / connections / workflow choices",PALETTE["blue"])
    msg("s2","ui","api",295,"2  PUT profile/connection/workflow; verify and publish",PALETTE["blue"])
    msg("s3","api","db",355,"3  Persist non-secret profile + immutable workflow version",PALETTE["gray"])
    msg("s4","user","ui",415,"4  Select ticker, as-of, agents, chains, models, budgets",PALETTE["blue"])
    msg("s5","ui","api",475,"5  POST /runs : clamped RunRequest; nested validation errors formatted",PALETTE["blue"])
    msg("s6","api","db",580,"6  Create QUEUED Run + trace_id + configuration/policy",PALETTE["gray"])
    msg("s7","api","wf",640,"7  WorkflowTask: configured definition + runtime connections",PALETTE["orange"])
    msg("s8","wf","wf",700,"8  Validate graph; model budget counts actual nodes × retries (not full graph × depth)",PALETTE["orange"])
    msg("s9","wf","wf",760,"9  Restore checkpoint or initialize NodeRuns; select ready wave",PALETTE["orange"])
    msg("s10","wf","ev",820,"10  par: NodeTask × 5 fetch branches",PALETTE["amber"])
    msg("s11","ev","data",880,"11  real-provider-chain HTTPS; no fixture fallback; Frankfurter FX when needed",PALETTE["amber"])
    msg("s12","data","ev",940,"12  raw payload or classified HTTP/connection/provider error",PALETTE["amber"],True)
    msg("s13","ev","wf",1000,"13  EvidenceSet or safe HTTP 502 detail → remote RuntimeError",PALETTE["teal"],True)
    msg("s14","wf","wf",1100,"14  Join branches; time guard; checkpoint wave",PALETTE["orange"])
    msg("s15","wf","mg",1160,"15  par: 4 typed analyst tasks with evidence refs",PALETTE["purple"])
    msg("s16","mg","models",1220,"16  prompt + requested model / temperature / reasoning",PALETTE["purple"])
    msg("s17","models","mg",1280,"17  model text",PALETTE["purple"],True)
    msg("s18","mg","mg",1340,"18  extract JSON; validate schema; retry; protect facts",PALETTE["purple"])
    msg("s19","mg","wf",1400,"19  AgentReports → Bull/Bear → Manager",PALETTE["green"],True)
    msg("s20","wf","wf",1460,"20  loop 1..depth: repeat bounded control node; do not rerun every model agent",PALETTE["orange"])
    msg("s21","wf","mg",1605,"21  Proposal + 3 risk perspectives (parallel narratives)",PALETTE["red"])
    msg("s22","mg","wf",1665,"22  typed risk views; protected proposal fields retained",PALETTE["red"],True)
    msg("s23","wf","wf",1725,"23  deterministic decision validation against InvestorPolicy",PALETTE["blue"])
    msg("s24","wf","report",1785,"24  Decision + all node outputs + lineage + settings",PALETTE["blue"])
    msg("s25","report","db",1845,"25  persist report metadata + artifact SHA-256",PALETTE["gray"])
    msg("s26","wf","db",1905,"26  final checkpoint + RunEvent + terminal status",PALETTE["teal"])
    msg("s27","api","ui",1965,"27  activity/SSE and GET report/history/export",PALETTE["blue"],True)
    return c


def state_machine() -> Canvas:
    c=base_canvas("D09_Run_State_Machine","D09 — Run and node state machines",1850,1050,"Terminal and degradation behavior used by API, runtime, persistence, Agent Room, and recovery.")
    c.boundary("RunStatus",30,95,850,900,PALETTE["blue"],PALETTE["blue_fill"])
    c.boundary("NodeStatus",920,95,900,900,PALETTE["teal"],PALETTE["teal_fill"])
    n=c.node
    queued=n("queued","QUEUED",["accepted; background task pending"],90,170,220,90,PALETTE["blue_fill"],PALETTE["blue"],"state")
    running=n("running","RUNNING",["validated; waves executing"],390,170,220,90,PALETTE["blue_fill"],PALETTE["blue"],"state")
    degraded=n("degraded","DEGRADED",["optional failure or limit warning","report still available"],90,430,250,115,PALETTE["amber_fill"],PALETTE["amber"],"terminal")
    succeeded=n("succeeded","SUCCEEDED",["all required work complete"],390,430,220,90,PALETTE["green_fill"],PALETTE["green"],"terminal")
    failed=n("failed","FAILED",["validation / required node / deadlock"],650,430,190,105,PALETTE["red_fill"],PALETTE["red"],"terminal")
    cancelling=n("cancelling","CANCELLING",["cancel requested"],390,670,220,90,PALETTE["orange_fill"],PALETTE["orange"],"state")
    cancelled=n("cancelled","CANCELLED",["probe observed; nodes stopped"],90,840,230,90,PALETTE["gray_fill"],PALETTE["gray"],"terminal")
    interrupted=n("interrupted","INTERRUPTED",["worker/process loss","resume from checkpoint"],610,840,220,100,PALETTE["gray_fill"],PALETTE["gray"],"state")
    pending=n("pending","PENDING",["not yet eligible"],980,170,200,85,PALETTE["teal_fill"],PALETTE["teal"],"state")
    ready=n("ready","READY",["all parents terminal","inputs available"],1260,170,210,95,PALETTE["teal_fill"],PALETTE["teal"],"state")
    nrun=n("nrun","RUNNING",["attempt + timeout active"],1540,170,220,85,PALETTE["teal_fill"],PALETTE["teal"],"state")
    nsucc=n("nsucc","SUCCEEDED",["typed output emitted"],980,470,210,90,PALETTE["green_fill"],PALETTE["green"],"terminal")
    ndeg=n("ndeg","DEGRADED",["optional branch failure","warning output"],1260,470,210,100,PALETTE["amber_fill"],PALETTE["amber"],"terminal")
    nfail=n("nfail","FAILED",["attempts exhausted","required may fail run"],1540,470,220,105,PALETTE["red_fill"],PALETTE["red"],"terminal")
    skipped=n("skipped","SKIPPED",["unselected analyst / unreachable after policy"],980,780,230,105,PALETTE["gray_fill"],PALETTE["gray"],"terminal")
    ncancel=n("ncancel","CANCELLED",["run cancellation probe"],1510,790,230,90,PALETTE["gray_fill"],PALETTE["gray"],"terminal")
    lr(c,"q_r",queued,running,"background execution starts",color=PALETTE["blue"],label_at=(350,205))
    c.edge("r_s",[running.bottom,(500,365),succeeded.top],"all required success",PALETTE["green"],False,True,(520,360))
    c.edge("r_d",[running.left,(360,215),(360,385),(215,385),degraded.top],"optional failure / allowed degradation",PALETTE["amber"],False,True,(285,385))
    c.edge("r_f",[running.right,(635,215),(635,385),(745,385),failed.top],"validation, required failure, deadlock",PALETTE["red"],False,True,(710,385))
    c.edge("r_cg",[running.right,(870,running.right[1]),(870,cancelling.right[1]),cancelling.right],"cancel requested",PALETTE["orange"],False,True,(870,620))
    c.edge("cg_c",[cancelling.left,(340,715),(340,805),(205,805),cancelled.top],"probe observed",PALETTE["gray"],False,True,(330,805))
    c.edge("r_i",[running.right,(860,215),(860,790),(720,790),interrupted.top],"worker/process loss",PALETTE["gray"],True,True,(860,700))
    c.edge("i_r",[interrupted.right,(870,interrupted.right[1]),(870,140),(running.top[0],140),running.top],"resume: restore checkpoint",PALETTE["blue"],True,True,(720,140))
    lr(c,"p_ready",pending,ready,"parents terminal",color=PALETTE["teal"],label_at=(1220,210))
    lr(c,"ready_run",ready,nrun,"selected in bounded wave",color=PALETTE["teal"],label_at=(1510,210))
    c.edge("nr_s",[nrun.left,(1500,nrun.left[1]),(1500,410),(nsucc.top[0],410),nsucc.top],"valid typed output",PALETTE["green"],False,True,(1260,410))
    tb(c,"nr_d",nrun,ndeg,"optional failure after retry",corridor=390,color=PALETTE["amber"],label_at=(1500,390))
    tb(c,"nr_f",nrun,nfail,"required failure / attempts exhausted",corridor=390,color=PALETTE["red"],label_at=(1650,390))
    c.edge("p_skip",[pending.left,(940,pending.left[1]),(940,skipped.left[1]),skipped.left],"configuration removes node",PALETTE["gray"],False,True,(940,690))
    c.edge("nr_cancel",[nrun.right,(1790,nrun.right[1]),(1790,ncancel.right[1]),ncancel.right],"cancellation probe",PALETTE["gray"],False,True,(1790,700))
    c.edge("retry",[nfail.right,(1790,nfail.right[1]),(1790,120),(1650,120),nrun.top],"retry while attempt < max_attempts",PALETTE["orange"],True,True,(1790,300))
    return c


def deployment() -> Canvas:
    c=base_canvas("D10_Deployment","D10 — Docker Compose deployment",2100,1120,"Concrete containers, ports, volumes, health dependencies, and external trust boundaries from docker-compose.yml.")
    c.boundary("Client host",30,100,300,930,PALETTE["blue"],PALETTE["blue_fill"])
    c.boundary("Docker network: omnitrade-ai",370,100,1300,930,PALETTE["teal"],PALETTE["teal_fill"])
    c.boundary("External provider networks",1710,100,350,930,PALETTE["purple"],PALETTE["purple_fill"])
    n=c.node
    browser=n("browser","Browser",["localhost:5173","JWT held by frontend client"],70,230,220,110,PALETTE["blue_fill"],PALETTE["blue"],"device")
    frontend=n("frontend","frontend",["Nginx + React","host 5173 → container 80"],420,170,250,125,PALETTE["blue_fill"],PALETTE["blue"],"container")
    api=n("api","api",["uvicorn :8000","artifact volume","depends workflow + Redis + migrate"],750,160,270,150,PALETTE["teal_fill"],PALETTE["teal"],"container")
    workflow=n("workflow","workflow",["uvicorn :8001","WorkflowRuntime","depends Redis + migrate"],1090,160,260,145,PALETTE["orange_fill"],PALETTE["orange"],"container")
    evidence=n("evidence","evidence",["uvicorn :8002","provider/calculation nodes"],750,420,270,120,PALETTE["amber_fill"],PALETTE["amber"],"container")
    model=n("model","model-gateway",["uvicorn :8003","model clients + validation"],1090,420,260,120,PALETTE["purple_fill"],PALETTE["purple"],"container")
    report=n("report","report",["uvicorn :8004","artifact volume"],750,660,270,115,PALETTE["blue_fill"],PALETTE["blue"],"container")
    postgres=n("postgres","postgres:16-alpine",["DB omnitrade","health: pg_isready","postgres-data volume"],1390,650,235,145,PALETTE["gray_fill"],PALETTE["gray"],"container")
    redis=n("redis","redis:7.4-alpine",["appendonly yes","health: redis-cli ping","redis-data volume"],1390,385,235,145,PALETTE["gray_fill"],PALETTE["gray"],"container")
    migrate=n("migrate","migrate job",["alembic upgrade head","must complete before services"],1090,830,260,115,PALETTE["gray_fill"],PALETTE["gray"],"job")
    artifact=n("artifact","artifacts volume",["/data/artifacts","JSON + PDF reports"],750,860,270,110,PALETTE["gray_fill"],PALETTE["gray"],"volume")
    data=n("data","Data APIs",["Yahoo / Alpha / FRED","Polymarket / social feeds","Frankfurter.dev FX"],1760,330,250,145,PALETTE["amber_fill"],PALETTE["amber"],"external")
    llm=n("llm","Model APIs",["OpenAI-compatible / Anthropic / Gemini","Azure / AWS Bedrock"],1760,650,250,145,PALETTE["purple_fill"],PALETTE["purple"],"external")
    lr(c,"browser_front",browser,frontend,"HTTP :5173",corridor=350,color=PALETTE["blue"],label_at=(350,270))
    lr(c,"front_api",frontend,api,"/api/v1 reverse proxy",corridor=710,color=PALETTE["blue"],label_at=(710,230))
    lr(c,"api_workflow",api,workflow,"HTTP :8001",corridor=1055,color=PALETTE["teal"],label_at=(1055,225))
    c.edge("wf_evidence",[workflow.left,(1055,workflow.left[1]),(1055,evidence.right[1]),evidence.right],"HTTP :8002",PALETTE["amber"],False,True,(1055,430))
    tb(c,"wf_model",workflow,model,"HTTP :8003",corridor=365,color=PALETTE["purple"],label_at=(1220,365))
    c.edge("wf_report",[workflow.left,(1040,workflow.left[1]),(1040,report.right[1]),report.right],"HTTP :8004",PALETTE["blue"],False,True,(1040,670))
    redis_routes = [
        [api.top,(api.top[0],120),(1370,120),(1370,redis.left[1]),redis.left],
        [workflow.right,(1370,workflow.right[1]),(1370,redis.left[1]),redis.left],
        [evidence.bottom,(evidence.bottom[0],570),(1370,570),(1370,redis.left[1]),redis.left],
        [model.right,(1370,model.right[1]),(1370,redis.left[1]),redis.left],
        [report.right,(1370,report.right[1]),(1370,redis.left[1]),redis.left],
    ]
    pg_routes = [
        [api.top,(api.top[0],120),(1360,120),(1360,postgres.left[1]),postgres.left],
        [workflow.right,(1360,workflow.right[1]),(1360,postgres.left[1]),postgres.left],
        [evidence.bottom,(evidence.bottom[0],570),(1360,570),(1360,postgres.left[1]),postgres.left],
        [model.right,(1360,model.right[1]),(1360,postgres.left[1]),postgres.left],
        [report.right,(1360,report.right[1]),(1360,postgres.left[1]),postgres.left],
    ]
    for index,points in enumerate(redis_routes):
        c.edge(f"to_redis_{index}",points,"Redis Streams" if index == 0 else "",PALETTE["teal"],True,True)
    for index,points in enumerate(pg_routes):
        c.edge(f"to_pg_{index}",points,"SQLAlchemy" if index == 0 else "",PALETTE["gray"],False,True)
    c.edge("e_data",[evidence.bottom,(evidence.bottom[0],570),(1680,570),(1680,data.left[1]),data.left],"HTTPS",PALETTE["amber"],False,True,(1680,480))
    c.edge("m_llm",[model.bottom,(model.bottom[0],570),(1680,570),(1680,llm.left[1]),llm.left],"HTTPS",PALETTE["purple"],False,True,(1680,700))
    tb(c,"report_art",report,artifact,"write files",corridor=820,color=PALETTE["gray"],label_at=(885,820))
    lr(c,"migrate_pg",migrate,postgres,"schema migration",corridor=1370,color=PALETTE["gray"],label_at=(1370,900))
    return c


def plantuml_for(canvas: Canvas) -> str:
    lines=["@startuml",f"title {canvas.title}","skinparam shadowing false","skinparam linetype ortho","skinparam componentStyle rectangle","left to right direction"]
    for node in canvas.nodes:
        label="\\n".join([node.title,*node.lines])
        lines.append(f'rectangle "{label}" as {slug(node.key)} #{node.fill.lstrip("#")}')
    # Portable sources express topology; the VDX/SVG files keep exact routed geometry.
    for edge in canvas.edges:
        if len(edge.points)<2: continue
        # Only emit edges whose endpoints exactly touch known nodes.
        source=next((n for n in canvas.nodes if edge.points[0] in {n.left,n.right,n.top,n.bottom}),None)
        target=next((n for n in canvas.nodes if edge.points[-1] in {n.left,n.right,n.top,n.bottom}),None)
        if source and target:
            arrow="..>" if edge.dashed else "-->"
            label=edge.label.replace("\n"," ")
            lines.append(f"{slug(source.key)} {arrow} {slug(target.key)} : {label}")
    lines.append("@enduml")
    return "\n".join(lines)+"\n"


def build_xmi(canvases: list[Canvas]) -> str:
    packages: dict[str,list[tuple[str,str]]]={
        "L3 Domain Contracts":[(n.title,n.stereotype) for n in domain_contracts().nodes],
        "L3 Engine Kernel":[(n.title,n.stereotype) for n in runtime_kernel().nodes],
        "L3 Adapters":[(n.title,n.stereotype) for n in adapters().nodes],
        "L2 Evidence Subsystem":[(n.title,n.stereotype) for n in evidence_pipeline().nodes],
        "L2 Agent Subsystem":[(n.title,n.stereotype) for n in agent_collaboration().nodes],
        "L1 Application Services":[(n.title,n.stereotype) for n in service_architecture().nodes],
        "L1 Deployment":[(n.title,n.stereotype) for n in deployment().nodes],
        "L0 System Context":[(n.title,n.stereotype) for n in master_system().nodes],
    }
    out=['<?xml version="1.0" encoding="UTF-8"?>','<xmi:XMI xmi:version="2.1" xmlns:xmi="http://schema.omg.org/spec/XMI/2.1" xmlns:uml="http://www.eclipse.org/uml2/3.0.0/UML">',f'<uml:Model xmi:id="{stable_id("model","OmniTradeAI")}" name="OmniTradeAI">']
    seen: dict[str,str]={}
    for package,items in packages.items():
        pid=stable_id("package",package);out.append(f'<packagedElement xmi:type="uml:Package" xmi:id="{pid}" name="{escape(package)}">')
        for title,stereotype in items:
            name=f"{title} [{stereotype}]";eid=stable_id("element",f"{package}:{title}");seen[f"{package}:{title}"]=eid
            element_type="uml:Class" if stereotype in {"entity","contract","value object","state","terminal"} else "uml:Component"
            out.append(f'<packagedElement xmi:type="{element_type}" xmi:id="{eid}" name="{escape(name)}"/>')
        out.append('</packagedElement>')
    # Semantic dependencies are derived from every routed view with stable IDs.
    by_title: dict[str,str]={}
    for package,items in packages.items():
        for title,_ in items: by_title.setdefault(title,seen[f"{package}:{title}"])
    for canvas in canvases:
        for edge in canvas.edges:
            source=next((n for n in canvas.nodes if edge.points[0] in {n.left,n.right,n.top,n.bottom}),None)
            target=next((n for n in canvas.nodes if edge.points[-1] in {n.left,n.right,n.top,n.bottom}),None)
            if source and target and source.title in by_title and target.title in by_title:
                did=stable_id("dependency",f"{canvas.name}:{edge.key}")
                label=escape(edge.label.replace("\n"," / ") or edge.key)
                out.append(f'<packagedElement xmi:type="uml:Dependency" xmi:id="{did}" name="{label}" client="{by_title[source.title]}" supplier="{by_title[target.title]}"/>')
    # Exact 31-node catalog is retained as a semantic package.
    catalog_pid=stable_id("package","Workflow Node Catalog")
    out.append(f'<packagedElement xmi:type="uml:Package" xmi:id="{catalog_pid}" name="Workflow Node Catalog (31 owned node types)">')
    for node_type,spec in NODE_CATALOG.items():
        eid=stable_id("catalog-node",node_type)
        label=f"{node_type} [{spec.group}]"
        out.append(f'<packagedElement xmi:type="uml:Component" xmi:id="{eid}" name="{escape(label)}">')
        out.append(f'<ownedComment xmi:id="{stable_id("comment",node_type)}"><body>{escape(NODE_DESCRIPTIONS[node_type])}</body></ownedComment>')
        out.append('</packagedElement>')
    out.append('</packagedElement>')
    out.extend(['</uml:Model>','</xmi:XMI>'])
    return "\n".join(out)+"\n"


def manifest(canvases: list[Canvas]) -> dict[str,object]:
    workflow=defense_workflow()
    return {
        "generated_from": {
            "node_catalog": "omnitrade/engine/catalog.py",
            "workflow": "omnitrade/sample_workflow.py",
            "contracts": "omnitrade/contracts.py",
            "runtime": "omnitrade/engine/runtime.py",
            "validator": "omnitrade/engine/validator.py",
            "providers": "omnitrade/providers.py",
            "connections": "omnitrade/connections.py",
            "model_gateway": "omnitrade/model_gateway.py",
            "services": "omnitrade/services.py",
            "api": "omnitrade/api.py",
            "deployment": "docker-compose.yml",
        },
        "facts": {
            "catalog_node_types": len(NODE_CATALOG),
            "default_workflow_nodes": len(workflow.nodes),
            "default_workflow_edges": len(workflow.edges),
            "model_boundary": "decision support only; no brokerage execution",
        },
        "diagrams": [
            {"id":c.name,"title":c.title,"nodes":len(c.nodes),"edges":len(c.edges),"vdx":f"drawings/{c.name}.vdx","svg":f"previews/{c.name}.svg","plantuml":f"plantuml/{c.name}.puml"}
            for c in canvases
        ],
    }


def validate_routes(canvases: list[Canvas]) -> None:
    """Fail generation when an edge segment crosses an unrelated box interior."""
    problems: list[str] = []
    epsilon = 0.1
    for canvas in canvases:
        boxes = [*canvas.nodes, *canvas.notes]
        for edge in canvas.edges:
            endpoint_nodes = {
                node.key
                for node in boxes
                if edge.points[0] in {node.left, node.right, node.top, node.bottom}
                or edge.points[-1] in {node.left, node.right, node.top, node.bottom}
            }
            for start, end in zip(edge.points, edge.points[1:]):
                x1, y1 = start; x2, y2 = end
                if abs(x1 - x2) > epsilon and abs(y1 - y2) > epsilon:
                    problems.append(f"{canvas.name}:{edge.key}: non-orthogonal segment {start}->{end}")
                    continue
                for node in boxes:
                    if node.key in endpoint_nodes:
                        continue
                    if abs(y1 - y2) <= epsilon:
                        left, right = sorted((x1, x2))
                        crosses = node.y + epsilon < y1 < node.y + node.h - epsilon and max(left, node.x) < min(right, node.x + node.w) - epsilon
                    else:
                        top, bottom = sorted((y1, y2))
                        crosses = node.x + epsilon < x1 < node.x + node.w - epsilon and max(top, node.y) < min(bottom, node.y + node.h) - epsilon
                    if crosses:
                        problems.append(f"{canvas.name}:{edge.key}: segment {start}->{end} crosses {node.key}")
    if problems:
        raise RuntimeError("Diagram routing validation failed:\n" + "\n".join(problems))


def main() -> None:
    for directory in (OUT,DRAWINGS,PREVIEWS,SOURCES): directory.mkdir(parents=True,exist_ok=True)
    canvases=[domain_contracts(),runtime_kernel(),adapters(),evidence_pipeline(),agent_collaboration(),service_architecture(),master_system(),sequence(),state_machine(),deployment()]
    validate_routes(canvases)
    for canvas in canvases:
        (PREVIEWS/f"{canvas.name}.svg").write_text(render_svg(canvas),encoding="utf-8")
        (DRAWINGS/f"{canvas.name}.vdx").write_text(render_vdx(canvas),encoding="utf-8")
        (SOURCES/f"{canvas.name}.puml").write_text(plantuml_for(canvas),encoding="utf-8")
    xmi=build_xmi(canvases)
    (OUT/"OmniTradeAI-UML-2.1.xmi").write_text(xmi,encoding="utf-8")
    data=manifest(canvases)
    data["checksums"]={
        str(path.relative_to(OUT)).replace("\\","/"):hashlib.sha256(path.read_bytes()).hexdigest()
        for directory in (DRAWINGS,PREVIEWS,SOURCES)
        for path in sorted(directory.iterdir())
    }
    (OUT/"model-manifest.json").write_text(json.dumps(data,indent=2),encoding="utf-8")
    print(json.dumps({"diagrams":len(canvases),"catalog_nodes":len(NODE_CATALOG),"workflow_nodes":len(defense_workflow().nodes),"workflow_edges":len(defense_workflow().edges)},indent=2))


if __name__ == "__main__":
    main()
