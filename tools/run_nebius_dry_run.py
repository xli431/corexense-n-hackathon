"""Exercise the Nebius request/response contract with an injected transport; never network."""
import argparse
import json
from pathlib import Path

from coresense.corexense_n.fruit import run_fruit_fixture
from coresense.corexense_n.lineage import Ledger,digest,verify
from coresense.corexense_n.validators import NebiusValidator


class CaptureTransport:
    def __init__(self):
        self.requests=[]

    def request(self,path,payload):
        assert path=='chat/completions'
        assert payload['model'].startswith('nvidia/')
        self.requests.append({'path':path,'payload':payload})
        bound=json.loads(payload['messages'][1]['content'])
        # This response is a protocol fixture, not an NVIDIA model judgment.
        return {'choices':[{'finish_reason':'stop','message':{'content':json.dumps({
            'verdict':'unknown','request_hash':bound['request_hash']})}}],
            'usage':{'prompt_tokens':0,'completion_tokens':0,'total_tokens':0}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    row,source=run_fruit_fixture('healthy_lift')
    request={'episode_id':'nebius-dry-run','data_origin':'synthetic',
        'stage':row['stage'],'local_decision':row['action'],
        'source_terminal_hash':source.tip,'evidence_events':source.records,
        'authority':'contract_test_only'}
    transport=CaptureTransport()
    verdict=NebiusValidator(transport,'nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B').evaluate(request)
    assert verdict.request_hash==digest(request)
    assert verdict.status=='unknown' and verdict.diagnostic=='model_unknown'
    ledger=Ledger()
    ledger.append('dry_run_request',request)
    ledger.append('injected_transport_response',{'status':verdict.status,
        'request_hash':verdict.request_hash,'diagnostic':verdict.diagnostic,
        'transport':'injected_no_network','actual_model_inference':False})
    report={'status':'request_contract_passed','mode':'dry_run',
        'model_id':transport.requests[0]['payload']['model'],
        'transport':'injected_no_network','network_requests':0,'inference_requests':0,
        'credentials_read':False,'cloud_resources_created':0,'motor_commands_sent':0,
        'request_hash':digest(request),'trace_terminal_hash':ledger.tip,
        'checks':{'request_binding':True,'json_response_validation':True,'trace_integrity':True},
        'not_verified':['Current API authentication','Current model availability',
            'Live model response quality','GPU runtime','Thor access'],
        'adapter_internal_mode_warning':'The adapter labels itself live, but this test injects its transport; no cloud call occurred.'}
    verify(ledger.records,ledger.tip)
    ledger.write(args.output/'trace.jsonl')
    (args.output/'request_preview.json').write_text(json.dumps(transport.requests[0],indent=2)+'\n')
    (args.output/'nebius_dry_run.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
