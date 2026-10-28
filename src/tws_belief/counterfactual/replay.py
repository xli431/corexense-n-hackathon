from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from tws_belief.decision import Decision, DecisionPolicy
from tws_belief.models import BeliefState, Claim, PropositionKey
from tws_belief.models.claim import thaw_json
from tws_belief.resolution import DeterministicBeliefResolver

from .interventions import InterventionSet
from .manifest import PerturbationManifest


@dataclass(frozen=True, slots=True)
class BeliefDelta:
    proposition: PropositionKey
    baseline_value: Any
    counterfactual_value: Any
    baseline_claim_id: str | None
    counterfactual_claim_id: str | None

    @property
    def changed(self) -> bool:
        return (
            self.baseline_value != self.counterfactual_value
            or self.baseline_claim_id != self.counterfactual_claim_id
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "proposition": str(self.proposition),
            "baseline_value": thaw_json(self.baseline_value),
            "counterfactual_value": thaw_json(self.counterfactual_value),
            "baseline_claim_id": self.baseline_claim_id,
            "counterfactual_claim_id": self.counterfactual_claim_id,
            "changed": self.changed,
        }


@dataclass(frozen=True, slots=True)
class CounterfactualReplayResult:
    baseline: BeliefState
    counterfactual: BeliefState
    interventions: InterventionSet
    belief_deltas: tuple[BeliefDelta, ...]
    baseline_decision: Decision | None
    counterfactual_decision: Decision | None

    @property
    def decision_changed(self) -> bool | None:
        if self.baseline_decision is None or self.counterfactual_decision is None:
            return None
        return self.baseline_decision.action != self.counterfactual_decision.action

    def to_dict(self) -> dict[str, object]:
        return {
            "interventions": self.interventions.to_dict()["interventions"],
            "baseline": self.baseline.to_dict(),
            "counterfactual": self.counterfactual.to_dict(),
            "belief_deltas": [delta.to_dict() for delta in self.belief_deltas],
            "baseline_decision": (
                self.baseline_decision.to_dict() if self.baseline_decision else None
            ),
            "counterfactual_decision": (
                self.counterfactual_decision.to_dict()
                if self.counterfactual_decision
                else None
            ),
            "decision_changed": self.decision_changed,
        }


class CounterfactualReplayer:
    """Algorithm 2: deterministic replay under an explicit intervention manifest."""

    def __init__(
        self,
        resolver: DeterministicBeliefResolver,
        *,
        decision_policy: DecisionPolicy | None = None,
    ) -> None:
        self.resolver = resolver
        self.decision_policy = decision_policy

    def replay(
        self,
        claims: Iterable[Claim],
        knowledge_time: datetime,
        interventions: InterventionSet,
        *,
        event_time: datetime | None = None,
    ) -> CounterfactualReplayResult:
        original_claims = tuple(claims)
        baseline = self.resolver.resolve(
            original_claims,
            knowledge_time,
            event_time=event_time,
        )
        altered = interventions.apply(original_claims, self.resolver.sources)
        counterfactual_resolver = DeterministicBeliefResolver(
            policy=self.resolver.policy,
            sources=altered.sources,
        )
        counterfactual = counterfactual_resolver.resolve(
            altered.claims,
            knowledge_time,
            event_time=event_time,
        )

        propositions = sorted(
            set(baseline.effective_beliefs) | set(counterfactual.effective_beliefs)
        )
        deltas: list[BeliefDelta] = []
        for proposition in propositions:
            before = baseline.get(proposition)
            after = counterfactual.get(proposition)
            deltas.append(
                BeliefDelta(
                    proposition=proposition,
                    baseline_value=before.value if before else None,
                    counterfactual_value=after.value if after else None,
                    baseline_claim_id=before.selected_claim.claim_id if before else None,
                    counterfactual_claim_id=after.selected_claim.claim_id if after else None,
                )
            )

        baseline_decision = (
            self.decision_policy.decide(baseline) if self.decision_policy else None
        )
        counterfactual_decision = (
            self.decision_policy.decide(counterfactual)
            if self.decision_policy
            else None
        )
        return CounterfactualReplayResult(
            baseline=baseline,
            counterfactual=counterfactual,
            interventions=interventions,
            belief_deltas=tuple(deltas),
            baseline_decision=baseline_decision,
            counterfactual_decision=counterfactual_decision,
        )

    def replay_manifest(
        self,
        claims: Iterable[Claim],
        knowledge_time: datetime,
        manifest: PerturbationManifest,
        *,
        dataset: str,
        reference_id: str,
        reference_sha256: str,
        event_time: datetime | None = None,
    ) -> CounterfactualReplayResult:
        """Verify a manifest's baseline binding before counterfactual replay."""

        manifest.require_reference(
            dataset=dataset,
            reference_id=reference_id,
            reference_sha256=reference_sha256,
        )
        return self.replay(
            claims,
            knowledge_time,
            manifest.intervention_set,
            event_time=event_time,
        )
