from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timezone

from tws_belief.models import (
    BeliefExplanation,
    BeliefState,
    CandidateAssessment,
    Claim,
    ClaimConflict,
    EffectiveBelief,
    PropositionKey,
    ResolutionStatus,
    detect_conflicts,
)
from tws_belief.sources import SourceRegistry

from .base import ResolutionContext, ResolutionPolicy
from .scoring import WeightedResolutionPolicy


def _utc_timestamp(value: datetime) -> float:
    return value.astimezone(timezone.utc).timestamp()


class DeterministicBeliefResolver:
    """Resolve eligible claims with explicit scoring and deterministic tie breaks."""

    def __init__(
        self,
        *,
        policy: ResolutionPolicy | None = None,
        sources: SourceRegistry | None = None,
    ) -> None:
        self.policy = policy or WeightedResolutionPolicy()
        self.sources = sources or SourceRegistry()

    def resolve(
        self,
        claims: Iterable[Claim],
        knowledge_time: datetime,
        *,
        event_time: datetime | None = None,
    ) -> BeliefState:
        query_event_time = event_time or knowledge_time
        context = ResolutionContext(knowledge_time, query_event_time, self.sources)
        eligible = [
            claim
            for claim in claims
            if claim.known_by(knowledge_time) and claim.valid_at(query_event_time)
        ]
        groups: dict[PropositionKey, list[Claim]] = defaultdict(list)
        for claim in eligible:
            groups[claim.proposition].append(claim)

        raw_conflicts = detect_conflicts(eligible)
        effective: dict[PropositionKey, EffectiveBelief] = {}
        explanations: dict[PropositionKey, BeliefExplanation] = {}
        selected_by_proposition: dict[PropositionKey, Claim] = {}

        for proposition in sorted(groups):
            scored = [(claim, self.policy.score(claim, context)) for claim in groups[proposition]]
            ranked = sorted(
                scored,
                key=lambda item: (
                    -item[1].total,
                    -_utc_timestamp(item[0].knowledge_time),
                    -_utc_timestamp(item[0].event_time),
                    item[0].claim_id,
                ),
            )
            selected_claim = ranked[0][0]
            selected_by_proposition[proposition] = selected_claim
            competitors = tuple(claim for claim, _ in ranked[1:])
            effective[proposition] = EffectiveBelief(
                proposition=proposition,
                value=selected_claim.value,
                selected_claim=selected_claim,
                competing_claims=competitors,
            )

            assessments: list[CandidateAssessment] = []
            winning_score = ranked[0][1].total
            for rank, (claim, score) in enumerate(ranked, start=1):
                if rank == 1:
                    outcome = "selected"
                    reason = "highest deterministic rank"
                elif score.total < winning_score:
                    outcome = "not_selected"
                    reason = f"score was {winning_score - score.total:.6f} below selected"
                else:
                    outcome = "not_selected"
                    reason = (
                        "score tied; lost ordered tie-break: later knowledge_time, "
                        "later event_time, then lexical claim_id"
                    )
                assessments.append(
                    CandidateAssessment(
                        claim=claim,
                        score=score,
                        rank=rank,
                        outcome=outcome,
                        reason=reason,
                    )
                )
            conflict_ids = tuple(
                conflict.conflict_id
                for conflict in raw_conflicts
                if conflict.proposition == proposition
            )
            explanations[proposition] = BeliefExplanation(
                proposition=proposition,
                selected_claim=selected_claim,
                candidates=tuple(assessments),
                policy_id=self.policy.policy_id,
                conflict_ids=conflict_ids,
            )

        resolved_conflicts: list[ClaimConflict] = []
        for conflict in raw_conflicts:
            selected = selected_by_proposition[conflict.proposition]
            resolved_conflicts.append(
                ClaimConflict(
                    conflict_id=conflict.conflict_id,
                    proposition=conflict.proposition,
                    claims=conflict.claims,
                    conflict_type=conflict.conflict_type,
                    resolution_status=ResolutionStatus.RESOLVED,
                    selected_claim=selected,
                    explanation=(
                        f"{conflict.explanation} Resolver selected {selected.claim_id}; "
                        "both claims remain recorded."
                    ),
                )
            )

        return BeliefState(
            effective_beliefs=effective,
            explanations=explanations,
            conflicts=tuple(resolved_conflicts),
            reconstruction_time=knowledge_time,
            event_time=query_event_time,
            resolution_policy_id=self.policy.policy_id,
        )

    def explain(
        self, belief_state: BeliefState, proposition: PropositionKey
    ) -> BeliefExplanation:
        return belief_state.explain(proposition)
