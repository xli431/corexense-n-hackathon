import pytest
from coresense.corexense_n.replay_quality import qualify

def frame(**kw):
 return dict(rgb_decodable=True,rgb_ms=1000,force_ms=1000,decision_ms=1000,force=[0.]*6,**kw)

@pytest.mark.parametrize('stamp,expected',[(750,'EVIDENCE_READY'),(749,'HOLD'),(1001,'HOLD')])
def test_age_boundary_and_future(stamp,expected):
 r=frame();r['force_ms']=stamp
 assert qualify(r,'temporal_gate')==expected

def test_numeric_corruption_is_not_contact_evidence():
 r=frame();r['force'][2]=float('nan')
 assert qualify(r,'vision_force')=='HOLD'
 assert qualify(r,'temporal_gate')=='HOLD'

def test_vision_only_is_an_explicit_limited_baseline():
 r=frame();r['force']=None
 assert qualify(r,'vision_only')=='EVIDENCE_READY'
 assert qualify(r,'temporal_gate')=='HOLD'

def test_policy_name_is_not_silently_defaulted():
 with pytest.raises(ValueError):qualify(frame(),'unknown')

from coresense.corexense_n.replay_quality import bounded_review

def test_recovery_uses_new_observation_once():
 a=frame();a['rgb_decodable']=False
 b=frame();b.update(rgb_ms=1100,force_ms=1099,decision_ms=1100)
 r=bounded_review(a,b)
 assert (r['qualification'],r['queries'],r['wait_ms'])==('EVIDENCE_READY',1,100)

def test_persistent_failure_stops_after_one_query():
 a=frame();a['force']=None
 b=dict(a,decision_ms=1100,rgb_ms=1100)
 r=bounded_review(a,b)
 assert r['path']==['ACQUIRE','HOLD'] and r['queries']==1

@pytest.mark.parametrize('t',[1000,999,1251])
def test_recovery_cannot_reuse_old_frame_or_wait_forever(t):
 a=frame();a['rgb_decodable']=False
 b=frame();b.update(rgb_ms=t,force_ms=t,decision_ms=t)
 assert bounded_review(a,b)['qualification']=='HOLD'
