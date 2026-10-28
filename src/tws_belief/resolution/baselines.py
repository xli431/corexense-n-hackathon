from __future__ import annotations

import math

from tws_belief.models import Claim, ResolutionScore

from .base import ResolutionContext


def _score(total: float) -> ResolutionScore:
    return ResolutionScore(
        total=total,
        confidence=0.0,
        source_reliability=0.0,
        recency=0.0,
        provenance_quality=0.0,
        staleness_penalty=0.0,
    )


class LatestKnowledgePolicy:
    """Selection baseline approximating latest-write-wins."""

    policy_id = "baseline-latest-knowledge-v0.1"

    def score(self, claim: Claim, context: ResolutionContext) -> ResolutionScore:
        del context
        return _score(claim.knowledge_time.timestamp())


class HighestConfidencePolicy:
    """Selection baseline using only producer-reported confidence."""

    policy_id = "baseline-highest-confidence-v0.1"

    def score(self, claim: Claim, context: ResolutionContext) -> ResolutionScore:
        del context
        score = _score(claim.confidence)
        return ResolutionScore(
            total=score.total,
            confidence=claim.confidence,
            source_reliability=0.0,
            recency=0.0,
            provenance_quality=0.0,
            staleness_penalty=0.0,
        )


class RecencyOnlyPolicy:
    """Selection baseline using event-time exponential recency only."""

    policy_id = "baseline-recency-only-v0.1"

    def __init__(self, half_life_seconds: float = 300.0) -> None:
        if half_life_seconds <= 0:
            raise ValueError("half_life_seconds must be positive")
        self.half_life_seconds = half_life_seconds
        self.policy_id = f"baseline-recency-only-v0.1:{half_life_seconds:g}"

    def score(self, claim: Claim, context: ResolutionContext) -> ResolutionScore:
        age = max(0.0, (context.event_time - claim.event_time).total_seconds())
        recency = math.exp(-math.log(2.0) * age / self.half_life_seconds)
        return ResolutionScore(
            total=recency,
            confidence=0.0,
            source_reliability=0.0,
            recency=recency,
            provenance_quality=0.0,
            staleness_penalty=0.0,
        )
