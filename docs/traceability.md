# Requirements, design, implementation, and verification traceability

## Story-centered trace matrix

| Story | User requirement | System requirements | Custom logic / UML | Main implementation | Main executable verification |
|---|---|---|---|---|---|
| US-01 | UR-01 | FR-01; NFR-02 | Use-case and login/API sequence | `auth.py`, API ownership dependencies, `storage.py` | `test_user_cannot_read_another_users_workflow`, token and login tests |
| US-02 | UR-05 | FR-16; NFR-08 | Component and deployment UML | React shell, `api.py`, contracts, Compose | `test_complete_browser_api_scenario`, login/frontend build |
| US-03 | UR-02 | FR-02, FR-23, FR-35 | Use-case, package, class UML | Workflow Lab, catalog, workflow repository | draft reset and catalog-description tests |
| US-04 | UR-02, UR-03 | FR-03, FR-04, FR-19, FR-22, FR-31, FR-36; NFR-04, NFR-10 | CCL-01, CCL-07; validator activity and publication sequence | `validator.py`, catalog, version storage, active-workflow policy | `test_validator.py`, configuration matrix, draft/publish API tests |
| US-05 | UR-06 | FR-05, FR-06, FR-13, FR-17; NFR-01, NFR-04, NFR-10 | CCL-02, CCL-04; scheduler activity, communication, timing UML | `runtime.py`, events, Agent Room | deterministic runtime, failure-policy, event/activity tests |
| US-06 | UR-09 | FR-12, FR-34; NFR-01, NFR-10 | CCL-04, CCL-05; state, object, timing, recovery activity UML | runtime checkpoints, API reconciliation, run controls | failed/paused resume, cancellation, late completion tests |
| US-07 | UR-04, UR-12 | FR-07, FR-24, FR-25, FR-32; NFR-02, NFR-07 | CCL-03, CCL-04; evidence sequence and failure activity UML | providers, connections, evidence service, run preconditions | provider chain, write-only secret, live-only and safe-error tests |
| US-08 | UR-04, UR-08 | FR-08, FR-14, FR-37; NFR-05, NFR-10 | CCL-03, CCL-08; evidence and lineage sequences | `evidence.py`, calculations, providers, reporting | time/freshness, FX, content-hash, lineage tests |
| US-09 | UR-04, UR-05 | FR-21, FR-24, FR-26, FR-29, FR-33; NFR-02 | Component/model interaction UML | connections, model gateway, profile/options APIs | model discovery/routing, Bedrock, redaction, adaptive-choice tests |
| US-10 | UR-06, UR-07 | FR-09, FR-20; NFR-05 | CCL-06; end-to-end sequence and communication UML | model/service executors, report assembler | schema handling, specialist role-set, PDF tests |
| US-11 | UR-06, UR-07 | FR-10, FR-38; NFR-04, NFR-05 | CCL-06; bounded-research activity | research executors, services, reporting | research-depth matrix and support/confidence tests |
| US-12 | UR-07, UR-11 | FR-11, FR-27; NFR-05, NFR-07 | CCL-06; risk fan-out/decision activity | risk and policy executors, manager validation | risk-view, profile-limit, configuration/report tests |
| US-13 | UR-07, UR-08, UR-10 | FR-14, FR-15, FR-18, FR-20; NFR-05, NFR-10 | CCL-08; lineage sequence, class/object UML | reporting, artifacts, report history/storage | report completeness, export/hash, history and ownership tests |
| US-14 | UR-05, UR-06, UR-10, UR-11 | FR-16, FR-17, FR-18, FR-27, FR-28, FR-30, FR-33; NFR-06 | Use-case and UI/API sequence | Analysis, Agent Room, Profile, Reports, Guide pages | frontend unit tests and browser acceptance journey |
| US-15 | UR-12 | FR-25; NFR-02, NFR-07, NFR-08, NFR-09 | Deployment and component UML | Compose, migrations, CI, health checks | clean deployment, migration, static and full regression gates |
| US-16 | UR-03, UR-08, UR-09, UR-12 | FR-01..FR-38; NFR-01..NFR-10 | CCL-01..CCL-08; complete strict UML set | complete product and controlled engineering artifacts | quality measurement, complete defense scenario, artifact-integrity tests |

## Functional requirement implementation index

| Requirement range | Main code boundary | Verification family |
|---|---|---|
| FR-01 | `omnitrade/auth.py`, API dependencies, owner-scoped repositories | API authentication and foreign-owner tests |
| FR-02..FR-04 | Workflow Lab, contracts, catalog, validator, workflow storage | validator, draft, publication, and editor tests |
| FR-05..FR-06 | `engine/runtime.py`, failure policies, typed inputs | deterministic scheduler and required/optional failure tests |
| FR-07..FR-08 | providers, evidence normalization, time/quality gate, FX | provider/evidence/calculation tests |
| FR-09..FR-11 | model gateway, specialist/research/risk executors | model/service/runtime/configuration tests |
| FR-12..FR-13 | checkpoints, event transport, pause/resume/cancel, SSE | runtime recovery, API controls, event tests |
| FR-14..FR-15 | report/lineage builder, history, renderers, artifacts | reporting, API, hash and format tests |
| FR-16..FR-18 | configuration contract, Analysis, Agent Room, Profile, Reports | configuration matrix, API and frontend tests |
| FR-19..FR-23 | immutable versions, catalog/options, suggestions/descriptions | workflow/API/catalog/frontend tests |
| FR-24..FR-26 | session connection store, verification, provider/model adapters | connection, provider and model-gateway tests |
| FR-27..FR-30 | profile policy, adaptive options, Bedrock, guide | policy, API, frontend and guide tests |
| FR-31..FR-33 | active workflow, provider capabilities, model defaults | active-version, provider-map and profile tests |
| FR-34..FR-36 | late reconciliation, draft presentation/reset, configuration validation | API recovery/reset and configuration-matrix tests |
| FR-37..FR-38 | historical FX lineage and research support/confidence | provider, runtime, report, PDF and frontend tests |

## Non-functional requirement evidence index

| NFR | Design enforcement | Test / measurement evidence |
|---|---|---|
| NFR-01 | Deterministic states, checkpoints, idempotent event effects | resume/restart/duplicate-event tests |
| NFR-02 | JWT, ownership, input validation, session-only write-only secrets | authorization matrix, canary redaction, JWT length/expiry checks |
| NFR-03 | Small typed read paths and repository queries | `scripts/measure_quality.py` API p95 result |
| NFR-04 | Pre-run budget validation and bounded runtime scheduling | validator p95, concurrency/call/depth boundary tests |
| NFR-05 | Typed role outputs and claim/evidence lineage | report-role and 100% claim lineage checks |
| NFR-06 | Labels, keyboard controls, readable errors, recovery/help paths | frontend/browser acceptance and manual accessibility checklist |
| NFR-07 | No broker/order interface, production live-only precondition, warnings | route inspection, report warning, live-only rejection tests |
| NFR-08 | Contracts, adapters, ADRs, strict type/lint/coverage and artifact gate | 80% core threshold, mypy, Ruff, frontend build, engineering-artifact tests |
| NFR-09 | One Compose project, migration ordering, health checks, volumes | clean-host deployment rehearsal within 180 seconds |
| NFR-10 | Immutable version/config snapshot, trace/event/evidence/artifact hashes | restart/reload, hash, event-deduplication and lineage tests |

## Change rule

A story or requirement is not Done when only code changes. Its linked UML,
tests, evidence, user/system specification, and this matrix must remain
consistent. The engineering-artifact test checks ID completeness and the
presence of the strict UML source set.
