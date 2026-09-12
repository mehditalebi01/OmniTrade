import asyncio

import pytest
from pydantic import BaseModel

from omnitrade.model_gateway import (
    BedrockClient,
    DeterministicFakeModel,
    InvalidModelOutput,
    extract_json_object,
    typed_completion,
)


class Output(BaseModel):
    score: float


def test_typed_model_output():
    assert (
        asyncio.run(typed_completion(DeterministicFakeModel({"score": 0.7}), "x", Output)).score
        == 0.7
    )


def test_bad_model_output_is_rejected():
    with pytest.raises(InvalidModelOutput):
        asyncio.run(typed_completion(DeterministicFakeModel({"wrong": 1}), "x", Output))


def test_fenced_json_from_compatible_provider_is_accepted():
    assert extract_json_object('```json\n{"status":"ok"}\n```') == {"status": "ok"}


def test_bedrock_bearer_token_uses_direct_authorization_header(monkeypatch: pytest.MonkeyPatch):
    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"output": {"message": {"content": [{"text": '{"status":"ok"}'}]}}}

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        async def post(self, url: str, **kwargs: object) -> Response:
            assert url.endswith("/model/us.anthropic.claude-sonnet-4-6/converse")
            headers = kwargs["headers"]
            assert isinstance(headers, dict)
            assert headers["Authorization"] == "Bearer private-token"
            return Response()

    monkeypatch.setattr("omnitrade.model_gateway.httpx.AsyncClient", lambda **_: Client())
    result = asyncio.run(
        BedrockClient(
            {
                "provider": "bedrock",
                "region": "us-east-1",
                "aws_bearer_token_bedrock": "private-token",
            },
            "us.anthropic.claude-sonnet-4-6",
        ).complete("verify")
    )
    assert result == '{"status":"ok"}'
