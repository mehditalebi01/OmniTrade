# OmniTrade report diagrams for Visual Paradigm

This package recreates the engineering diagrams in `omnitrade_v5.6_final.pdf` as one Visual Paradigm project and adds the missing UML views. The models were reconciled with OmniTrade revision `c90900f0b38c169cfd50678c7baba84ae15ebf77`.

## Open this file

Open `OmniTradeAI-Professional-UML.vpp` in Visual Paradigm Community Edition 18.1 or later for the report model. Open `OmniTradeAI-Professional-UML-Architecture.vpp` for the enhanced project, which preserves the supplied diagrams and adds five native architecture views (25 diagrams in total). A paid license is not required to view or edit them. The PNG files in `visual-paradigm-exports/` and `architecture-exports/` are verified exports.

## Diagram index

1. `Figure 1 - Expanded use-case model of the implemented product boundary`
2. `Figure 2 - Agile incremental cycle with XP engineering practices`
3. `Figure 3 - XP verification and Continuous Integration pipeline`
4. `Figure 4 - Reconstructed function-point timing model`
5. `Figure 5 - OmniTrade high-level as-built architecture`
6. `Figure 6 - Integrated component architecture`
7. `Figure 14 - Package and module dependency model`
8. `Figure 15 - Domain and class model`
9. `Figure 16 - Analysis pipeline: stages, gates, parallelism, and recovery`
10. `Figure 17 - UML communication diagram for one analysis run`
11. `Figure 18 - End-to-end execution sequence`
12. `Figure 19 - Validator activity for publication and run preparation`
13. `Figure 20 - Deterministic readiness scheduler activity`
14. `Figure 21 - Run lifecycle and resumable outcomes`
15. `Supplement 22 - Object diagram: one paused analysis snapshot`
16. `Supplement 23 - Composite structure: WorkflowRuntime internals`
17. `Supplement 24 - Timing diagram: run, node, event, and UI state`
18. `Supplement 25 - Interaction overview: end-to-end analysis control`
19. `Supplement 26 - Deployment diagram: Docker Compose topology`

Figures 7-13 in the report are application screenshots, not UML or engineering models, so they are not duplicated in the Visual Paradigm project.

## Architecture extension

1. `Architecture 1 - OmniTrade main web information system architecture`
2. `Architecture 2 - Decomposition of the three CONTROL subsystems`
3. `Architecture 3 - Dominant and supporting architectural styles`
4. `Architecture 4 - Architectural pattern realization map`
5. `Architecture 5 - Architecture principles and quality-attribute traceability`

The dominant classification is a layered web information system. Client-server, modular services, typed pipes-and-filters, event-driven notification, and repository/checkpoint styles are applied within narrower boundaries. The main architecture traces profile, connection, Workflow Lab, analysis-run, and run-control inputs through request composition, deterministic orchestration, specialist execution, decision governance, durable state, and observable outputs. The three owned CONTROL subsystems are expanded separately down to their validation, scheduling, recovery, risk, lineage, and report-assembly responsibilities.

## Latest implementation details represented

- 31 workflow catalog node types; the default workflow has 33 nodes and 48 edges.
- Profile, connection, workflow, and new-analysis inputs are traced to validation, immutable run configuration, and execution.
- Profile defaults prefill New Analysis; verified provider and quick/deep model defaults remain overridable per run.
- `InvestorPolicy` is deep-copied into each run and applied by the risk work and deterministic decision validation.
- Run History, durable `PAUSING`/`PAUSED`, connection recheck, and checkpoint resume are represented.
- Provider-chain fallback uses real providers in live mode; live fetches do not fall back to fixtures.
- Market, news, macro, FX, prediction-market, and model providers are separated behind typed ports.
- The validator counts actual model-node calls and retry allowance; research depth controls declared bounded loops only.
- Deterministic readiness scheduling, stable ordering, parallel waves, typed joins, retries, failures, checkpoints, cancellation, and resume are explicit.
- Specialist analysis, bounded Bull/Bear research, risk perspectives, deterministic decision validation, reporting, evidence lineage, and event observation are shown.
- The system provides financial decision support only. No brokerage execution is present.

## Supporting files

- `previews/F*.svg` and `previews/F*.png`: high-resolution report and presentation views.
- `drawings/F*.vdx`: routed editable drawing exchange files.
- `plantuml/F*.puml`: portable text sources.
- `OmniTradeAI-Report-UML-2.1.xmi`: semantic UML exchange model.
- `report-model-manifest.json`: report mapping, repository revision, model counts, and checksums.
- `vp-diagrams.tsv`: deterministic Visual Paradigm OpenAPI exchange.
- `generate_report_model.py`: report-specific generator and connector-crossing validator.
- `generate_architecture_model.py`: architecture extension generator and connector-crossing validator.
- `architecture-model-manifest.json`: architecture scope, implementation revision, counts, and checksums.
- `vp-plugin/`: native Visual Paradigm project builder source and compiled plugin.

The project is built with Visual Paradigm's native editable elements rather than imported flat drawings. It uses UML systems and use cases, packages, classes and attributes, components and operations, communication lifelines/links/messages, state and activity nodes with transitions, object instances and links, composite parts and ports, deployment nodes, a native timing frame with lifelines/state conditions/time instances, interaction occurrences, and a native sequence interaction with lifelines, activations, and messages. Connector waypoints are authored so that relationship lines do not cross unrelated nodes.

## Regeneration

From the repository root:

```powershell
$env:PYTHONPATH = (Get-Location).Path
python .\modeling\visual-paradigm\generate_report_model.py
.\modeling\visual-paradigm\render_previews.ps1
```

Generation fails if an orthogonal connector segment crosses an unrelated node or note box.
