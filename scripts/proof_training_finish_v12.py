#!/usr/bin/env python3
"""Finish bookkeeping for the already frozen V12 batch; never generates or fits.

This process only waits for the existing batch status and summarizes saved DEV
predictions. It does not retry training, access TEST, alter labels or publish.
"""
import argparse
import collections
import csv
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'outputs/proof-semantic-search-v12/continuation-02'


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def finish():
    batch = RUN / 'training-01'
    frozen = read(batch / 'training-freeze.json')
    rows = read(RUN / 'supervision-35/rows.json')
    if any(r['split'] not in ('TRAIN', 'DEV') for r in rows):
        raise ValueError('NON_TRAIN_DEV_ROW')
    index = {r['key']: r for r in rows}
    results, cases = [], []
    labels = ['USABLE', 'UNUSABLE', 'UNRESOLVED']
    for kind in ['Flat', 'RGCN', 'CrossEncoder']:
        for seed in frozen['seeds']:
            dest = batch / 'runs' / f'{kind}-{seed}'
            completed = dest / 'training-complete.json'
            reloaded = dest / 'dev-reloaded-predictions.json'
            run = dest / 'run.json'
            failure = dest / 'failure.json'
            result = {'method': kind, 'seed': seed, 'answer': None}
            if completed.exists() and reloaded.exists() and run.exists() and read(run)['status'] == 'OK':
                info = read(completed)
                result.update(status='OK', evaluation=info['evaluation'],
                              seconds=info['seconds'], epochs=info.get('epochs'),
                              reload_verified=True,
                              prediction_sha256=hashlib.sha256(reloaded.read_bytes()).hexdigest())
                counter = collections.defaultdict(collections.Counter)
                confusion = collections.Counter()
                for pred in read(reloaded):
                    row = index[pred['key']]
                    if row['split'] != 'DEV' or not row['valid'] or row['label'] == 'UNLABELED':
                        raise ValueError('INVALID_EVALUATION_ROW')
                    actual = row['label']
                    guess = labels[max(range(3), key=lambda i: pred['probabilities'][i])]
                    c = counter[row['case_id']]
                    c['supervised_uses'] += 1
                    c['reference_agreement'] += actual == guess
                    c['false_accepts'] += actual == 'UNUSABLE' and guess == 'USABLE'
                    c['usable_covered'] += actual == guess == 'USABLE'
                    c['usable_total'] += actual == 'USABLE'
                    c['unresolved_preserved'] += actual == guess == 'UNRESOLVED'
                    confusion[actual + '->' + guess] += 1
                result['confusion'] = dict(confusion)
                for case_id, c in counter.items():
                    cases.append({'method': kind, 'seed': seed, 'case_id': case_id, **dict(c)})
            elif failure.exists():
                result.update(status='TECHNICAL_FAILURE', failure=read(failure))
            elif dest.exists():
                result.update(status='INCOMPLETE_FIT', reason='No completed reloaded prediction; retain all partial files.')
            else:
                result.update(status='SKIPPED', reason='Not started within frozen aggregate budget.')
            results.append(result)

    delivery = []
    for path in sorted((batch / 'delivery').glob('*/*/checked.json')):
        obj = read(path)
        outputs = obj.get('requests', [])
        if isinstance(outputs, dict):
            outputs = list(outputs.values())
        states = collections.Counter(x.get('answer', x.get('state', x.get('status', 'UNRECORDED'))) for x in outputs)
        delivery.append({'method_seed': path.parent.parent.name, 'case_id': path.parent.name,
                         'request_rule_outcomes': dict(states), 'file': str(path.relative_to(ROOT))})
    # Explicitly retain the unlearned cached proposal comparison; no new model.
    summary = {'status': 'FIXED_BATCH_FINISHED', 'planned_fits': 9,
               'successful_fits': sum(x['status'] == 'OK' for x in results),
               'results': results, 'per_case': cases, 'delivery': delivery,
               'cached_proposal_baseline': read(RUN / 'dev-cached-proposal-baseline.json'),
               'reference_kind': 'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD',
               'test_read': False, 'new_legal_answers': 0, 'no_automatic_next_round': True}
    save(RUN / 'training-comparison.json', summary)
    with (RUN / 'training-case-comparison.csv').open('w') as f:
        fields = ['method', 'seed', 'case_id', 'supervised_uses', 'reference_agreement',
                  'false_accepts', 'usable_covered', 'usable_total', 'unresolved_preserved']
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(cases)
    base = (RUN / 'report-zh.md').read_text()
    marker = '## 当前边界与剩余步骤'
    if marker in base:
        base = base.split(marker)[0]
    base = base.replace('（进行中）', '（已结束）').replace(
        'CrossEncoder正在按同一冻结协议运行。',
        'CrossEncoder按同一冻结协议运行的结果及失败均已保存。')
    lines = ['## 固定批次完成记录', '',
             f"九个预定拟合位置中，{summary['successful_fits']}个保存并重载成功；其余失败或未启动位置保留，不替换或重试。", '',
             '| 方法 | 种子 | 技术状态 | 误接受不可用用途 | 可用覆盖（56） | 训练秒数 |',
             '|---|---:|---|---:|---:|---:|']
    for result in results:
        e = result.get('evaluation', {})
        seconds = result.get('seconds', result.get('failure', {}).get('seconds'))
        lines.append(f"| {result['method']} | {result['seed']} | {result['status']} | "
                     f"{e.get('false_accepts', '不可得')} | {e.get('confirmed_usable_predicted', '不可得')} | "
                     f"{round(seconds, 2) if seconds is not None else '不可得'} |")
    outcome_counts = collections.Counter()
    for item in delivery:
        outcome_counts.update(item['request_rule_outcomes'])
    lines += ['', '下游请求×规则候选的状态总计（含各方法、种子重复，不作独立样本）：' + json.dumps(dict(outcome_counts), ensure_ascii=False) + '。',
              '', '暂不扩大图排序，也不自动运行TEST或新完整法律回答。三案DEV参考有限，原提议已高度一致，完整推导存在共同对象连接与开放规则缺口；局部用途指标不足以证明完整法律收益。任何非未知结果仍须核对具体依赖，不能由标签自动认定改善。CrossEncoder与图方法的输入形式和计算成本也不同，不能把差异全部归于图传播。',
              '', '峰值内存未被可靠记录，标为不可得；运行中抽样RSS不作为峰值。所有训练日志、权重、重载预测、失败和下游检查保留本地。无提交或推送。']
    (RUN / 'report-zh.md').write_text(base + '\n'.join(lines) + '\n')
    progress = read(RUN / 'training-progress.json')
    progress.update(status='FIXED_BATCH_FINISHED', successful_fits=summary['successful_fits'],
                    comparison='training-comparison.json', test_read=False)
    save(RUN / 'training-progress.json', progress)
    policy_path = ROOT / 'docs/repository-artifacts.json'
    policy = read(policy_path)
    old_summary = policy['current_review']['summary']
    new_summary = (f"V12固定批次结束：30个TRAIN／722条监督、3个DEV／72条；33条审阅分歧屏蔽，"
                   f"九个拟合位置中{summary['successful_fits']}个保存、重载成功。完整结果与失败保留，"
                   '未运行TEST或新法律回答，暂不扩大图方法；无提交推送。')
    policy['current_review'].update(summary=new_summary, status='FIXED_BATCH_FINISHED')
    save(policy_path, policy)
    state_path = ROOT / 'docs/PROJECT_STATE.json'
    state = read(state_path)
    state['status'] = 'FIXED_BATCH_FINISHED'
    state['current_review'].update(summary=new_summary, status='FIXED_BATCH_FINISHED')
    save(state_path, state)
    for filename in ['README.md', 'docs/EXPERIMENTS.json']:
        path = ROOT / filename
        path.write_text(path.read_text().replace(old_summary, new_summary))
    changelog = ROOT / 'docs/CHANGELOG.md'
    changelog.write_text('## V12固定三方法批次结束\n\n' + new_summary + '\n\n' + changelog.read_text())
    subprocess.run(['python3', 'scripts/repository_bridge.py', 'prepare'], cwd=ROOT, check=True)
    manifest = read(ROOT / 'review/MANIFEST.json')
    public = [x['path'] for x in manifest['source_files']
              if x['path'].startswith('outputs/proof-semantic-search-v12/continuation-02/')]
    bad = [x for x in public if any(s in x for s in ['/browser/', '/qc/', '/raw/', '/generated/',
                                                     '/supervision-', '/training-01/', 'weights.safetensors'])]
    if bad:
        raise ValueError('SENSITIVE_OR_BULK_PUBLICATION:' + repr(bad))
    save(ROOT / '.bridge/v12-publication-inspection-final.json',
         {'snapshot_id': manifest['snapshot_id'], 'sensitive_or_bulk_inclusion': bad,
          'public_files': len(public), 'passed': True, 'submitted_or_pushed': False})
    subprocess.run(['python3', 'scripts/repository_bridge.py', 'verify'], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--wait', action='store_true')
    args = parser.parse_args()
    status = RUN / 'training-01/status.json'
    if args.wait:
        deadline = read(RUN / 'training-01/training-freeze.json')['deadline_unix'] + 600
        while not status.exists():
            if time.time() >= deadline:
                raise TimeoutError('BATCH_TERMINAL_RECORD_NOT_AVAILABLE')
            time.sleep(30)
    if not status.exists():
        raise ValueError('BATCH_STILL_RUNNING')
    if (RUN / 'training-comparison.json').exists():
        raise FileExistsError('FINAL_SUMMARY_ALREADY_EXISTS')
    finish()


if __name__ == '__main__':
    main()
