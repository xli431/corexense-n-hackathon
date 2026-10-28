"""Episode-bound review for local MCP demos. No filesystem or actuator authority."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import math
import os
import time

from tws_belief import Claim, ClaimStore, HistoricalReconstructor, PropositionKey

from .fruit import run_fruit_fixture
from .lineage import Ledger, canonical, digest, verify
from .validators import MockValidator, NebiusClient, NebiusValidator


class AuditSession:
    """Cloud is enabled by the host, never by untrusted MCP arguments."""

    def __init__(self):
        self.calls = 0
        self.validator = None

    def evaluate(self, request):
        mode = os.environ.get('COREXENSE_AUDIT_MODE', 'offline')
        if mode not in ('offline', 'live'):
            raise ValueError('Audit mode must be offline or live')
        if mode == 'offline':
            return MockValidator(status='allow').evaluate(request)
        if self.calls >= 10:
            raise ValueError('Live audit budget exhausted; restart explicitly for a new session')
        model = os.environ.get('COREXENSE_NVIDIA_MODEL', '')
        if not model.startswith('nvidia/') or 'nemotron' not in model.lower():
            raise ValueError('Set COREXENSE_NVIDIA_MODEL to an available NVIDIA Nemotron ID')
        if self.validator is None:
            client = NebiusClient(timeout=30)
            if model not in client.models():
                raise ValueError('Configured NVIDIA model is unavailable for this key')
            self.validator = NebiusValidator(client, model,
                max_tokens=int(os.environ.get('COREXENSE_AUDIT_MAX_TOKENS', '256')))
        self.calls += 1
        return self.validator.evaluate(request)


audit_session = AuditSession()


def explain_belief(case: str) -> dict:
    """Independent synthetic TWS-Belief example, never a sensor estimator."""
    if case not in ('delayed_evidence', 'conflicting_evidence'):
        raise ValueError('Unknown belief fixture')
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    def claim(identifier, value, observed, received):
        return Claim(claim_id=identifier, entity_id='orange', predicate='location',
            value=value, confidence=.9, source_id=identifier,
            observation_id='synthetic-'+identifier, event_time=base+timedelta(milliseconds=observed),
            knowledge_time=base+timedelta(milliseconds=received),
            valid_from=base+timedelta(milliseconds=observed), valid_until=None, revision=0)
    claims = [claim('camera_a', 'table', 100, 350)]
    if case == 'conflicting_evidence':
        claims = [claim('camera_a', 'table', 100, 150), claim('camera_b', 'carton', 120, 350)]
    store = HistoricalReconstructor(ClaimStore(claims))
    key = PropositionKey('orange', 'location')
    snapshots = []
    for ms in (250, 400):
        state = store.reconstruct(base+timedelta(milliseconds=ms))
        snapshots.append({'decision_time_ms': ms, 'state': state.to_dict(),
            'explanation': state.explain(key).format_human() if state.get(key) else 'No evidence received yet'})
    return {'case':case, 'data_origin':'synthetic', 'snapshots':snapshots,
        'physical_execution':False, 'cloud_inference':False,
        'meaning':'Deterministic ranking and historical reconstruction, not physical ground truth or calibrated probability'}


def review_episode(case: str, *, validator=None, clock=None) -> dict:
    """Review a synthetic episode with one bound semantic call after local qualification."""
    report, source_ledger = run_fruit_fixture(case)
    episode_id = 'synthetic-fruit-'+case
    request = {'episode_id':episode_id, 'data_origin':'synthetic',
        'stage':report['stage'], 'local_decision':report['action'],
        'source_terminal_hash':source_ledger.tip, 'evidence_events':source_ledger.records,
        'authority':'synthetic_review_only'}
    ledger = Ledger()
    ledger.append('review_request', request)
    verdict = None
    elapsed = 0.0
    action, reason = report['action'], report['reason']
    if action == 'PROCEED':
        timer = clock or time.monotonic
        started = timer()
        verdict = (validator or audit_session).evaluate(request)
        elapsed = (timer()-started)*1000
        ledger.append('semantic_review', asdict(verdict))
        if verdict.request_hash != digest(request):
            action, reason = 'HOLD', 'unbound_model_review'
        elif verdict.status != 'allow':
            action, reason = 'HOLD', 'semantic_review_not_allow'
        elif not math.isfinite(elapsed) or elapsed < 0 or elapsed > 250:
            action, reason = 'HOLD', 'evidence_expired_during_audit'
    final = {'episode_id':episode_id, 'case':case, 'stage':report['stage'],
        'action':action, 'reason':reason, 'local_action':report['action'],
        'queries':report['queries'], 'data_origin':'synthetic',
        'validator_mode':verdict.mode if verdict else 'not_called',
        'model':verdict.model if verdict else None, 'audit_elapsed_ms':round(elapsed,3),
        'request_hash':digest(request), 'source_terminal_hash':source_ledger.tip,
        'semantic_status':verdict.status if verdict else 'not_called',
        'motor_command_sent':False, 'physical_outcome':'not_run',
        'clock_scope':'Synthetic observation is defined at review start; elapsed audit is measured locally'}
    ledger.append('review_decision', final)
    final['terminal_hash'] = ledger.tip
    verify(ledger.records, ledger.tip)
    return {'report':final, 'trace':ledger.records, 'source_trace':source_ledger.records}


def review_simulation_episode(report: dict, trace: list[dict], *, validator=None) -> dict:
    """Bind an owner's supplied FIRA replay to a semantic audit, never authorize replay execution."""
    if len(canonical({'report':report, 'trace':trace})) > 200_000:
        raise ValueError('Episode exceeds review size limit')
    if report.get('data_origin') != 'simulation' or type(report.get('physical_trials')) is not int or report['physical_trials'] != 0:
        raise ValueError('Only simulation replay bundles are accepted')
    tip = report.get('terminal_hash')
    if not isinstance(tip, str) or len(tip) != 64 or not trace:
        raise ValueError('Non-empty trace and terminal hash are required')
    verify(trace, tip)
    if any(row['kind'] != 'simulation_stage' for row in trace):
        raise ValueError('Unexpected FIRA trace kind')
    if report.get('events') != [row['payload'] for row in trace]:
        raise ValueError('Report and trace disagree')
    # Only a minimal allowlisted projection reaches the provider, never arbitrary report fields.
    events = []
    for row in report['events']:
        obj, stage = row.get('object'), row.get('stage')
        if not isinstance(obj, str) or not obj.isascii() or not obj.replace('_','').isalnum() or len(obj)>40:
            raise ValueError('Invalid object label')
        if not isinstance(stage, str) or not stage.isascii() or not stage.replace('_','').isalnum() or len(stage)>60:
            raise ValueError('Invalid stage label')
        events.append({'object':obj, 'stage':stage})
    request = {'episode_id':'fira-'+tip[:16], 'data_origin':'simulation_replay',
        'source_terminal_hash':tip, 'events':events,
        'authority':'Historical semantic review only; never current execution permission',
        'limitations':['privileged_simulator_pose','unvalidated_dynamics','no_real_tactile']}
    ledger = Ledger()
    ledger.append('review_request',request)
    started = time.monotonic()
    verdict = (validator or audit_session).evaluate(request)
    elapsed = (time.monotonic()-started)*1000
    ledger.append('semantic_review',asdict(verdict))
    bound = verdict.request_hash == digest(request)
    final = {'episode_id':request['episode_id'], 'data_origin':'simulation_replay',
        'action':'HOLD', 'reason':'historical_replay_not_executable',
        'semantic_status':verdict.status if bound else 'unknown',
        'validator_mode':verdict.mode, 'model':verdict.model,
        'audit_elapsed_ms':round(elapsed,3), 'request_hash':digest(request),
        'source_terminal_hash':tip, 'motor_command_sent':False, 'physical_trials':0,
        'integrity_scope':'Self-consistent bundle; publisher authenticity not established'}
    ledger.append('review_decision',final)
    final['terminal_hash']=ledger.tip
    verify(ledger.records,ledger.tip)
    return {'report':final, 'trace':ledger.records}
