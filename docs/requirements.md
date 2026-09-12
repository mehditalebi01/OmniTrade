# OmniTrade AI controlled requirements specification

## 1. Scope and requirement rules

OmniTrade AI helps a registered user produce repeatable and explainable stock
decision support. It combines current evidence, a user-owned analysis process,
specialist opinions, research debate, risk views, and a final report. It does
not create broker orders. Requirements describe a user problem or observable
system behavior. Technology choices belong to design documents, not to user
requirements.

Every requirement has one stable ID. `UR` means user requirement, `FR` means
system functional requirement, and `NFR` means system non-functional
requirement. MoSCoW gives priority. A change to an approved requirement must
update its linked story, UML element, code, test, and evidence record.

Sources are the course material, professor feedback, the approved project
scope, user journeys, observed defects, external-provider constraints, and the
implemented product. Requirements were checked for relevance, consistency,
feasibility, clarity, completeness, testability, and traceability.

## 2. User requirements

User requirements state the need and result without naming an implementation
technology.

| ID | Priority | User need / outcome | User acceptance criterion | Main stories |
|---|---|---|---|---|
| UR-01 | Must | Keep each user's analysis work private from other users. | A user can access owned work and cannot read another user's work. | US-01 |
| UR-02 | Must | Create, change, understand, and reuse the sequence of analysis activities. | A saved analysis process can be reviewed, corrected, published, and used again. | US-03, US-04 |
| UR-03 | Must | Know why an unsafe or incomplete analysis process cannot start. | Invalid structure or settings are rejected with clear reasons before execution. | US-04 |
| UR-04 | Must | Use current evidence from suitable financial, economic, and public-sentiment sources. | The user can verify available sources and see which sources contributed or failed. | US-07, US-08 |
| UR-05 | Must | Choose the analysis scope, depth, risk attitude, evidence choices, models, language, currency, and limits. | Every offered choice is valid, saved with the run, and changes the relevant analysis behavior. | US-02, US-09, US-14 |
| UR-06 | Must | Observe how specialist, research, risk, and manager roles contribute to the result. | The user can follow role states and read each executed role's point of view. | US-05, US-10, US-11, US-12 |
| UR-07 | Must | Receive one clear decision-support report that explains agreement, conflict, uncertainty, and risk. | A completed run produces a readable report with all executed role outputs and the final decision. | US-10, US-11, US-12, US-13 |
| UR-08 | Must | Check the origin and processing history of important report claims. | Each material claim links to evidence source, time, currency, workflow version, and processing context. | US-08, US-13 |
| UR-09 | Must | Control a long analysis and continue recoverable work after a pause or failure. | Pause, resume, cancel, and recovery follow clear rules and do not repeat completed effects. | US-06 |
| UR-10 | Should | Find and compare past owned analyses and reports. | History can be searched by date, ticker, configuration, result, and analysis-process version. | US-13, US-14 |
| UR-11 | Should | Make the analysis respect personal risk limits and investment context. | Saved limits and preferences change risk evaluation and report guidance without changing source facts. | US-12, US-14 |
| UR-12 | Must | Use the system only as decision support, with no hidden prepared production data and no automatic trade. | Production analysis uses verified live capabilities and no order can be submitted. | US-07, US-15, US-16 |

## 3. System functional requirements

These requirements define observable system behavior. Their acceptance
criteria are written so that a test can decide pass or fail.

