from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tws_belief.counterfactual import (
    AddClaim,
    Intervention,
    RemoveClaim,
    SetClaimConfidence,
    SetSourceReliability,
    ShiftKnowledgeTime,
)
from tws_belief.decision import Decision, SelectedValueDecisionPolicy
from tws_belief.models import Claim, PropositionKey
from tws_belief.sources import SourceRegistry

from .models import FailureScenario

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)
CATEGORIES = (
    "stale_evidence",
    "delayed_evidence",
    "contradictory_evidence",
    "source_reliability",
    "identity_error",
    "relation_error",
    "human_correction",
    "missing_evidence",
)


def _claim(
    scenario_id: str,
    label: str,
    *,
    entity_id: str,
    predicate: str,
    value: str,
    confidence: float,
    source_id: str,
    start: datetime,
    event_second: float,
    knowledge_second: float,
) -> Claim:
    return Claim(
        claim_id=f"{scenario_id}:{label}",
        entity_id=entity_id,
        predicate=predicate,
        value=value,
        confidence=confidence,
        source_id=source_id,
        observation_id=f"obs:{scenario_id}:{label}",
        event_time=start + timedelta(seconds=event_second),
        knowledge_time=start + timedelta(seconds=knowledge_second),
        valid_from=start + timedelta(seconds=event_second),
        valid_until=None,
        revision=0,
        metadata={
            "benchmark": "tws-belief-failure-v0.1",
            "scenario_id": scenario_id,
        },
    )


def _target_decision(
    policy: SelectedValueDecisionPolicy,
    correct: Claim,
) -> Decision:
    return Decision(
        action=policy.action_for_value(correct.value),
        proposition=policy.proposition,
        selected_claim_id=correct.claim_id,
    )


