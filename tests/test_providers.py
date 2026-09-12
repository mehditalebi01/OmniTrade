import asyncio
from datetime import UTC, datetime

import httpx
import pytest

from omnitrade.providers import (
    AlphaVantageProvider,
    ProviderError,
    convert_evidence_currency,
    fetch_from_chain,
)


def test_real_provider_chain_never_inserts_recorded_data(monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenNodeProvider:
        async def fetch_node(self, node_type: str, ticker: str, as_of: datetime):
            raise ProviderError("real source unavailable")

    monkeypatch.setattr(
        "omnitrade.providers.live_provider", lambda name, settings: BrokenNodeProvider()
    )
    with pytest.raises(ProviderError, match="All selected real providers failed"):
        asyncio.run(
            fetch_from_chain(
                "fetch_market", "AAPL", datetime.now(UTC), ["yfinance", "alpha_vantage"], {}
            )
        )


def test_real_provider_chain_uses_the_next_selected_source(monkeypatch: pytest.MonkeyPatch) -> None:
    class ChainProvider:
        def __init__(self, name: str):
            self.name = name

        async def fetch_node(self, node_type: str, ticker: str, as_of: datetime):
            if self.name == "first":
                raise ProviderError("source unavailable")
            return {"kind": node_type, "ticker": ticker, "provider": self.name}

    monkeypatch.setattr(
        "omnitrade.providers.live_provider", lambda name, settings: ChainProvider(name)
    )

    result = asyncio.run(
        fetch_from_chain("fetch_market", "AMD", datetime.now(UTC), ["first", "second"], {})
    )

    assert result["provider"] == "second"
    assert result["provider_chain"] == ["first", "second"]
    assert result["providers_failed_before_success"] == ["first: source unavailable"]


def test_alpha_vantage_market_normalization_blocks_look_ahead() -> None:
    provider = AlphaVantageProvider("test")
    body = {
        "Time Series (Daily)": {
            f"2026-01-{day:02d}": {
                "1. open": str(100 + day),
                "2. high": str(102 + day),
                "3. low": str(99 + day),
                "4. close": str(101 + day),
                "5. volume": str(1_000_000 + day),
            }
            for day in range(1, 32)
        }
    }
    result = provider._normalize("fetch_market", "IBM", datetime(2026, 1, 25, 12, tzinfo=UTC), body)
    assert result["bars"][-1]["date"] == "2026-01-25"
    assert all(item["date"] <= "2026-01-25" for item in result["bars"])


def test_currency_conversion_uses_current_frankfurter_api(monkeypatch: pytest.MonkeyPatch) -> None:
    requested: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request)
        return httpx.Response(
            200, json={"date": "2026-08-27", "base": "USD", "rates": {"EUR": 0.85}}
        )

    transport = httpx.MockTransport(handler)
    async_client = httpx.AsyncClient

    def client(**kwargs):
        return async_client(transport=transport, **kwargs)

    monkeypatch.setattr("omnitrade.providers.httpx.AsyncClient", client)
    payload = {
        "kind": "fetch_market",
        "currency": "USD",
        "bars": [{"open": 100, "high": 110, "low": 90, "close": 105}],
    }

    converted = asyncio.run(
        convert_evidence_currency(payload, "EUR", datetime(2026, 8, 27, tzinfo=UTC))
    )

    assert requested[0].url.host == "api.frankfurter.dev"
    assert requested[0].url.path == "/v1/2026-08-27"
    assert converted["currency"] == "EUR"
    assert converted["bars"][0]["close"] == 89.25


def test_provider_http_errors_do_not_leak_request_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenNodeProvider:
        async def fetch_node(self, node_type: str, ticker: str, as_of: datetime):
            request = httpx.Request("GET", "https://provider.test/data?apikey=private")
            response = httpx.Response(429, request=request)
            raise httpx.HTTPStatusError("limited", request=request, response=response)

    monkeypatch.setattr(
        "omnitrade.providers.live_provider", lambda name, settings: BrokenNodeProvider()
    )
    with pytest.raises(ProviderError) as caught:
        asyncio.run(
            fetch_from_chain("fetch_market", "AMD", datetime.now(UTC), ["alpha_vantage"], {})
        )
    assert "HTTP 429" in str(caught.value)
    assert "private" not in str(caught.value)
