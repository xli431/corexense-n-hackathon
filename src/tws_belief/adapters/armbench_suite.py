from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from tws_belief.counterfactual import (
    CounterfactualReplayer,
    PerturbationManifest,
    load_perturbation_manifest,
)
from tws_belief.models import BeliefState, Claim, EvidenceRecord, PropositionKey
from tws_belief.models.claim import thaw_json
from tws_belief.models.evidence import evidence_records_sha256
from tws_belief.resolution import DeterministicBeliefResolver

ARMBENCH_FIXTURE_CATEGORIES = (
    "confidence_perturbation",
    "contradictory_evidence",
    "delayed_evidence",
    "identity_error",
    "missing_evidence",
    "relation_error",
    "source_reliability",
    "stale_evidence",
)


def _required_mapping(
    data: Mapping[str, Any],
    key: str,
) -> Mapping[str, Any]:
    value = data.get(key)
    if not isinstance(value, Mapping):
        raise TypeError(f"manifest metadata.{key} must be an object")
    return value


@dataclass(frozen=True, slots=True)
class ArmbenchPerturbationCase:
    manifest: PerturbationManifest
    category: str
    proposition: PropositionKey
    baseline_present: bool
    baseline_value: Any
    counterfactual_present: bool
    counterfactual_value: Any
    belief_changed: bool
    conflict_delta: int

    @classmethod
    def from_manifest(
        cls,
        manifest: PerturbationManifest,
    ) -> ArmbenchPerturbationCase:
        if manifest.dataset != "ARMBench":
            raise ValueError("ARMBench fixture case must use dataset='ARMBench'")
        metadata = manifest.metadata
        if metadata.get("fixture") is not True or metadata.get("synthetic") is not True:
            raise ValueError("ARMBench fixture case must be marked fixture and synthetic")
        category = metadata.get("perturbation_category")
        if category not in ARMBENCH_FIXTURE_CATEGORIES:
            raise ValueError(f"unsupported ARMBench fixture category: {category!r}")
        target = _required_mapping(metadata, "target")
        for key in ("entity_id", "predicate"):
            if not isinstance(target.get(key), str) or not target[key].strip():
                raise ValueError(f"manifest metadata.target.{key} must be non-empty")
        expected = _required_mapping(metadata, "expected")
        required_expected = {
            "baseline_present",
            "baseline_value",
            "counterfactual_present",
            "counterfactual_value",
            "belief_changed",
            "conflict_delta",
        }
        missing = required_expected - set(expected)
        if missing:
            raise ValueError(f"missing expected fields: {sorted(missing)}")
        for key in ("baseline_present", "counterfactual_present", "belief_changed"):
            if not isinstance(expected[key], bool):
                raise TypeError(f"metadata.expected.{key} must be boolean")
        conflict_delta = expected["conflict_delta"]
        if isinstance(conflict_delta, bool) or not isinstance(conflict_delta, int):
            raise TypeError("metadata.expected.conflict_delta must be an integer")
        return cls(
            manifest=manifest,
            category=category,
            proposition=PropositionKey(
                entity_id=target["entity_id"],
                predicate=target["predicate"],
            ),
            baseline_present=expected["baseline_present"],
            baseline_value=expected["baseline_value"],
            counterfactual_present=expected["counterfactual_present"],
            counterfactual_value=expected["counterfactual_value"],
            belief_changed=expected["belief_changed"],
            conflict_delta=conflict_delta,
        )


@dataclass(frozen=True, slots=True)
class ArmbenchPerturbationResult:
    manifest_id: str
    manifest_sha256: str
    category: str
    proposition: PropositionKey
    baseline_present: bool
    baseline_value: Any
    counterfactual_present: bool
    counterfactual_value: Any
    belief_changed: bool
    conflict_delta: int
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "manifest_sha256": self.manifest_sha256,
            "category": self.category,
            "proposition": str(self.proposition),
            "baseline_present": self.baseline_present,
            "baseline_value": thaw_json(self.baseline_value),
            "counterfactual_present": self.counterfactual_present,
            "counterfactual_value": thaw_json(self.counterfactual_value),
            "belief_changed": self.belief_changed,
            "conflict_delta": self.conflict_delta,
            "passed": self.passed,
        }


