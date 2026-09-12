# Fair feature classification

This classification follows the professor's rule. A formula, API, library, or
pretrained model is not called complex by itself.

## Data, repository, and formula functions

| Function | Why it belongs here |
|---|---|
| User-owned workflow CRUD | Standard create, read, update, and delete operations |
| Immutable workflow versions | Database storage plus content hash |
| Run, event, checkpoint, and report history | Durable PostgreSQL records |
| Evidence repository | Structured values, provider metadata, time, unit, and currency |
| Technical indicators | Deterministic formulas such as SMA, RSI, and volatility |
| Fundamental ratios | Deterministic P/E, debt/equity, and ROE formulas |
| Report export records | Artifact path, format, and SHA-256 hash |
| Lineage queries | Read and join stored run, node, event, and evidence records |

## Third-party functions

| Function | Why it belongs here |
|---|---|
| React Flow and MUI | Third-party GUI libraries |
| FastAPI and SQLAlchemy | Third-party web and database libraries |
| PostgreSQL and Redis Streams | Third-party infrastructure |
| Live market/news provider calls | External data services |
| OpenAI-compatible model call | External or pretrained model service |
| ReportLab PDF renderer | Third-party document library |
| JWT library | Third-party token implementation |
| Docker and Nginx | Third-party deployment tools |

## Complex functions implemented by us

| Function | Why it is complex application logic |
|---|---|
| Typed graph validator | Combines reachability, port types, cycle bounds, joins, evidence rules, side effects, and budgets |
| Deterministic parallel scheduler | Calculates readiness, runs batches, manages node states, and merges in stable order |
| Required/optional branch policy | Propagates failure into failed, degraded, skipped, or continued workflow states |
| Bounded bull/bear debate | Controls repeated research rounds with an explicit stopping bound |
| Multi-view risk coordination | Starts three views in parallel, joins them, and validates one final decision |
| Provider resilience policy | Coordinates timeout, retry, exponential wait, fallback, and degraded evidence |
| Global budget control | Coordinates runtime, parallelism, provider calls, model calls, and token use across the graph |
| Event and idempotency protocol | Uses versioned IDs, traces, consumer-safe events, and duplicate protection |
| Checkpoint resume | Restores successful nodes, resets incomplete nodes, and avoids repeated completed work |
| Cooperative pause | Finishes the current parallel batch, saves a durable checkpoint, and exposes the paused state for later continuation |
| Cancellation coordination | Sends cancellation through Redis and stops pending workflow work safely |
| Evidence time and quality gate | Prevents wrong ticker, stale, future, untrusted, unit-less, or currency-mismatched evidence |
| Claim lineage | Preserves the node, provider, content hash, and event path behind the report |

The proposal is balanced because useful storage functions and third-party tools
support the product, while the main behavior is controlled by our own workflow
logic. None of the complex rows depends on calling a feature complex only
because it uses AI.
