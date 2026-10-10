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
    body = '''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
    <title>Legal AI · 完整流程工作台</title><style>
    body{font:16px/1.7 system-ui;max-width:1160px;margin:45px auto;padding:0 25px;color:#233441;background:#f7f9fb}
    h1{font-size:32px}a{color:#135f91}.chain{padding:20px;background:#e6eef4;border-radius:8px}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px}
    article{background:white;padding:20px;border:1px solid #d6dfe6;border-radius:9px}small{color:#586877}footer{margin-top:35px}
    </style><h1>Legal AI · 完整流程工作台</h1>
    <p>统一流程实现与历史材料集成交付。8案复用，0次新模型调用，不是新的方法效果实验。</p>
    <div class="chain">来源与任务 → 原始提议导入 → 独立来源参考／研究政策 → 类型化图与审阅队列 → 推导凭据 → 独立检查 → 带出处的分析与版本修正</div>
    <p>图分数不决定法律真值；研究性接受不代表正式法律批准；开放法律评价保留明确假设。
    每案均可从请求点击到规则、前提、原始段落和独立检查记录。</p>
    <p><a href="report-zh.txt">中文报告</a> · <a href="pipeline-inventory.json">完整清单</a> ·
    <a href="case-delivery.csv">逐案交付表</a> · <a href="freeze/implementation-03/config.json">实际冻结版本</a> ·
    <a href="delivery-validation.json">完整性核验</a></p><div class="grid">'''
    for row in rows:
        origin = '保留旧模型原始推导及既有审阅政策' if row['case_id'] in ('789051', '1418721', '1841885') else '保留维护者组装推导；不计为模型自动生成'
        body += '<article><h2><a href="cases/' + row['case_id'] + '/index.html">' + row['case_id'] + '</a></h2><p>' + html.escape(row['name']) + '</p>'
        body += '<p>{premises}项前提 · {rules}个规则版本 · {requests}项请求</p>'.format(**row)
        body += '<p>' + html.escape(str(row['status_counts'])) + '</p><small>' + origin + '</small></article>'
    body += '</div><footer>本地工作台；没有提交或推送。正式法律批准待定。旧输出、原失败及冻结快照保留。</footer></html>'
    (OUT / 'index.html').write_text(body)
    print(json.dumps({'requests': dict(totals), 'cases': len(rows)}, indent=2))


if __name__ == '__main__':
    main()
