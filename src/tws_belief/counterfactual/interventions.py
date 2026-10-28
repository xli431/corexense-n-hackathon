from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import timedelta
from typing import Any, Protocol

from tws_belief.models import Claim
from tws_belief.sources import SourceRegistry


@dataclass(frozen=True, slots=True)
class InterventionState:
    claims: tuple[Claim, ...]
    sources: SourceRegistry


class Intervention(Protocol):
    intervention_id: str
    cause_id: str

    def apply(self, state: InterventionState) -> InterventionState: ...

    def to_dict(self) -> dict[str, object]: ...


def _ordered(claims: Iterable[Claim]) -> tuple[Claim, ...]:
    return tuple(sorted(claims, key=lambda claim: claim.claim_id))


def _require_claim(state: InterventionState, claim_id: str) -> Claim:
    matches = [claim for claim in state.claims if claim.claim_id == claim_id]
    if not matches:
        raise KeyError(f"unknown claim_id: {claim_id}")
    return matches[0]


def _non_empty(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _validate_identity(intervention_id: str, cause_id: str) -> None:
    _non_empty(intervention_id, "intervention_id")
    _non_empty(cause_id, "cause_id")


def _strict_fields(
    data: Mapping[str, Any],
    *,
    intervention_type: str,
    required: set[str],
) -> None:
    expected = required | {"type"}
    extra = set(data) - expected
    missing = expected - set(data)
    if extra:
        raise ValueError(
            f"unknown {intervention_type} intervention fields: {sorted(extra)}"
        )
    if missing:
        raise ValueError(
            f"missing {intervention_type} intervention fields: {sorted(missing)}"
        )


@dataclass(frozen=True, slots=True)
class RemoveClaim:
    intervention_id: str
    claim_id: str
    cause_id: str

    def __post_init__(self) -> None:
        _validate_identity(self.intervention_id, self.cause_id)
        _non_empty(self.claim_id, "claim_id")

    def apply(self, state: InterventionState) -> InterventionState:
        _require_claim(state, self.claim_id)
        return InterventionState(
            claims=tuple(claim for claim in state.claims if claim.claim_id != self.claim_id),
            sources=state.sources,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "type": "remove_claim",
            "intervention_id": self.intervention_id,
            "claim_id": self.claim_id,
            "cause_id": self.cause_id,
        }


@dataclass(frozen=True, slots=True)
class AddClaim:
    intervention_id: str
    claim: Claim
    cause_id: str

    def __post_init__(self) -> None:
        _validate_identity(self.intervention_id, self.cause_id)
        if not isinstance(self.claim, Claim):
            raise TypeError("claim must be a Claim")

    def apply(self, state: InterventionState) -> InterventionState:
        if any(existing.claim_id == self.claim.claim_id for existing in state.claims):
            raise ValueError(f"duplicate claim_id: {self.claim.claim_id}")
        return InterventionState(
            claims=_ordered((*state.claims, self.claim)),
            sources=state.sources,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "type": "add_claim",
            "intervention_id": self.intervention_id,
            "claim": self.claim.to_dict(),
            "cause_id": self.cause_id,
        }


@dataclass(frozen=True, slots=True)
class SetClaimConfidence:
    intervention_id: str
    claim_id: str
    confidence: float
    cause_id: str

    def __post_init__(self) -> None:
        _validate_identity(self.intervention_id, self.cause_id)
        _non_empty(self.claim_id, "claim_id")
        confidence = _finite_number(self.confidence, "confidence")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1 inclusive")
        object.__setattr__(self, "confidence", confidence)

    def apply(self, state: InterventionState) -> InterventionState:
        target = _require_claim(state, self.claim_id)
        updated = replace(target, confidence=self.confidence)
        return InterventionState(
            claims=_ordered(updated if claim == target else claim for claim in state.claims),
            sources=state.sources,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "type": "set_claim_confidence",
            "intervention_id": self.intervention_id,
            "claim_id": self.claim_id,
            "confidence": self.confidence,
            "cause_id": self.cause_id,
        }


@dataclass(frozen=True, slots=True)
class ShiftKnowledgeTime:
    intervention_id: str
    claim_id: str
    delta_seconds: float
    cause_id: str

    def __post_init__(self) -> None:
        _validate_identity(self.intervention_id, self.cause_id)
        _non_empty(self.claim_id, "claim_id")
        object.__setattr__(
            self,
            "delta_seconds",
            _finite_number(self.delta_seconds, "delta_seconds"),
        )

    def apply(self, state: InterventionState) -> InterventionState:
        target = _require_claim(state, self.claim_id)
        updated = replace(
            target,
            knowledge_time=target.knowledge_time + timedelta(seconds=self.delta_seconds),
        )
        return InterventionState(
            claims=_ordered(updated if claim == target else claim for claim in state.claims),
            sources=state.sources,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "type": "shift_knowledge_time",
            "intervention_id": self.intervention_id,
            "claim_id": self.claim_id,
            "delta_seconds": self.delta_seconds,
            "cause_id": self.cause_id,
        }


@dataclass(frozen=True, slots=True)
class SetSourceReliability:
    intervention_id: str
    source_id: str
    reliability: float
    cause_id: str

    def __post_init__(self) -> None:
        _validate_identity(self.intervention_id, self.cause_id)
        _non_empty(self.source_id, "source_id")
        reliability = _finite_number(self.reliability, "reliability")
        if not 0.0 <= reliability <= 1.0:
            raise ValueError("reliability must be between 0 and 1 inclusive")
        object.__setattr__(self, "reliability", reliability)

    def apply(self, state: InterventionState) -> InterventionState:
        return InterventionState(
            claims=state.claims,
            sources=state.sources.with_reliability(self.source_id, self.reliability),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "type": "set_source_reliability",
            "intervention_id": self.intervention_id,
            "source_id": self.source_id,
            "reliability": self.reliability,
            "cause_id": self.cause_id,
        }


@dataclass(frozen=True, slots=True)
class InterventionSet:
    interventions: tuple[Intervention, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "interventions", tuple(self.interventions))
        identifiers = [item.intervention_id for item in self.interventions]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("intervention_id values must be unique")

    @property
    def intervention_ids(self) -> tuple[str, ...]:
        return tuple(item.intervention_id for item in self.interventions)

    def apply(
        self,
        claims: Iterable[Claim],
        sources: SourceRegistry,
    ) -> InterventionState:
        state = InterventionState(_ordered(claims), sources.copy())
        for intervention in self.interventions:
            state = intervention.apply(state)
        return state

    def to_dict(self) -> dict[str, object]:
        return {
            "interventions": [item.to_dict() for item in self.interventions],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> InterventionSet:
        if not isinstance(data, Mapping):
            raise TypeError("intervention set must be an object")
        if set(data) != {"interventions"}:
            extra = set(data) - {"interventions"}
            missing = {"interventions"} - set(data)
            if extra:
                raise ValueError(f"unknown intervention set fields: {sorted(extra)}")
            raise ValueError(f"missing intervention set fields: {sorted(missing)}")
        raw = data["interventions"]
        if not isinstance(raw, list):
            raise TypeError("interventions must be an array")
        return cls(tuple(intervention_from_dict(item) for item in raw))


def intervention_from_dict(data: Mapping[str, Any]) -> Intervention:
    if not isinstance(data, Mapping):
        raise TypeError("intervention must be an object")
    intervention_type = data.get("type")
    if not isinstance(intervention_type, str):
        raise ValueError("intervention type must be a non-empty string")

    common = {"intervention_id", "cause_id"}
    if intervention_type == "remove_claim":
        _strict_fields(
            data,
            intervention_type=intervention_type,
            required=common | {"claim_id"},
        )
        return RemoveClaim(
            intervention_id=data["intervention_id"],
            claim_id=data["claim_id"],
            cause_id=data["cause_id"],
        )
    if intervention_type == "add_claim":
        _strict_fields(
            data,
            intervention_type=intervention_type,
            required=common | {"claim"},
        )
        return AddClaim(
            intervention_id=data["intervention_id"],
            claim=Claim.from_dict(data["claim"]),
            cause_id=data["cause_id"],
        )
    if intervention_type == "set_claim_confidence":
        _strict_fields(
            data,
            intervention_type=intervention_type,
            required=common | {"claim_id", "confidence"},
        )
        return SetClaimConfidence(
            intervention_id=data["intervention_id"],
            claim_id=data["claim_id"],
            confidence=data["confidence"],
            cause_id=data["cause_id"],
        )
    if intervention_type == "shift_knowledge_time":
        _strict_fields(
            data,
            intervention_type=intervention_type,
            required=common | {"claim_id", "delta_seconds"},
        )
        return ShiftKnowledgeTime(
            intervention_id=data["intervention_id"],
            claim_id=data["claim_id"],
            delta_seconds=data["delta_seconds"],
            cause_id=data["cause_id"],
        )
    if intervention_type == "set_source_reliability":
        _strict_fields(
            data,
            intervention_type=intervention_type,
            required=common | {"source_id", "reliability"},
        )
        return SetSourceReliability(
            intervention_id=data["intervention_id"],
            source_id=data["source_id"],
            reliability=data["reliability"],
            cause_id=data["cause_id"],
        )
    raise ValueError(f"unsupported intervention type: {intervention_type!r}")
