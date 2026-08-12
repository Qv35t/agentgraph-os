import asyncio
import json
from collections import deque
from collections.abc import AsyncGenerator
from datetime import datetime

from agentgraph.domain.remote import RuntimeEvent

SECRET_MARKERS = ("api_key", "token", "password", "authorization", "secret", "credential")


class RuntimeEventBus:
    """Transport-neutral fan-out; losing a subscriber never stops a run."""

    def __init__(self, history_limit: int = 500) -> None:
        self._history: deque[RuntimeEvent] = deque(maxlen=history_limit)
        self._subscribers: set[asyncio.Queue[RuntimeEvent]] = set()

    async def publish(self, event: RuntimeEvent) -> None:
        sanitized = RuntimeEvent(
            id=event.id,
            type=event.type,
            timestamp=event.timestamp,
            project_id=event.project_id,
            run_id=event.run_id,
            task_id=event.task_id,
            agent_id=event.agent_id,
            provider_id=event.provider_id,
            severity=event.severity,
            payload=_sanitize_payload(event.payload),
        )
        self._history.append(sanitized)
        for queue in tuple(self._subscribers):
            if queue.full():
                continue
            queue.put_nowait(sanitized)

    def history(self, run_id: str | None = None) -> list[RuntimeEvent]:
        return [event for event in self._history if run_id is None or event.run_id == run_id]

    async def subscribe(self, run_id: str | None = None) -> AsyncGenerator[RuntimeEvent, None]:
        queue: asyncio.Queue[RuntimeEvent] = asyncio.Queue(maxsize=100)
        self._subscribers.add(queue)
        try:
            while True:
                event = await queue.get()
                if run_id is None or event.run_id == run_id:
                    yield event
        finally:
            self._subscribers.discard(queue)


def event_json(event: RuntimeEvent) -> dict[str, object]:
    payload: dict[str, object] = {
        "event_id": event.id,
        "type": event.type,
        "timestamp": event.timestamp.isoformat(),
        "project_id": event.project_id,
        "run_id": event.run_id,
        "task_id": event.task_id,
        "agent_id": event.agent_id,
        "provider_id": event.provider_id,
        "severity": event.severity,
        "payload": event.payload,
    }
    json.dumps(payload)
    return payload


def _sanitize_payload(value: dict[str, object]) -> dict[str, object]:
    return {str(key): _sanitize_item(key, item) for key, item in value.items()}


def _sanitize_item(key: object, value: object) -> object:
    if any(marker in str(key).lower() for marker in SECRET_MARKERS):
        return "[redacted]"
    return _sanitize(value)


def _sanitize(value: object) -> object:
    if isinstance(value, dict):
        return _sanitize_payload(value)
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
