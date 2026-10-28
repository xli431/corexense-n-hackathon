"""Deterministic qualification baseline, not a calibrated failure-belief model."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .lineage import digest
from .models import SOURCES, Decision, Proposal, Snapshot, Verdict


@dataclass(frozen=True)
class Config:
    max_age_ms: int = 250
    min_confidence: float = 0.8
    query_budget: int = 1

    def __post_init__(self) -> None:
        if self.max_age_ms < 0 or not 0 <= self.min_confidence <= 1:
            raise ValueError("invalid gate thresholds")
        if self.query_budget not in (0, 1):
            raise ValueError("v0 fixture supports zero or one acquisition")


def qualify(
    history: list[Snapshot], proposal: Proposal, used_queries: int, config: Config
) -> Decision:
    if proposal.action != "press_button" or proposal.target != "button_A":
        return Decision("HOLD", "action_outside_allowlist")
    if not history:
        return Decision("HOLD", "missing_history")
    latest = history[-1]
    by_source = {o.source: o for o in latest.observations}
    issue = ""
    if set(by_source) != SOURCES:
        issue = "missing_source"
    for o in latest.observations:
        if not o.acquired_ms <= o.received_ms <= latest.now_ms:
            return Decision("HOLD", "invalid_timestamp_order")
        previous = next(
            (
                old
                for snap in reversed(history[:-1])
                for old in snap.observations
                if old.source == o.source
            ),
            None,
        )
        if previous and (
            o.source_frame <= previous.source_frame or o.acquired_ms <= previous.acquired_ms
        ):
            issue = "nonadvancing_source_history"
        if latest.now_ms - o.acquired_ms > config.max_age_ms:
            issue = "stale_source_evidence"
        if not o.supports_action:
            return Decision("HOLD", "current_evidence_contradicts_action")
        if o.confidence < config.min_confidence:
            issue = "uncertain_evidence"
    if len({o.upstream_id for o in latest.observations}) < len(SOURCES):
        issue = issue or "correlated_or_insufficient_sources"
    if issue:
        return Decision("ACQUIRE" if used_queries < config.query_budget else "HOLD", issue)
    return Decision("PROCEED", "local_checks_passed_pending_audit")


def audit_request(snapshot: Snapshot, proposal: Proposal) -> dict:
    """Cloud projection: omit raw data, source IDs, paths, and experiment labels."""
    return {
        "schema": "corexense-n.audit.v1",
        "data_origin": "synthetic",
        "observed_at_ms": snapshot.now_ms,
        "proposal": asdict(proposal),
        "evidence_digest": digest(asdict(snapshot)),
        "independent_source_count": len({o.upstream_id for o in snapshot.observations}),
        "evidence": [
            {
                "source": o.source,
                "age_ms": snapshot.now_ms - o.acquired_ms,
                "confidence": o.confidence,
                "supports_action": o.supports_action,
            }
            for o in snapshot.observations
        ],
    }


def finalize(local: Decision, request: dict, verdicts: list[Verdict], *,
             now_ms: int | None = None, max_age_ms: int = 250) -> Decision:
    if local.action != "PROCEED":
        return local
    if not verdicts:
        return Decision("HOLD", "missing_required_validator")
    for verdict in verdicts:
        if verdict.request_hash != digest(request):
            return Decision("HOLD", "validator_evidence_binding_mismatch")
        if verdict.status != "allow":
            return Decision("HOLD", "validator_" + verdict.status)
    # The caller must supply its trusted clock, never a model-provided timestamp.
    observed = request.get("observed_at_ms")
    if (type(now_ms) is not int or type(observed) is not int or
            type(max_age_ms) is not int or max_age_ms < 0 or now_ms < observed):
        return Decision("HOLD", "invalid_execution_clock")
    evidence = request.get("evidence", [])
    if not evidence:
        return Decision("HOLD", "missing_execution_evidence")
    for item in evidence:
        age = item.get("age_ms")
        if type(age) is not int or age < 0:
            return Decision("HOLD", "invalid_execution_evidence_age")
        if age + now_ms - observed > max_age_ms:
            return Decision("HOLD", "evidence_expired_during_audit")
    return Decision("PROCEED", "local_and_required_validator_checks_passed")