def load_armbench_perturbation_suite(
    directory: str | Path,
) -> tuple[ArmbenchPerturbationCase, ...]:
    paths = sorted(Path(directory).glob("*.manifest.json"))
    if not paths:
        raise ValueError("ARMBench perturbation suite contains no manifest files")
    cases = tuple(
        ArmbenchPerturbationCase.from_manifest(load_perturbation_manifest(path))
        for path in paths
    )
    categories = [case.category for case in cases]
    if len(categories) != len(set(categories)):
        raise ValueError("ARMBench perturbation categories must be unique")
    missing = set(ARMBENCH_FIXTURE_CATEGORIES) - set(categories)
    if missing:
        raise ValueError(f"ARMBench perturbation suite is missing categories: {sorted(missing)}")
    return tuple(sorted(cases, key=lambda case: case.category))


def armbench_perturbation_suite_sha256(
    cases: Sequence[ArmbenchPerturbationCase],
) -> str:
    encoded = json.dumps(
        [
            case.manifest.to_dict()
            for case in sorted(cases, key=lambda item: item.category)
        ],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _conflict_count(state: BeliefState, proposition: PropositionKey) -> int:
    return sum(conflict.proposition == proposition for conflict in state.conflicts)


def evaluate_armbench_perturbation_suite(
    records: Iterable[EvidenceRecord],
    cases: Sequence[ArmbenchPerturbationCase],
    decision_time: datetime,
    *,
    resolver: DeterministicBeliefResolver | None = None,
) -> tuple[ArmbenchPerturbationResult, ...]:
    evidence = tuple(records)
    if not evidence:
        raise ValueError("ARMBench perturbation suite requires evidence records")
    if any(record.dataset != "ARMBench" for record in evidence):
        raise ValueError("ARMBench perturbation suite requires ARMBench evidence")
    episode_ids = {record.episode_id for record in evidence}
    if len(episode_ids) != 1:
        raise ValueError("ARMBench fixture records must share one episode_id")
    claims: tuple[Claim, ...] = tuple(
        claim
        for record in sorted(evidence, key=lambda item: item.evidence_id)
        for claim in record.to_claims()
    )
    reference_id = next(iter(episode_ids))
    reference_sha256 = evidence_records_sha256(evidence)
    replayer = CounterfactualReplayer(resolver or DeterministicBeliefResolver())
    results: list[ArmbenchPerturbationResult] = []

    for case in sorted(cases, key=lambda item: item.category):
        replay = replayer.replay_manifest(
            claims,
            decision_time,
            case.manifest,
            dataset="ARMBench",
            reference_id=reference_id,
            reference_sha256=reference_sha256,
        )
        before = replay.baseline.get(case.proposition)
        after = replay.counterfactual.get(case.proposition)
        baseline_present = before is not None
        counterfactual_present = after is not None
        baseline_value = before.value if before else None
        counterfactual_value = after.value if after else None
        belief_changed = next(
            delta.changed
            for delta in replay.belief_deltas
            if delta.proposition == case.proposition
        )
        conflict_delta = _conflict_count(
            replay.counterfactual,
            case.proposition,
        ) - _conflict_count(replay.baseline, case.proposition)
        passed = (
            baseline_present == case.baseline_present
            and thaw_json(baseline_value) == thaw_json(case.baseline_value)
            and counterfactual_present == case.counterfactual_present
            and thaw_json(counterfactual_value) == thaw_json(case.counterfactual_value)
            and belief_changed == case.belief_changed
            and conflict_delta == case.conflict_delta
        )
        results.append(
            ArmbenchPerturbationResult(
                manifest_id=case.manifest.manifest_id,
                manifest_sha256=case.manifest.sha256,
                category=case.category,
                proposition=case.proposition,
                baseline_present=baseline_present,
                baseline_value=baseline_value,
                counterfactual_present=counterfactual_present,
                counterfactual_value=counterfactual_value,
                belief_changed=belief_changed,
                conflict_delta=conflict_delta,
                passed=passed,
            )
        )
    return tuple(results)
