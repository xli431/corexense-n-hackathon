from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from tws_belief.counterfactual import Intervention
from tws_belief.decision import Decision, SelectedValueDecisionPolicy
from tws_belief.models import Claim
from tws_belief.sources import SourceRegistry


@dataclass(frozen=True, slots=True)
class FailureScenario:
    scenario_id: str
    category: str
    claims: tuple[Claim, ...]
    knowledge_time: datetime
    event_time: datetime
    sources: SourceRegistry
    decision_policy: SelectedValueDecisionPolicy
    candidates: tuple[Intervention, ...]
    ground_truth_intervention_ids: tuple[str, ...]
    ground_truth_cause_ids: tuple[str, ...]
    target_decision: Decision

    def to_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "category": self.category,
            "claims": [claim.to_dict() for claim in self.claims],
            "knowledge_time": self.knowledge_time.isoformat(),
            "event_time": self.event_time.isoformat(),
            "sources": self.sources.to_dict(),
            "source_default_reliability": self.sources.default_reliability,
            "decision_policy_id": self.decision_policy.policy_id,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "ground_truth_intervention_ids": list(
                self.ground_truth_intervention_ids
            ),
            "ground_truth_cause_ids": list(self.ground_truth_cause_ids),
            "target_decision": self.target_decision.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class ScenarioEvaluation:
    scenario_id: str
    category: str
    baseline_action: str
    target_action: str
    counterfactual_action: str
    counterfactual_valid: bool
    attribution_succeeded: bool
    attribution_top1_exact: bool
    attribution_cause_exact: bool
    minimal_cardinality: int | None
    evaluated_sets: int
    conflict_count: int
    competitor_count: int
    future_knowledge_violations: int

    def to_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "category": self.category,
            "baseline_action": self.baseline_action,
            "target_action": self.target_action,
            "counterfactual_action": self.counterfactual_action,
            "counterfactual_valid": self.counterfactual_valid,
            "attribution_succeeded": self.attribution_succeeded,
            "attribution_top1_exact": self.attribution_top1_exact,
            "attribution_cause_exact": self.attribution_cause_exact,
            "minimal_cardinality": self.minimal_cardinality,
            "evaluated_sets": self.evaluated_sets,
            "conflict_count": self.conflict_count,
            "competitor_count": self.competitor_count,
            "future_knowledge_violations": self.future_knowledge_violations,
        }
