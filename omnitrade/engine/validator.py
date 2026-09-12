from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Mapping

from omnitrade.contracts import (
    NodeDefinition,
    ValidationIssue,
    ValidationResult,
    WorkflowDefinition,
)
from omnitrade.engine.catalog import NODE_CATALOG, ports_compatible


class WorkflowValidator:
    def validate(self, workflow: WorkflowDefinition) -> ValidationResult:
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []
        nodes = {node.id: node for node in workflow.nodes}
        normal_adj: dict[str, list[str]] = defaultdict(list)
        reverse: dict[str, list[str]] = defaultdict(list)

        starts = [node for node in workflow.nodes if node.type == "start"]
        ends = [node for node in workflow.nodes if node.type == "end"]
        if len(starts) != 1:
            errors.append(
                ValidationIssue(
                    code="START_COUNT", message="Workflow must have exactly one start node"
                )
            )
        if len(ends) != 1:
            errors.append(
                ValidationIssue(code="END_COUNT", message="Workflow must have exactly one end node")
            )

        for node in workflow.nodes:
            spec = NODE_CATALOG.get(node.type)
            if spec is None:
                errors.append(
                    ValidationIssue(
                        code="UNKNOWN_NODE",
                        message=f"Unknown node type: {node.type}",
                        node_id=node.id,
                    )
                )
                continue
            for key in spec.required_config:
                if key not in node.config:
                    errors.append(
                        ValidationIssue(
                            code="MISSING_CONFIG",
                            message=f"Required config '{key}' is missing",
                            node_id=node.id,
                        )
                    )
            if node.type == "bounded_loop":
                bound = node.config.get("max_iterations")
                if not isinstance(bound, int) or not 1 <= bound <= 5:
                    errors.append(
                        ValidationIssue(
                            code="UNBOUNDED_LOOP",
                            message="Loop bound must be an integer from 1 to 5",
                            node_id=node.id,
                        )
                    )
            if node.type == "join" and node.config.get("join_policy") not in {
                "all",
                "required",
                "first_success",
            }:
                errors.append(
                    ValidationIssue(
                        code="INVALID_JOIN",
                        message="Join policy must be all, required, or first_success",
                        node_id=node.id,
                    )
                )

        for edge in workflow.edges:
            source = nodes.get(edge.source)
            target = nodes.get(edge.target)
            if source is None or target is None:
                errors.append(
                    ValidationIssue(
                        code="DANGLING_EDGE",
                        message="Edge endpoint does not exist",
                        edge_id=edge.id,
                    )
                )
                continue
            source_spec = NODE_CATALOG.get(source.type)
            target_spec = NODE_CATALOG.get(target.type)
            if source_spec is None or target_spec is None:
                continue
            source_type = source_spec.outputs.get(edge.source_port)
            target_type = target_spec.inputs.get(edge.target_port)
            if source_type is None or target_type is None:
                errors.append(
                    ValidationIssue(
                        code="UNKNOWN_PORT", message="Edge uses an unknown port", edge_id=edge.id
                    )
                )
            elif not ports_compatible(source_type, target_type):
                errors.append(
                    ValidationIssue(
                        code="PORT_TYPE",
                        message=f"Cannot connect {source_type} to {target_type}",
                        edge_id=edge.id,
                    )
                )
            if edge.loop:
                if target.type != "bounded_loop" and source.type != "bounded_loop":
                    errors.append(
                        ValidationIssue(
                            code="LOOP_GATE",
                            message="A loop edge must pass through bounded_loop",
                            edge_id=edge.id,
                        )
                    )
            else:
                normal_adj[source.id].append(target.id)
                reverse[target.id].append(source.id)

        if starts:
            reachable = self._reachable(starts[0].id, normal_adj)
            for node_id in nodes.keys() - reachable:
                errors.append(
                    ValidationIssue(
                        code="UNREACHABLE",
                        message="Node is unreachable from start",
                        node_id=node_id,
                    )
                )
        if self._has_cycle(nodes, normal_adj):
            errors.append(
                ValidationIssue(
                    code="UNBOUNDED_CYCLE", message="Cycles are allowed only on declared loop edges"
                )
            )

        self._validate_input_edges(workflow, reverse, errors)
        self._validate_loop_safety(workflow, nodes, errors)
        self._validate_budget(workflow, errors, warnings)
        return ValidationResult(valid=not errors, errors=errors, warnings=warnings)

    @staticmethod
    def _reachable(start: str, adjacency: dict[str, list[str]]) -> set[str]:
        seen: set[str] = set()
        stack = [start]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(adjacency[current])
        return seen

    @staticmethod
    def _has_cycle(nodes: Mapping[str, NodeDefinition], adjacency: dict[str, list[str]]) -> bool:
        indegree = {node_id: 0 for node_id in nodes}
        for targets in adjacency.values():
            for target in targets:
                indegree[target] += 1
        queue = deque(node_id for node_id, degree in indegree.items() if degree == 0)
        visited = 0
        while queue:
            current = queue.popleft()
            visited += 1
            for target in adjacency[current]:
                indegree[target] -= 1
                if indegree[target] == 0:
                    queue.append(target)
        return visited != len(nodes)

    @staticmethod
    def _validate_input_edges(
        workflow: WorkflowDefinition, reverse: dict[str, list[str]], errors: list[ValidationIssue]
    ) -> None:
        for node in workflow.nodes:
            spec = NODE_CATALOG.get(node.type)
            if not spec or not spec.inputs:
                continue
            incoming = [edge for edge in workflow.edges if edge.target == node.id]
            covered = {edge.target_port for edge in incoming}
            for port in spec.inputs:
                if port not in covered:
                    errors.append(
                        ValidationIssue(
                            code="MISSING_INPUT",
                            message=f"Required input '{port}' is not connected",
                            node_id=node.id,
                        )
                    )
            if node.type == "join" and len(reverse[node.id]) < 2:
                errors.append(
                    ValidationIssue(
                        code="INVALID_JOIN",
                        message="Join needs at least two incoming branches",
                        node_id=node.id,
                    )
                )

    @staticmethod
    def _validate_loop_safety(
        workflow: WorkflowDefinition,
        nodes: Mapping[str, NodeDefinition],
        errors: list[ValidationIssue],
    ) -> None:
        loop_node_ids = {edge.source for edge in workflow.edges if edge.loop} | {
            edge.target for edge in workflow.edges if edge.loop
        }
        for node_id in loop_node_ids:
            node = nodes.get(node_id)
            if node is None:
                continue
            spec = NODE_CATALOG.get(node.type)
            if spec and spec.side_effect:
                errors.append(
                    ValidationIssue(
                        code="LOOP_SIDE_EFFECT",
                        message="Side-effect nodes are not safe inside loops",
                        node_id=node_id,
                    )
                )

    @staticmethod
    def _validate_budget(
        workflow: WorkflowDefinition, errors: list[ValidationIssue], warnings: list[ValidationIssue]
    ) -> None:
        model_calls = sum(
            NODE_CATALOG.get(node.type, NODE_CATALOG["start"]).model_cost for node in workflow.nodes
        )
        provider_calls = sum(
            NODE_CATALOG.get(node.type, NODE_CATALOG["start"]).provider_cost
            * node.retry.max_attempts
            for node in workflow.nodes
        )
        # The runtime repeats only the bounded-loop control node. It does not
        # rerun every model node, so multiplying the full graph by the research
        # depth rejects valid configurations and overstates the real cost.
        if model_calls > workflow.budget.max_model_calls:
            errors.append(
                ValidationIssue(
                    code="MODEL_BUDGET",
                    message=f"Graph may need {model_calls} model calls but budget allows {workflow.budget.max_model_calls}",
                )
            )
        if provider_calls > workflow.budget.max_provider_calls:
            errors.append(
                ValidationIssue(
                    code="PROVIDER_BUDGET",
                    message=f"Graph may need {provider_calls} provider calls but budget allows {workflow.budget.max_provider_calls}",
                )
            )
        if workflow.budget.max_runtime_seconds < len(workflow.nodes):
            warnings.append(
                ValidationIssue(
                    code="TIGHT_RUNTIME", message="Runtime budget may be too small for this graph"
                )
            )
