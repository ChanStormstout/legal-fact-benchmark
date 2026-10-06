"""Complete a stopped data-contract round without fitting or reading SEALED bodies."""
import collections
import csv
import datetime
import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
R = Path('outputs/rgcn-dev-contract-repair-10')

def read(p):
    return json.loads(Path(p).read_text())

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def save(name, value):
    p = R / name
    if p.exists():
        if read(p) == value:
            return
        raise FileExistsError(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def run():
    protocol = read(R/'protocol.json')
    assert not read(R/'readiness.json')['training_allowed']
    train = read(R/'import-report-TRAIN.json')
    dev = read(R/'import-report-DEV.json')
    ranking = read(R/'saved-ranking-reevaluation.json')
    totals = lambda rows: {s: sum(x['slots'][s] for x in rows) for s in ['KNOWN', 'UNKNOWN', 'ISOLATED', 'UNPROCESSED']}
    reviews = [x for p in sorted((R/'web').glob('TRAIN*.raw.json')) for x in read(p)['reviews']]
    changes = read(R/'train-location-changes.json')
    summaries = []
    for seed in protocol['training_settings']['seeds']:
        for method in ['S', 'B', 'C']:
            rows = [x for x in ranking if x['seed'] == seed and x['method'] == method]
            sums = lambda group, key: [sum(x[group][key][i] for x in rows) for i in range(2)]
            summaries.append(dict(seed=seed, method=method,
                legacy_core=[sum(x['legacy_metrics']['core_delivered'][i] for x in rows) for i in range(2)],
                fixed_historical_core=sums('same_historical_reference_fixed_mapping_material', 'core_delivered'),
                expanded_core=sums('expanded_all30_reference', 'core_delivered'),
                feasible_core=sums('expanded_all30_reference', 'feasible_core_delivered'),
                document_core=sums('expanded_all30_reference', 'core_document_delivered'),
                irrelevant_selected=sum(len(x['expanded_all30_reference']['known_irrelevant_selected']) for x in rows),
                unknown_selected=sum(len(x['expanded_all30_reference']['unknown_selected']) for x in rows),
                selection_changes=sum(x['old_selected_ids'] != x['new_selected_ids'] for x in rows)))
    save('reevaluation-summary.json', summaries)
    rows = read(R/'cohort-status-precompletion.json')['rows']
    for row in rows:
        if row['split'] == 'DEVELOPMENT':
            c = row['case_id']; q = next(x for x in dev if x['case_id'] == c)
            row.update(current_status='ALL30_ALIGNMENT_AND_MODEL_SOURCE_REVIEW_COMPLETE; NOT_HUMAN_GOLD',
                       label_states=q['slots'], label_path=str(R/'labels'/f'{c}.json'),
                       graph_path=str(R/'graphs'/f'{c}.json'))
    save('cohort-status-final.json', dict(rows=rows, counts={'TRAIN':27, 'DEVELOPMENT':6, 'SEALED':8},
        train_labels=totals(train), dev_labels=totals(dev), association_independence_not_proven=True,
        sealed_body_feature_or_label_accessed=False))
    old = read(R/'registration.json')['old_hashes']
    audit = dict(checked=len(old), changed=[p for p,h in old.items() if not Path(p).exists() or sha(p)!=h])
    assert not audit['changed']
    save('preservation-audit-final.json', audit)
    calls = []
    for p in sorted((R/'web').glob('*.completed.json')):
        complete = read(p); task = complete['task']; submission = R/'web'/f'{task}.submitted.json'
        submitted = read(submission) if submission.exists() else None
        elapsed = None if submitted is None else (datetime.datetime.fromisoformat(complete['at'].replace('Z','+00:00')) - datetime.datetime.fromisoformat(submitted['at'].replace('Z','+00:00'))).total_seconds()
        calls.append(dict(task=task, submitted=None if submitted is None else submitted['at'], observed_complete=complete['at'],
            observed_elapsed_seconds=elapsed, elapsed_is_observation_bound_not_exact_generation_time=True,
            mode=complete['mode'], exact_model=complete['exact_model'], url=complete['url'],
            raw=str(R/'web'/f'{task}.raw.json'), raw_sha256=sha(R/'web'/f'{task}.raw.json'),
            input_sha256=sha(R/'tasks'/f'{task}.txt'), run_status='OK'))
    assert len(calls)==22 and all(x['mode']=='High' for x in calls)
    save('cost-final.json', dict(web_calls=22, semantic_retry=0, new_training_fits=0,
        fits_skipped=6, legal_answer_calls=0, paid_api_calls=0, exact_tokens=None, calls=calls,
        api_upload_timeouts_are_not_model_retry=True))
    final_gate = dict(read(R/'readiness.json'), dev_review_pending=False,
        dev_review_complete=True, final_status='DATA_CONTRACT_REPAIRED; TRAINING_STOPPED_ON_REPEATED_SCOPE_DISPUTE',
        known_train_positions=totals(train)['KNOWN'], known_dev_positions=totals(dev)['KNOWN'],
        semantics_not_certified_by_format_or_locator=True,
        related_tests='contract-tests-final.txt', no_semantic_repair_loop=True)
    save('readiness-final.json', final_gate)
    headers=['case_id','method','seed','old_core','fixed_historical_core','expanded_core','document_core','known_irrelevant_selected','unknown_selected','old_characters','new_characters','material_changed']
    with (R/'comparison-table.csv').open('x', newline='') as f:
        w=csv.writer(f); w.writerow(headers)
        for x in ranking:
            h=x['same_historical_reference_fixed_mapping_material']; n=x['expanded_all30_reference']
            fmt=lambda a: '/'.join(map(str,a))
            w.writerow([x['case_id'],x['method'],x['seed'],fmt(x['legacy_metrics']['core_delivered']),fmt(h['core_delivered']),fmt(n['core_delivered']),fmt(n['core_document_delivered']),len(n['known_irrelevant_selected']),len(n['unknown_selected']),x['old_characters'],x['new_characters'],x['old_selected_ids']!=x['new_selected_ids']])
    rejected = {}
    for c in protocol['dev']:
        reviewed=read(R/'web'/f'REVIEW-{c}.raw.json')
        rejected[c]=dict(review_rejections=reviewed.get('rejections',[]),
            systematic_issues=reviewed.get('systematic_issues',[]),
            disagreements=reviewed.get('disagreements',[]),
            applied_mask=read(R/'rejections'/f'{c}.json'),
            interpretation='conservative model-source-review isolation, not a human truth certificate')
    save('dev-review-decisions.json', rejected)
    stats=dict(train_states=totals(train),dev_states=totals(dev),
        train_sample_decisions=dict(collections.Counter(x['decision'] for x in reviews)),
        restored=sum(not x['old_entered_loss'] and x['new_entered_loss'] for x in changes),
        newly_isolated=sum(x['old_entered_loss'] and not x['new_entered_loss'] for x in changes),
        material_changes=sum(x['old_selected_ids']!=x['new_selected_ids'] for x in ranking),
        train_known_quality=dict(collections.Counter(x['layer'] for x in read(R/'quality-ledger.json') if x['state']=='KNOWN')))
    save('completion-summary.json',stats)
    codes=[Path('scripts/rgcn10_report.py'),Path('scripts/repository_bridge.py')]+[Path('scripts')/('rgcn10_'+x+'.py') for x in ['prepare','review_prepare','import','train']]+[Path('legal_bench/rules_verdict_v1')/(x+'.py') for x in ['authority_use_v10','authority_evaluation_v10','coarse_label_v10','legal_material_v10','rgcn_development_v4','rgcn_use_v3','rgcn_train_v2','authority_index','source_location_v3']]+[Path('tests/test_rgcn10_contract.py')]
    for p in codes:
        target=R/'completion-snapshot/code'/p; target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    files=[p for p in R.rglob('*') if p.is_file() and 'browser' not in p.parts and 'completion-snapshot' not in p.parts and p.suffix not in ('.sqlite','.npz') and not p.name.endswith(('.snapshot.txt','.preview.txt','.response.txt'))]
    save('completion-snapshot/manifest.json',dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        role='POST_PREPARATION_SNAPSHOT_NOT_A_PRETRAINING_FREEZE', code={str(p):sha(p) for p in codes}, files={str(p):sha(p) for p in files},
        fits=0, readiness=False, old_head=read(R/'registration.json')['head']))
    print(json.dumps(stats,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    run()
