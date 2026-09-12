<div align="center">

# OmniTrade AI

### A Visual, Event-Driven Multi-Agent Financial Analysis Framework

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-TypeScript-149ECA?logo=react&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-Streams-DC382D?logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

OmniTrade AI collects several kinds of stock evidence, runs specialist agents in
parallel, challenges their views through a bounded debate, evaluates three risk
positions, and produces an explainable report with evidence lineage.

**Financial decision support only. The system never executes trades.**

</div>

---

## Contents

- [Why OmniTrade AI](#why-omnitrade-ai)
- [Main features](#main-features)
- [System workflow](#system-workflow)
- [Architecture](#architecture)
- [Technology](#technology)
- [Quick start](#quick-start)
- [Using the application](#using-the-application)
- [API](#api)
- [Testing and quality](#testing-and-quality)
- [Project structure](#project-structure)
- [Engineering documentation](#engineering-documentation)
- [User guide](docs/USER_GUIDE.md)
- [Current limitations](#current-limitations)
- [Academic team](#academic-team)

## Why OmniTrade AI

The main software complexity is not a pretrained model or a financial formula.
It is the complete user-to-report workflow:

- Five evidence branches: market, fundamentals, news, macro, and sentiment.
- Typed ports and versioned workflow definitions.
- Parallel scheduling with deterministic joins.
- Required and optional branches with degraded results.
- Bounded bull-versus-bear research loops with separate case support and evidence-confidence measures.
- Aggressive, balanced, and conservative risk reviews.
- Time, model-call, provider-call, token, and parallelism budgets.
- Validation, retries, fallback, pause, cancellation, checkpoints, and safe resume.
- Full traceability from each report section to runtime events and evidence.

The project is implemented independently. Other trading-agent systems were used
only as study references; their workflow code was not copied or renamed.

## Main features

| Area | What the user can do |
|---|---|
| Connections | Add private provider credentials, discover models, and verify each real connection before use. |
| New Analysis | Automatically use the latest published Workflow Lab graph, then select a stock, agents, verified providers, models, policy, and budgets. |
| Agent Room | Follow real workflow events and read the output and impact of each agent. |
| Run History | Pause active runs and resume paused, failed, or interrupted runs from durable checkpoints. |
| Reports | Browse saved reports by calendar, compare agent views, inspect evidence, and export PDF or JSON. |
| Workflow Lab | Build, rename, recolor, delete, reset, undo, validate, publish, and run typed workflow graphs with smart connection suggestions. |
| Profiles | Save default AI models plus horizon, experience, loss limit, position limit, and excluded sectors that change analysis and decision rules. |
| Recovery | Pause, cancel, or resume work from checkpoints without repeating completed nodes. |

## System workflow

```mermaid
flowchart LR
    U["User configuration"] --> V["Validate run and workflow"]
    V --> P["Parallel evidence collection"]
    P --> Q["Normalize and check quality"]
    Q --> A["Four specialist analysts"]
    A --> D["Bounded bull and bear debate"]
    D --> T["Trading proposal"]
    T --> R["Three parallel risk views"]
    R --> M["Decision validation"]
    M --> O["Report, lineage, and export"]
```

Every node moves through explicit states such as `pending`, `ready`, `running`,
`succeeded`, `degraded`, `failed`, `skipped`, or `cancelled`. Each run keeps the
exact immutable workflow version that it executed.

## Architecture

```mermaid
flowchart TB
    GUI["React GUI"] --> API["FastAPI service"]
    API --> DB[("PostgreSQL")]
    API --> BUS[("Redis Streams")]
    BUS --> WF["Workflow service"]
    BUS --> EV["Evidence service"]
    BUS --> MG["Model gateway"]
    BUS --> RP["Report service"]
    WF --> BUS
    EV --> BUS
    MG --> BUS
    RP --> BUS
    RP --> FS["Hashed artifacts"]
    API -. "SSE activity" .-> GUI
```

One `docker-compose.yml` starts one application with eight containers:

1. React frontend
2. API service
3. Workflow service
4. Evidence service
5. Model gateway
6. Report service
7. PostgreSQL
8. Redis

The services are separated to make ownership, event flow, partial failure, and
recovery clear. They are still managed together with one Compose command.

## Technology

| Layer | Main tools |
|---|---|
| Frontend | React, TypeScript, Vite, Material UI, React Flow, TanStack Query |
| Backend | Python 3.12, FastAPI, Pydantic, SQLAlchemy, Alembic |
| Data | PostgreSQL and hashed filesystem artifacts |
| Events | Redis Streams and consumer groups |
| Reports | Structured JSON and ReportLab PDF |
| Testing | Pytest, Hypothesis, Vitest, Testing Library, Playwright |
| Quality | Ruff, mypy, TypeScript checks, GitHub Actions |
| Deployment | Docker Compose and Nginx |

## Quick start

### Requirements

- Docker Desktop with Docker Compose
- Git

### Run the full system

```bash
git clone https://github.com/Aminjahanimajd/OmniTradeAI.git
cd OmniTradeAI
cp .env.example .env
docker compose up --build -d
```

Open [http://localhost:5173](http://localhost:5173).

For the local demonstration profile, use:

```text
Username: demo
Password: demo
```

Stop the complete application with:

```bash
docker compose down
```

Use `docker compose down -v` only when you also want to remove local database
and Redis volumes.

### Configuration

Copy `.env.example` to `.env`. Never commit the real `.env` file.

| Variable | Purpose |
|---|---|
| `OMNITRADE_DATABASE_URL` | PostgreSQL connection string |
| `OMNITRADE_REDIS_URL` | Redis connection string |
| `OMNITRADE_JWT_SECRET` | Local authentication signing secret |
| `OMNITRADE_ARTIFACT_DIR` | Report and artifact location |
| `OMNITRADE_FIXTURE_MODE` | Enables deterministic evidence only for tests |

Replace all example credentials and secrets before any shared deployment.

## Using the application

1. Open **Connections**, save the needed provider settings, and verify each connection.
2. Open **New Analysis**. It uses the latest published Workflow Lab graph automatically. Choose the stock, provider chains, models, agents, and analysis policy.
3. Start the run and follow each node in **Agent Room**.
4. Open **Reports** to read every analyst, debate, risk, and manager view.
5. Use **Workflow Lab** for advanced graph editing, then save, validate, and publish it.

When two verified providers support the same data role, their controls become
checkboxes. For example, Yahoo Finance and Alpha Vantage can both be selected
for market, fundamental, news, or sentiment evidence. The ordered chain uses
the next selected provider when the earlier provider fails.

The normal Docker application accepts real providers only. Credentials are held
in API memory for the current server session. They are never written to the
database, run state, event stream, report, or exported artifact. Real provider
fallback is explicit: the user selects an ordered chain, and OmniTrade never
inserts recorded evidence when that chain fails.

Model connections cover OpenAI, Gemini, Anthropic, xAI, DeepSeek, Qwen, GLM,
MiniMax, OpenRouter, Mistral, Kimi, Groq, NVIDIA NIM, Azure OpenAI, Amazon
Bedrock, Ollama, and other OpenAI-compatible servers. Data connections cover
Yahoo Finance, Alpha Vantage, FRED, Polymarket, and optional StockTwits and
Reddit public feeds. Yahoo and Polymarket can be connected automatically.
StockTwits and Reddit must be selected and verified manually because their
anonymous public endpoints may reject or rate-limit requests. A failed optional
public feed is removed from the session instead of being left as usable. Alpha
Vantage requires its own API key.

New Analysis shows a verified provider map and places every provider only in
the roles supported by its API. The How to Use tab contains expandable steps
for every index range and an openable/downloadable complete guide file.

Amazon Bedrock accepts either an AWS Bedrock bearer token or standard temporary
AWS credentials. The user can register several Bedrock model IDs and choose
different quick and deep models for each analysis.

Investor profile values are active workflow inputs. The investment horizon
changes analysis thresholds, the maximum acceptable loss changes risk checks,
the position limit changes decision guidance, excluded sectors can block a
`BUY` result, and experience level changes the detail of model explanations.

Workflow Lab uses the same typed-port rules as the backend validator. Selecting
a node shows its role, name and color controls, delete/reset actions, and safe
next-node suggestions. **Reset graph** restores the complete default draft but
keeps all published versions and old reports. An invalid edge is blocked before
it enters the draft.

If a distributed worker finishes after the API transport limit, OmniTrade
rebuilds the report from the final checkpoint and event stream. A result that
exceeds the selected runtime budget is kept and marked `degraded` instead of
being shown as interrupted with no report.

The time guard always rejects future evidence and stale core market or
fundamental evidence. When **Allow degraded results** is enabled, stale news,
sentiment, or macro branches are removed before analysis, recorded as quality
warnings, and the remaining workflow continues to an auditable report.

## API

The API is available at `http://localhost:8000`. Important routes include:

```text
POST   /api/v1/auth/login
GET    /api/v1/catalog
GET    /api/v1/analysis-options
GET    /api/v1/connections/catalog
PUT    /api/v1/connections/{provider}
POST   /api/v1/connections/{provider}/verify
GET    /api/v1/workflows
POST   /api/v1/workflows/{id}/validate
POST   /api/v1/workflows/{id}/publish
POST   /api/v1/workflows/{id}/reset-default
POST   /api/v1/runs
GET    /api/v1/runs/{id}
POST   /api/v1/runs/{id}/pause
POST   /api/v1/runs/{id}/cancel
POST   /api/v1/runs/{id}/resume
GET    /api/v1/runs/{id}/events
GET    /api/v1/runs/{id}/lineage
GET    /api/v1/reports/{id}
GET    /api/v1/reports/{id}/export/{format}
```

Interactive OpenAPI documentation is available at
[http://localhost:8000/docs](http://localhost:8000/docs).

## Testing and quality

### Backend

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
ruff check omnitrade tests
mypy omnitrade
```

### Frontend

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm test --run
pnpm build
pnpm exec playwright test
```

CI uses deterministic models and recorded evidence. Live provider tests must be
run separately. The workflow core has an 80% minimum coverage gate.

Latest local verification: 222 backend tests and 17 frontend tests passed. The
workflow engine reached 89% test coverage and the production frontend built
successfully. The configuration matrix covers every research depth, analyst
combination, risk profile, report level, reasoning level, supported language
and currency, temperature, retry count, and provider-chain contract.

A live AMD run also completed all 34 nodes with Amazon Bedrock and real data.
It used aggressive risk, detailed output, EUR conversion, high reasoning,
temperature 0.2, three retries, and four bounded debate rounds. Currency
conversion uses the current Frankfurter API and records the real FX rate in
evidence lineage.

## Project structure

```text
OmniTradeAI/
├── omnitrade/              Python services and domain logic
│   ├── engine/             Catalog, validator, scheduler, and executors
│   └── infrastructure/     Redis event adapter
├── frontend/               React web application and browser tests
├── migrations/             Alembic database migrations
├── tests/                  Backend unit and integration tests
├── docs/                   Requirements, architecture, ADRs, and Agile evidence
├── artifacts/defense/      Reproducible defense-scenario evidence
├── scripts/                Verification and scenario scripts
├── docker-compose.yml      Complete local deployment
└── .github/workflows/      Continuous integration
```

## Engineering documentation

- [Product requirements](docs/requirements.md)
- [Architecture](docs/architecture.md)
- [Feature classification](docs/feature-categories.md)
- [Requirements traceability](docs/traceability.md)
- [Agile increments](docs/agile/increments.md)
- [Implementation evidence](docs/agile/implementation-evidence.md)
- [ADR 0001: Custom event engine](docs/adr/0001-custom-event-engine.md)
- [ADR 0002: Modular services](docs/adr/0002-modular-services.md)
- [Reuse register](docs/reuse-register.md)
- [Complete user guide](docs/USER_GUIDE.md)

## Current limitations

- Real providers need network access and, where required, valid user credentials.
- Provider coverage, limits, costs, and model names can change outside this project.
- Recorded evidence and the deterministic model remain isolated test seams for CI; the Docker GUI does not offer them for analysis runs.
- The system supports stocks only.
- It does not manage portfolios or connect to a broker.
- A recommendation is not a guarantee of correctness or future performance.

## Academic team

Developed for the Software Engineering course in the Bachelor Degree Course in
Data Analysis (L-31), University of Messina.

- Mohammadamin Jahanimajd — Matricola 557910
- Mehdi Talebikhatir — Matricola 558948

Course professor: Prof. Salvatore Distefano.

---

<div align="center">

**OmniTrade AI — transparent financial analysis through explicit software workflows**

</div>
