"""Create a shareable review summary from a completed MCP report; no cloud calls."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path

from coresense.corexense_n.lineage import verify


def summarize(document):
    if document.get('mode') not in ('live', 'offline'):
        raise ValueError('Report must declare live or offline mode')
    rows = []
    usage = dict(prompt_tokens=0, completion_tokens=0, total_tokens=0)
    for entry in document['results']:
        result = entry['result']
        report = result.get('report')
        if not report:
            continue
        verify(result['trace'], report['terminal_hash'])
        audits = [event['payload'] for event in result['trace']
                  if event['kind'] == 'semantic_review']
        for audit in audits:
            recorded_usage = audit.get('usage') or {}
            if not isinstance(recorded_usage, dict):
                raise ValueError('Invalid token accounting')
            for key in usage:
                value = recorded_usage.get(key, 0)
                if type(value) is not int or value < 0:
                    raise ValueError('Invalid token accounting')
                usage[key] += value
        rows.append(dict(case=report.get('case', report.get('episode_id')),
            origin=report.get('data_origin'), action=report['action'],
            reason=report['reason'], source_terminal_hash=report['source_terminal_hash'],
            terminal_hash=report['terminal_hash'], audit_elapsed_ms=report.get('audit_elapsed_ms'),
            audits=audits))
    if not rows:
        raise ValueError('No verifiable reviews')
    return dict(mode=document['mode'], trace_verification='passed', cases=rows,
        usage=usage, audit_max_tokens=document.get('audit_max_tokens', 'not_recorded'),
        semantic_reviews=sum(len(row['audits']) for row in rows),
        scope='Synthetic evidence and historical simulation review; no physical success measurement')


def render(summary):
    esc = lambda value: html.escape(str(value))
    titles = {'healthy_lift':'Synthetic lift evidence',
        'slip':'A local conflict stopped the review',
        'stale_recovery':'Model approval arrived after evidence expired'}
    reasons = {'semantic_review_not_allow':'A complete, valid model approval was not available.',
        'workspace_or_slip_conflict':'The evidence reported a workspace or slip conflict.',
        'evidence_expired_during_audit':'The model approved, but the supporting observation was no longer current.',
        'historical_replay_not_executable':'A historical replay cannot authorize a current action.'}
    origins = {'synthetic':'Synthetic test observations','simulation_replay':'Historical simulation record'}
    cards = []
    for row in summary['cases']:
        audits = row['audits']
        audit = audits[-1] if audits else {}
        title = titles.get(row['case'], 'Historical FIRA replay' if row['origin']=='simulation_replay' else row['case'])
        cards.append('<article><h2>'+esc(title)+'</h2><p class="decision">'
            +esc(row['action'])+'</p><p>'+esc(reasons.get(row['reason'],row['reason']))+'</p><dl>'
            +'<dt>Input origin</dt><dd>'+esc(origins.get(row['origin'],row['origin']))+'</dd>'
            +'<dt>Model verdict</dt><dd>'+esc(audit.get('status', 'not_called'))+'</dd>'
            +'<dt>Response diagnostic</dt><dd>'+esc(audit.get('diagnostic', 'not_recorded'))+'</dd>'
            +'<dt>Audit elapsed (ms)</dt><dd>'+esc(row['audit_elapsed_ms'])+'</dd></dl>'
            +'<details><summary>Evidence identity and recorded audit</summary><pre>'
            +esc(json.dumps(row, indent=2))+'</pre></details></article>')
    return ('<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>CoreXense-N · Verified evidence review</title><style>'
        'body{font:17px system-ui;background:#101827;color:#edf3fa;max-width:1080px;margin:40px auto;padding:0 20px}'
        'h1{color:#9fe5c1}article{background:#202d43;padding:24px;border-radius:14px;margin:18px 0}'
        '.decision{font-size:26px;font-weight:bold;color:#ffd18a}dt{color:#b4c3d8}dd{margin:0 0 12px}'
        'pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}summary{cursor:pointer}'
        '</style><h1>CoreXense-N</h1><p>An MCP Evidence Gateway for Physical AI</p>'
        '<p>Recorded '+esc(summary['mode'])+' run · hash chains verified · no actuator interface</p>'
        '<p>'+esc(summary['scope'])+'</p><p>Measured semantic reviews: '
        +esc(summary['semantic_reviews'])+' · tokens present in recorded usage: '+esc(summary['usage']['total_tokens'])
        +'</p>'+''.join(cards)+'<footer>SKAI scene asset loading, Cosmos GPU inference and '
        'robot-learning improvements are separate milestones; this report does not establish them.</footer></html>')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Use a new output directory')
    raw = args.report.read_bytes()
    summary = summarize(json.loads(raw))
    summary['source_report_sha256'] = hashlib.sha256(raw).hexdigest()
    args.output.mkdir(parents=True)
    (args.output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    (args.output/'index.html').write_text(render(summary))
    print(json.dumps({'status':'completed', 'trace_verification':'passed',
        'output':str(args.output), 'network_requests':0}))


if __name__ == '__main__':
    main()
