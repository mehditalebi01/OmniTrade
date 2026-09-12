from __future__ import annotations

from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID

from redis.asyncio import Redis

from omnitrade.contracts import RunEvent


class EventBus(Protocol):
    async def publish(self, event: RunEvent) -> None: ...
    async def stream(self, run_id: UUID, after: str | None = None) -> AsyncIterator[RunEvent]: ...


class InMemoryEventBus:
    def __init__(self) -> None:
        self.events: dict[UUID, list[RunEvent]] = defaultdict(list)

    async def publish(self, event: RunEvent) -> None:
        if all(existing.event_id != event.event_id for existing in self.events[event.run_id]):
            self.events[event.run_id].append(event)

    async def stream(self, run_id: UUID, after: str | None = None) -> AsyncIterator[RunEvent]:
        start = int(after or 0)
        for event in self.events[run_id][start:]:
            yield event


class RedisStreamEventBus:
    def __init__(self, url: str) -> None:
        self.redis = Redis.from_url(url, decode_responses=True)

    async def publish(self, event: RunEvent) -> None:
        await self.redis.xadd(
            f"omnitrade:run:{event.run_id}",
            {"event": event.model_dump_json()},
            maxlen=10_000,
            approximate=True,
        )

    async def stream(self, run_id: UUID, after: str | None = None) -> AsyncIterator[RunEvent]:
        cursor = after or "0-0"
        entries = await self.redis.xrange(f"omnitrade:run:{run_id}", min=f"({cursor}")
        for _entry_id, fields in entries:
            yield RunEvent.model_validate_json(fields["event"])

    async def request_cancel(self, run_id: UUID) -> None:
        await self.redis.set(f"omnitrade:cancel:{run_id}", "1", ex=3600)

    async def is_cancelled(self, run_id: UUID) -> bool:
        return bool(await self.redis.exists(f"omnitrade:cancel:{run_id}"))

    async def clear_cancel(self, run_id: UUID) -> None:
        await self.redis.delete(f"omnitrade:cancel:{run_id}")

    async def request_pause(self, run_id: UUID) -> None:
        await self.redis.set(f"omnitrade:pause:{run_id}", "1", ex=3600)

    async def is_paused(self, run_id: UUID) -> bool:
        return bool(await self.redis.exists(f"omnitrade:pause:{run_id}"))

    async def clear_pause(self, run_id: UUID) -> None:
        await self.redis.delete(f"omnitrade:pause:{run_id}")
