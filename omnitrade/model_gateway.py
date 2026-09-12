from __future__ import annotations

import json
from typing import Any, Protocol, TypeVar
from urllib.parse import quote

import httpx
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class ModelClient(Protocol):
    async def complete(self, prompt: str) -> str: ...


class InvalidModelOutput(RuntimeError):
    pass


class DeterministicFakeModel:
    def __init__(self, response: dict[str, object]):
        self.response = response

    async def complete(self, prompt: str) -> str:
        return json.dumps(self.response, sort_keys=True)


class OpenAICompatibleClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 30,
        temperature: float | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature

    async def complete(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    **({"temperature": self.temperature} if self.temperature is not None else {}),
                },
            )
            response.raise_for_status()
            return str(response.json()["choices"][0]["message"]["content"])


class AnthropicClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.anthropic.com",
        temperature: float | None = None,
    ):
        self.api_key, self.model, self.base_url = api_key, model, base_url.rstrip("/")
        self.temperature = temperature

    async def complete(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/v1/messages",
                headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
                json={
                    "model": self.model,
                    "max_tokens": 1800,
                    **({"temperature": self.temperature} if self.temperature is not None else {}),
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            return str(response.json()["content"][0]["text"])


class GeminiClient:
    def __init__(self, api_key: str, model: str, temperature: float | None = None):
        self.api_key, self.model = api_key, model
        self.temperature = temperature

    async def complete(self, prompt: str) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        )
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                url,
                params={"key": self.api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        **(
                            {"temperature": self.temperature}
                            if self.temperature is not None
                            else {}
                        ),
                        "responseMimeType": "application/json",
                    },
                },
            )
            response.raise_for_status()
            return str(response.json()["candidates"][0]["content"]["parts"][0]["text"])


class AzureOpenAIClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        api_version: str,
        temperature: float | None = None,
    ):
        self.api_key, self.model = api_key, model
        self.base_url, self.api_version = base_url.rstrip("/"), api_version
        self.temperature = temperature

    async def complete(self, prompt: str) -> str:
        url = f"{self.base_url}/openai/deployments/{self.model}/chat/completions"
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                url,
                params={"api-version": self.api_version},
                headers={"api-key": self.api_key},
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    **({"temperature": self.temperature} if self.temperature is not None else {}),
                },
            )
            response.raise_for_status()
            return str(response.json()["choices"][0]["message"]["content"])


class BedrockClient:
    def __init__(self, settings: dict[str, str], model: str, temperature: float | None = None):
        self.settings, self.model = settings, model
        self.temperature = temperature

    async def complete(self, prompt: str) -> str:
        import asyncio

        bearer_token = self.settings.get("aws_bearer_token_bedrock")
        if bearer_token:
            region = self.settings.get("region") or "us-east-1"
            model_path = quote(self.model, safe=".:-_")
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(
                    f"https://bedrock-runtime.{region}.amazonaws.com/model/{model_path}/converse",
                    headers={
                        "Authorization": f"Bearer {bearer_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "messages": [{"role": "user", "content": [{"text": prompt}]}],
                        "inferenceConfig": {
                            **(
                                {"temperature": self.temperature}
                                if self.temperature is not None
                                else {}
                            ),
                            "maxTokens": 1800,
                        },
                    },
                )
                response.raise_for_status()
                return str(response.json()["output"]["message"]["content"][0]["text"])

        def call() -> str:
            try:
                import boto3  # type: ignore[import-untyped]
            except ImportError as exc:
                raise RuntimeError("Amazon Bedrock support requires the boto3 package") from exc
            client = boto3.client(
                "bedrock-runtime",
                region_name=self.settings.get("region") or "us-east-1",
                aws_access_key_id=self.settings.get("aws_access_key_id"),
                aws_secret_access_key=self.settings.get("aws_secret_access_key"),
                aws_session_token=self.settings.get("aws_session_token"),
            )
            response = client.converse(
                modelId=self.model,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={
                    **({"temperature": self.temperature} if self.temperature is not None else {}),
                    "maxTokens": 1800,
                },
            )
            return str(response["output"]["message"]["content"][0]["text"])

        return await asyncio.to_thread(call)


def build_model_client(
    settings: dict[str, str], model: str, temperature: float | None = None
) -> ModelClient:
    provider = settings["provider"]
    api_key = settings.get("api_key", "")
    if provider == "anthropic":
        return AnthropicClient(
            api_key, model, settings.get("base_url", "https://api.anthropic.com"), temperature
        )
    if provider == "google":
        return GeminiClient(api_key, model, temperature)
    if provider == "azure":
        return AzureOpenAIClient(
            api_key,
            model,
            settings["base_url"],
            settings.get("azure_api_version", "2024-10-21"),
            temperature,
        )
    if provider == "bedrock":
        return BedrockClient(settings, model, temperature)
    base_url = settings.get("base_url")
    if not base_url:
        raise ValueError(f"A base URL is required for {provider}")
    return OpenAICompatibleClient(
        base_url, api_key or "not-required", model, temperature=temperature
    )


def extract_json_object(raw: str) -> dict[str, Any]:
    """Accept plain JSON or a fenced JSON object, then reject non-object output."""
    value = raw.strip()
    if value.startswith("```"):
        value = value.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise InvalidModelOutput("Model output must be one JSON object")
    return parsed


async def typed_completion(client: ModelClient, prompt: str, output_type: type[T]) -> T:
    raw = await client.complete(prompt)
    try:
        return output_type.model_validate_json(raw)
    except (ValidationError, ValueError) as exc:
        raise InvalidModelOutput(f"Model output failed {output_type.__name__} validation") from exc
