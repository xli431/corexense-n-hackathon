import json
import os
from pathlib import Path
import subprocess
import sys


def test_injected_nebius_contract_is_not_reported_as_inference(tmp_path):
    root=Path(__file__).resolve().parents[1]
    out=tmp_path/'dry-run'
    result=subprocess.run([sys.executable,str(root/'tools/run_nebius_dry_run.py'),str(out)],
        cwd=root,env=dict(os.environ,PYTHONPATH=str(root/'src')),
        capture_output=True,text=True,timeout=15)
    assert result.returncode==0,result.stderr
    report=json.loads((out/'nebius_dry_run.json').read_text())
    assert report['transport']=='injected_no_network'
    assert report['inference_requests']==report['network_requests']==0
    assert report['credentials_read'] is False
    preview=json.loads((out/'request_preview.json').read_text())
    assert set(preview)=={'path','payload'}
    assert 'Authorization' not in str(preview)
    assert preview['payload']['store'] is False
