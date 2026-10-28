from dataclasses import replace
import pytest
from coresense.corexense_n.fixtures import make_cases
from coresense.corexense_n.gate import Config, qualify, audit_request, finalize
from coresense.corexense_n.validators import MockValidator


@pytest.mark.parametrize('clock,expected', [(None,'HOLD'), (999,'HOLD'),
    (1000,'PROCEED'), (1230,'PROCEED'), (1231,'HOLD'), (3000,'HOLD'), (True,'HOLD')])
def test_execution_clock_boundary(clock, expected):
    case = make_cases(0)[0]
    local = qualify([case.prior,case.initial],case.proposal,0,Config())
    request = audit_request(case.initial,case.proposal)
    verdict = MockValidator().evaluate(request)
    assert finalize(local,request,[verdict],now_ms=clock).action == expected


def test_changed_observation_invalidates_review():
    case = make_cases(0)[0]
    request = audit_request(case.initial,case.proposal)
    verdict = MockValidator().evaluate(request)
    changed = audit_request(case.followup,case.proposal)
    local = qualify([case.initial,case.followup],case.proposal,0,Config())
    assert finalize(local,changed,[verdict],now_ms=1100).reason == 'validator_evidence_binding_mismatch'


def test_runner_measures_audit_delay_independently(monkeypatch):
    from coresense.corexense_n.experiment import run_case
    from coresense.corexense_n.lineage import Ledger
    class SlowAdapter:
        def evaluate(self, request):
            # A dishonest/incorrect zero latency cannot bypass the caller's clock.
            return replace(MockValidator().evaluate(request), mode='live', latency_ms=0)
    ticks=iter([0,2_000_000_000])
    monkeypatch.setattr('coresense.corexense_n.experiment.time.monotonic_ns',lambda: next(ticks))
    result=run_case(make_cases(0)[0],'corexense_n',Config(),Ledger(),[SlowAdapter()])
    assert result['decision']=='HOLD'
    assert result['reason']=='evidence_expired_during_audit'
