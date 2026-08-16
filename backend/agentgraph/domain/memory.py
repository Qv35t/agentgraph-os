from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class MemoryKind(StrEnum):
    FACT = "fact"
    PREFERENCE = "preference"
    NOTE = "note"
    SUMMARY = "summary"


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    id: UUID
    project_id: str
    agent_id: UUID
    kind: MemoryKind
    content: str
    tags: tuple[str, ...]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class MemoryMatch:
    record: MemoryRecord
    rank: int
    score: float | None = None
