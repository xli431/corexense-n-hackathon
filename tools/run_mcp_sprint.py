"""Run a real MCP client/server demo; cloud mode requires explicit owner configuration."""
from __future__ import annotations
import argparse
import asyncio
import getpass
import html
import json
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from coresense.corexense_n.validators import NebiusClient
from coresense.corexense_n.lineage import digest, verify


async def run(args, env):
    root=Path(__file__).resolve().parents[1]
    env['PYTHONPATH']=str(root/'src')
    params=StdioServerParameters(command=sys.executable,
        args=['-m','coresense.corexense_n.mcp_server'],env=env)
    results=[]
    async with stdio_client(params) as (reader,writer):
        async with ClientSession(reader,writer) as session:
            await session.initialize()
            listing=await session.list_tools()
            calls=[('review_episode',{'case':c}) for c in ('healthy_lift','slip','stale_recovery')]
            calls += [('explain_belief',{'case':c}) for c in ('delayed_evidence','conflicting_evidence')]
            if args.simulation_episode:
                folder=args.simulation_episode
                files=[folder/'result.json',folder/'trace.jsonl']
                if any(p.stat().st_size>200_000 for p in files):
                    raise ValueError('Simulation bundle too large')
                report=json.loads(files[0].read_text())
                trace=[json.loads(x) for x in files[1].read_text().splitlines()]
                calls += [('review_simulation_episode',{'report':report,'trace':trace})]
            for name,arguments in calls:
                result=await session.call_tool(name,arguments)
                if result.isError:
                    raise ValueError('MCP review failed: '+name)
                payload=json.loads(result.content[0].text)
                if 'trace' in payload:
                    verify(payload['trace'],payload['report']['terminal_hash'])
                results.append({'tool':name,'result':payload})
    args.output.mkdir(parents=True,exist_ok=False)
    source_hashes={str(p.relative_to(root)):digest(p.read_text()) for p in sorted((root/'src').rglob('*.py'))}
    document={'mode':env['COREXENSE_AUDIT_MODE'],'transport':'actual_mcp_stdio',
        'audit_max_tokens':args.audit_max_tokens,
        'physical_trials':0,'tools':[t.name for t in listing.tools],
        'source_hashes':source_hashes,'results':results}
    (args.output/'mcp_report.json').write_text(json.dumps(document,indent=2)+'\n')
    cards=[]
    for row in results:
        data=row['result']; report=data.get('report',{})
        title=report.get('case',report.get('episode_id',data.get('case','Review')))
        body=html.escape(json.dumps(data,indent=2))
        cards.append('<section><h2>'+html.escape(title)+'</h2><p>'+html.escape(
            report.get('action','EXPLAIN')+' — '+report.get('reason','Decision-time evidence reconstruction'))+
            '</p><details><summary>Evidence and trace</summary><pre>'+body+'</pre></details></section>')
    page='<!doctype html><meta charset="utf-8"><title>CoreXense-N MCP review</title>'
    page+='<style>body{font:18px system-ui;max-width:1000px;margin:40px auto;background:#101827;color:#edf3fa}section{padding:20px;margin:20px 0;background:#202d43;border-radius:12px}pre{font-size:13px;white-space:pre-wrap;overflow-wrap:anywhere}summary{cursor:pointer}h1{color:#9fe5c1}</style>'
    page+='<h1>CoreXense-N · MCP Evidence Gateway</h1><p>Recorded review · '+html.escape(env['COREXENSE_AUDIT_MODE'])+' audit · no motor commands · no physical trials</p>'
    page+=''.join(cards)
    (args.output/'review.html').write_text(page)
    print(json.dumps({'status':'completed','mode':env['COREXENSE_AUDIT_MODE'],
        'mcp_tools':len(listing.tools),'reviews':len(results),'output':str(args.output)}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--prompt-key',action='store_true')
    parser.add_argument('--model',help='Exact model ID from the current account catalog')
    parser.add_argument('--audit-max-tokens',type=int,default=256,
        help='Host-controlled output budget, 256..4096; independent experiment setting')
    parser.add_argument('--simulation-episode',type=Path,help='Owner-selected FIRA result.json/trace.jsonl folder')
    args=parser.parse_args()
    if not 256 <= args.audit_max_tokens <= 4096:
        parser.error('Audit output budget must be 256..4096 tokens')
    if args.output.exists():
        parser.error('Choose a new output directory to preserve previous results')
    env=dict(os.environ)
    env['COREXENSE_AUDIT_MODE']='live' if args.live else 'offline'
    env['COREXENSE_AUDIT_MAX_TOKENS']=str(args.audit_max_tokens)
    if args.live:
        key=None
        if args.prompt_key:
            if not sys.stdin.isatty():
                parser.error('Use an interactive terminal for the hidden credential prompt')
            key=getpass.getpass('Nebius Token Factory key (hidden): ')
            if not key:
                parser.error('Empty key; no requests sent')
            env['NEBIUS_API_KEY']=key
        client=NebiusClient(key=key)
        models=[m for m in client.models() if 'nemotron' in m.lower()]
        model=args.model
        if model not in models:
            print(json.dumps({'status':'select_model','available_nemotron_models':models,
                'inference_requests':0}))
            return 2
        env['COREXENSE_NVIDIA_MODEL']=model
    asyncio.run(asyncio.wait_for(run(args,env),timeout=180))
    return 0


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        # Provider exception bodies and environment variables must never be printed.
        print('MCP sprint failed: '+type(error).__name__,file=sys.stderr)
        raise SystemExit(1)
