from dataclasses import replace
import pytest
from coresense.corexense_n.fruit import FruitEvidence, qualify_fruit, run_fruit_fixture
from coresense.corexense_n.lineage import verify


@pytest.mark.parametrize('case,expected,queries',[
 ('healthy_lift','PROCEED',0),('stale_recovery','PROCEED',1),
 ('missing_tactile','HOLD',1),('slip','HOLD',0),
 ('release_unverified','HOLD',1),('real_input_blocked','HOLD',0)])
def test_fixture(case,expected,queries):
    row,ledger=run_fruit_fixture(case)
    assert (row['action'],row['queries']) == (expected,queries)
    assert row['motor_command_sent'] is False
    verify(ledger.records,row['terminal_hash'])


@pytest.mark.parametrize('changes',[
 {'clock_verified':False},{'calibration_verified':False},{'target_visible':'yes'},
 {'observed_ms':1001},{'data_origin':'real'},{'workspace_clear':False}])
def test_invalid_evidence_never_proceeds(changes):
    decision=qualify_fruit('approach',replace(FruitEvidence(1000),**changes),now_ms=1000)
    assert decision.action == 'HOLD'


def test_stage_and_budget_bounds():
    e=FruitEvidence(1000)
    assert qualify_fruit('start_motor',e,now_ms=1000).action=='HOLD'
    assert qualify_fruit('lift',e,now_ms=1000,query_budget=2).action=='HOLD'
    assert qualify_fruit('lift',e,now_ms=1000,queries_used=1).action=='HOLD'
