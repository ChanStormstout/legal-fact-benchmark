"""One frozen 10-case use-supervision development run, then bounded web tasks."""
import sys, json, time, hashlib, shutil, datetime, importlib.metadata, csv
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import mlx.core as mx
from mlx.utils import tree_flatten
from legal_bench.rules_verdict_v1 import rgcn_use_v1 as use, rgcn_train_v2 as train
from legal_bench.rules_verdict_v1 import rgcn_development_v3 as graph, legal_rule_support_study as pack, authority_index
R = Path('outputs/rgcn-use-development-08')
P = Path('outputs/rgcn-ranking-diagnostic-07/pilot')
def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name, value):
    path = R / name; path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists(): raise FileExistsError(path)
    path.write_text(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def evaluate(row, labels, units, selection, predictions):
    uid = [u['id'] for u in units]; selected = set(selection['selected_ids']); mandatory = set(selection['mandatory_ids'])
    refs = {x['unit_id']: x for x in labels['uses'] if x['category'] in use.MAPPING}
    confusion = [[0] * 3 for _ in range(3)]
    for key, ref in refs.items(): confusion[use.MAPPING[ref['category']]][int(predictions[uid.index(key)])] += 1
    core = {k for k, v in refs.items() if use.MAPPING[v['category']] == 0} - mandatory
    background = {k for k, v in refs.items() if use.MAPPING[v['category']] == 1}
    irrelevant = {k for k, v in refs.items() if use.MAPPING[v['category']] == 2}
    unreachable = []
    for key in core:
        isolated = pack.select([{'id': key}], units, pack.PRIMARY_CONFIG, mandatory=selection['mandatory_ids'])
        if key not in isolated['selected_ids']: unreachable.append(key)
    predicted_core = {uid[i] for i, cls in enumerate(predictions) if cls == 0} & set(refs)
    truth_core = {k for k, v in refs.items() if use.MAPPING[v['category']] == 0}
    rank = {x['id']: i for i, x in enumerate(row['ranking'])}
    prefs = labels['preferences']
    # Accounting is additive per rendered object; list punctuation is separately documented.
    chars = {u['id']: len(pack.render([u])) - 2 for u in units}
    return dict(case_id=row['case_id'], method=row['method'], seed=row['seed'], status=row['status'],
                confusion=confusion, known_uses=len(refs), core_identification=[len(predicted_core & truth_core), len(truth_core)],
                core_false_positive=len(predicted_core - truth_core), selected_ids=selection['selected_ids'],
                core_delivered=[len(core & selected), len(core)], core_excluding_mandatory=sorted(core),
                mandatory_core_excluded=sorted(truth_core & mandatory), individually_undeliverable_core=unreachable,
                background_delivered=sorted(background & selected), irrelevant_selected=sorted(irrelevant & selected),
                irrelevant_payload_characters=sum(chars[k] for k in irrelevant & selected),
                unlabeled_selected=sorted(selected - set(refs)), legal_characters=selection['legal_characters'],
                preference_agreement=[sum(rank[x['preferred']] < rank[x['other']] for x in prefs), len(prefs)])

def main():
    if (R / 'training-freeze.json').exists(): raise RuntimeError('Frozen run exists; resume stored outputs, do not refit')
    config = read(R / 'protocol.json'); samples = read(P / 'samples.json'); units = read(P / 'sources/laws.json')
    ids = [s['case_id'] for s in samples]; uid = [u['id'] for u in units]
    raw = {}; targets = {}; labels = {}; rankings = {}
    authority_index.build(units, R / 'indexes/original.sqlite')
    for sample in samples:
        cid = sample['case_id']; material = read(P / 'task-material' / (cid + '.json'))
        # Pilot has no stored rankings: deterministic common full-allowed-source query, no labels/answers.
        query = material['question'] + '\n' + '\n'.join(x['text'] for x in material['case']['segments'])
        ranking = authority_index.search(R / 'indexes/original.sqlite', query, 40)
        rankings[cid] = ranking
        save('retrieval/' + cid + '.json', dict(query=query, ranking=ranking, not_a_new_retrieval_treatment=True))
        raw[cid] = graph.numeric(read(P / 'graphs' / (cid + '.json')), ranking, units)
        labels[cid] = read(P / 'labels' / (cid + '.json')); targets[cid] = use.supervision(labels[cid], uid)
    save('supervision.json', dict(classes=use.CLASSES, mapping=use.MAPPING, accepted_by_case=targets,
                               all_other_uses_ignored=True, preferences_not_training=True))
    variation = []
    for unit in units:
        observed = [{'case_id': c, 'category': x['category'], 'class': use.CLASSES[use.MAPPING[x['category']]]}
                    for c in ids for x in labels[c]['uses'] if x['unit_id'] == unit['id'] and x['category'] in use.MAPPING]
        variation.append(dict(unit_id=unit['id'], records=observed, classes=len({x['class'] for x in observed})))
    save('same-authority-use-variation.json', variation)
    inputs = list((P / 'graphs').glob('*.json')) + list((P / 'labels').glob('*.json')) + list((P / 'sources').glob('*.json')) + list((P / 'task-material').glob('*.json')) + [P / 'samples.json']
    code = [Path(__file__), Path('tests/test_rgcn_use_v1.py')] + [Path('legal_bench/rules_verdict_v1') / f for f in ['rgcn_use_v1.py','rgcn_train_v2.py','rgcn_development_v3.py','rgcn_development_v2.py','source_location_v3.py','legal_rule_support_study.py','rule_retrieval_v21.py','final_v9.py','authority_index.py']]
    for path in code:
        destination = R / 'freeze/code' / path.resolve().relative_to(Path.cwd()); destination.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(path, destination)
    save('environment.json', dict(python=sys.version, executable=sys.executable, numpy=np.__version__, mlx=importlib.metadata.version('mlx')))
    save('training-freeze.json', dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(), configuration=config,
                                     hashes={str(p): sha(p) for p in inputs + code + [R / 'protocol.json', R / 'evaluation-rules.json', R / 'test-results.txt', R / 'execution-wrapper.txt']},
                                     groups={s['case_id']: s['group_id'] for s in samples}, no_labels_in_features=True,
                                     group_limits='No known duplicate; broader links unconfirmed; development not independent test'))
    rows = []; metrics = []; tasks = {}; slots = []; start = time.monotonic()
    for held in ids:
        group = next(s['group_id'] for s in samples if s['case_id'] == held)
        training = [s['case_id'] for s in samples if s['group_id'] != group]
        data, scale = train.fold_data(raw, training); save('folds/' + held + '/scaler.json', scale)
        supervised = {c: targets[c] for c in training}
        for seed in config['seeds']:
            for kind in config['methods']:
                prefix = f'folds/{held}/{seed}-{kind}'; st = time.monotonic()
                row = dict(case_id=held, method=kind, seed=seed)
                try:
                    model, log = use.fit(kind, data, supervised, seed, config['updates'], config['lr'], config['l2'])
                    probabilities, scores = use.probabilities_and_scores(model(data[held])); predictions = probabilities.argmax(1)
                    log.update(seconds=time.monotonic()-st, held_case=held, peak_active_bytes=int(mx.get_peak_memory()), held_labels_in_loss=False)
                    save(prefix + '-train.json', log)
                    mx.savez(str(R / (prefix + '-weights.npz')), **dict(tree_flatten(model.parameters())))
                    ranking = [dict(id=uid[i], score=float(scores[i])) for i in sorted(range(len(uid)), key=lambda i: (-scores[i], i))]
                    row.update(status='OK', ranking=ranking, probabilities=probabilities.tolist(), predicted_classes=predictions.tolist())
                    selection = pack.select(ranking, units, pack.PRIMARY_CONFIG, mandatory=config['mandatory'])
                    save('selections/' + held + f'/{seed}-{kind}.json', selection)
                    metric = evaluate(row, labels[held], units, selection, predictions)
                    material = read(P / 'task-material' / (held + '.json'))
                    text = pack.prompt(material['case'], selection['units'], material['question'])
                    metric['task_sha256'] = hashlib.sha256(text.encode()).hexdigest(); metrics.append(metric)
                    if held in config['answer_cases'] and seed == config['primary_seed']:
                        key = (held, metric['task_sha256'])
                        if key not in tasks:
                            tid = 'ANS%02d' % (len(tasks) + 1); tasks[key] = dict(id=tid, case_id=held, sha256=key[1], methods=[])
                            save('tasks/' + tid + '.txt', text)
                        tasks[key]['methods'].append(kind); slots.append(dict(case_id=held, method=kind, seed=seed, id=tasks[key]['id'], sha256=key[1]))
                except Exception as e:
                    row.update(status='FAILED', error=repr(e), answer=None); save(prefix + '-failure.json', row)
                rows.append(row)
    save('training-results.json', rows); save('selection-results.json', metrics)
    assert len(rows) == 80 and len(tasks) <= 12
    save('answer-order.json', list(tasks.values())); save('answer-slots.json', slots)
    save('compute-cost.json', dict(seconds=time.monotonic()-start, fits=len(rows), successful=sum(x['status']=='OK' for x in rows), failures=sum(x['status']!='OK' for x in rows), unique_final_tasks=len(tasks), logical_answer_slots=12))
    save('answer-freeze.json', dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(), no_observed_answers=True,
                                  hashes={str(p):sha(p) for p in list((R/'tasks').glob('*.txt')) + [R/'answer-order.json',R/'answer-slots.json']},
                                  shared_only_when_same_case_full_input_hash_matches=True, no_reference_or_scores_in_tasks=True))
    with (R / 'material-comparison.csv').open('w') as f:
        fields = ['case_id','method','seed','core_delivered','core_identification','core_false_positive','irrelevant_payload_characters','unlabeled_selected','legal_characters','preference_agreement','selected_ids','task_sha256']
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(metrics)
    print(read(R / 'compute-cost.json'))

if __name__ == '__main__': main()
