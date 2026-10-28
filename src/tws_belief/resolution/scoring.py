from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

from tws_belief.models import Claim, ResolutionScore

from .base import ResolutionContext


@dataclass(frozen=True, slots=True)
class WeightedResolutionPolicy:
    """Transparent additive v0.1 baseline, not probabilistic inference."""

    confidence_weight: float = 0.50
    source_weight: float = 0.25
    recency_weight: float = 0.20
    provenance_weight: float = 0.05
    staleness_weight: float = 0.10
    recency_half_life_seconds: float = 300.0
    stale_after_seconds: float = 600.0
    staleness_horizon_seconds: float = 600.0

    def __post_init__(self) -> None:
        weights = (
            self.confidence_weight,
            self.source_weight,
            self.recency_weight,
            self.provenance_weight,
            self.staleness_weight,
        )
        if any(weight < 0 for weight in weights):
            raise ValueError("score weights must be non-negative")
        if self.recency_half_life_seconds <= 0:
            raise ValueError("recency_half_life_seconds must be positive")
        if self.stale_after_seconds < 0 or self.staleness_horizon_seconds <= 0:
            raise ValueError("staleness thresholds must be valid")

    @property
    def policy_id(self) -> str:
        config = {
            "confidence_weight": self.confidence_weight,
            "provenance_weight": self.provenance_weight,
            "recency_half_life_seconds": self.recency_half_life_seconds,
            "recency_weight": self.recency_weight,
            "source_weight": self.source_weight,
            "stale_after_seconds": self.stale_after_seconds,
            "staleness_horizon_seconds": self.staleness_horizon_seconds,
            "staleness_weight": self.staleness_weight,
        }
        digest = hashlib.sha256(
            json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:12]
        return f"weighted-v0.1-{digest}"

    def score(self, claim: Claim, context: ResolutionContext) -> ResolutionScore:
        age = max(0.0, (context.event_time - claim.event_time).total_seconds())
        recency_factor = math.exp(
            -math.log(2.0) * age / self.recency_half_life_seconds
        )
        stale_age = max(0.0, age - self.stale_after_seconds)
        staleness_factor = min(1.0, stale_age / self.staleness_horizon_seconds)
        provenance_factor = (
            float(bool(claim.source_id)) + float(bool(claim.observation_id))
        ) / 2.0

        confidence = self.confidence_weight * claim.confidence
        source = self.source_weight * context.sources.reliability(claim.source_id)
        recency = self.recency_weight * recency_factor
        provenance = self.provenance_weight * provenance_factor
        staleness = self.staleness_weight * staleness_factor
        total = confidence + source + recency + provenance - staleness
        return ResolutionScore(
            total=total,
            confidence=confidence,
            source_reliability=source,
            recency=recency,
            provenance_quality=provenance,
            staleness_penalty=staleness,
        )
