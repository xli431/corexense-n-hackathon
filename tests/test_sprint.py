import asyncio
import json
import os
from pathlib import Path
import sys

import pytest

from coresense.corexense_n.lineage import Ledger, digest, verify
from coresense.corexense_n.models import Verdict
from coresense.corexense_n.sprint import explain_belief, review_episode, review_simulation_episode
from coresense.corexense_n.validators import MockValidator


def bundle():
    ledger = Ledger()
    event = {'object':'orange','stage':'placed','sim_time':1.2,'position':[0,0,.1]}
    ledger.append('simulation_stage',event)
    return {'data_origin':'simulation','physical_trials':0,'events':[event],
        'terminal_hash':ledger.tip}, ledger.records


def test_decision_time_has_no_future_evidence():
    result = explain_belief('delayed_evidence')
    assert result['snapshots'][0]['state']['effective_beliefs'] == []
    assert result['snapshots'][1]['state']['effective_beliefs'][0]['value'] == 'table'
    assert explain_belief('conflicting_evidence')['snapshots'][1]['state']['conflicts']


def test_delayed_audit_holds_and_trace_binds_request():
    ticks=iter([10.,12.])
    result=review_episode('healthy_lift',validator=MockValidator(),clock=lambda:next(ticks))
    assert result['report']['reason']=='evidence_expired_during_audit'
    assert result['report']['motor_command_sent'] is False
    verify(result['trace'],result['report']['terminal_hash'])
    assert digest(result['trace'][0]['payload'])==result['report']['request_hash']


def test_local_conflict_never_calls_model():
    class Unexpected:
        def evaluate(self, request):
            raise AssertionError('Local rejection should not call a provider')
    assert review_episode('slip',validator=Unexpected())['report']['action']=='HOLD'


def test_unbound_review_cannot_proceed():
    class Wrong:
        def evaluate(self, request):
            return Verdict('test','allow','0'*64,'mock')
    assert review_episode('healthy_lift',validator=Wrong())['report']['reason']=='unbound_model_review'


def test_replay_stays_non_executable_even_when_model_allows():
    report,trace=bundle()
    result=review_simulation_episode(report,trace,validator=MockValidator())
    assert result['report']['semantic_status']=='allow'
    assert result['report']['reason']=='historical_replay_not_executable'
    assert result['report']['action']=='HOLD'
    trace[0]['payload']['stage']='tampered'
    with pytest.raises(ValueError):
        review_simulation_episode(report,trace,validator=MockValidator())


def test_fira_report_cannot_disagree_or_claim_physical_input():
    report,trace=bundle()
    report['events']=[]
    with pytest.raises(ValueError):
        review_simulation_episode(report,trace)
    report,trace=bundle()
    report['data_origin']='real'
    with pytest.raises(ValueError):
        review_simulation_episode(report,trace)


def test_real_mcp_episode_and_belief_exchange():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    async def check():
        env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'),
            COREXENSE_AUDIT_MODE='offline')
        params=StdioServerParameters(command=sys.executable,
            args=['-m','coresense.corexense_n.mcp_server'],env=env)
        async with stdio_client(params) as (reader,writer):
            async with ClientSession(reader,writer) as session:
                await session.initialize()
                result=await session.call_tool('review_episode',{'case':'healthy_lift'})
                assert not result.isError
                data=json.loads(result.content[0].text)
                assert data['report']['validator_mode']=='mock'
                assert data['report']['action']=='PROCEED'
                result=await session.call_tool('explain_belief',{'case':'delayed_evidence'})
                assert not result.isError
                report,trace=bundle()
                result=await session.call_tool('review_simulation_episode',{'report':report,'trace':trace})
                assert not result.isError
                assert json.loads(result.content[0].text)['report']['action']=='HOLD'
                invalid=await session.call_tool('review_episode',{'case':'move_robot'})
                assert invalid.isError
    asyncio.run(asyncio.wait_for(check(),timeout=30))
