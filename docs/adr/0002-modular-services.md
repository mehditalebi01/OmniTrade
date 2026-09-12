# ADR 0002: Five backend services with versioned contracts

Status: accepted.

A monolith is simpler to deploy but would mix scheduling, external failures,
model budgets and report generation. We separate API, workflow, evidence, model
and report responsibilities. Docker Compose keeps deployment suitable for a
course project. Versioned events reduce coupling and allow independent tests.

