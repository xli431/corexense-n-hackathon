"""Validate historical image inputs by default; --run explicitly enables gated GPU inference."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import struct
import time

MODEL = 'nvidia/Cosmos-Reason2-2B'
PROMPT = ('Review only what is visible in this historical robot simulation image. '
    'Return a final JSON object inside <answer>...</answer> with exactly these keys: '
    'visible_state (string), unknowns (list of strings), additional_observations (list of strings). '
    'Do not output motor commands, certify safety, or invent tactile measurements. '
    'Do not include private reasoning in the final answer.')


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_inputs(manifest_path):
    manifest_path=Path(manifest_path).resolve()
    root=manifest_path.parent
    manifest=json.loads(manifest_path.read_text())
    inputs=manifest.get('inputs')
    if not isinstance(inputs,list) or not 1<=len(inputs)<=3:
        raise ValueError('Pilot requires one to three input images')
    rows=[]
    for row in inputs:
        if row.get('data_origin')!='historical_simulation':
            raise ValueError('Only explicitly historical simulation inputs are accepted')
        name=row.get('file')
        if not isinstance(name,str) or Path(name).name!=name or not name.endswith('.png'):
            raise ValueError('Input must be a local PNG basename')
        path=(root/name).resolve()
        if path.parent!=root or not path.is_file() or path.stat().st_size>10_000_000:
            raise ValueError('Invalid, escaping or oversized image')
        if sha256(path)!=row.get('sha256'):
            raise ValueError('Image digest mismatch')
        raw=path.read_bytes()[:24]
        if len(raw)!=24 or raw[:8]!=b'\x89PNG\r\n\x1a\n' or raw[12:16]!=b'IHDR':
            raise ValueError('Invalid PNG header')
        width,height=struct.unpack('>II',raw[16:24])
        if not 0<width<=4096 or not 0<height<=4096:
            raise ValueError('Image dimensions outside pilot limit')
        rows.append({'file':name,'sha256':row['sha256'],'width':width,'height':height})
    if len({r['file'] for r in rows})!=len(rows):
        raise ValueError('Duplicate input image')
    return manifest,rows


def parse_final(text):
    # Do not persist unvalidated reasoning or a truncated reasoning-only completion.
    if '<answer>' not in text or '</answer>' not in text:
        return None,'missing_complete_final_answer'
    body=text.rsplit('<answer>',1)[1].split('</answer>',1)[0].strip()
    try:
        value=json.loads(body)
    except (ValueError,TypeError):
        return None,'malformed_final_json'
    if not isinstance(value,dict) or set(value)!={'visible_state','unknowns','additional_observations'}:
        return None,'invalid_final_schema'
    if not isinstance(value['visible_state'],str) or len(value['visible_state'])>4000:
        return None,'invalid_final_schema'
    for key in ('unknowns','additional_observations'):
        if not isinstance(value[key],list) or len(value[key])>20 or any(not isinstance(v,str) or len(v)>2000 for v in value[key]):
            return None,'invalid_final_schema'
    return value,'validated_final_answer'


def infer(manifest_path,rows,revision,max_tokens):
    import torch
    from transformers import AutoProcessor,Qwen3VLForConditionalGeneration
    from huggingface_hub import HfApi
    if not torch.cuda.is_available():
        raise ValueError('CUDA GPU required; no CPU fallback')
    if torch.cuda.get_device_properties(0).total_memory<24_000_000_000:
        raise ValueError('Pilot follows the official 24 GB minimum; use Thor or a cloud GPU')
    revision=revision or HfApi().model_info(MODEL).sha
    started=time.monotonic()
    processor=AutoProcessor.from_pretrained(MODEL,revision=revision,trust_remote_code=False)
    model=Qwen3VLForConditionalGeneration.from_pretrained(MODEL,revision=revision,
        dtype=torch.bfloat16,device_map='auto',attn_implementation='sdpa',trust_remote_code=False)
    model.eval()
    load_seconds=time.monotonic()-started
    results=[]
    for row in rows:
        path=Path(manifest_path).resolve().parent/row['file']
        messages=[{'role':'user','content':[{'type':'image','image':str(path)},
            {'type':'text','text':PROMPT}]}]
        inputs=processor.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,
            return_dict=True,return_tensors='pt').to(model.device)
        torch.cuda.synchronize()
        start=time.monotonic()
        with torch.inference_mode():
            generated=model.generate(**inputs,do_sample=False,max_new_tokens=max_tokens)
        torch.cuda.synchronize()
        elapsed=(time.monotonic()-start)*1000
        output=generated[:,inputs['input_ids'].shape[1]:]
        text=processor.batch_decode(output,skip_special_tokens=True,clean_up_tokenization_spaces=False)[0]
        final,diagnostic=parse_final(text)
        results.append({**row,'final_answer':final,'diagnostic':diagnostic,
            'output_sha256':hashlib.sha256(text.encode()).hexdigest(),
            'generation_ms':round(elapsed,3),'output_tokens':output.shape[1],
            'hit_token_limit':output.shape[1]>=max_tokens,
            'workflow_action':'HOLD','workflow_reason':'historical_visual_review_not_executable'})
    return {'model_revision':revision,'model_load_seconds':round(load_seconds,3),
        'gpu':torch.cuda.get_device_name(0),'torch_version':torch.__version__,
        'results':results,'model_inference_completed':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run',action='store_true')
    mode.add_argument('--run',action='store_true')
    parser.add_argument('--revision',help='Optional pinned Hugging Face model revision')
    parser.add_argument('--max-new-tokens',type=int,default=4096)
    args=parser.parse_args()
    if args.output.exists():parser.error('Output exists; use a fresh directory')
    if not 256<=args.max_new_tokens<=4096:parser.error('Output budget must be 256..4096 tokens')
    manifest,rows=validate_inputs(args.manifest)
    report={'mode':'inference' if args.run else 'dry_run','model_id':MODEL,
        'episode_id':manifest.get('episode_id'),'source_terminal_hash':manifest.get('source_terminal_hash'),
        'manifest_sha256':sha256(args.manifest),'script_sha256':sha256(Path(__file__)),
        'prompt_sha256':hashlib.sha256(PROMPT.encode()).hexdigest(),
        'input_validation':'passed','inputs':rows,'python':platform.python_version(),
        'dependency_presence':{k:importlib.util.find_spec(k) is not None for k in ('torch','transformers','accelerate','PIL')},
        'access_verified':False,'gpu_inference_verified':False,'model_inference_completed':False,
        'physical_trials':0,'motor_commands_sent':0,'max_new_tokens':args.max_new_tokens}
    args.output.mkdir(parents=True,exist_ok=False)
    error_code=0
    if args.run:
        try:
            report.update(infer(args.manifest,rows,args.revision,args.max_new_tokens))
            report['access_verified']=True
            report['gpu_inference_verified']=True
            if any(r['diagnostic']!='validated_final_answer' or r['hit_token_limit'] for r in report['results']):
                report['review_validation']='incomplete'
                error_code=3
            else:report['review_validation']='passed'
        except Exception as error:
            report['runtime_error_type']=type(error).__name__
            report['review_validation']='failed'
            error_code=2
    else:
        report['next_requirements']=['Owner-approved model access','Compatible Thor/CUDA environment',
            'At least 24 GB GPU memory','Actual weight loading and inference still required']
    (args.output/'cosmos_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'mode':report['mode'],'input_validation':report['input_validation'],
        'model_inference_completed':report['model_inference_completed'],'output':str(args.output),
        'runtime_error_type':report.get('runtime_error_type')}))
    return error_code


if __name__=='__main__':
    raise SystemExit(main())
