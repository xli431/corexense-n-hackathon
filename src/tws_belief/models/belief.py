from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any

from .claim import Claim, thaw_json
from .conflict import ClaimConflict, ResolutionStatus
from .proposition import PropositionKey
from .provenance import BeliefExplanation


@dataclass(frozen=True, slots=True)
class EffectiveBelief:
    proposition: PropositionKey
    value: Any
    selected_claim: Claim
    competing_claims: tuple[Claim, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposition": str(self.proposition),
            "value": thaw_json(self.value),
            "selected_claim_id": self.selected_claim.claim_id,
            "competing_claim_ids": [claim.claim_id for claim in self.competing_claims],
        }


@dataclass(frozen=True, slots=True)
class BeliefState:
    """Immutable snapshot of selected beliefs and preserved competing evidence."""

    effective_beliefs: Mapping[PropositionKey, EffectiveBelief]
    explanations: Mapping[PropositionKey, BeliefExplanation]
    conflicts: tuple[ClaimConflict, ...]
    reconstruction_time: datetime
    event_time: datetime
    resolution_policy_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "effective_beliefs",
            MappingProxyType(dict(sorted(self.effective_beliefs.items()))),
        )
        object.__setattr__(
            self,
            "explanations",
            MappingProxyType(dict(sorted(self.explanations.items()))),
        )

    @property
    def unresolved_conflicts(self) -> tuple[ClaimConflict, ...]:
        return tuple(
            conflict
            for conflict in self.conflicts
            if conflict.resolution_status is ResolutionStatus.UNRESOLVED
        )

    def get(self, proposition: PropositionKey) -> EffectiveBelief | None:
        return self.effective_beliefs.get(proposition)

    def explain(self, proposition: PropositionKey) -> BeliefExplanation:
        try:
            return self.explanations[proposition]
        except KeyError as error:
            raise KeyError(f"no effective belief for {proposition}") from error

    def to_dict(self) -> dict[str, Any]:
        beliefs = [
            self.effective_beliefs[key].to_dict() for key in sorted(self.effective_beliefs)
        ]
        return {
            "reconstruction_time": self.reconstruction_time.isoformat(),
            "event_time": self.event_time.isoformat(),
            "resolution_policy_id": self.resolution_policy_id,
            "effective_beliefs": beliefs,
            "conflicts": [
                {
                    "conflict_id": conflict.conflict_id,
                    "proposition": str(conflict.proposition),
                    "claim_ids": [claim.claim_id for claim in conflict.claims],
                    "conflict_type": conflict.conflict_type.value,
                    "resolution_status": conflict.resolution_status.value,
                    "selected_claim_id": (
                        conflict.selected_claim.claim_id if conflict.selected_claim else None
                    ),
                    "explanation": conflict.explanation,
                }
                for conflict in self.conflicts
            ],
            "explanations": [
                self.explanations[key].to_dict() for key in sorted(self.explanations)
            ],
        }
