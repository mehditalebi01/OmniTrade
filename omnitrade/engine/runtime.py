from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from omnitrade.contracts import (
    Checkpoint,
    FailurePolicy,
    NodeDefinition,
    NodeRun,
    NodeStatus,
    Run,
    RunEvent,
    RunStatus,
    WorkflowDefinition,
)
from omnitrade.engine.validator import WorkflowValidator

NodeExecutor = Callable[[NodeDefinition, dict[str, Any], "ExecutionContext"], Awaitable[Any]]
EventListener = Callable[[RunEvent], Awaitable[None]]
CancellationProbe = Callable[[UUID], Awaitable[bool]]
PauseProbe = Callable[[UUID], Awaitable[bool]]


class ExecutionError(RuntimeError):
    pass


class WorkerCrash(RuntimeError):
    """Signals process loss; normal node failures must not use this exception."""

    pass


@dataclass
class ExecutionContext:
    run: Run
    connections: dict[str, dict[str, str]] = field(default_factory=dict, repr=False)
    provider_calls: int = 0
    model_calls: int = 0
    tokens: int = 0
    cancelled: asyncio.Event = field(default_factory=asyncio.Event)

    def spend_provider_call(self) -> None:
        self.provider_calls += 1

    def spend_model_call(self, tokens: int = 0) -> None:
        self.model_calls += 1
        self.tokens += tokens


@dataclass
class ExecutionResult:
    run: Run
    node_runs: dict[str, NodeRun]
    events: list[RunEvent]
    checkpoints: list[Checkpoint]


