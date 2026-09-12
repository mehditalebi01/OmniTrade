from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
from pydantic import BaseModel, Field, SecretStr

from omnitrade.model_gateway import build_model_client


class ConnectionInput(BaseModel):
    """Session-only integration settings. Secret values are never returned."""

    provider: str = Field(min_length=2, max_length=40)
    api_key: SecretStr | None = None
    base_url: str | None = Field(default=None, max_length=500)
    test_model: str | None = Field(default=None, max_length=180)
    model_ids: list[str] = Field(default_factory=list, max_length=50)
    region: str | None = Field(default=None, max_length=50)
    aws_bearer_token_bedrock: SecretStr | None = None
    aws_access_key_id: SecretStr | None = None
    aws_secret_access_key: SecretStr | None = None
    aws_session_token: SecretStr | None = None
    azure_api_version: str | None = Field(default=None, max_length=40)

    def runtime_dict(self) -> dict[str, str]:
        values: dict[str, str] = {"provider": self.provider}
        for name in ("base_url", "test_model", "region", "azure_api_version"):
            value = getattr(self, name)
            if value:
                values[name] = value
        if self.model_ids:
            values["model_ids"] = "\n".join(dict.fromkeys(self.model_ids))
        for name in (
            "api_key",
            "aws_bearer_token_bedrock",
            "aws_access_key_id",
            "aws_secret_access_key",
            "aws_session_token",
        ):
            value = getattr(self, name)
            if value:
                values[name] = value.get_secret_value()
        return values


class ConnectionStatus(BaseModel):
    provider: str
    category: str
    configured: bool
    verified: bool = False
    message: str = "Not configured"
    base_url: str | None = None
    test_model: str | None = None
    models: list[str] = Field(default_factory=list)


@dataclass
class SessionConnectionStore:
    _values: dict[UUID, dict[str, ConnectionInput]] = field(default_factory=dict)
    _verification: dict[tuple[UUID, str], tuple[bool, str]] = field(default_factory=dict)
    _models: dict[tuple[UUID, str], list[str]] = field(default_factory=dict)

    def put(self, user_id: UUID, value: ConnectionInput) -> ConnectionStatus:
        current = self.get(user_id, value.provider)
        if current:
            for secret_name in (
                "api_key",
                "aws_bearer_token_bedrock",
                "aws_access_key_id",
                "aws_secret_access_key",
                "aws_session_token",
            ):
                if getattr(value, secret_name) is None:
                    setattr(value, secret_name, getattr(current, secret_name))
        self._values.setdefault(user_id, {})[value.provider] = value
        self._verification.pop((user_id, value.provider), None)
        self._models.pop((user_id, value.provider), None)
        return self.status(user_id, value.provider)

    def delete(self, user_id: UUID, provider: str) -> None:
        self._values.get(user_id, {}).pop(provider, None)
        self._verification.pop((user_id, provider), None)
        self._models.pop((user_id, provider), None)

    def get(self, user_id: UUID, provider: str) -> ConnectionInput | None:
        return self._values.get(user_id, {}).get(provider)

    def runtime_connections(self, user_id: UUID) -> dict[str, dict[str, str]]:
        return {
            name: value.runtime_dict()
            for name, value in self._values.get(user_id, {}).items()
            if self._verification.get((user_id, name), (False, ""))[0]
        }

    def status(self, user_id: UUID, provider: str) -> ConnectionStatus:
        spec = PROVIDER_CATALOG[provider]
        value = self.get(user_id, provider)
        verified, message = self._verification.get((user_id, provider), (False, "Not verified"))
        return ConnectionStatus(
            provider=provider,
            category=spec["category"],
            configured=value is not None,
            verified=verified,
            message=message if value else "Not configured",
            base_url=value.base_url if value else spec.get("base_url"),
            test_model=value.test_model if value else None,
            models=self.models(user_id, provider) if value else list(spec.get("models", [])),
        )

    def statuses(self, user_id: UUID) -> list[ConnectionStatus]:
        return [self.status(user_id, name) for name in PROVIDER_CATALOG]

    def mark_verified(self, user_id: UUID, provider: str, ok: bool, message: str) -> None:
        self._verification[(user_id, provider)] = (ok, message)

    def save_models(self, user_id: UUID, provider: str, models: list[str]) -> None:
        self._models[(user_id, provider)] = sorted(set(models))

    def models(self, user_id: UUID, provider: str) -> list[str]:
        discovered = self._models.get((user_id, provider), [])
        value = self.get(user_id, provider)
        configured = (
            (value.model_ids + ([value.test_model] if value.test_model else [])) if value else []
        )
        catalog = list(MODEL_PROVIDERS.get(provider, {}).get("models", []))
        return list(dict.fromkeys(discovered or configured or catalog))


