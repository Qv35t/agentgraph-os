import hashlib
import json
from enum import StrEnum
from typing import Any

CHECKPOINT_FORMAT_VERSION = 1


class CheckpointReason(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActionLedgerStatus(StrEnum):
    INTENT_RECORDED = "intent_recorded"
    STARTED = "started"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    UNCERTAIN = "uncertain"


class RecoveryOutcome(StrEnum):
    STOPPED_NO_REPLAY = "stopped_no_replay"
    BLOCKED_UNCERTAIN_ACTION = "blocked_uncertain_action"
    BLOCKED_CORRUPT_CHECKPOINT = "blocked_corrupt_checkpoint"
    BLOCKED_NO_CHECKPOINT = "blocked_no_checkpoint"


def checkpoint_checksum(state: dict[str, object]) -> str:
    """Produce a stable integrity checksum for a JSON-safe checkpoint state."""
    encoded = json.dumps(state, ensure_ascii=True, separators=(",", ":"), sort_keys=True, default=_json_default)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _json_default(value: Any) -> str:
    return str(value)
