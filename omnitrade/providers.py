from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol
from xml.etree import ElementTree

import httpx


class Provider(Protocol):
    name: str

    async def fetch(self, ticker: str, as_of: datetime) -> dict[str, Any]: ...


class NodeProvider(Protocol):
    async def fetch_node(self, node_type: str, ticker: str, as_of: datetime) -> dict[str, Any]: ...


class ProviderError(RuntimeError):
    pass


@dataclass
class AlphaVantageProvider:
    """Live stock evidence adapter with look-ahead filtering and normalized metadata."""

    api_key: str
    base_url: str = "https://www.alphavantage.co/query"
    timeout_seconds: float = 20
    name: str = "alpha-vantage"

    async def fetch_node(self, node_type: str, ticker: str, as_of: datetime) -> dict[str, Any]:
        if not self.api_key:
            raise ProviderError("Alpha Vantage API key is not configured")
        function = {
            "fetch_market": "TIME_SERIES_DAILY",
            "fetch_fundamentals": "OVERVIEW",
            "fetch_news": "NEWS_SENTIMENT",
            "fetch_sentiment": "NEWS_SENTIMENT",
            "fetch_macro": "TREASURY_YIELD",
        }.get(node_type)
        if not function:
            raise ProviderError(f"Unsupported live evidence node: {node_type}")
        params: dict[str, str] = {"function": function, "apikey": self.api_key}
        if node_type != "fetch_macro":
            params["symbol" if function != "NEWS_SENTIMENT" else "tickers"] = ticker
        else:
            params.update({"interval": "daily", "maturity": "10year"})
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise ProviderError("Alpha Vantage response must be a JSON object")
        provider_message = body.get("Error Message") or body.get("Information") or body.get("Note")
        if provider_message:
            raise ProviderError(str(provider_message))
        payload = self._normalize(node_type, ticker, as_of, body)
        payload["content_hash"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()
        return payload

    def _normalize(
        self, node_type: str, ticker: str, as_of: datetime, body: dict[str, Any]
    ) -> dict[str, Any]:
        cutoff = as_of.astimezone(UTC)
        common: dict[str, Any] = {
            "kind": node_type,
            "ticker": ticker,
            "as_of": cutoff.isoformat(),
            "retrieved_at": datetime.now(UTC).isoformat(),
            "provider": self.name,
            "currency": "USD",
        }
        if node_type == "fetch_market":
            series = body.get("Time Series (Daily)")
            if not isinstance(series, dict):
                raise ProviderError("Daily market series is missing")
            bars = [
                {
                    "date": date,
                    "open": float(values["1. open"]),
                    "high": float(values["2. high"]),
                    "low": float(values["3. low"]),
                    "close": float(values["4. close"]),
                    "volume": int(values["5. volume"]),
                }
                for date, values in series.items()
                if datetime.fromisoformat(date).replace(tzinfo=UTC) <= cutoff
            ]
            bars.sort(key=lambda item: item["date"])
            if len(bars) < 20:
                raise ProviderError("At least 20 market bars are required")
            return {
                **common,
                "observed_at": f"{bars[-1]['date']}T00:00:00+00:00",
                "bars": bars[-100:],
            }
        if node_type == "fetch_fundamentals":
            if not body.get("Symbol"):
                raise ProviderError("Company overview is missing")
            latest_quarter = str(body.get("LatestQuarter") or cutoff.date().isoformat())
            quarter_time = datetime.fromisoformat(latest_quarter).replace(tzinfo=UTC)
            if quarter_time > cutoff:
                raise ProviderError("Company overview is newer than the requested analysis time")
            keys = (
                "Name",
                "Sector",
                "Industry",
                "LatestQuarter",
                "MarketCapitalization",
                "PERatio",
                "PEGRatio",
                "PriceToBookRatio",
                "EPS",
                "ProfitMargin",
                "OperatingMarginTTM",
                "ReturnOnEquityTTM",
                "RevenueGrowthTTM",
                "QuarterlyEarningsGrowthYOY",
                "DividendYield",
                "Beta",
                "52WeekHigh",
                "52WeekLow",
                "AnalystTargetPrice",
            )
            return {
                **common,
                "observed_at": quarter_time.isoformat(),
                "company": {key: body.get(key) for key in keys},
            }
        if node_type in {"fetch_news", "fetch_sentiment"}:
            feed = body.get("feed", [])
            if not isinstance(feed, list):
                raise ProviderError("News feed is missing")
            articles: list[dict[str, Any]] = []
            for item in feed:
                published = self._news_time(str(item.get("time_published", "")))
                if not published or published > cutoff:
                    continue
                ticker_scores = item.get("ticker_sentiment", [])
                score = next(
                    (
                        self._number(entry.get("ticker_sentiment_score"))
                        for entry in ticker_scores
                        if entry.get("ticker") == ticker
                    ),
                    self._number(item.get("overall_sentiment_score")),
                )
                articles.append(
                    {
                        "title": item.get("title", "Untitled"),
                        "summary": item.get("summary", ""),
                        "url": item.get("url", ""),
                        "source": item.get("source", ""),
                        "published_at": published.isoformat(),
                        "sentiment_score": score,
                    }
                )
            articles = sorted(articles, key=lambda item: item["published_at"], reverse=True)[:50]
            if not articles:
                raise ProviderError("No news available before the analysis time")
            return {**common, "observed_at": articles[0]["published_at"], "articles": articles}
        data = body.get("data", [])
        observations = [
            {"date": item.get("date"), "value": self._number(item.get("value"))}
            for item in data
            if item.get("date")
            and datetime.fromisoformat(str(item["date"])).replace(tzinfo=UTC) <= cutoff
            and self._number(item.get("value")) is not None
        ]
        if not observations:
            raise ProviderError("Treasury-yield observations are missing")
        return {
            **common,
            "observed_at": f"{observations[0]['date']}T00:00:00+00:00",
            "series": observations[:100],
        }

    @staticmethod
    def _news_time(value: str) -> datetime | None:
        try:
            return datetime.strptime(value[:15], "%Y%m%dT%H%M%S").replace(tzinfo=UTC)
        except ValueError:
            return None

    @staticmethod
    def _number(value: Any) -> float | None:
        try:
            if value in {None, "None", "-"}:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None


@dataclass
class YahooFinanceProvider:
    """Keyless Yahoo Finance adapter. It returns only provider data, never fixtures."""

    timeout_seconds: float = 20
    name: str = "yfinance"

    async def fetch_node(self, node_type: str, ticker: str, as_of: datetime) -> dict[str, Any]:
        cutoff = as_of.astimezone(UTC)
        payload: dict[str, Any]
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds, follow_redirects=True
        ) as _client:
            if node_type == "fetch_market":
                bars, currency = await asyncio.to_thread(self._market_history, ticker, cutoff)
                if len(bars) < 20:
                    raise ProviderError("Yahoo Finance returned fewer than 20 market bars")
                payload = {
                    "kind": node_type,
                    "ticker": ticker,
                    "as_of": cutoff.isoformat(),
                    "retrieved_at": datetime.now(UTC).isoformat(),
                    "observed_at": f"{bars[-1]['date']}T00:00:00+00:00",
                    "provider": self.name,
                    "currency": currency,
                    "bars": bars[-100:],
                }
            elif node_type == "fetch_fundamentals":
                if cutoff.date() < datetime.now(UTC).date() - timedelta(days=2):
                    raise ProviderError(
                        "Yahoo company profile is current-only and cannot support a historical point-in-time run"
                    )
                row = await asyncio.to_thread(self._company_info, ticker)
                company = {
                    "Name": row.get("longName") or row.get("shortName"),
                    "Sector": row.get("sector"),
                    "Industry": row.get("industry"),
                    "MarketCapitalization": row.get("marketCap"),
                    "PERatio": row.get("trailingPE"),
                    "EPS": row.get("epsTrailingTwelveMonths"),
                    "DividendYield": row.get("trailingAnnualDividendYield"),
                    "52WeekHigh": row.get("fiftyTwoWeekHigh"),
                    "52WeekLow": row.get("fiftyTwoWeekLow"),
                    "AnalystTargetPrice": row.get("targetMeanPrice"),
                }
                payload = {
                    "kind": node_type,
                    "ticker": ticker,
                    "as_of": cutoff.isoformat(),
                    "retrieved_at": datetime.now(UTC).isoformat(),
                    "observed_at": cutoff.isoformat(),
                    "provider": self.name,
                    "currency": row.get("currency", "USD"),
                    "company": company,
                }
            elif node_type in {"fetch_news", "fetch_sentiment"}:
                news = await asyncio.to_thread(self._ticker_news, ticker)
                articles = []
                for raw in news:
                    item = raw.get("content", raw)
                    published_raw = item.get("pubDate") or item.get("providerPublishTime")
                    try:
                        published = (
                            datetime.fromisoformat(str(published_raw).replace("Z", "+00:00"))
                            if isinstance(published_raw, str)
                            else datetime.fromtimestamp(float(published_raw), UTC)
                        )
                    except (TypeError, ValueError):
                        continue
                    if published > cutoff:
                        continue
                    provider = item.get("provider") or {}
                    link = (
                        item.get("canonicalUrl")
                        or item.get("clickThroughUrl")
                        or item.get("link")
                        or {}
                    )
                    articles.append(
                        {
                            "title": item.get("title", "Untitled"),
                            "summary": item.get("summary") or item.get("description", ""),
                            "url": link.get("url", "") if isinstance(link, dict) else link,
                            "source": provider.get("displayName", "Yahoo Finance")
                            if isinstance(provider, dict)
                            else str(provider),
                            "published_at": published.isoformat(),
                            "sentiment_score": None,
                        }
                    )
                if not articles:
                    raise ProviderError("Yahoo Finance returned no news before the analysis time")
                payload = {
                    "kind": node_type,
                    "ticker": ticker,
                    "as_of": cutoff.isoformat(),
                    "retrieved_at": datetime.now(UTC).isoformat(),
                    "observed_at": articles[0]["published_at"],
                    "provider": self.name,
                    "currency": "USD",
                    "articles": articles,
                }
            else:
                raise ProviderError(f"Yahoo Finance does not support {node_type}")
        payload["content_hash"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()
        return payload

    @staticmethod
    def _market_history(ticker: str, cutoff: datetime) -> tuple[list[dict[str, Any]], str]:
        import yfinance as yf  # type: ignore[import-untyped]

        instrument = yf.Ticker(ticker)
        frame = instrument.history(
            start=(cutoff - timedelta(days=180)).date(),
            end=(cutoff + timedelta(days=1)).date(),
            interval="1d",
            auto_adjust=False,
        )
        if frame.empty:
            raise ProviderError("Yahoo Finance returned no market history")
        bars = [
            {
                "date": index.date().isoformat(),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]),
            }
            for index, row in frame.iterrows()
            if row["Close"] == row["Close"]
        ]
        return bars, str(instrument.fast_info.get("currency") or "USD")

    @staticmethod
    def _company_info(ticker: str) -> dict[str, Any]:
        import yfinance as yf

        info = yf.Ticker(ticker).get_info()
        if not info:
            raise ProviderError("Yahoo Finance returned no company data")
        return dict(info)

    @staticmethod
    def _ticker_news(ticker: str) -> list[dict[str, Any]]:
        import yfinance as yf

        return list(yf.Ticker(ticker).get_news(count=30))