MODEL_PROVIDERS: dict[str, dict[str, Any]] = {
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-5.4-mini", "gpt-5.4-nano", "gpt-5.5", "gpt-5.4", "gpt-5.2", "gpt-5.5-pro"],
    },
    "google": {
        "label": "Google Gemini",
        "models": ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.1-pro-preview"],
    },
    "anthropic": {
        "label": "Anthropic Claude",
        "base_url": "https://api.anthropic.com",
        "models": [
            "claude-sonnet-5",
            "claude-haiku-4-5",
            "claude-fable-5",
            "claude-opus-4-8",
            "claude-opus-4-7",
        ],
    },
    "xai": {
        "label": "xAI",
        "base_url": "https://api.x.ai/v1",
        "models": [
            "grok-4.3",
            "grok-4.20-0309-non-reasoning",
            "grok-build-0.1",
            "grok-4.20-0309-reasoning",
            "grok-4.20-multi-agent-0309",
        ],
    },
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "models": ["deepseek-v4-flash", "deepseek-v4-pro"],
    },
    "qwen": {
        "label": "Qwen International",
        "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen3.7-plus", "qwen3.7-max", "qwen3.6-plus", "qwen3.6-max"],
    },
    "qwen-cn": {
        "label": "Qwen China",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen3.7-plus", "qwen3.7-max", "qwen3.6-plus", "qwen3.6-max"],
    },
    "glm": {
        "label": "GLM International",
        "base_url": "https://api.z.ai/api/paas/v4",
        "models": ["glm-5-turbo", "glm-5.2", "glm-5.1", "glm-5", "glm-4.7", "glm-4.5-air"],
    },
    "glm-cn": {
        "label": "GLM China",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["glm-5-turbo", "glm-5.2", "glm-5.1", "glm-5", "glm-4.7", "glm-4.5-air"],
    },
    "minimax": {
        "label": "MiniMax Global",
        "base_url": "https://api.minimax.io/v1",
        "models": [
            "MiniMax-M3",
            "MiniMax-M2.7-highspeed",
            "MiniMax-M2.7",
            "MiniMax-M2.5-highspeed",
            "MiniMax-M2.5",
        ],
    },
    "minimax-cn": {
        "label": "MiniMax China",
        "base_url": "https://api.minimaxi.com/v1",
        "models": [
            "MiniMax-M3",
            "MiniMax-M2.7-highspeed",
            "MiniMax-M2.7",
            "MiniMax-M2.5-highspeed",
            "MiniMax-M2.5",
        ],
    },
    "openrouter": {"label": "OpenRouter", "base_url": "https://openrouter.ai/api/v1", "models": []},
    "mistral": {"label": "Mistral", "base_url": "https://api.mistral.ai/v1", "models": []},
    "kimi": {"label": "Kimi (Moonshot)", "base_url": "https://api.moonshot.ai/v1", "models": []},
    "groq": {"label": "Groq", "base_url": "https://api.groq.com/openai/v1", "models": []},
    "nvidia": {
        "label": "NVIDIA NIM",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "models": [],
    },
    "azure": {"label": "Azure OpenAI", "models": []},
    "bedrock": {"label": "Amazon Bedrock", "models": []},
    "ollama": {
        "label": "Ollama",
        "base_url": "http://host.docker.internal:11434/v1",
        "models": ["qwen3:latest", "gpt-oss:latest", "glm-4.7-flash:latest"],
        "key_optional": True,
    },
    "openai_compatible": {"label": "OpenAI-compatible server", "models": [], "key_optional": True},
}

DATA_PROVIDERS: dict[str, dict[str, Any]] = {
    "yfinance": {
        "label": "Yahoo Finance",
        "key_optional": True,
        "auto_connect": True,
        "capabilities": ["market", "fundamentals", "news", "sentiment"],
    },
    "alpha_vantage": {
        "label": "Alpha Vantage",
        "base_url": "https://www.alphavantage.co/query",
        "credential_note": "Requires an Alpha Vantage API key. After verification it adds market, fundamental, news, sentiment, and macro choices.",
        "capabilities": ["market", "fundamentals", "news", "sentiment", "macro"],
    },
    "fred": {
        "label": "FRED",
        "base_url": "https://api.stlouisfed.org/fred",
        "credential_note": "Requires a FRED API key and provides macroeconomic series.",
        "capabilities": ["macro"],
    },
    "polymarket": {
        "label": "Polymarket",
        "base_url": "https://gamma-api.polymarket.com",
        "key_optional": True,
        "auto_connect": True,
        "capabilities": ["macro", "prediction_markets"],
    },
    "stocktwits": {
        "label": "StockTwits",
        "base_url": "https://api.stocktwits.com/api/2",
        "key_optional": True,
        "auto_connect": False,
        "availability_note": "Optional public feed. Its endpoint may block or rate-limit requests, so connect and verify it manually.",
        "capabilities": ["sentiment"],
    },
    "reddit": {
        "label": "Reddit public feeds",
        "key_optional": True,
        "auto_connect": False,
        "availability_note": "Optional public feed. Reddit may reject anonymous requests, so connect and verify it manually.",
        "capabilities": ["sentiment"],
    },
}

