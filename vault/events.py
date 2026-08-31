from __future__ import annotations

"""Event bus for inter-service communication via Redis Streams."""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

import redis.asyncio as redis

from vault.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Event Types
# ---------------------------------------------------------------------------

class EventType:
    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_KYC_COMPLETED = "user.kyc.completed"

    # Subscription events
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_UPDATED = "subscription.updated"
    SUBSCRIPTION_USAGE_RECORDED = "subscription.usage.recorded"

    # Market events
    LISTING_CREATED = "listing.created"
    LISTING_UPDATED = "listing.updated"
    LISTING_EXPIRED = "listing.expired"

    # Match events
    MATCH_PROPOSED = "match.proposed"
    MATCH_ACCEPTED = "match.accepted"
    MATCH_REJECTED = "match.rejected"
    MATCH_COMPLETED = "match.completed"

    # Escrow events
    ESCROW_CREATED = "escrow.created"
    ESCROW_FUNDED = "escrow.funded"
    ESCROW_RELEASED = "escrow.released"
    ESCROW_REFUNDED = "escrow.refunded"
    ESCROW_DISPUTED = "escrow.disputed"

    # Compliance events
    RISK_ALERT = "compliance.risk_alert"
    TOS_VIOLATION = "compliance.tos_violation"
    CIRCUIT_BREAKER = "compliance.circuit_breaker"

    # Financial events
    PAYOUT_INITIATED = "payout.initiated"
    PAYOUT_COMPLETED = "payout.completed"


# ---------------------------------------------------------------------------
# Redis Stream Event Bus
# ---------------------------------------------------------------------------

class Event:
    """Immutable event envelope."""

    def __init__(self, event_type: str, data: dict[str, Any], source: str = ""):
        self.id: str = ""  # set by publish
        self.event_type = event_type
        self.data = data
        self.source = source
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, str]:
        return {
            "event_type": self.event_type,
            "data": json.dumps(self.data),
            "source": self.source,
            "timestamp": self.timestamp,
        }


class EventPublisher:
    """Publishes events to Redis Streams."""

    def __init__(self):
        self._redis: redis.Redis | None = None

    async def connect(self):
        self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def close(self):
        if self._redis:
            await self._redis.close()

    async def publish(self, event: Event) -> str:
        """Publish an event and return the stream ID."""
        if not self._redis:
            try:
                await self.connect()
            except Exception:
                logger.warning("Redis unavailable — event %s logged but not published", event.event_type)
                event.id = "local"
                return "local"
        try:
            stream_key = f"vault:events:{event.event_type}"
            general_stream = "vault:events:all"
            msg_id = await self._redis.xadd(stream_key, event.to_dict(), maxlen=10000)
            await self._redis.xadd(general_stream, event.to_dict(), maxlen=50000)
            event.id = msg_id
            logger.info("Published event %s [%s] id=%s", event.event_type, event.source, msg_id)
            return msg_id
        except Exception:
            logger.warning("Redis unavailable — event %s logged but not published", event.event_type)
            event.id = "local"
            return "local"


class EventConsumer:
    """Consumes events from Redis Streams with consumer groups."""

    def __init__(self, group_name: str, consumer_name: str):
        self.group_name = group_name
        self.consumer_name = consumer_name
        self._redis: redis.Redis | None = None
        self._handlers: dict[str, list[Callable[..., Awaitable[None]]]] = {}

    async def connect(self):
        self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def close(self):
        if self._redis:
            await self._redis.close()

    def on(self, event_type: str, handler: Callable[..., Awaitable[None]]):
        """Register a handler for a specific event type."""
        self._handlers.setdefault(event_type, []).append(handler)

    async def _ensure_group(self, stream_key: str):
        """Create the consumer group if it doesn't exist."""
        try:
            await self._redis.xgroup_create(stream_key, self.group_name, id="0", mkstream=True)
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    async def listen(self, streams: list[str] | None = None, block_ms: int = 5000, count: int = 10):
        """Listen for events and dispatch to handlers."""
        if not self._redis:
            await self.connect()

        target_streams = streams or ["vault:events:all"]
        for stream in target_streams:
            await self._ensure_group(stream)

        while True:
            try:
                entries = await self._redis.xreadgroup(
                    self.group_name,
                    self.consumer_name,
                    {s: ">" for s in target_streams},
                    count=count,
                    block=block_ms,
                )
                for stream_name, messages in entries:
                    for msg_id, fields in messages:
                        event = Event(
                            event_type=fields.get("event_type", ""),
                            data=json.loads(fields.get("data", "{}")),
                            source=fields.get("source", ""),
                        )
                        event.id = msg_id
                        await self._dispatch(event)
                        await self._redis.xack(stream_name, self.group_name, msg_id)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Event consumer error: %s", e)
                await asyncio.sleep(1)

    async def _dispatch(self, event: Event):
        """Dispatch an event to registered handlers."""
        handlers = self._handlers.get(event.event_type, [])
        if not handlers:
            return
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.exception("Handler error for %s: %s", event.event_type, e)


# Module-level singleton publisher
import asyncio  # noqa: E402

publisher = EventPublisher()
