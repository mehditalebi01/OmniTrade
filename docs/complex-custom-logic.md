# Complex custom application logic

## Assessment boundary

The external data services, pretrained language models, technical formulas,
frameworks, database, and message transport are not classified as complex custom logic.
The assessed complexity is the software-owned policy that turns a
user-owned process and varied evidence into a safe, recoverable, and traceable
result. This chapter is the implementation index for that logic.

## CCL-01 - Typed graph validation and publication safety

- Problem: a user can create a graph that is disconnected, type-incompatible,
  unbounded, impossible to join, missing required evidence, unsafe in a loop,
  or impossible within its budget.
- Input/state: `WorkflowDefinition`, node catalog, typed ports, loop metadata,
  branch policy, and global budget.
- Algorithm: index nodes; verify unique IDs/start/end; build incoming/outgoing
  adjacency; traverse reachability; check every edge's port types; inspect
  strongly relevant cycle/loop rules; calculate join requirements; verify
  required evidence roles; estimate bounded provider/model calls and runtime.
- Output: one `ValidationResult` with stable issues. Publication is allowed only
  when `valid` is true; the published definition is content-hashed and immutable.
- Complexity: graph passes are mainly O(V + E); catalog and budget checks are
  O(V). Complexity comes from combining several constraints and useful error
  paths, not from traversal alone.
- Implementation: `omnitrade/engine/validator.py`, `omnitrade/storage.py`.
- Trace: UR-02, UR-03; FR-03, FR-04, FR-19, FR-22, FR-31; NFR-04, NFR-10.
- Verification/UML: TC-GRAPH-02..13; validator UML activity and publication sequence.

## CCL-02 - Deterministic readiness scheduler

- Problem: independent activities should run concurrently, but joins, loops,
  optional inputs, budgets, and repeatable ordering must remain correct.
- Input/state: validated graph, predecessor states, restored checkpoint, loop
  counters, active-run controls, and budget counters.
- Algorithm: restore terminal node states; find nodes whose required inputs are
  satisfied; sort the ready set by stable node identity; limit the batch by
  concurrency; execute the batch; merge predecessor outputs in stable order;
  apply state/failure policy; checkpoint; repeat until end or terminal condition.
- Invariant: one node is started at most once per execution attempt unless a
  bounded loop explicitly permits another round. No completed checkpointed node
  is restarted after resume.
- Complexity: readiness scanning is O(V + E) per scheduling wave in the current
  bounded graph. The difficult part is coordinated state and termination under
  concurrency, optional loss, controls, and restoration.
- Implementation: `omnitrade/engine/runtime.py`, `omnitrade/contracts.py`.
- Trace: UR-06, UR-09; FR-05, FR-06, FR-12, FR-13; NFR-01, NFR-04, NFR-10.
- Verification/UML: TC-RUN-01..04, TC-REC-01..05; scheduler activity, composite structure, timing, and state-machine UML.

## CCL-03 - Evidence resilience, normalization, and quality gate

- Problem: provider results differ in format, time, reliability, unit, currency,
  and failure behavior; unsafe evidence must not silently enter analysis.
- Input/state: user-selected verified provider chain, branch criticality,
  requested ticker/as-of, freshness rule, currency, timeout/retry/fallback budget.
- Algorithm: call the selected chain in order; bound each attempt; classify
  provider failure; normalize to one evidence contract; validate ticker, time,
  freshness, provenance, unit, currency, and hash; convert currency when needed;
  accept, exclude with degradation, or fail according to evidence role.
- Invariant: an unselected/unverified provider and prepared production evidence
  cannot be used as hidden fallback. Original values and transformations remain
  in lineage.
- Complexity: one role is O(P + D), where P is bounded provider attempts and D
  is returned data size; five roles execute in parallel and then join.
- Implementation: `omnitrade/providers.py`, `omnitrade/evidence.py`,
  `omnitrade/calculations.py`, `omnitrade/engine/executors.py`.
- Trace: UR-04, UR-08, UR-12; FR-07, FR-08, FR-24, FR-25, FR-32, FR-37; NFR-01, NFR-05, NFR-07.
- Verification/UML: TC-EVID-01..14, TC-SAFE-01; provider/evidence sequence and failure activity UML.

## CCL-04 - Failure, degradation, cancellation, and control propagation

- Problem: the same failure cannot have one global meaning. A required branch,
  optional branch, cancelled run, timeout, invalid model output, or stale source
  must affect only the correct nodes and final state.
- Algorithm: classify the event; apply node `FailurePolicy`; mark the node;
  calculate dependent readiness; skip only impossible dependants; preserve
  independent work; aggregate disclosed degradation reasons; stop on required
  failure or budget exhaustion; apply cancel/pause only at safe boundaries.
- Output: legal node/run states plus events and checkpoints that explain the path.
- Complexity: each completed node/result is classified once, O(V + E), while
  propagation must preserve branch criticality, control state, and audit order.
- Implementation: `omnitrade/engine/runtime.py`, `omnitrade/services.py`,
  `omnitrade/infrastructure/events.py`.