PROVIDER_CATALOG: dict[str, dict[str, Any]] = {
    **{key: {**value, "category": "model"} for key, value in MODEL_PROVIDERS.items()},
    **{key: {**value, "category": "data"} for key, value in DATA_PROVIDERS.items()},
}


def verification_error_message(provider: str, exc: Exception) -> str:
    """Return a short user-safe reason instead of a raw provider URL and stack detail."""
    label = PROVIDER_CATALOG[provider]["label"]
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 403:
            return f"{label} refused the request (HTTP 403). Public access is blocked from this network."
        if status == 429:
            return f"{label} rate limit reached (HTTP 429). Try later or use another provider."
        return f"{label} returned HTTP {status}. Check the provider, key, quota, and network."
    return str(exc)


async def verify_connection(value: ConnectionInput) -> str:
    spec = PROVIDER_CATALOG[value.provider]
    runtime = value.runtime_dict()
    if spec["category"] == "model":
        if not value.test_model:
            raise ValueError("Select a test model before verification")
        model_client = build_model_client(runtime, value.test_model)
        answer = await model_client.complete('Return only JSON: {"status":"ok"}')
        if "ok" not in answer.lower():
            raise ValueError("The model answered, but its verification output was invalid")
        return "Model connection verified"
    base_url = runtime.get("base_url") or str(spec.get("base_url", ""))
    api_key = runtime.get("api_key", "")
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        if value.provider == "alpha_vantage":
            response = await client.get(
                base_url, params={"function": "SYMBOL_SEARCH", "keywords": "IBM", "apikey": api_key}
            )
        elif value.provider == "fred":
            response = await client.get(
                f"{base_url.rstrip('/')}/series",
                params={"series_id": "DGS10", "api_key": api_key, "file_type": "json"},
            )
        elif value.provider == "polymarket":
            response = await client.get(f"{base_url.rstrip('/')}/markets", params={"limit": 1})
        elif value.provider in {"stocktwits", "reddit"}:
            from omnitrade.providers import live_provider

            await live_provider(value.provider, runtime).fetch_node(
                "fetch_sentiment", "AAPL", datetime.now(UTC)
            )
            return "Data connection verified"
        else:
            from omnitrade.providers import YahooFinanceProvider

            await YahooFinanceProvider().fetch_node("fetch_market", "AAPL", datetime.now(UTC))
            return "Data connection verified"
        response.raise_for_status()
        body = response.json()
        if isinstance(body, dict) and (
            body.get("Error Message") or body.get("Information") or body.get("error")
        ):
            raise ValueError(
                str(body.get("Error Message") or body.get("Information") or body.get("error"))
            )
    await asyncio.sleep(0)
    return "Data connection verified"


async def discover_models(value: ConnectionInput) -> list[str]:
    spec = MODEL_PROVIDERS.get(value.provider)
    if not spec:
        raise ValueError("This is not a model provider")
    if value.provider == "bedrock":
        models = value.model_ids + ([value.test_model] if value.test_model else [])
        return list(dict.fromkeys(model for model in models if model))
    if spec.get("models") and value.provider not in {"ollama", "openrouter"}:
        return list(spec["models"])
    runtime = value.runtime_dict()
    base_url = runtime.get("base_url") or str(spec.get("base_url", ""))
    if not base_url:
        return [value.test_model] if value.test_model else []
    headers = (
        {"Authorization": f"Bearer {runtime.get('api_key', '')}"} if runtime.get("api_key") else {}
    )
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(f"{base_url.rstrip('/')}/models", headers=headers)
        response.raise_for_status()
    body = response.json()
    rows = (body.get("data") or body.get("models") or []) if isinstance(body, dict) else []
    models = [
        str(row.get("id") or row.get("name", "")).removeprefix("models/")
        for row in rows
        if isinstance(row, dict)
    ]
    return [model for model in models if model]


connections = SessionConnectionStore()
