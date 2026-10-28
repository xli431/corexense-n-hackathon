"""Offline evidence-availability ablation, not an action or contact policy."""
from math import isfinite


def qualify(row, policy):
    if policy not in ('vision_only','vision_force','temporal_gate'):
        raise ValueError('Unknown policy')
    if not row['rgb_decodable']:
        return 'HOLD'
    if policy == 'vision_only':
        return 'EVIDENCE_READY'
    force=row.get('force')
    if force is None or len(force)!=6 or not all(isfinite(x) for x in force):
        return 'HOLD'
    if policy == 'vision_force':
        return 'EVIDENCE_READY'
    now=row['decision_ms']
    for field in ('rgb_ms','force_ms'):
        t=row.get(field)
        if t is None or not isfinite(t) or not 0 <= now-t <= 250:
            return 'HOLD'
    return 'EVIDENCE_READY'


def bounded_review(initial, next_observation=None, *, max_wait_ms=250):
    """At most one real subsequent replay observation; never actuates hardware."""
    first=qualify(initial,'temporal_gate')
    if first=='EVIDENCE_READY':
        return dict(qualification=first,queries=0,wait_ms=0,path=[first])
    if next_observation is None:
        return dict(qualification='HOLD',queries=1,wait_ms=0,path=['ACQUIRE','HOLD'],reason='no_next_observation')
    dt=next_observation['decision_ms']-initial['decision_ms']
    if not isfinite(dt) or not 0 < dt <= max_wait_ms:
        return dict(qualification='HOLD',queries=1,wait_ms=0,path=['ACQUIRE','HOLD'],reason='next_observation_outside_deadline')
    final=qualify(next_observation,'temporal_gate')
    return dict(qualification=final,queries=1,wait_ms=dt,path=['ACQUIRE',final],reason='next_observation_evaluated')
