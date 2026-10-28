import importlib.util
import json
from pathlib import Path
import hashlib
import struct
import pytest

path=Path(__file__).resolve().parents[1]/'tools/run_cosmos_pilot.py'
spec=importlib.util.spec_from_file_location('cosmos_pilot',path)
pilot=importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


def fixture(tmp_path):
    raw=b'\x89PNG\r\n\x1a\n'+b'\0\0\0\rIHDR'+struct.pack('>II',640,480)
    (tmp_path/'image.png').write_bytes(raw)
    row={'file':'image.png','sha256':hashlib.sha256(raw).hexdigest(),'data_origin':'historical_simulation'}
    p=tmp_path/'manifest.json'
    p.write_text(json.dumps({'inputs':[row]}))
    return p,row


def test_manifest_rejects_modified_image(tmp_path):
    p,_=fixture(tmp_path)
    assert pilot.validate_inputs(p)[1][0]['width']==640
    (tmp_path/'image.png').write_bytes(b'modified')
    with pytest.raises(ValueError):pilot.validate_inputs(p)


@pytest.mark.parametrize('field,value',[('file','../image.png'),('file','/tmp/image.png'),('data_origin','real')])
def test_manifest_does_not_admit_other_sources_or_paths(tmp_path,field,value):
    p,row=fixture(tmp_path)
    row[field]=value
    p.write_text(json.dumps({'inputs':[row]}))
    with pytest.raises(ValueError):pilot.validate_inputs(p)


def test_only_final_answer_is_retained():
    text='<think>private reasoning</think><answer>{"visible_state":"object held", "unknowns":["contact force"],"additional_observations":["tactile"]}</answer>'
    final,status=pilot.parse_final(text)
    assert status=='validated_final_answer'
    assert 'private' not in str(final)
    assert pilot.parse_final('<think>unfinished')[0] is None
    assert pilot.parse_final('<answer>{"move_robot":true}</answer>')[0] is None
