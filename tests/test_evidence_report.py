import importlib.util
from pathlib import Path

import pytest

from coresense.corexense_n.sprint import review_episode

spec = importlib.util.spec_from_file_location('evidence_report',
    Path(__file__).resolve().parents[1]/'tools/build_evidence_report.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_report_rejects_tampered_trace(monkeypatch):
    monkeypatch.setenv('COREXENSE_AUDIT_MODE','offline')
    result = review_episode('healthy_lift')
    result['trace'][-1]['payload']['action']='UNRECORDED'
    with pytest.raises(ValueError):
        module.summarize({'mode':'offline','results':[{'result':result}]})


def test_report_retains_origin_and_escapes_labels(monkeypatch):
    monkeypatch.setenv('COREXENSE_AUDIT_MODE','offline')
    summary = module.summarize({'mode':'offline', 'results':[
        {'result':review_episode('slip')}]})
    assert summary['cases'][0]['origin']=='synthetic'
    assert summary['semantic_reviews']==0
    summary['cases'][0]['case']='<script>alert(1)</script>'
    page=module.render(summary)
    assert '<script>' not in page and '&lt;script&gt;' in page


def test_offline_mock_has_no_provider_usage(monkeypatch):
    monkeypatch.setenv('COREXENSE_AUDIT_MODE','offline')
    summary=module.summarize({'mode':'offline','results':[
        {'result':review_episode('healthy_lift')}]})
    assert summary['mode']=='offline'
    assert summary['usage']['total_tokens']==0