| ID | Priority | System behavior | Acceptance criterion | Verification ID |
|---|---|---|---|---|
| FR-01 | Must | Authenticate a user and restrict workflows, runs, profiles, connections, reports, and artifacts to their owner. | Given two valid users, when one requests the other's object, the system returns no object data and denies access. | TC-AUTH-01, TC-AUTH-02 |
| FR-02 | Must | Create, read, update, delete, position, connect, rename, recolor, undo, and reset analysis-process drafts using the allowed activity catalog. | A saved draft matches the submitted activities, links, settings, and appearance after reload. | TC-GRAPH-01 |
| FR-03 | Must | Validate reachability, port compatibility, start/end rules, loop bounds, join rules, required evidence, side effects, and global budgets. | Each seeded defect is rejected with a stable issue code and a corrected reference graph is accepted. | TC-GRAPH-02..09 |
| FR-04 | Must | Publish only a valid immutable analysis-process version. | Invalid drafts cannot publish; a valid publish creates a new content-hashed version and does not change old versions. | TC-GRAPH-10 |
| FR-05 | Must | Select ready activities, execute independent activities concurrently within limits, and merge inputs in stable order. | Repeated execution of the same deterministic graph produces the same start batches, merge order, states, and result. | TC-RUN-01, TC-RUN-02 |
| FR-06 | Must | Propagate required, optional, skipped, degraded, and failed outcomes only to the correct dependent activities. | A required failure stops the run; an allowed optional failure produces a disclosed degraded result and unrelated branches continue. | TC-RUN-03, TC-RUN-04 |
| FR-07 | Must | Call only selected and verified evidence sources using bounded timeout, retry, backoff, and ordered fallback rules. | No unselected source is called; all attempts are bounded and exhaustion follows the branch failure policy. | TC-EVID-01..04 |
| FR-08 | Must | Normalize and check evidence identity, observation time, retrieval time, freshness, provenance, units, currency, and content hash before analysis. | Wrong-ticker, future, missing-provenance, and critical stale evidence stop; allowed stale optional evidence is excluded and reported. | TC-EVID-05..10 |
| FR-09 | Must | Produce schema-valid market, fundamental, news, and sentiment specialist reports for selected branches. | Every selected specialist returns its point of view, confidence, reasoning, key points, risks, and evidence references; invalid output is rejected. | TC-AGENT-01..04 |
| FR-10 | Must | Coordinate opposing research cases for exactly the configured bounded number of rounds. | Depth values 1 to 4 terminate at their bound and preserve distinct bull and bear outputs for every round. | TC-DEBATE-01..04 |
| FR-11 | Must | Evaluate aggressive, balanced, and conservative risk views before final decision validation. | Three independent risk outputs are joined; the manager applies profile limits and returns a valid decision or a clear failure. | TC-RISK-01, TC-RISK-02 |
| FR-12 | Must | Pause at a safe batch boundary, resume paused/failed/interrupted runs from a durable checkpoint, and keep cancellation final. | Completed activities are not started again after resume and only legal run-state transitions are accepted. | TC-REC-01..05 |
| FR-13 | Must | Publish ordered run and activity events and support event-stream reconnection. | A reconnecting client continues from its last event without losing the terminal event or applying an event effect twice. | TC-EVENT-01, TC-EVENT-02 |
| FR-14 | Must | Link each material report claim to the activities and normalized evidence that support it. | Lineage is complete for all supported claims; an unsupported claim is labelled unsupported and cannot be hidden. | TC-REP-01 |
| FR-15 | Must | Store report history and export owned reports in JSON, HTML, and PDF with artifact hashes. | All formats identify the same run, decision, configuration, roles, and lineage; a recalculated hash matches stored metadata. | TC-REP-02..05 |
| FR-16 | Must | Accept per-run choices for ticker, date, selected specialists, depth, risk profile, evidence chains, models, output detail, language, currency, freshness, and budgets. | A valid configuration is stored unchanged with the run and each setting changes its specified behavior or output. | TC-CONF-01..12 |
| FR-17 | Must | Show live role states, collaboration order, activity results, warnings, and terminal state for an owned run. | The live view is derived from real run events and role outputs, not a prepared animation. | TC-UI-01 |
| FR-18 | Should | Save user defaults and provide searchable calendar-based report history. | Saved defaults load on a later session and history filters return only matching owned reports. | TC-PROF-01, TC-HIST-01 |
| FR-19 | Must | Execute the exact immutable process version recorded by a run and isolate unapproved draft changes. | Changing a draft has no effect until publication; old runs still refer to their original version and result. | TC-GRAPH-11 |
| FR-20 | Must | Include the saved point of view, confidence, reasoning, evidence references, and limitations of every executed specialist, researcher, risk role, and manager. | API, browser, and PDF contain the same executed role set and no selected successful role is missing. | TC-REP-06 |
| FR-21 | Must | Offer only backend-supported tickers, providers, models, languages, currencies, modes, and limits. | Every displayed option is accepted by the run contract; unsupported values are rejected before queueing. | TC-CONF-13 |
| FR-22 | Must | Suggest compatible next activities and reject an incompatible link before it becomes part of a valid draft. | Every suggestion has compatible source/target ports and an incompatible test link is blocked with a clear reason. | TC-GRAPH-12 |
| FR-23 | Should | Explain the purpose, input, and output of a selected activity in simple language. | Every catalog activity has a non-empty description visible when selected. | TC-UI-02 |
| FR-24 | Must | Configure and verify session evidence/model credentials without returning or durably storing secret values. | A saved secret can be used for verification but is absent from API responses, events, reports, artifacts, and durable records. | TC-SEC-01..04 |
| FR-25 | Must | Prevent production analysis from using recorded evidence or an unverified external capability. | A production run with recorded mode or an unverified required capability is rejected before queueing. | TC-SAFE-01 |
| FR-26 | Should | Discover and use supported local, cloud, Bedrock, and compatible model endpoints through one typed model contract. | Verified model capabilities appear as valid choices and the selected endpoint receives the correct typed request. | TC-MODEL-01..05 |
| FR-27 | Must | Apply investment horizon, experience, loss limit, position limit, excluded sectors, and currency to prompts, risk thresholds, decision checks, or report guidance. | Changing each profile field changes its documented policy result while normalized evidence values stay unchanged. | TC-POL-01..05 |
| FR-28 | Should | Hide meaningless one-choice controls, apply their value automatically, and explain missing choices. | Zero choices show an action message, one choice is fixed, and two or more choices show a selector. | TC-UI-03 |
| FR-29 | Should | Verify Bedrock access using supported credential forms and expose the verified user-configured model identifiers. | Valid credentials pass a real capability check; invalid credentials fail safely and secrets remain write-only. | TC-MODEL-06, TC-SEC-05 |
| FR-30 | Should | Provide a topic-based complete user guide that can be opened and downloaded. | Every guide topic expands to complete steps and the downloaded file contains the same indexed guidance. | TC-UI-04 |
| FR-31 | Must | Start analysis with the latest published owned process and prevent accidental selection of an unrelated process. | New Analysis resolves one active published version; after a new publish, the next run stores the new version. | TC-GRAPH-13 |
| FR-32 | Must | Map every verified evidence source to all supported roles and handle access/rate errors with safe useful messages. | Capability mapping controls available chains; 403/429 messages omit URLs/secrets and a failed optional public feed does not remain verified. | TC-EVID-11..13 |
| FR-33 | Should | Save default verified AI provider and quick/deep models and allow valid per-run alternatives. | Defaults load when supported; invalidated models are not offered and alternatives can be selected when available. | TC-PROF-02 |
| FR-34 | Must | Reconcile late terminal events and checkpoints when distributed work finishes after an API transport timeout. | A late completed non-default ticker run becomes recoverable, its report remains available, and no duplicate run is created. | TC-REC-06 |
| FR-35 | Should | Change draft activity name, color, position, existence, and reset state without replacing published versions or old reports. | Draft reset restores the reference draft while published version IDs and historical reports stay unchanged. | TC-GRAPH-14 |
| FR-36 | Must | Validate every supported configuration combination against the configured process before queueing. | All offered combinations pass the contract; an invalid budget or branch selection returns field/graph issue codes rather than a raw object. | TC-CONF-14, TC-CONF-15 |
| FR-37 | Must | Convert non-base-currency values using a historical rate and preserve original value, currency, rate, source, and time in lineage. | The converted result matches the selected rate within tolerance and the complete conversion record is traceable. | TC-EVID-14 |
| FR-38 | Must | Report directional support separately from evidence confidence for bull and bear research. | The two values are calculated from different inputs, can differ between sides, and remain distinct in API, browser, and PDF. | TC-DEBATE-05 |

