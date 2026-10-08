#!/usr/bin/env python3
"""One fixed split and fit-only context preparation, before training."""
import sys,json,hashlib,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from scripts.irac_aligned_train import load
from legal_bench.irac_application.aligned_train import stratified_group_split
from legal_bench.irac_application.aligned_tasks import ROOT,put,prepare_baselines
from legal_bench.irac_application.aligned_context import normalization_candidates,given_rule_package,mine_existing_interface

def main():
    packs=load(False);splits=stratified_group_split(packs,seed=20261007,folds=3);put(ROOT/'freeze/splits.json',splits)
    distribution=[]
    for f in splits:
        for part in ('fit_groups','validation_groups','test_groups'):
            ps=[p for p in packs if p['group_id'] in f[part]];c=collections.Counter(y for p in ps for y,m in zip(p['labels'],p['mask']) if m)
            distribution.append(dict(fold=f['fold'],partition=part,groups=f[part],packages=len(ps),labels=dict(c),families=dict(collections.Counter(p['family'] for p in ps))))
        assert not (set(f['fit_groups'])&set(f['validation_groups']) or set(f['fit_groups'])&set(f['test_groups']) or set(f['test_groups'])&set(f['validation_groups']))
    put(ROOT/'freeze/split-coverage.json',dict(rows=distribution,limitations=['Only one admitted REFUTED test in one dispute: held-out refutation and model training cannot both have this class in that fold.','Dispute groups retain prior association uncertainty; no assertion of verified independence.','All packages were used in prior development.'],label_order=['SUPPORTED','REFUTED','UNRESOLVED']))
    vectors=np.load(ROOT/'text-cache/vectors.npz');prepare_baselines(splits,vectors)
    templates={f:json.loads((ROOT/'templates'/f'{f}.json').read_text()) for f in ('DRC_SUBLETTING','DRC_BONA_FIDE')};laws={f:json.loads((ROOT/'sources'/f'{f}-law.json').read_text()) for f in templates}
    for f in splits:
        records=[]
        for p in packs:
            if p['group_id'] not in f['fit_groups']:continue
            legacy=json.loads((ROOT/'inputs'/f"{p['package_id']}-legacy-facts.json").read_text())
            records.extend(dict(x,id=p['package_id']+':'+x['id'],group_id=p['group_id']) for x in legacy['facts'])
        put(ROOT/'context'/f"fold{f['fold']}-normalization-candidates.json",normalization_candidates(records,vectors))
        put(ROOT/'context'/f"fold{f['fold']}-patterns.json",mine_existing_interface(records,lambda *a,**k: (_ for _ in ()).throw(ValueError('NO_SILENT_TYPED_CONVERSION'))))
    for family in templates:put(ROOT/'context'/f'{family}-rule-delivery.json',given_rule_package(family,templates,laws))
    put(ROOT/'context/canonical-integration.json',dict(status='NATIVE_RUNNING_REAL_GROUP_SAMPLE_PENDING',synthetic_adapter_tests_not_real_integration=True,automatically_merged_clusters=0,reason='No verified real team canonical sample has been supplied to this run; embeddings propose neighbors only.'))
    graph_audit=[]
    for p in sorted((ROOT/'graphs').glob('*.json')):
        g=json.loads(p.read_text());graph_audit.append(dict(case_id=p.stem,nodes=len(g['nodes']),edges=len(g['edges']),isolated=g.get('isolation',g.get('quarantine',[])),anco=g.get('anco',{})))
    put(ROOT/'engineering/graph-inventory.json',graph_audit)
    print(json.dumps(dict(packages=len(packs),folds=len(splits),baseline_tasks=len(list((ROOT/'tasks').glob('baseline-*.txt'))),distribution=distribution),indent=2))
if __name__=='__main__':main()
