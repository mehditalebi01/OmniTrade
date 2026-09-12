# Architecture control document

The detailed logical, process, development, data, interface, security, quality,
and deployment design is in `docs/system-design.md`. Architecture decisions are
in `docs/adr/`. Strict UML source and rendered figures are in
`modeling/visual-paradigm/plantuml/V7_*.puml` and
`modeling/visual-paradigm/uml-v7/`.

## Main architecture

OmniTrade is a web information system with event-driven workflow control. The
browser uses a public API. Workflow design owns drafts, validation, and
immutable versions. Runtime owns scheduling, state, failure policy, budgets,
events, checkpoints, and recovery. Evidence, model, and report components expose
typed interfaces. PostgreSQL is durable truth; event transport supports live
and distributed processing; the artifact store keeps hashed exports. External
providers and models remain outside the product boundary. No broker interface
exists.

## UML view set

| Concern | UML diagram |
|---|---|
| Scope and user goals | Use-case diagram |
| Components and interfaces | Component diagram |
| Code dependency direction | Package diagram |
| Durable domain structure | Class and object diagrams |
| Runtime internal collaboration | Composite-structure and communication diagrams |
| End-to-end behavior | Sequence and interaction/activity diagrams |
| Graph validation and scheduling algorithms | Activity diagrams |
| Run lifecycle | State-machine diagram |
| Pause/resume timing | Timing diagram |
| Runtime topology | Deployment diagram |

## Event and state rules

Each event has schema version, event ID, type, run ID, optional node ID, trace
ID, time, and typed payload. Effects are idempotent. A cooperative pause finishes
the active safe batch, saves a checkpoint, and then stops. Resume retains
successful/degraded node states and resets only unfinished work. Cancellation
is final. A required failure stops the required path; an allowed optional loss
is disclosed as degradation.

## Data ownership

Identity owns user access. Workflow owns drafts, versions, runs, node states,
events, and checkpoints. Evidence owns normalized items and provider metadata.
Model owns call/usage metadata. Report owns decisions, claims, lineage, and
artifact metadata. Cross-component access uses IDs and typed interfaces rather
than hidden table coupling. Session credentials are not durable data.
