import json
from urllib.error import HTTPError

import pytest

from coresense.corexense_n.lineage import digest
from coresense.corexense_n.validators import NebiusValidator


@pytest.mark.parametrize('kind,expected',[
    ('unknown','model_unknown'),('truncated','truncated_completion'),
    ('malformed','malformed_json'),('empty','empty_or_nontext_content'),
    ('wrong_hash','invalid_verdict_schema'),('http','http_error')])
def test_diagnostic_distinguishes_unknown_from_invalid_response(kind,expected):
    request={'data_origin':'synthetic'}
    class Client:
        def request(self,path,payload):
            if kind=='http':
                raise HTTPError('https://invalid.example',429,'private body must not be recorded',{},None)
            content=json.dumps({'verdict':'unknown','request_hash':digest(request)})
            if kind=='malformed': content='private invalid output'
            if kind=='empty': content=None
            if kind=='wrong_hash':content=json.dumps({'verdict':'allow','request_hash':'0'*64})
            return {'choices':[{'finish_reason':'length' if kind=='truncated' else 'stop',
                'message':{'content':content}}],
                'usage':{'prompt_tokens':100,'completion_tokens':20,'total_tokens':120,
                         'untrusted_metadata':'not retained'}}
    verdict=NebiusValidator(Client(),'nvidia/test').evaluate(request)
    assert verdict.status=='unknown'
    assert verdict.diagnostic==expected
    assert 'private' not in str(verdict)
    if kind=='http':assert verdict.http_status==429
    else:assert verdict.usage=={'prompt_tokens':100,'completion_tokens':20,'total_tokens':120}


def test_larger_budget_keeps_truncated_response_unknown():
    class Client:
        def request(self,path,payload):
            assert payload['max_tokens']==1024
            return {'choices':[{'finish_reason':'length','message':{
                'content':json.dumps({'verdict':'allow','request_hash':digest({})})}}]}
    verdict=NebiusValidator(Client(),'nvidia/test',max_tokens=1024).evaluate({})
    assert verdict.status=='unknown'
    assert verdict.diagnostic=='truncated_completion'


@pytest.mark.parametrize('budget',[0,255,4097,True,'1024'])
def test_invalid_output_budget_rejected_before_network(budget):
    with pytest.raises(ValueError):
        NebiusValidator(None,'nvidia/test',max_tokens=budget)
