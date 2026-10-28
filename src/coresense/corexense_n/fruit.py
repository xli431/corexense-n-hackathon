"""Fruit-stage evidence contract. Synthetic decision tests, no robot executor."""
from dataclasses import asdict, dataclass, replace
from .lineage import Ledger
from .models import Decision

STAGES = ('approach', 'close', 'lift', 'transfer', 'release')
SOURCES = {'oak_rgb', 'd405_rgbd', 'joint_state', 'xense'}


@dataclass(frozen=True)
class FruitEvidence:
    observed_ms: int
    sources: tuple[str, ...] = tuple(sorted(SOURCES))
    clock_verified: bool = True
    calibration_verified: bool = True
    target_visible: bool = True
    workspace_clear: bool = True
    contact_verified: bool = False
    slip_detected: bool = False
    release_zone_verified: bool = False
    data_origin: str = 'synthetic'


def qualify_fruit(stage: str, evidence: FruitEvidence, *, now_ms: int,
                  queries_used: int = 0, query_budget: int = 1) -> Decision:
    """Returns a decision only. Caller-provided booleans are not sensor estimators."""
    if stage not in STAGES:
        return Decision('HOLD', 'action_outside_allowlist')
    if any(type(v) is not int or v < 0 for v in
           (now_ms, evidence.observed_ms, queries_used, query_budget)) or query_budget > 1 or queries_used > query_budget:
        return Decision('HOLD', 'invalid_clock_or_budget')
    if evidence.data_origin != 'synthetic':
        return Decision('HOLD', 'physical_adapter_not_commissioned')
    flags = (evidence.clock_verified, evidence.calibration_verified,
             evidence.target_visible, evidence.workspace_clear, evidence.contact_verified,
             evidence.slip_detected, evidence.release_zone_verified)
    if any(type(v) is not bool for v in flags):
        return Decision('HOLD', 'invalid_evidence_flag')
    if not evidence.clock_verified or not evidence.calibration_verified:
        return Decision('HOLD', 'unverified_clock_or_calibration')
    if now_ms < evidence.observed_ms:
        return Decision('HOLD', 'future_observation')
    if not evidence.workspace_clear or evidence.slip_detected:
        return Decision('HOLD', 'workspace_or_slip_conflict')
    issue = None
    if len(evidence.sources) != len(SOURCES) or set(evidence.sources) != SOURCES:
        issue = 'missing_or_duplicate_source'
    elif now_ms - evidence.observed_ms > 250:
        issue = 'stale_evidence'
    elif not evidence.target_visible:
        issue = 'target_not_visible'
    elif stage in ('lift', 'transfer') and not evidence.contact_verified:
        issue = 'contact_not_verified'
    elif stage == 'release' and not evidence.release_zone_verified:
        issue = 'release_zone_not_verified'
    if issue:
        return Decision('ACQUIRE' if queries_used < query_budget else 'HOLD', issue)
    return Decision('PROCEED', 'synthetic_stage_evidence_supported')


def run_fruit_fixture(case: str) -> tuple[dict, Ledger]:
    normal = FruitEvidence(1000, contact_verified=True, release_zone_verified=True)
    cases = {
        'healthy_lift': ('lift', normal, None),
        'stale_recovery': ('lift', replace(normal, observed_ms=500), normal),
        'missing_tactile': ('lift', replace(normal, sources=('oak_rgb','d405_rgbd','joint_state')), None),
        'slip': ('transfer', replace(normal, slip_detected=True), None),
        'release_unverified': ('release', replace(normal, release_zone_verified=False), None),
        'real_input_blocked': ('lift', replace(normal, data_origin='real'), None),
    }
    if case not in cases:
        raise ValueError('Unknown fixture')
    stage, evidence, recovery = cases[case]
    ledger = Ledger()
    queries = 0
    while True:
        ledger.append('fruit_evidence', asdict(evidence))
        decision = qualify_fruit(stage, evidence, now_ms=1000, queries_used=queries)
        ledger.append('fruit_decision', {'stage':stage, **asdict(decision), 'motor_command_sent':False})
        if decision.action != 'ACQUIRE':
            break
        queries += 1
        evidence = recovery or evidence
    return {'case':case, 'stage':stage, **asdict(decision), 'queries':queries,
            'data_origin':'synthetic', 'validator_mode':'not_used',
            'motor_command_sent':False, 'physical_outcome':'not_run', 'terminal_hash':ledger.tip}, ledger


CASES = ('healthy_lift','stale_recovery','missing_tactile','slip','release_unverified','real_input_blocked')
