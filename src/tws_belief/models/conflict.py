from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .claim import Claim, thaw_json
from .proposition import PropositionKey


class ConflictType(str, Enum):
    VALUE_MISMATCH = "value_mismatch"


class ResolutionStatus(str, Enum):
    UNRESOLVED = "unresolved"
    RESOLVED = "resolved"


class CompatibilityPolicy(Protocol):
    policy_id: str

    def compatible(self, left: Claim, right: Claim) -> bool: ...


class ExactValueCompatibility:
    """v0.1 compatibility: values are compatible only when exactly equal."""

    policy_id = "exact-value-v0.1"

    def compatible(self, left: Claim, right: Claim) -> bool:
        left_json = json.dumps(
            thaw_json(left.value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        right_json = json.dumps(
            thaw_json(right.value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return left_json == right_json


def validity_overlaps(left: Claim, right: Claim) -> bool:
    start = max(left.effective_valid_from, right.effective_valid_from)
    if left.valid_until is None:
        end = right.valid_until
    elif right.valid_until is None:
        end = left.valid_until
    else:
        end = min(left.valid_until, right.valid_until)
    return end is None or start < end


@dataclass(frozen=True, slots=True)
class ClaimConflict:
    conflict_id: str
    proposition: PropositionKey
    claims: tuple[Claim, Claim]
    conflict_type: ConflictType
    resolution_status: ResolutionStatus
    selected_claim: Claim | None
    explanation: str


def detect_conflicts(
    claims: Iterable[Claim],
    compatibility: CompatibilityPolicy | None = None,
) -> tuple[ClaimConflict, ...]:
    """Return deterministic pairwise conflict records without discarding evidence."""

    policy = compatibility or ExactValueCompatibility()
    ordered = sorted(claims, key=lambda claim: claim.claim_id)
    conflicts: list[ClaimConflict] = []
    for index, left in enumerate(ordered):
        for right in ordered[index + 1 :]:
            if left.proposition != right.proposition:
                continue
            if validity_overlaps(left, right) and not policy.compatible(left, right):
                pair = (left.claim_id, right.claim_id)
                digest = hashlib.sha256("\x00".join(pair).encode()).hexdigest()[:16]
                conflicts.append(
                    ClaimConflict(
                        conflict_id=f"conflict-{digest}",
                        proposition=left.proposition,
                        claims=(left, right),
                        conflict_type=ConflictType.VALUE_MISMATCH,
                        resolution_status=ResolutionStatus.UNRESOLVED,
                        selected_claim=None,
                        explanation=(
                            f"{left.claim_id} and {right.claim_id} assert incompatible "
                            f"values under {policy.policy_id} during overlapping validity."
                        ),
                    )
                )
    return tuple(conflicts)