## Quality requirements

System NFRs refine user quality expectations into measurable targets. A target
is accepted only by the stated method and environment.

| ID | Priority | Quality property | System target | Measurement and test method | Acceptance rule |
|---|---|---|---|---|---|
| NFR-01 | Must | Reliability and recovery | For the controlled crash/resume scenario, 100% of previously successful or degraded activities are not restarted; one terminal state is stored. | Compare activity IDs and event IDs before/after checkpoint resume in `TC-REC-03`; repeat 20 deterministic runs. | Zero duplicated completed activity starts and zero runs with multiple terminal states. |
| NFR-02 | Must | Security and privacy | 100% of protected object endpoints enforce ownership; secret test values appear zero times in responses, events, reports, logs, artifacts, and durable records; HS256 secret is at least 32 bytes. | Authorization matrix, secret-canary scan, token expiry test, configuration check. | All ownership cases deny foreign access; canary count = 0; weak JWT configuration fails the gate. |
| NFR-03 | Must | API performance | Authenticated local read endpoints have p95 latency below 500 ms for 40 measured requests after 5 warm-ups. | Run `python -m scripts.measure_quality` on the stated local environment. | Measured p95 < 500 ms. |
| NFR-04 | Must | Validation performance and bounded resource use | The 33-activity reference process validates at p95 below 100 ms over 50 runs; runtime never exceeds configured activity/provider/model concurrency and call limits. | Quality measurement script plus instrumented boundary tests. | Validation p95 < 100 ms and every observed maximum is at or below its configured limit. |
| NFR-05 | Must | Explainability and auditability | 100% of material decision claims have evidence lineage or an explicit unsupported marker; all executed successful reasoning roles appear in the report. | Lineage completeness and report-role-set tests over the full deterministic scenario. | Missing hidden claims = 0 and missing executed roles = 0. |
| NFR-06 | Should | Usability and accessibility | The main keyboard journey completes login, connection, configuration, run monitoring, report review, recovery, and graph correction without pointer-only actions; errors name the field, provider, or activity. | Browser acceptance test and manual WCAG 2.2 AA checklist for focus, labels, contrast, keyboard, and status text. | All Must journey steps pass; no critical keyboard/focus/label defect remains. |
| NFR-07 | Must | Safety | The public API exposes zero broker/order/trade-execution routes; every report displays the decision-support boundary; production mode rejects prepared evidence. | Route inspection, report checks, and production-precondition tests. | Forbidden route count = 0, missing warning count = 0, prepared production run acceptance count = 0. |
| NFR-08 | Must | Maintainability and testability | Custom workflow-core statement coverage is at least 80%; strict type checking and linting report zero errors; requirement and UML artifact integrity tests pass. | `pytest`, coverage, strict `mypy`, `ruff`, frontend type/unit build, and engineering-artifact test. | Coverage >= 80% and every listed quality command exits 0. |
| NFR-09 | Should | Portability and deployability | A clean supported Docker host starts the complete Compose project through one command; migration finishes and all eight steady services become healthy within 180 seconds. | Clean-volume deployment rehearsal and health inspection. | Migration exit = 0 and 8/8 steady services healthy within 180 seconds. |
| NFR-10 | Must | Integrity and reproducibility | A run retains one workflow version hash, configuration snapshot, trace ID, ordered events, evidence hashes, report hash, and migration revision; duplicate event effects are ignored. | Restart/reload scenario, artifact hash recalculation, and duplicate-event test. | All identifiers/hashes are present and match; duplicate-effect count = 0. |

## 5. Requirement validation and change control

A requirement is ready when its need, scope, priority, source, normal and
abnormal cases, acceptance rule, and dependencies are clear. It is accepted
when its linked tests pass and the implemented behavior is demonstrated. The
shared Definition of Done also requires reviewed code, updated UML and
traceability, static checks, regression tests, and honest evidence. If a
requirement changes, its ID remains stable when the intent is unchanged; a new
intent receives a new ID and a replaced requirement is marked superseded.
