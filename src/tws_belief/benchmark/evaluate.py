from __future__ import annotations

from tws_belief.attribution import MinimalInterventionAttributor
from tws_belief.counterfactual import CounterfactualReplayer, InterventionSet
from tws_belief.resolution import DeterministicBeliefResolver

from .models import FailureScenario, ScenarioEvaluation


def evaluate_scenario(scenario: FailureScenario) -> ScenarioEvaluation:
    resolver = DeterministicBeliefResolver(sources=scenario.sources)
    replayer = CounterfactualReplayer(
        resolver,
        decision_policy=scenario.decision_policy,
    )
    ground_truth_items = tuple(
        candidate
        for candidate in scenario.candidates
        if candidate.intervention_id in scenario.ground_truth_intervention_ids
    )
    ground_truth_replay = replayer.replay(
        scenario.claims,
        scenario.knowledge_time,
        InterventionSet(ground_truth_items),
        event_time=scenario.event_time,
    )
    attributor = MinimalInterventionAttributor(replayer)
    attribution = attributor.attribute(
        scenario.claims,
        scenario.knowledge_time,
        scenario.candidates,
        scenario.target_decision,
        event_time=scenario.event_time,
        max_cardinality=1,
    )
    if ground_truth_replay.baseline_decision is None:
        raise RuntimeError("benchmark requires a baseline decision")
    if ground_truth_replay.counterfactual_decision is None:
        raise RuntimeError("benchmark requires a counterfactual decision")

    baseline_state = ground_truth_replay.baseline
    competitor_count = sum(
        len(belief.competing_claims)
        for belief in baseline_state.effective_beliefs.values()
    )
    eligible_claims = [
        claim
        for belief in baseline_state.effective_beliefs.values()
        for claim in (belief.selected_claim, *belief.competing_claims)
    ]
    future_violations = sum(
        claim.knowledge_time > scenario.knowledge_time for claim in eligible_claims
    )
    top1 = attribution.top1
    return ScenarioEvaluation(
        scenario_id=scenario.scenario_id,
        category=scenario.category,
        baseline_action=ground_truth_replay.baseline_decision.action,
        target_action=scenario.target_decision.action,
        counterfactual_action=ground_truth_replay.counterfactual_decision.action,
        counterfactual_valid=(
            ground_truth_replay.counterfactual_decision.action
            == scenario.target_decision.action
        ),
        attribution_succeeded=attribution.succeeded,
        attribution_top1_exact=(
            top1 is not None
            and top1.intervention_ids == scenario.ground_truth_intervention_ids
        ),
        attribution_cause_exact=(
            top1 is not None and top1.cause_ids == scenario.ground_truth_cause_ids
        ),
        minimal_cardinality=attribution.minimal_cardinality,
        evaluated_sets=attribution.evaluated_sets,
        conflict_count=len(baseline_state.conflicts),
        competitor_count=competitor_count,
        future_knowledge_violations=future_violations,
    )