- Trace: UR-03, UR-09; FR-06, FR-07, FR-12, FR-13, FR-34; NFR-01, NFR-10.
- Verification/UML: TC-RUN-03..04, TC-REC-01..06, TC-EVENT-01..02; failure activity and run state-machine UML.

## CCL-05 - Checkpoint, idempotency, late completion, and resume

- Problem: a long distributed run may pause, crash, lose API transport, deliver
  an event twice, or finish after the caller timed out.
- Algorithm: after a stable batch, serialize node states and event position;
  record consumed event IDs before applying effects; on resume, restore
  succeeded/degraded states and reset only unfinished states; reconcile terminal
  events with durable checkpoints; rebuild the report when distributed work
  completed; reject resume from final cancellation/success states.
- Invariants: duplicate event effects = 0; restarted completed nodes = 0; one
  durable terminal state per run.
- Complexity: checkpoint serialization/restoration is O(V + K), where K is the
  consumed-event ID set; correctness also depends on distributed event order.
- Implementation: `omnitrade/engine/runtime.py`, `omnitrade/api.py`,
  `omnitrade/storage.py`, `omnitrade/infrastructure/events.py`.
- Trace: UR-09; FR-12, FR-13, FR-34; NFR-01, NFR-10.
- Verification/UML: TC-REC-01..06, TC-EVENT-02; object, state, timing, sequence, and deployment UML.

## CCL-06 - Bounded multi-agent research and risk coordination

- Problem: specialist outputs must be challenged without creating an unbounded
  or opaque conversation, and user risk policy must constrain the final result.
- Algorithm: join typed specialist reports; execute bull and bear cases for the
  configured round bound; update each side from evidence and prior counters;
  keep directional support separate from evidence confidence; form a proposal;
  fan out three risk attitudes; join them; apply deterministic profile limits and
  validate final action/confidence/reasoning fields.
- Invariants: rounds never exceed depth; all selected successful specialists are
  represented; three risk views use the same evidence but different policies;
  the manager cannot bypass hard profile limits.
- Complexity: model-role work is bounded by selected specialists S, debate
  depth R, and three risk views, O(S + 2R + 3); orchestration and validation are
  team-owned even though model inference is external.
- Implementation: `omnitrade/engine/executors.py`, `omnitrade/services.py`,
  `omnitrade/reporting.py`.
- Trace: UR-06, UR-07, UR-11; FR-09, FR-10, FR-11, FR-20, FR-27, FR-38; NFR-05.
- Verification/UML: TC-AGENT-01..04, TC-DEBATE-01..05, TC-RISK-01..02, TC-POL-01..05; interaction-overview, sequence, activity, and communication UML.

## CCL-07 - Global budget and configuration contract

- Problem: many user choices interact. A valid individual value can still make
  the configured graph impossible or exceed time, call, token, retry, or
  concurrency limits.
- Algorithm: resolve profile defaults and run overrides; filter the published
  graph by selected branches; apply depth/model/provider choices; calculate
  worst-case bounded calls; validate cross-field compatibility and graph safety;
  reject before queueing with field/graph issue codes.
- Complexity: resolving configuration is O(C + V + E), where C is the number of
  interacting choices; the risk is the valid-combination space and its effect
  on the executable graph, not any single selector.
- Implementation: `omnitrade/api.py`, `omnitrade/contracts.py`,
  `omnitrade/engine/validator.py`, `frontend/src/components/AnalysisPage.tsx`.
- Trace: UR-03, UR-05; FR-16, FR-21, FR-28, FR-31, FR-33, FR-36; NFR-04.
- Verification/UML: TC-CONF-01..15; configuration-to-run sequence and validator activity UML.

## CCL-08 - Claim lineage and multi-format report assembly

- Problem: the final decision combines data and role outputs across many nodes;
  users must see which evidence and process produced each important claim.
- Algorithm: traverse executed node outputs; collect evidence references and
  hashes; create claim-to-node-to-provider links; mark unsupported claims;
  include immutable workflow/configuration/trace identity; assemble one typed
  report model; render browser, JSON, HTML, and PDF views; hash artifacts.
- Invariant: browser and export formats use the same report model and executed
  role set. Rendering cannot invent a role, claim, or evidence source.
- Complexity: lineage assembly is O(C + R), where C is claims and R is evidence
  references, plus format rendering; correctness crosses runtime, evidence,
  persistence, and user-interface components.
- Implementation: `omnitrade/reporting.py`, `omnitrade/api.py`,
  `omnitrade/storage.py`, `frontend/src/components/ReportsPage.tsx`.
- Trace: UR-07, UR-08, UR-10; FR-14, FR-15, FR-18, FR-20; NFR-05, NFR-10.
- Verification/UML: TC-REP-01..06; claim-lineage sequence, domain class, object, and component UML.

## Combined structural complexity

The algorithms are not isolated. One run applies CCL-07 before queueing,
CCL-01 at publication and run preparation, CCL-02 throughout execution,
CCL-03 for five evidence roles, CCL-04 on every abnormal path, CCL-05 at each
safe batch and recovery, CCL-06 for specialist/research/risk collaboration, and
CCL-08 for the final auditable result. This connected control flow is the main
custom software complexity requested by the project guidelines.
