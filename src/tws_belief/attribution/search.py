from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations

from tws_belief.counterfactual import (
    CounterfactualReplayer,
    CounterfactualReplayResult,
    Intervention,
    InterventionSet,
)
from tws_belief.decision import Decision
from tws_belief.models import Claim


@dataclass(frozen=True, slots=True)
class AttributionHypothesis:
    intervention_ids: tuple[str, ...]
    cause_ids: tuple[str, ...]
    replay: CounterfactualReplayResult

    def to_dict(self) -> dict[str, object]:
        return {
            "intervention_ids": list(self.intervention_ids),
            "cause_ids": list(self.cause_ids),
            "decision_changed": self.replay.decision_changed,
            "counterfactual_decision": (
                self.replay.counterfactual_decision.to_dict()
                if self.replay.counterfactual_decision
                else None
            ),
        }


@dataclass(frozen=True, slots=True)
class AttributionResult:
    baseline_decision: Decision
    target_decision: Decision
    minimal_cardinality: int | None
    hypotheses: tuple[AttributionHypothesis, ...]
    evaluated_sets: int

    @property
    def succeeded(self) -> bool:
        return bool(self.hypotheses)

    @property
    def top1(self) -> AttributionHypothesis | None:
        return self.hypotheses[0] if self.hypotheses else None

    def to_dict(self) -> dict[str, object]:
        return {
            "baseline_decision": self.baseline_decision.to_dict(),
            "target_decision": self.target_decision.to_dict(),
            "minimal_cardinality": self.minimal_cardinality,
            "hypotheses": [hypothesis.to_dict() for hypothesis in self.hypotheses],
            "evaluated_sets": self.evaluated_sets,
        }


class MinimalInterventionAttributor:
    """Exhaustive bounded search over declared interventions.

    The result is counterfactual attribution within the supplied candidate set,
    not proof of real-world causality.
    """

    def __init__(self, replayer: CounterfactualReplayer) -> None:
        if replayer.decision_policy is None:
            raise ValueError("attribution requires a decision_policy")
        self.replayer = replayer

    def attribute(
        self,
        claims: Iterable[Claim],
        knowledge_time: datetime,
        candidates: Sequence[Intervention],
        target_decision: Decision,
        *,
        event_time: datetime | None = None,
        max_cardinality: int = 1,
    ) -> AttributionResult:
        if max_cardinality < 1:
            raise ValueError("max_cardinality must be positive")
        original_claims = tuple(claims)
        empty_replay = self.replayer.replay(
            original_claims,
            knowledge_time,
            InterventionSet(()),
            event_time=event_time,
        )
        if empty_replay.baseline_decision is None:
            raise RuntimeError("decision policy produced no baseline decision")
        if empty_replay.baseline_decision.action == target_decision.action:
            return AttributionResult(
                baseline_decision=empty_replay.baseline_decision,
                target_decision=target_decision,
                minimal_cardinality=0,
                hypotheses=(
                    AttributionHypothesis(
                        intervention_ids=(),
                        cause_ids=(),
                        replay=empty_replay,
                    ),
                ),
                evaluated_sets=0,
            )
        ordered = sorted(candidates, key=lambda item: item.intervention_id)
        evaluated = 0
        hypotheses: list[AttributionHypothesis] = []

        for cardinality in range(1, min(max_cardinality, len(ordered)) + 1):
            for selected in combinations(ordered, cardinality):
                evaluated += 1
                replay = self.replayer.replay(
                    original_claims,
                    knowledge_time,
                    InterventionSet(tuple(selected)),
                    event_time=event_time,
                )
                decision = replay.counterfactual_decision
                if decision is not None and decision.action == target_decision.action:
                    hypotheses.append(
                        AttributionHypothesis(
                            intervention_ids=tuple(
                                item.intervention_id for item in selected
                            ),
                            cause_ids=tuple(item.cause_id for item in selected),
                            replay=replay,
                        )
                    )
            if hypotheses:
                hypotheses.sort(key=lambda item: item.intervention_ids)
                return AttributionResult(
                    baseline_decision=empty_replay.baseline_decision,
                    target_decision=target_decision,
                    minimal_cardinality=cardinality,
                    hypotheses=tuple(hypotheses),
                    evaluated_sets=evaluated,
                )

        return AttributionResult(
            baseline_decision=empty_replay.baseline_decision,
            target_decision=target_decision,
            minimal_cardinality=None,
            hypotheses=(),
            evaluated_sets=evaluated,
        )