@dataclass
class FredProvider:
    api_key: str
    base_url: str = "https://api.stlouisfed.org/fred"
    name: str = "fred"

    async def fetch_node(self, node_type: str, ticker: str, as_of: datetime) -> dict[str, Any]:
        if node_type != "fetch_macro":
            raise ProviderError("FRED supplies macro evidence only")
        if not self.api_key:
            raise ProviderError("FRED API key is not configured")
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{self.base_url.rstrip('/')}/series/observations",
                params={
                    "series_id": "DGS10",
                    "api_key": self.api_key,
                    "file_type": "json",
                    "observation_end": as_of.date().isoformat(),
                    "sort_order": "desc",
                    "limit": 100,
                },
            )
            response.raise_for_status()
        observations = [
            {"date": row["date"], "value": float(row["value"])}
            for row in response.json().get("observations", [])
            if row.get("value") not in {None, "."}
        ]
        if not observations:
            raise ProviderError("FRED returned no Treasury observations")
        payload = {
            "kind": node_type,
            "ticker": ticker,
            "as_of": as_of.isoformat(),
            "retrieved_at": datetime.now(UTC).isoformat(),
            "observed_at": f"{observations[0]['date']}T00:00:00+00:00",
            "provider": self.name,
            "currency": "USD",
            "series": observations,
        }
        payload["content_hash"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()
        return payload


@dataclass
class PolymarketProvider:
    base_url: str = "https://gamma-api.polymarket.com"
    name: str = "polymarket"

    async def fetch_node(self, node_type: str, ticker: str, as_of: datetime) -> dict[str, Any]:
        if node_type != "fetch_macro":
            raise ProviderError("Polymarket supplies macro event evidence only")
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(
                f"{self.base_url.rstrip('/')}/markets",
                params={"active": "true", "closed": "false", "limit": 30},
            )
            response.raise_for_status()
        markets = response.json()
        if not isinstance(markets, list) or not markets:
            raise ProviderError("Polymarket returned no active markets")
        articles = []
        for market in markets:
            articles.append(
                {
                    "title": market.get("question", "Prediction market"),
                    "summary": f"Outcome prices: {market.get('outcomePrices', 'unavailable')}",
                    "url": market.get("url", ""),
                    "source": "Polymarket",
                    "published_at": as_of.isoformat(),
                    "sentiment_score": None,
                }
            )
        payload = {
            "kind": node_type,
            "ticker": ticker,
            "as_of": as_of.isoformat(),
            "retrieved_at": datetime.now(UTC).isoformat(),
            "observed_at": as_of.isoformat(),
            "provider": self.name,
            "currency": "USD",
            "articles": articles,
        }
        payload["content_hash"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()
        return payload


@dataclass
class StockTwitsProvider:
    base_url: str = "https://api.stocktwits.com/api/2"
    name: str = "stocktwits"

    async def fetch_node(self, node_type: str, ticker: str, as_of: datetime) -> dict[str, Any]:
        if node_type != "fetch_sentiment":
            raise ProviderError("StockTwits supplies sentiment evidence only")
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(f"{self.base_url.rstrip('/')}/streams/symbol/{ticker}.json")
            response.raise_for_status()
        messages = response.json().get("messages", [])
        articles = []
        for item in messages:
            try:
                published = datetime.fromisoformat(str(item["created_at"]).replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue
            if published > as_of:
                continue
            sentiment = (item.get("entities", {}).get("sentiment") or {}).get("basic")
            score = 0.7 if sentiment == "Bullish" else -0.7 if sentiment == "Bearish" else None
            articles.append(
                {
                    "title": f"StockTwits post by {item.get('user', {}).get('username', 'user')}",
                    "summary": item.get("body", ""),
                    "url": f"https://stocktwits.com/message/{item.get('id', '')}",
                    "source": "StockTwits",
                    "published_at": published.isoformat(),
                    "sentiment_score": score,
                }
            )
        if not articles:
            raise ProviderError("StockTwits returned no messages before the analysis time")
        return self._payload(ticker, as_of, articles)

    def _payload(
        self, ticker: str, as_of: datetime, articles: list[dict[str, Any]]
    ) -> dict[str, Any]:
        payload = {
            "kind": "fetch_sentiment",
            "ticker": ticker,
            "as_of": as_of.isoformat(),
            "retrieved_at": datetime.now(UTC).isoformat(),
            "observed_at": articles[0]["published_at"],
            "provider": self.name,
            "currency": "USD",
            "articles": articles,
        }
        payload["content_hash"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()
        return payload


@dataclass
class RedditProvider:
    name: str = "reddit"

    async def fetch_node(self, node_type: str, ticker: str, as_of: datetime) -> dict[str, Any]:
        if node_type != "fetch_sentiment":
            raise ProviderError("Reddit supplies sentiment evidence only")
        articles: list[dict[str, Any]] = []
        headers = {"User-Agent": "OmniTradeAI/0.1 academic decision support"}
        async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers=headers) as client:
            for subreddit in ("stocks", "investing", "wallstreetbets"):
                response = await client.get(
                    f"https://www.reddit.com/r/{subreddit}/search.rss",
                    params={"q": ticker, "restrict_sr": "on", "sort": "new", "t": "week"},
                )
                response.raise_for_status()
                root = ElementTree.fromstring(response.text)
                namespace = {"a": "http://www.w3.org/2005/Atom"}
                for entry in root.findall("a:entry", namespace):
                    updated = entry.findtext("a:updated", default="", namespaces=namespace)
                    try:
                        published = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    except ValueError:
                        continue
                    if published > as_of:
                        continue
                    link = entry.find("a:link", namespace)
                    articles.append(
                        {
                            "title": entry.findtext(
                                "a:title", default="Reddit post", namespaces=namespace
                            ),
                            "summary": entry.findtext(
                                "a:content", default="", namespaces=namespace
                            ),
                            "url": link.get("href", "") if link is not None else "",
                            "source": f"Reddit r/{subreddit}",
                            "published_at": published.isoformat(),
                            "sentiment_score": None,
                        }
                    )
        articles.sort(key=lambda item: item["published_at"], reverse=True)
        if not articles:
            raise ProviderError("Reddit returned no matching posts before the analysis time")
        payload = {
            "kind": node_type,
            "ticker": ticker,
            "as_of": as_of.isoformat(),
            "retrieved_at": datetime.now(UTC).isoformat(),
            "observed_at": articles[0]["published_at"],
            "provider": self.name,
            "currency": "USD",
            "articles": articles[:60],
        }
        payload["content_hash"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()
        return payload


def live_provider(name: str, settings: dict[str, str]) -> NodeProvider:
    if name == "alpha_vantage":
        return AlphaVantageProvider(
            settings.get("api_key", ""),
            settings.get("base_url", "https://www.alphavantage.co/query"),
        )
    if name == "yfinance":
        return YahooFinanceProvider()
    if name == "fred":
        return FredProvider(
            settings.get("api_key", ""), settings.get("base_url", "https://api.stlouisfed.org/fred")
        )
    if name == "polymarket":
        return PolymarketProvider(settings.get("base_url", "https://gamma-api.polymarket.com"))
    if name == "stocktwits":
        return StockTwitsProvider(settings.get("base_url", "https://api.stocktwits.com/api/2"))
    if name == "reddit":
        return RedditProvider()
    raise ProviderError(f"Unsupported evidence provider: {name}")


async def fetch_from_chain(
    node_type: str,
    ticker: str,
    as_of: datetime,
    provider_names: list[str],
    connections: dict[str, dict[str, str]],
) -> dict[str, Any]:
    errors: list[str] = []
    for name in provider_names:
        try:
            output = await live_provider(
                name, connections.get(name, {"provider": name})
            ).fetch_node(node_type, ticker, as_of)
            output["provider_chain"] = provider_names
            output["providers_failed_before_success"] = errors
            return output
        except httpx.HTTPStatusError as exc:
            errors.append(f"{name}: HTTP {exc.response.status_code}")
        except httpx.RequestError:
            errors.append(f"{name}: connection error")
        except (ProviderError, ValueError) as exc:
            errors.append(f"{name}: {exc}")
    raise ProviderError("All selected real providers failed: " + "; ".join(errors))


async def convert_evidence_currency(
    payload: dict[str, Any], target: str, as_of: datetime
) -> dict[str, Any]:
    source = str(payload.get("currency") or "USD")
    if source == target or payload.get("kind") not in {"fetch_market", "fetch_fundamentals"}:
        return payload
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            response = await client.get(
                f"https://api.frankfurter.dev/v1/{as_of.date().isoformat()}",
                params={"base": source, "symbols": target},
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ProviderError(f"FX service returned HTTP {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        raise ProviderError("FX service is unavailable") from exc
    rate = float(response.json().get("rates", {}).get(target, 0))
    if rate <= 0:
        raise ProviderError(f"No real FX rate was returned for {source}/{target}")
    converted = dict(payload)
    if "bars" in converted:
        converted["bars"] = [
            {
                **bar,
                **{
                    key: round(float(bar[key]) * rate, 6)
                    for key in ("open", "high", "low", "close")
                    if bar.get(key) is not None
                },
            }
            for bar in converted["bars"]
        ]
    if "company" in converted:
        company = dict(converted["company"])
        for key in ("MarketCapitalization", "52WeekHigh", "52WeekLow", "AnalystTargetPrice"):
            try:
                if company.get(key) not in {None, "None", "-"}:
                    company[key] = float(company[key]) * rate
            except (TypeError, ValueError):
                pass
        converted["company"] = company
    converted.update(
        {
            "currency": target,
            "fx_source": "Frankfurter/ECB",
            "fx_rate": rate,
            "original_currency": source,
        }
    )
    converted["content_hash"] = hashlib.sha256(
        json.dumps(converted, sort_keys=True).encode()
    ).hexdigest()
    return converted


@dataclass
class RecordedProvider:
    name: str
    records: dict[str, dict[str, Any]]

    async def fetch(self, ticker: str, as_of: datetime) -> dict[str, Any]:
        if ticker not in self.records:
            raise ProviderError(f"No recorded data for {ticker}")
        return {
            **self.records[ticker],
            "ticker": ticker,
            "as_of": as_of.isoformat(),
            "provider": self.name,
        }


@dataclass
class HttpJsonProvider:
    name: str
    base_url: str
    api_key: str
    timeout_seconds: float = 10

    async def fetch(self, ticker: str, as_of: datetime) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(
                self.base_url,
                params={"symbol": ticker, "as_of": as_of.isoformat()},
                headers=headers,
            )
            response.raise_for_status()
            body = response.json()
            if not isinstance(body, dict):
                raise ProviderError("Provider response must be a JSON object")
            return {**body, "provider": self.name}
