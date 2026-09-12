from omnitrade.engine.validator import WorkflowValidator
from omnitrade.sample_workflow import defense_workflow


def codes(result):
    return {item.code for item in result.errors}


def test_complete_defense_graph_is_valid():
    result = WorkflowValidator().validate(defense_workflow())
    assert result.valid, result.errors


def test_optional_sentiment_agent_can_be_removed_and_published():
    graph = defense_workflow()
    graph.nodes = [node for node in graph.nodes if node.id != "sentiment_analyst"]
    graph.edges = [
        edge
        for edge in graph.edges
        if edge.source != "sentiment_analyst" and edge.target != "sentiment_analyst"
    ]
    result = WorkflowValidator().validate(graph)
    assert result.valid, result.errors


def test_rejects_missing_start():
    graph = defense_workflow()
    graph.nodes = [n for n in graph.nodes if n.type != "start"]
    assert "START_COUNT" in codes(WorkflowValidator().validate(graph))


def test_rejects_wrong_port_type():
    graph = defense_workflow()
    graph.edges[0].target_port = "report"
    assert "UNKNOWN_PORT" in codes(WorkflowValidator().validate(graph))


def test_rejects_unbounded_loop():
    graph = defense_workflow()
    next(n for n in graph.nodes if n.type == "bounded_loop").config["max_iterations"] = 50
    assert "UNBOUNDED_LOOP" in codes(WorkflowValidator().validate(graph))


def test_rejects_budget_overrun():
    graph = defense_workflow()
    graph.budget.max_model_calls = 1
    assert "MODEL_BUDGET" in codes(WorkflowValidator().validate(graph))
