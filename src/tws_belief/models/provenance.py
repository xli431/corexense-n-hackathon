from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .claim import Claim, thaw_json
from .proposition import PropositionKey


@dataclass(frozen=True, slots=True)
class ResolutionScore:
    total: float
    confidence: float
    source_reliability: float
    recency: float
    provenance_quality: float
    staleness_penalty: float

    def to_dict(self) -> dict[str, float]:
        return {
            "total": self.total,
            "confidence": self.confidence,
            "source_reliability": self.source_reliability,
            "recency": self.recency,
            "provenance_quality": self.provenance_quality,
            "staleness_penalty": self.staleness_penalty,
        }


@dataclass(frozen=True, slots=True)
class CandidateAssessment:
    claim: Claim
    score: ResolutionScore
    rank: int
    outcome: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim": self.claim.to_dict(),
            "score": self.score.to_dict(),
            "rank": self.rank,
            "outcome": self.outcome,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class BeliefExplanation:
    proposition: PropositionKey
    selected_claim: Claim
    candidates: tuple[CandidateAssessment, ...]
    policy_id: str
    conflict_ids: tuple[str, ...]

    @property
    def competing_claims(self) -> tuple[Claim, ...]:
        return tuple(item.claim for item in self.candidates if item.rank != 1)

    def format_human(self) -> str:
        selected = self.candidates[0]
        lines = [
            f"{self.proposition}: selected {selected.claim.claim_id} "
            f"value={thaw_json(selected.claim.value)!r} score={selected.score.total:.6f}.",
            (
                f"Source={selected.claim.source_id}; "
                f"observation={selected.claim.observation_id}; "
                f"event_time={selected.claim.event_time.isoformat()}; "
                f"knowledge_time={selected.claim.knowledge_time.isoformat()}."
            ),
        ]
        for candidate in self.candidates[1:]:
            lines.append(
                f"Rank {candidate.rank}: {candidate.claim.claim_id} "
                f"value={thaw_json(candidate.claim.value)!r} "
                f"score={candidate.score.total:.6f}; {candidate.reason}"
            )
        lines.append(
            f"Recorded conflicts: {len(self.conflict_ids)}; policy={self.policy_id}."
        )
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposition": {
                "entity_id": self.proposition.entity_id,
                "predicate": self.proposition.predicate,
            },
            "selected_claim_id": self.selected_claim.claim_id,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "policy_id": self.policy_id,
            "conflict_ids": list(self.conflict_ids),
        }
