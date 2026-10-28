"""Controlled synthetic fixtures; oracle labels never enter the policy or cloud request."""

from __future__ import annotations

import random
from dataclasses import dataclass, field, replace

from .models import Observation, Proposal, Snapshot


@dataclass(frozen=True)
class Case:
    name: str
    seed: int
    prior: Snapshot
    initial: Snapshot
    followup: Snapshot
    supported_initial: bool
    supported_followup: bool
    proposal: Proposal = field(default_factory=Proposal)
    mock_status: str = "allow"


def make_cases(seed: int) -> list[Case]:
    rng = random.Random(seed)
    confidence = round(rng.uniform(0.85, 0.99), 4)

    def snapshot(now: int, frame: int) -> Snapshot:
        return Snapshot(
            now,
            tuple(
                Observation(
                    source, frame, now - 20, now - 5, confidence, True, source + "-upstream"
                )
                for source in ("camera", "joint_state")
            ),
        )

    prior, initial, followup = snapshot(900, 1), snapshot(1000, 2), snapshot(1100, 3)

    def camera(snap: Snapshot, **changes) -> Snapshot:
        return replace(
            snap, observations=(replace(snap.observations[0], **changes), snap.observations[1])
        )

    stale = camera(initial, acquired_ms=100, source_frame=1)
    stale_followup = camera(followup, acquired_ms=100, source_frame=1)
    # Latest packet is IDENTICAL to healthy; only the source history differs.
    restamped_prior = camera(prior, source_frame=2)
    restamped = initial
    restamped_followup = camera(followup, source_frame=2)
    correlated = camera(initial, upstream_id="joint_state-upstream")
    correlated_followup = camera(followup, upstream_id="joint_state-upstream")
    missing = replace(initial, observations=(initial.observations[1],))
    missing_followup = replace(followup, observations=(followup.observations[1],))
    return [
        Case("healthy", seed, prior, initial, followup, True, True),
        Case("camera_freeze", seed, prior, stale, stale_followup, False, False),
        # Same observed stale packets, but privileged simulator truth says the scene
        # stayed unchanged. The policy cannot know that and conservatively holds.
        Case("stationary_stale_control", seed, prior, stale, stale_followup, True, True),
        Case(
            "restamped_freeze", seed, restamped_prior, restamped, restamped_followup, False, False
        ),
        Case("correlated_sources", seed, prior, correlated, correlated_followup, False, False),
        Case(
            "target_moved",
            seed,
            prior,
            camera(initial, supports_action=False),
            camera(followup, supports_action=False),
            False,
            False,
        ),
        Case("camera_dropout", seed, prior, missing, missing_followup, False, False),
        Case("freeze_recovery", seed, prior, stale, followup, False, True),
        Case(
            "uncertainty_recovery",
            seed,
            prior,
            camera(initial, confidence=0.5),
            followup,
            False,
            True,
        ),
        Case(
            "validator_reject", seed, prior, initial, followup, False, False, mock_status="reject"
        ),
        Case(
            "validator_unavailable",
            seed,
            prior,
            initial,
            followup,
            False,
            False,
            mock_status="unknown",
        ),
        Case(
            "disallowed_action",
            seed,
            prior,
            initial,
            followup,
            False,
            False,
            proposal=Proposal("move_joint", "button_A"),
        ),
    ]