class WorkflowRuntime:
    """Deterministic scheduler owned by OmniTrade AI, not a workflow library."""

    def __init__(
        self,
        executors: dict[str, NodeExecutor],
        listener: EventListener | None = None,
        cancellation_probe: CancellationProbe | None = None,
        pause_probe: PauseProbe | None = None,
        connections: dict[str, dict[str, str]] | None = None,
    ):
        self.executors = executors
        self.listener = listener
        self.cancellation_probe = cancellation_probe
        self.pause_probe = pause_probe
        self.connections = connections or {}
        self._events: list[RunEvent] = []
        self._checkpoints: list[Checkpoint] = []
        self._checkpoint_sequence = 0

    async def execute(
        self,
        workflow: WorkflowDefinition,
        run: Run,
        restored: Checkpoint | None = None,
    ) -> ExecutionResult:
        validation = WorkflowValidator().validate(workflow)
        if not validation.valid:
            raise ExecutionError("Cannot execute an invalid workflow")

        self._events = []
        self._checkpoints = []
        self._checkpoint_sequence = restored.sequence if restored else 0
        states = (
            {key: value.model_copy(deep=True) for key, value in restored.node_states.items()}
            if restored
            else {node.id: NodeRun(run_id=run.id, node_id=node.id) for node in workflow.nodes}
        )
        context = ExecutionContext(run=run, connections=self.connections)
        run.status = RunStatus.RUNNING
        await self._emit(run, "run.started")

        nodes = {node.id: node for node in workflow.nodes}
        incoming: dict[str, list[Any]] = defaultdict(list)
        outgoing: dict[str, list[Any]] = defaultdict(list)
        for edge in workflow.edges:
            if not edge.loop:
                incoming[edge.target].append(edge)
                outgoing[edge.source].append(edge)

        try:
            while True:
                if self.cancellation_probe and await self.cancellation_probe(run.id):
                    context.cancelled.set()
                if context.cancelled.is_set():
                    await self._cancel(run, states)
                    break
                if self.pause_probe and await self.pause_probe(run.id):
                    await self._pause(run, states)
                    break
                ready = self._ready_nodes(nodes, incoming, states)
                if not ready:
                    if all(
                        state.status in self._terminal_node_states() for state in states.values()
                    ):
                        break
                    pending = [
                        node_id
                        for node_id, state in states.items()
                        if state.status == NodeStatus.PENDING
                    ]
                    if pending:
                        raise ExecutionError(f"Scheduler deadlock at nodes: {pending}")
                    break
                ready = sorted(ready)[: workflow.budget.max_parallel_nodes]
                for node_id in ready:
                    states[node_id].status = NodeStatus.READY
                    await self._emit(run, "node.ready", node_id)
                tasks = [
                    self._execute_node(nodes[node_id], incoming[node_id], states, context, workflow)
                    for node_id in ready
                ]
                await asyncio.gather(*tasks)
                await self._checkpoint(run, states)
                if any(
                    state.status == NodeStatus.FAILED
                    and nodes[node_id].failure_policy == FailurePolicy.REQUIRED
                    for node_id, state in states.items()
                ):
                    run.status = RunStatus.FAILED
                    self._skip_blocked(states)
                    break
        except asyncio.CancelledError:
            context.cancelled.set()
            await self._cancel(run, states)
        except Exception as exc:
            run.status = RunStatus.INTERRUPTED
            await self._emit(run, "run.interrupted", payload={"error": str(exc)})
            raise

        if run.status in {RunStatus.RUNNING, RunStatus.DEGRADED}:
            run.status = RunStatus.DEGRADED if run.degraded_reasons else RunStatus.SUCCEEDED
            await self._emit(run, "run.completed", payload={"status": run.status})
        elif run.status == RunStatus.FAILED:
            await self._emit(run, "run.failed")
        run.updated_at = datetime.now(UTC)
        return ExecutionResult(
            run=run,
            node_runs=states,
            events=list(self._events),
            checkpoints=list(self._checkpoints),
        )

    async def _execute_node(
        self,
        node: NodeDefinition,
        edges: list[Any],
        states: dict[str, NodeRun],
        context: ExecutionContext,
        workflow: WorkflowDefinition,
    ) -> None:
        state = states[node.id]
        state.status = NodeStatus.RUNNING
        inputs: dict[str, Any] = defaultdict(list)
        for edge in sorted(edges, key=lambda item: item.id):
            value = states[edge.source].output
            inputs[edge.target_port].append(value)
        inputs = {key: values[0] if len(values) == 1 else values for key, values in inputs.items()}
        await self._emit(context.run, "node.started", node.id)
        executor = self.executors.get(node.type)
        if executor is None:
            state.status = NodeStatus.FAILED
            state.error = f"No executor for node type {node.type}"
            await self._emit(context.run, "node.failed", node.id, {"error": state.error})
            return

        last_error = ""
        for attempt in range(1, node.retry.max_attempts + 1):
            state.attempt = attempt
            try:
                if context.model_calls > workflow.budget.max_model_calls:
                    raise ExecutionError("Model-call budget exceeded")
                if context.provider_calls > workflow.budget.max_provider_calls:
                    raise ExecutionError("Provider-call budget exceeded")
                if context.tokens > workflow.budget.max_tokens:
                    raise ExecutionError("Token budget exceeded")
                call_inputs = dict(inputs)
                if (
                    attempt == node.retry.max_attempts
                    and attempt > 1
                    and node.retry.fallback_provider
                ):
                    call_inputs["_fallback_provider"] = node.retry.fallback_provider
                    await self._emit(
                        context.run,
                        "provider.fallback",
                        node.id,
                        {"provider": node.retry.fallback_provider},
                    )
                if node.type == "bounded_loop":
                    state.output = call_inputs
                    for iteration in range(1, int(node.config["max_iterations"]) + 1):
                        state.iteration = iteration
                        state.output = await asyncio.wait_for(
                            executor(node, {**call_inputs, "previous": state.output}, context),
                            timeout=node.timeout_seconds,
                        )
                        await self._emit(
                            context.run,
                            "node.loop_iteration",
                            node.id,
                            {"iteration": iteration, "bound": node.config["max_iterations"]},
                        )
                        if state.output.get("stopped", False):
                            break
                else:
                    state.output = await asyncio.wait_for(
                        executor(node, call_inputs, context), timeout=node.timeout_seconds
                    )
                quality_warnings = (
                    state.output.get("quality_warnings", [])
                    if node.type == "time_guard" and isinstance(state.output, dict)
                    else []
                )
                if quality_warnings:
                    state.status = NodeStatus.DEGRADED
                    for warning in quality_warnings:
                        reason = f"{node.id}: {warning}"
                        if reason not in context.run.degraded_reasons:
                            context.run.degraded_reasons.append(reason)
                    await self._emit(
                        context.run,
                        "node.degraded",
                        node.id,
                        {"warnings": quality_warnings},
                    )
                    return
                state.status = NodeStatus.SUCCEEDED
                await self._emit(context.run, "node.succeeded", node.id, {"attempt": attempt})
                return
            except WorkerCrash:
                raise
            except Exception as exc:
                last_error = str(exc)
                if attempt < node.retry.max_attempts:
                    await self._emit(
                        context.run,
                        "node.retrying",
                        node.id,
                        {"attempt": attempt, "error": last_error},
                    )
                    await asyncio.sleep(node.retry.backoff_ms / 1000)
        state.error = last_error
        if node.failure_policy == FailurePolicy.OPTIONAL:
            state.status = NodeStatus.DEGRADED
            context.run.degraded_reasons.append(f"{node.id}: {last_error}")
            await self._emit(context.run, "node.degraded", node.id, {"error": last_error})
        else:
            state.status = NodeStatus.FAILED
            await self._emit(context.run, "node.failed", node.id, {"error": last_error})

    @staticmethod
    def _ready_nodes(
        nodes: dict[str, NodeDefinition], incoming: dict[str, list[Any]], states: dict[str, NodeRun]
    ) -> list[str]:
        ready: list[str] = []
        acceptable = {NodeStatus.SUCCEEDED, NodeStatus.DEGRADED, NodeStatus.SKIPPED}
        for node_id in nodes:
            if states[node_id].status != NodeStatus.PENDING:
                continue
            parents = [edge.source for edge in incoming[node_id]]
            if not parents or all(states[parent].status in acceptable for parent in parents):
                ready.append(node_id)
        return ready

    @staticmethod
    def _terminal_node_states() -> set[NodeStatus]:
        return {
            NodeStatus.SUCCEEDED,
            NodeStatus.DEGRADED,
            NodeStatus.FAILED,
            NodeStatus.SKIPPED,
            NodeStatus.CANCELLED,
        }

    @staticmethod
    def _skip_blocked(states: dict[str, NodeRun]) -> None:
        for state in states.values():
            if state.status in {NodeStatus.PENDING, NodeStatus.READY}:
                state.status = NodeStatus.SKIPPED

    async def _checkpoint(self, run: Run, states: dict[str, NodeRun]) -> None:
        self._checkpoint_sequence += 1
        checkpoint = Checkpoint(
            run_id=run.id,
            sequence=self._checkpoint_sequence,
            node_states={key: value.model_copy(deep=True) for key, value in states.items()},
            consumed_event_ids={event.event_id for event in self._events},
        )
        self._checkpoints.append(checkpoint)
        await self._emit(
            run,
            "run.checkpointed",
            payload={
                "sequence": checkpoint.sequence,
                "node_states": {
                    key: value.model_dump(mode="json")
                    for key, value in checkpoint.node_states.items()
                },
            },
        )

    async def _cancel(self, run: Run, states: dict[str, NodeRun]) -> None:
        run.status = RunStatus.CANCELLED
        for state in states.values():
            if state.status not in self._terminal_node_states():
                state.status = NodeStatus.CANCELLED
        await self._emit(run, "run.cancelled")

    async def _pause(self, run: Run, states: dict[str, NodeRun]) -> None:
        """Stop only between node batches, after saving durable progress."""

        await self._checkpoint(run, states)
        run.status = RunStatus.PAUSED
        await self._emit(run, "run.paused")

    async def _emit(
        self,
        run: Run,
        event_type: str,
        node_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        event = RunEvent(
            event_type=event_type,
            run_id=run.id,
            node_id=node_id,
            trace_id=run.trace_id,
            payload=payload or {},
        )
        self._events.append(event)
        if self.listener:
            await self.listener(event)
