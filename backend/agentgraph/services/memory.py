from datetime import UTC, datetime
from uuid import UUID

from agentgraph.domain.memory import MemoryKind, MemoryMatch, MemoryRecord
from agentgraph.persistence.database import SessionFactory
from agentgraph.persistence.models import MemoryRecordRecord
from agentgraph.repositories.memory import MemoryRepository
from agentgraph.settings import Settings


class MemoryError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class MemoryService:
    """Local SQLite memory with explicit project-and-agent scope enforcement."""

    def __init__(self, session_factory: SessionFactory, settings: Settings) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._repository = MemoryRepository()

    async def create(
        self, *, project_id: str, agent_id: UUID, kind: MemoryKind, content: str, tags: list[str]
    ) -> MemoryRecord:
        self._require_enabled()
        normalized_content = content.strip()
        if not normalized_content:
            raise MemoryError("memory_invalid", "Memory content must not be empty")
        if len(normalized_content) > self._settings.memory_max_content_chars:
            raise MemoryError("memory_too_large", "Memory content exceeds the configured limit")
        normalized_tags = _normalize_tags(tags, self._settings)
        async with self._session_factory() as session:
            record = await self._repository.create(
                session,
                MemoryRecordRecord(
                    project_id=project_id,
                    agent_id=str(agent_id),
                    kind=kind.value,
                    content=normalized_content,
                    tags=normalized_tags,
                ),
            )
            await session.commit()
            await session.refresh(record)
            return _record(record)

    async def list_records(self, *, project_id: str, agent_id: UUID) -> list[MemoryRecord]:
        self._require_enabled()
        async with self._session_factory() as session:
            records = await self._repository.list_for_scope(session, project_id=project_id, agent_id=agent_id)
            return [_record(record) for record in records]

    async def search(self, *, project_id: str, agent_id: UUID, query: str) -> list[MemoryMatch]:
        self._require_enabled()
        normalized_query = query.strip()
        if len(normalized_query) > self._settings.memory_max_content_chars:
            raise MemoryError("memory_invalid", "Memory query exceeds the configured limit")
        async with self._session_factory() as session:
            # The first adapter intentionally offers bounded lexical retrieval, not semantic/vector search.
            records = await self._repository.list_for_scope(
                session,
                project_id=project_id,
                agent_id=agent_id,
                limit=self._settings.memory_max_results * 4,
            )
        terms = tuple(term for term in normalized_query.casefold().split() if term)
        scored = [(record, _score(record, terms)) for record in records]
        if terms:
            scored = [(record, score) for record, score in scored if score > 0]
        scored.sort(key=lambda item: (-item[1], -item[0].updated_at.timestamp(), item[0].id))
        matches: list[MemoryMatch] = []
        context_chars = 0
        for record, score in scored:
            if len(matches) >= self._settings.memory_max_results:
                break
            remaining = self._settings.memory_max_context_chars - context_chars
            if remaining <= 0:
                break
            if len(record.content) > remaining:
                continue
            matches.append(MemoryMatch(_record(record), rank=len(matches) + 1, score=float(score)))
            context_chars += len(record.content)
        return matches

    async def record_run_usage(self, *, run_id: UUID, matches: list[MemoryMatch]) -> None:
        if not matches:
            return
        async with self._session_factory() as session:
            records: list[tuple[MemoryRecordRecord, float | None]] = []
            for match in matches:
                record = await self._repository.get_for_scope(
                    session,
                    memory_id=match.record.id,
                    project_id=match.record.project_id,
                    agent_id=match.record.agent_id,
                )
                if record is not None:
                    records.append((record, match.score))
            await self._repository.add_run_links(session, run_id=run_id, matches=records)
            await session.commit()

    async def list_run_usage(self, run_id: UUID) -> list[dict[str, object]]:
        self._require_enabled()
        async with self._session_factory() as session:
            links = await self._repository.list_run_links(session, run_id)
            usage: list[dict[str, object]] = []
            for link in links:
                record = await session.get(MemoryRecordRecord, link.memory_id) if link.memory_id else None
                usage.append(
                    {
                        "memory_id": link.memory_id_snapshot,
                        "rank": link.rank,
                        "score": link.score,
                        "deleted": record is None or record.deleted_at is not None,
                    }
                )
            return usage

    async def delete(self, *, project_id: str, agent_id: UUID, memory_id: UUID) -> None:
        self._require_enabled()
        async with self._session_factory() as session:
            record = await self._repository.get_for_scope(
                session, memory_id=memory_id, project_id=project_id, agent_id=agent_id
            )
            if record is None:
                raise MemoryError("memory_not_found", "Memory record was not found")
            record.deleted_at = datetime.now(UTC)
            await session.commit()

    def _require_enabled(self) -> None:
        if not self._settings.memory_enabled:
            raise MemoryError("memory_disabled", "Memory is disabled by server configuration")


def _normalize_tags(tags: list[str], settings: Settings) -> list[str]:
    if len(tags) > settings.memory_max_tags:
        raise MemoryError("memory_invalid", "Too many memory tags")
    normalized: list[str] = []
    for tag in tags:
        value = tag.strip()
        if not value or len(value) > settings.memory_max_tag_chars:
            raise MemoryError("memory_invalid", "Memory tag is invalid")
        if value not in normalized:
            normalized.append(value)
    return normalized


def _score(record: MemoryRecordRecord, terms: tuple[str, ...]) -> int:
    haystack = f"{record.content} {' '.join(record.tags)}".casefold()
    return sum(term in haystack for term in terms)


def _record(record: MemoryRecordRecord) -> MemoryRecord:
    return MemoryRecord(
        id=UUID(record.id),
        project_id=record.project_id,
        agent_id=UUID(record.agent_id),
        kind=MemoryKind(record.kind),
        content=record.content,
        tags=tuple(record.tags),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
