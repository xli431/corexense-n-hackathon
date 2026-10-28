from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import PurePosixPath
from typing import Any

from .claim import Claim, _freeze_json, thaw_json


class EvidenceStage(str, Enum):
    PRE_PICK = "pre_pick"
    TRANSFER = "transfer"
    POST_PLACE = "post_place"
    TRAJECTORY = "trajectory"
    OTHER = "other"


_ASSERTION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _non_empty(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _parse_time(value: object, name: str) -> datetime:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be an ISO 8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{name} must be a valid ISO 8601 date-time") from error
    _aware(parsed, name)
    return parsed


def _asset_ref(value: str | None) -> str | None:
    if value is None:
        return None
    _non_empty(value, "asset_ref")
    path = PurePosixPath(value)
    if (
        value == "."
        or "\0" in value
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in value
        or "://" in value
        or (path.parts and ":" in path.parts[0])
    ):
        raise ValueError("asset_ref must be a safe dataset-relative POSIX path")
    return value


@dataclass(frozen=True, slots=True)
class EvidenceAssertion:
    """One normalized assertion carried by an evidence record."""

    assertion_id: str
    entity_id: str
    predicate: str
    value: Any
    confidence: float

    def __post_init__(self) -> None:
        _non_empty(self.assertion_id, "assertion_id")
        if not _ASSERTION_ID.fullmatch(self.assertion_id):
            raise ValueError(
                "assertion_id must contain only letters, digits, '.', '_', or '-'"
            )
        _non_empty(self.entity_id, "entity_id")
        _non_empty(self.predicate, "predicate")
        if isinstance(self.confidence, bool) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1 inclusive")
        object.__setattr__(self, "value", _freeze_json(self.value))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EvidenceAssertion:
        if not isinstance(data, Mapping):
            raise TypeError("assertion must be an object")
        expected = {"assertion_id", "entity_id", "predicate", "value", "confidence"}
        extra = set(data) - expected
        missing = expected - set(data)
        if extra:
            raise ValueError(f"unknown assertion fields: {sorted(extra)}")
        if missing:
            raise ValueError(f"missing assertion fields: {sorted(missing)}")
        return cls(
            assertion_id=data["assertion_id"],
            entity_id=data["entity_id"],
            predicate=data["predicate"],
            value=data["value"],
            confidence=data["confidence"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "assertion_id": self.assertion_id,
            "entity_id": self.entity_id,
            "predicate": self.predicate,
            "value": thaw_json(self.value),
            "confidence": self.confidence,
        }


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    """Immutable normalized evidence at the dataset/core trust boundary."""

    evidence_id: str
    dataset: str
    episode_id: str
    stage: EvidenceStage
    source_id: str
    event_time: datetime
    knowledge_time: datetime
    claims: tuple[EvidenceAssertion, ...]
    asset_ref: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("evidence_id", "dataset", "episode_id", "source_id"):
            _non_empty(getattr(self, name), name)
        if not isinstance(self.stage, EvidenceStage):
            raise TypeError("stage must be an EvidenceStage")
        _aware(self.event_time, "event_time")
        _aware(self.knowledge_time, "knowledge_time")
        if self.event_time > self.knowledge_time:
            raise ValueError("event_time must not be later than knowledge_time")
        claims = tuple(self.claims)
        if not claims:
            raise ValueError("claims must contain at least one assertion")
        if not all(isinstance(item, EvidenceAssertion) for item in claims):
            raise TypeError("claims must contain only EvidenceAssertion values")
        assertion_ids = [item.assertion_id for item in claims]
        if len(assertion_ids) != len(set(assertion_ids)):
            raise ValueError("assertion_id values must be unique within an evidence record")
        object.__setattr__(self, "claims", claims)
        object.__setattr__(self, "asset_ref", _asset_ref(self.asset_ref))
        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        frozen_metadata = _freeze_json(dict(self.metadata), "metadata")
        if not isinstance(frozen_metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        object.__setattr__(self, "metadata", frozen_metadata)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EvidenceRecord:
        if not isinstance(data, Mapping):
            raise TypeError("evidence record must be an object")
        required = {
            "evidence_id",
            "dataset",
            "episode_id",
            "stage",
            "source_id",
            "event_time",
            "knowledge_time",
            "claims",
        }
        allowed = required | {"asset_ref", "metadata"}
        extra = set(data) - allowed
        missing = required - set(data)
        if extra:
            raise ValueError(f"unknown evidence fields: {sorted(extra)}")
        if missing:
            raise ValueError(f"missing evidence fields: {sorted(missing)}")
        raw_claims = data["claims"]
        if not isinstance(raw_claims, list):
            raise TypeError("claims must be an array")
        try:
            stage = EvidenceStage(data["stage"])
        except (TypeError, ValueError) as error:
            allowed_stages = ", ".join(stage.value for stage in EvidenceStage)
            raise ValueError(f"stage must be one of: {allowed_stages}") from error
        metadata = data.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be an object")
        return cls(
            evidence_id=data["evidence_id"],
            dataset=data["dataset"],
            episode_id=data["episode_id"],
            stage=stage,
            source_id=data["source_id"],
            event_time=_parse_time(data["event_time"], "event_time"),
            knowledge_time=_parse_time(data["knowledge_time"], "knowledge_time"),
            claims=tuple(
                EvidenceAssertion.from_dict(item)
                for item in raw_claims
            ),
            asset_ref=data.get("asset_ref"),
            metadata=metadata,
        )

    def to_claims(self) -> tuple[Claim, ...]:
        """Convert normalized assertions to stable, evidence-linked claims."""

        ordered_assertions = sorted(
            self.claims,
            key=lambda assertion: assertion.assertion_id,
        )
        provenance = {
            "dataset": self.dataset,
            "episode_id": self.episode_id,
            "stage": self.stage.value,
            "asset_ref": self.asset_ref,
            "evidence_metadata": thaw_json(self.metadata),
        }
        return tuple(
            Claim(
                claim_id=f"{self.evidence_id}::{assertion.assertion_id}",
                entity_id=assertion.entity_id,
                predicate=assertion.predicate,
                value=assertion.value,
                confidence=assertion.confidence,
                source_id=self.source_id,
                observation_id=self.evidence_id,
                event_time=self.event_time,
                knowledge_time=self.knowledge_time,
                valid_from=self.event_time,
                valid_until=None,
                revision=0,
                metadata=provenance,
            )
            for assertion in ordered_assertions
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "dataset": self.dataset,
            "episode_id": self.episode_id,
            "stage": self.stage.value,
            "source_id": self.source_id,
            "event_time": self.event_time.isoformat(),
            "knowledge_time": self.knowledge_time.isoformat(),
            "asset_ref": self.asset_ref,
            "claims": [
                assertion.to_dict()
                for assertion in sorted(
                    self.claims,
                    key=lambda assertion: assertion.assertion_id,
                )
            ],
            "metadata": thaw_json(self.metadata),
        }


def evidence_records_sha256(records: Iterable[EvidenceRecord]) -> str:
    """Hash a canonical, order-independent normalized evidence bundle."""

    ordered = sorted(records, key=lambda record: record.evidence_id)
    identifiers = [record.evidence_id for record in ordered]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("evidence_id values must be unique")
    encoded = json.dumps(
        [record.to_dict() for record in ordered],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