def make_scenario(index: int) -> FailureScenario:
    if index < 0:
        raise ValueError("index must be non-negative")
    category = CATEGORIES[index % len(CATEGORIES)]
    scenario_id = f"scenario-{index:06d}"
    start = BASE + timedelta(seconds=index * 1_000)
    decision_time = start + timedelta(seconds=100)

    entity_id = f"object_{index:06d}"
    predicate = "location"
    correct_value = f"station_{2 + (index % 5)}"
    wrong_value = f"station_{index % 2}"
    if category == "identity_error":
        predicate = "identity"
        correct_value = f"item_expected_{index % 17}"
        wrong_value = f"item_confused_{index % 13}"
    elif category == "relation_error":
        predicate = "spatial_relation"
        container = f"container_{index % 11}"
        correct_value, wrong_value = f"inside:{container}", f"on:{container}"
    elif category == "human_correction":
        predicate = "condition"
        correct_value, wrong_value = "safe", "unsafe"

    proposition = PropositionKey(entity_id, predicate)
    decision_policy = SelectedValueDecisionPolicy(
        proposition,
        action_prefix="act_on",
    )
    sources = SourceRegistry(
        {
            "correct_sensor": 0.80,
            "wrong_sensor": 0.80,
            "human_operator": 0.99,
        },
        default_reliability=0.50,
    )

    correct = _claim(
        scenario_id,
        "correct",
        entity_id=entity_id,
        predicate=predicate,
        value=correct_value,
        confidence=0.70 + ((index * 7) % 15) / 100,
        source_id="correct_sensor",
        start=start,
        event_second=90,
        knowledge_second=92,
    )
    wrong = _claim(
        scenario_id,
        "fault",
        entity_id=entity_id,
        predicate=predicate,
        value=wrong_value,
        confidence=0.90 + ((index * 11) % 10) / 100,
        source_id="wrong_sensor",
        start=start,
        event_second=85,
        knowledge_second=86,
    )
    claims: tuple[Claim, ...] = (correct, wrong)
    ground_truth: Intervention

    if category == "stale_evidence":
        wrong = _claim(
            scenario_id,
            "fault",
            entity_id=entity_id,
            predicate=predicate,
            value=wrong_value,
            confidence=0.95 + ((index * 3) % 5) / 100,
            source_id="wrong_sensor",
            start=start,
            event_second=0,
            knowledge_second=5,
        )
        claims = (correct, wrong)
        ground_truth = RemoveClaim(
            f"{scenario_id}:remove-stale",
            wrong.claim_id,
            wrong.observation_id,
        )
    elif category == "delayed_evidence":
        correct = _claim(
            scenario_id,
            "correct",
            entity_id=entity_id,
            predicate=predicate,
            value=correct_value,
            confidence=0.99,
            source_id="correct_sensor",
            start=start,
            event_second=90,
            knowledge_second=110 + (index % 21),
        )
        claims = (correct, wrong)
        ground_truth = ShiftKnowledgeTime(
            f"{scenario_id}:remove-delay",
            correct.claim_id,
            -(15 + (index % 21)),
            correct.observation_id,
        )
    elif category == "source_reliability":
        correct = _claim(
            scenario_id,
            "correct",
            entity_id=entity_id,
            predicate=predicate,
            value=correct_value,
            confidence=0.82,
            source_id="correct_sensor",
            start=start,
            event_second=90,
            knowledge_second=92,
        )
        wrong = _claim(
            scenario_id,
            "fault",
            entity_id=entity_id,
            predicate=predicate,
            value=wrong_value,
            confidence=0.78,
            source_id="wrong_sensor",
            start=start,
            event_second=91,
            knowledge_second=93,
        )
        claims = (correct, wrong)
        sources = SourceRegistry(
            {
                "correct_sensor": 0.30 + (index % 4) / 10,
                "wrong_sensor": 0.90 + (index % 10) / 100,
            },
            default_reliability=0.50,
        )
        ground_truth = SetSourceReliability(
            f"{scenario_id}:recalibrate-source",
            "wrong_sensor",
            0.10,
            "source:wrong_sensor",
        )
    elif category == "human_correction":
        correct = _claim(
            scenario_id,
            "human-correction",
            entity_id=entity_id,
            predicate=predicate,
            value=correct_value,
            confidence=0.99,
            source_id="human_operator",
            start=start,
            event_second=80,
            knowledge_second=110 + (index % 21),
        )
        claims = (correct, wrong)
        ground_truth = ShiftKnowledgeTime(
            f"{scenario_id}:advance-correction",
            correct.claim_id,
            -(15 + (index % 21)),
            correct.observation_id,
        )
    elif category == "missing_evidence":
        claims = (wrong,)
        correct = _claim(
            scenario_id,
            "missing-correct",
            entity_id=entity_id,
            predicate=predicate,
            value=correct_value,
            confidence=0.99,
            source_id="correct_sensor",
            start=start,
            event_second=90,
            knowledge_second=95,
        )
        ground_truth = AddClaim(
            f"{scenario_id}:restore-missing",
            correct,
            correct.observation_id,
        )
    else:
        ground_truth = RemoveClaim(
            f"{scenario_id}:remove-fault",
            wrong.claim_id,
            wrong.observation_id,
        )

    distractors: list[Intervention]
    if any(claim.claim_id == correct.claim_id for claim in claims):
        distractors = [
            SetClaimConfidence(
                f"{scenario_id}:weaken-correct",
                correct.claim_id,
                0.01,
                correct.observation_id,
            ),
            SetSourceReliability(
                f"{scenario_id}:distrust-correct-source",
                correct.source_id,
                0.01,
                f"source:{correct.source_id}",
            ),
        ]
    else:
        distractors = [
            SetClaimConfidence(
                f"{scenario_id}:strengthen-fault",
                wrong.claim_id,
                0.99,
                wrong.observation_id,
            ),
            SetSourceReliability(
                f"{scenario_id}:trust-fault-source",
                wrong.source_id,
                1.0,
                f"source:{wrong.source_id}",
            ),
        ]

    return FailureScenario(
        scenario_id=scenario_id,
        category=category,
        claims=tuple(sorted(claims, key=lambda claim: claim.claim_id)),
        knowledge_time=decision_time,
        event_time=decision_time,
        sources=sources,
        decision_policy=decision_policy,
        candidates=tuple(
            sorted(
                (ground_truth, *distractors),
                key=lambda item: item.intervention_id,
            )
        ),
        ground_truth_intervention_ids=(ground_truth.intervention_id,),
        ground_truth_cause_ids=(ground_truth.cause_id,),
        target_decision=_target_decision(decision_policy, correct),
    )


def generate_scenarios(count: int = 1_000) -> tuple[FailureScenario, ...]:
    if count < 1:
        raise ValueError("count must be positive")
    return tuple(make_scenario(index) for index in range(count))
