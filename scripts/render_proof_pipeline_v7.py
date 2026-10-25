"""Render the integrated delivery catalog, without generating legal analysis."""
import csv
import html
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/proof-carrying-pipeline-v7'


def main():
    rows, totals = [], Counter()
    for item in json.loads((OUT / 'run-plan.json').read_text())['cases']:
        cid = item['case_id']; folder = OUT / 'cases' / cid
        load = lambda name: json.loads((folder / name).read_text())
        spec, result, graph = load('spec.json'), load('checker-result.json'), load('graph.json')
        facts, rules = load('stages/facts/usable.json'), load('stages/rules/usable.json')
        counts = Counter(q['draft_status'] for q in result['requests']); totals.update(counts)
        rows.append({'case_id': cid, 'name': spec['name'], 'premises': len(facts['premises']),
            'rules': len(rules['rules']), 'requests': len(result['requests']),
            'signed_relations': len(facts['relations']), 'nodes': len(graph['nodes']),
            'edges': len(graph['edges']), 'dangling_edges': len(graph['dangling']),
            'status_counts': dict(counts), 'origin': spec['proposal_origin'],
            'new_model_calls': 0, 'formal_approval': 'PENDING'})
    inventory = {'cases': rows, 'requests': dict(totals), 'new_experiment': False, 'new_model_calls': 0}
    (OUT / 'pipeline-inventory.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n')
    with (OUT / 'case-delivery.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    body = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
    <title>Legal AI · Full Workflow Workbench</title><style>
    body{font:16px/1.7 system-ui;max-width:1160px;margin:45px auto;padding:0 25px;color:#233441;background:#f7f9fb}
    h1{font-size:32px}a{color:#135f91}.chain{padding:20px;background:#e6eef4;border-radius:8px}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px}
    article{background:white;padding:20px;border:1px solid #d6dfe6;border-radius:9px}small{color:#586877}footer{margin-top:35px}
    </style><h1>Legal AI · Full Workflow Workbench</h1>
    <p>Integrated workflow and historical-material delivery. Eight reused cases, zero new model calls; this is not a new method-effectiveness experiment.</p>
    <div class="chain">Sources and tasks → raw proposal import → independent source references / research policy → typed graphs and review queues → derivation credentials → independent checking → source-linked analysis and version correction</div>
    <p>Graph scores do not determine legal truth. Research acceptance is not formal legal approval. Open legal assessments retain explicit assumptions.
    For each case, follow requests to rules, premises, original passages, and independent checks.</p>
    <p><a href="report-zh.txt">Report</a> · <a href="pipeline-inventory.json">Complete inventory</a> ·
    <a href="case-delivery.csv">Case delivery table</a> · <a href="freeze/implementation-03/config.json">Actual frozen version</a> ·
    <a href="delivery-validation.json">Integrity checks</a></p><div class="grid">'''
    for row in rows:
        origin = 'Original model derivations and existing review policy retained' if row['case_id'] in ('789051', '1418721', '1841885') else 'Maintainer-assembled derivations retained; not counted as automatic model generation'
        body += '<article><h2><a href="cases/' + row['case_id'] + '/index.html">' + row['case_id'] + '</a></h2><p>' + html.escape(row['name']) + '</p>'
        body += '<p>{premises} premises · {rules} rule versions · {requests} requests</p>'.format(**row)
        body += '<p>' + html.escape(str(row['status_counts'])) + '</p><small>' + origin + '</small></article>'
    body += '</div><footer>Local workbench; no commit or push. Formal legal approval pending. Old outputs, original failures, and frozen snapshots retained.</footer></html>'
    (OUT / 'index.html').write_text(body)
    print(json.dumps({'requests': dict(totals), 'cases': len(rows)}, indent=2))


if __name__ == '__main__':
    main()
