# ADR 0001: Build a custom event-driven workflow engine

Status: accepted.

We need programmable complexity that is implemented and defendable by us.
LangGraph and general workflow products would hide the main assessed logic.
We therefore implement typed graph validation, scheduling, joins, bounded loops,
budgets, failure policy, checkpoints and resume ourselves. Redis Streams is only
transport; it does not decide workflow behavior.

