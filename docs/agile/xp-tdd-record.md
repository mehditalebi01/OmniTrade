# XP iteration and TDD record

## Evidence rule

Each XP increment starts from selected user stories. The team holds the story
conversation, writes acceptance examples, creates the smallest failing test
(Red), implements the minimum behavior (Green), improves the design while tests
remain green (Refactor), integrates the vertical slice, runs acceptance and
regression checks, demonstrates the working result, and records feedback.

The original project history did not preserve every first failing-test log.
Therefore, historical increment rows below identify the present executable
tests that reconstruct the acceptance boundary. They do not claim an unrecorded
Red result. Revision R1 is the first increment with an explicitly observed Red
and Green record in this document.

## Shared artifacts

- Story card: ID, actor, value, priority, points, conversation notes, confirmation.
- Test list: stable TC IDs linked to UR, FR, and NFR IDs.
- UML sketch/model: only the view needed for the story risk.
- Red evidence: failing test name and observed failure.
- Green evidence: smallest implementation and passing focused test.
- Refactor evidence: design change plus focused and regression results.
- CI evidence: lint, strict types, backend, frontend, build, migration, and browser checks.
- Acceptance record: story confirmation, demonstration result, open defects, reviewer.
- Retrospective: one practice to keep, one issue, one improvement for the next increment.

## I1 - Walking skeleton (US-01, US-02)

- Conversation: identity, owned records, expired tokens, protected browser/API path.
- Acceptance tests: TC-AUTH-01, TC-AUTH-02 and the first browser-to-API scenario.
- Red target: foreign workflow access and unauthenticated protected calls must fail.
- Green scope: login, token validation, ownership filter, first run/status path.
- Refactor focus: keep identity checks in shared dependencies and repository ownership methods.
- Integration/acceptance: login, create starter work, read status, deny second user.
- Main evidence: `tests/test_api.py`, `frontend/src/components/Login.test.tsx`, API UML sequence.

## I2 - Safe process design (US-03, US-04)

- Conversation: drafts versus published versions, invalid structure, undo/reset, useful issue messages.
- Acceptance tests: TC-GRAPH-01..14.
- Red target: each invalid graph mutation must be accepted by the old stub and therefore fail its new test first.
- Green scope: catalog, typed graph, validator rules, immutable publication, safe draft reset.
- Refactor focus: separate graph contracts, catalog metadata, validation passes, and persistence.
- Integration/acceptance: break, explain, repair, publish, run, and prove that later draft edits do not change the run.
- Main evidence: `tests/test_validator.py`, workflow API tests, Workflow Lab tests, validator activity UML.

## I3 - Event execution and recovery (US-05, US-06)

- Conversation: readiness, stable merging, legal states, duplicate events, safe pause, crash/restart.
- Acceptance tests: TC-RUN-01..04, TC-REC-01..06, TC-EVENT-01..02.
- Red target: parallel nodes start in unstable order, a completed node restarts, or an illegal state is accepted.
- Green scope: deterministic ready batches, versioned events, checkpoints, pause/resume/cancel probes.
- Refactor focus: isolate runtime context, execution policy, event emission, and checkpoint creation.
- Integration/acceptance: run parallel graph, pause after a batch, restart, resume, and compare started-node IDs.
- Main evidence: `tests/test_runtime.py`, recovery API tests, scheduler activity, state machine, timing UML.

## I4 - Trusted evidence (US-07, US-08)

- Conversation: capability verification, selected chains, time boundaries, currency, provenance, optional loss.
- Acceptance tests: TC-EVID-01..14 and TC-SAFE-01.
- Red target: future/stale/wrong-ticker evidence reaches a specialist or an unselected fallback is called.
- Green scope: provider chain policy, normalized evidence contract, time/quality gate, FX lineage.
- Refactor focus: keep provider-specific parsing behind adapters and quality policy independent of providers.
- Integration/acceptance: run required and optional failure cases and inspect normalized lineage and warnings.
- Main evidence: evidence/provider tests and evidence acquisition UML sequence.

## I5 - Typed specialist analysis (US-09, US-10)

- Conversation: verified models, quick/deep routing, invalid output, evidence citations, secret boundaries.
- Acceptance tests: TC-MODEL-01..06, TC-AGENT-01..04, TC-SEC-01..05.
- Red target: malformed model output enters workflow state or a credential appears in a response/report.
- Green scope: model capability discovery, typed requests/responses, bounded repair/retry, four specialist roles.
- Refactor focus: one provider-neutral gateway and shared typed role contracts.
- Integration/acceptance: discover models, run selected specialists, reject malformed output, scan secret canary.
- Main evidence: model gateway/service tests and specialist collaboration UML sequence.

## I6 - Research, risk, and decision (US-11, US-12)

- Conversation: bounded debate, opposing evidence, support versus confidence, three risk attitudes, profile limits.
- Acceptance tests: TC-DEBATE-01..05, TC-RISK-01..02, TC-POL-01..05.
- Red target: debate exceeds depth, bull/bear values are copied, or final decision violates a profile limit.
- Green scope: bounded round counter, separate research metrics, risk fan-out/join, deterministic manager policy.
- Refactor focus: separate probabilistic role content from deterministic orchestration and safety validation.
- Integration/acceptance: compare depth/risk-profile runs and inspect distinct research/risk/manager outputs.
- Main evidence: configuration/runtime/report tests and research-risk interaction overview UML.

## I7 - Explainable product (US-13, US-14)

- Conversation: complete role report, history, hashes, lineage, live events, adaptive choices, guide.
- Acceptance tests: TC-REP-01..06, TC-UI-01..04, TC-PROF-01..02, TC-HIST-01.
- Red target: an executed role or material claim is missing, an artifact differs, or foreign history is visible.
- Green scope: report assembler, history, exports, Agent Room, profile defaults, adaptive controls.
- Refactor focus: make API response the common source for browser and exported formats.
- Integration/acceptance: complete browser journey from configuration to report, lineage, history, and export.
- Main evidence: report/API/frontend tests and claim-lineage UML sequence.

## I8 - Release evidence (US-15, US-16)

- Conversation: repeatable deployment, quality gates, failure/load evidence, UML consistency, maintenance.
- Acceptance tests: NFR-01..NFR-10 gates and complete system scenario.
- Red target: a quality threshold, migration, container health, trace link, or UML artifact integrity gate fails.
- Green scope: Compose health/dependencies, CI gates, measurement script, evidence package, corrected UML.
- Refactor focus: remove duplicate documents and make controlled sources generate report evidence.
- Integration/acceptance: clean start, migration, complete tests, controlled failures, recovery, report/hash review.
- Main evidence: CI, Compose, `scripts/measure_quality.py`, `artifacts/quality/`, final report.

## R1 - Professor-review revision (recorded TDD)

- Stories/requirements: US-16; NFR-02, NFR-03, NFR-04, NFR-07, NFR-08.
- Red: `tests/test_quality_evidence.py` first failed during collection because `omnitrade.quality` did not exist.
- Green: the new quality-target, nearest-rank percentile, and pass/fail evaluation code made all focused tests pass.
- Refactor: latency and minimum-threshold evaluation share one typed result contract; the measurement script uses the same contract.
- Integration: the script measured local authenticated API p95, reference-workflow validation p95, and forbidden-route count and wrote JSON evidence.
- Acceptance: all three measured gates passed; the full regression suite must pass before this report is released.
- Honest limitation: the first script run exposed an environment-specific database host and a short environment JWT secret warning. The script was isolated from Compose and given a standards-length measurement secret. Production still requires an injected secret.
