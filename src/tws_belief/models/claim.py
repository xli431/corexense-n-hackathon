from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any

from .proposition import PropositionKey

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | tuple["JsonValue", ...] | Mapping[str, "JsonValue"]


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _parse_datetime(value: object, name: str) -> datetime:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be an ISO 8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{name} must be a valid ISO 8601 date-time") from error
    _aware(parsed, name)
    return parsed


def _parse_optional_datetime(value: object, name: str) -> datetime | None:
    return None if value is None else _parse_datetime(value, name)


def _freeze_json(value: Any, path: str = "value") -> JsonValue:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must not contain NaN or infinity")
        return value
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item, f"{path}[]") for item in value)
    if isinstance(value, Mapping):
        frozen: dict[str, JsonValue] = {}
        for key in sorted(value):
            if not isinstance(key, str):
                raise TypeError(f"{path} mapping keys must be strings")
            frozen[key] = _freeze_json(value[key], f"{path}.{key}")
        return MappingProxyType(frozen)
    raise TypeError(f"{path} must be JSON-compatible, got {type(value).__name__}")


def thaw_json(value: JsonValue) -> Any:
    """Convert an immutable claim value into plain deterministic Python data."""

    if isinstance(value, Mapping):
        return {key: thaw_json(value[key]) for key in sorted(value)}
    if isinstance(value, tuple):
        return [thaw_json(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class Claim:
    """Immutable evidence-backed assertion with event and knowledge time."""

    claim_id: str
    entity_id: str
    predicate: str
    value: Any
    confidence: float
    source_id: str
    observation_id: str
    event_time: datetime
    knowledge_time: datetime
    valid_from: datetime | None
    valid_until: datetime | None
    revision: int
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("claim_id", "entity_id", "predicate", "source_id", "observation_id"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must be non-empty")
        if isinstance(self.confidence, bool) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1 inclusive")
        if (
            isinstance(self.revision, bool)
            or not isinstance(self.revision, int)
            or self.revision < 0
        ):
            raise ValueError("revision must be a non-negative integer")
        _aware(self.event_time, "event_time")
        _aware(self.knowledge_time, "knowledge_time")
        if self.event_time > self.knowledge_time:
            raise ValueError("event_time must not be later than knowledge_time")
        if self.valid_from is not None:
            _aware(self.valid_from, "valid_from")
        if self.valid_until is not None:
            _aware(self.valid_until, "valid_until")
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_from >= self.valid_until
        ):
            raise ValueError("valid_from must be earlier than valid_until")
        object.__setattr__(self, "value", _freeze_json(self.value))
        object.__setattr__(self, "metadata", _freeze_json(dict(self.metadata), "metadata"))

    @property
    def proposition(self) -> PropositionKey:
        return PropositionKey(self.entity_id, self.predicate)

    @property
    def effective_valid_from(self) -> datetime:
        return self.valid_from if self.valid_from is not None else self.event_time

    def known_by(self, knowledge_time: datetime) -> bool:
        _aware(knowledge_time, "knowledge_time")
        return self.knowledge_time <= knowledge_time

    def valid_at(self, event_time: datetime) -> bool:
        _aware(event_time, "event_time")
        return self.effective_valid_from <= event_time and (
            self.valid_until is None or event_time < self.valid_until
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Claim:
        if not isinstance(data, Mapping):
            raise TypeError("claim must be an object")
        expected = {
            "claim_id",
            "entity_id",
            "predicate",
            "value",
            "confidence",
            "source_id",
            "observation_id",
            "event_time",
            "knowledge_time",
            "valid_from",
            "valid_until",
            "revision",
            "metadata",
        }
        extra = set(data) - expected
        missing = expected - set(data)
        if extra:
            raise ValueError(f"unknown claim fields: {sorted(extra)}")
        if missing:
            raise ValueError(f"missing claim fields: {sorted(missing)}")
        metadata = data["metadata"]
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be an object")
        return cls(
            claim_id=data["claim_id"],
            entity_id=data["entity_id"],
            predicate=data["predicate"],
            value=data["value"],
            confidence=data["confidence"],
            source_id=data["source_id"],
            observation_id=data["observation_id"],
            event_time=_parse_datetime(data["event_time"], "event_time"),
            knowledge_time=_parse_datetime(data["knowledge_time"], "knowledge_time"),
            valid_from=_parse_optional_datetime(data["valid_from"], "valid_from"),
            valid_until=_parse_optional_datetime(data["valid_until"], "valid_until"),
            revision=data["revision"],
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "entity_id": self.entity_id,
            "predicate": self.predicate,
            "value": thaw_json(self.value),
            "confidence": self.confidence,
            "source_id": self.source_id,
            "observation_id": self.observation_id,
            "event_time": self.event_time.isoformat(),
            "knowledge_time": self.knowledge_time.isoformat(),
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "revision": self.revision,
            "metadata": thaw_json(self.metadata),
        }
