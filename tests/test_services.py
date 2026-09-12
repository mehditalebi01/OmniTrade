import asyncio

from omnitrade.services import complete_json_with_retries, merge_model_narrative


def test_model_narrative_merge_keeps_backend_values_and_shape():
    draft = {
        "action": "HOLD",
        "confidence": 0.63,
        "strength": 0.71,
        "summary": "Original summary",
        "key_points": ["First point", "Second point"],
        "nested": {"score": 4, "explanation": "Original explanation"},
    }
    proposed = {
        "action": "BUY",
        "confidence": "high",
        "strength": 0.12,
        "summary": "Clear model summary",
        "key_points": ["Improved first point", "Improved second point"],
        "nested": {"score": 99, "explanation": "Improved explanation"},
        "extra": "must be ignored",
    }

    merged = merge_model_narrative(draft, proposed, {"action", "confidence", "strength"})

    assert merged == {
        "action": "HOLD",
        "confidence": 0.63,
        "strength": 0.71,
        "summary": "Clear model summary",
        "key_points": ["Improved first point", "Improved second point"],
        "nested": {"score": 4, "explanation": "Improved explanation"},
    }


def test_model_narrative_merge_rejects_list_shape_change():
    draft = {"sections": [{"title": "One"}, {"title": "Two"}]}
    proposed = {"sections": [{"title": "Only one"}]}

    assert merge_model_narrative(draft, proposed) == draft


def test_malformed_model_json_is_retried_then_merged_safely():
    class Client:
        def __init__(self):
            self.calls = 0

        async def complete(self, _prompt: str) -> str:
            self.calls += 1
            return "{bad json" if self.calls == 1 else '{"summary":"Valid"}'

    client = Client()
    assert asyncio.run(complete_json_with_retries(client, "prompt", 2)) == {"summary": "Valid"}
    assert client.calls == 2
