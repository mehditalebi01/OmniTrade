# Software system design specification

## 1. Design goals and constraints

The design must make a user-defined analysis process executable, observable,
recoverable, and explainable. It must isolate external providers and models,
protect owned data and session secrets, preserve old run identity, and exclude
broker execution. The design favors high cohesion, explicit contracts, stable
dependency direction, bounded control, and test seams.

## 2. Logical view

- Identity and access controls session identity and ownership.
- Workflow design owns drafts, catalog, validation, and immutable versions.
- Workflow runtime owns readiness, states, failure policy, budgets, events,
  checkpoints, and legal controls.
- Evidence owns capability adapters, normalization, quality/time/currency rules,
  and deterministic calculations.
- Model coordination owns model discovery, routing, typed requests/responses,
  retries, and usage budgets.
- Report and lineage own claims, decision representation, history, rendering,
  artifacts, and hashes.

UML evidence: use-case, package, component, class, and composite-structure diagrams.

## 3. Process and interaction view

The public API accepts commands and returns owned state. The workflow worker
executes immutable versions. Independent evidence and reasoning activities run
concurrently. Versioned events update live clients and durable state. Required
joins wait for accepted predecessors; optional failures are disclosed and can
remove only dependent work. Pause and cancel are cooperative controls checked at
safe boundaries. Recovery uses checkpoints and consumed event IDs.

UML evidence: sequence, communication, interaction-overview, activity, timing,
and state-machine diagrams.

## 4. Development view and dependency rule

`contracts` and engine policy are stable inner modules. API, services,
persistence, provider adapters, model clients, reporting, and infrastructure
depend on those contracts. The React application depends on public API
contracts. External SDK types do not enter engine contracts. A provider module
must not import GUI or workflow scheduling code; the validator must not call an
external provider; report rendering must not change decisions.

UML evidence: package and component diagrams with required/provided interfaces.

## 5. Data design and ownership

- Identity schema: users and access identity.
- Workflow schema: drafts, immutable versions, runs, node runs, events, checkpoints.
- Evidence schema: normalized evidence and provider-call metadata.
- Model schema: model-call metadata and usage.
- Report schema: reports, claims, decisions, lineage links, artifact metadata.

Each durable object has an ID and owner/run identity where needed. Cross-service
relationships use stable IDs and contracts. Workflow versions and report
artifacts use content hashes. Session credentials are intentionally outside the
durable data model.

UML evidence: class and object diagrams. Deployment diagrams map databases,
event transport, artifacts, services, and volumes to runtime nodes.

## 6. Interface design

Public operations are grouped by authentication, workflows, runs, connections,
profiles, reports, and catalogs. Requests and responses use typed schemas.
Errors use HTTP status plus a readable message and, for validation, stable issue
codes with field/activity context. Events contain schema version, event ID,
type, run ID, optional activity ID, trace ID, time, and typed payload.

Internal ports are:

- `WorkflowRepository`: drafts, versions, runs, node state, checkpoints.
- `EventPublisher/EventConsumer`: versioned workflow events and controls.
- `EvidencePort`: typed role request to normalized evidence result.
- `ModelPort`: typed reasoning request to typed role result.
- `ReportPort`: executed state to report/artifact result.
- `Clock/ControlProbe`: time, pause, cancel, and test determinism.

## 7. Error and recovery design

Errors are classified as validation, authorization, capability, transient
provider, evidence quality, model contract, budget, node execution, transport,
and internal integrity errors. Classification decides retry, fallback,
degradation, failure, user message, event, checkpoint, and operator action.
Retries and loops are bounded. Completed side effects are idempotent. A terminal
cancel is not resumable. Old live runs require reconnection because credentials
are session-only.

## 8. Security and privacy design

JWT authenticates a session; repository and API ownership checks authorize each
protected object. Inputs are schema validated. Credential values are write-only
and memory-scoped. Secret canaries are tested across responses, events, durable
state, reports, artifacts, and logs. External URLs and provider errors are
sanitized. No broker/order interface exists. Production configuration must use
a strong injected signing secret and verified live capabilities.

## 9. Quality design

Reliability is enforced through legal state transitions, checkpoints,
idempotency, stable ordering, and recovery tests. Performance is controlled by
parallelism/call/time budgets and measured p95 targets. Explainability uses typed
role output and claim lineage. Maintainability uses contracts, adapters, ADRs,
migrations, strict typing, linting, coverage, and UML/source integrity tests.
Deployability uses one Compose project, health checks, migration ordering,
volumes, and a repeatable quality gate.

## 10. Design trade-offs

- A custom runtime gives defendable logic but requires more tests than a reused
  workflow framework.
- Modular services show ownership and failures but add local operational cost;
  one Compose project controls it.
- PostgreSQL and event transport serve different access needs but require
  consistency and restart tests.
- Session-only credentials reduce durable secret risk but must be reconnected
  after restart or for an old live run.
- Immutable versions improve reproducibility but require explicit publication
  and migration/evolution rules.
