#!/usr/bin/env python3
"""Unified F01-F10 acceptance: cached calls and real deterministic entry points.

No neural generation, embedding inference, training, or web submission.
"""
import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import proof_source_verification_v20_2 as entry
from legal_bench.proof_carrying import source_verification_v20 as old_core
from legal_bench.proof_carrying.source_verification_check_v20 import check as old_check
from legal_bench.proof_carrying.source_verification_check_v20_2 import check
from legal_bench.proof_carrying.artifact_state_v20_2 import execution_context,digest,local_closure
from legal_bench.proof_carrying.schema_contract_v19_6 import validate
from legal_bench.proof_carrying.presentation_v19_8_1 import unpack

OUT=entry.OUT


def cached_chain(cfg,tokenizer=None):
    rows=[]
    cases=sorted({p.parent.parent.name for p in OUT.glob('local/*/Q*/parsed.json')})
    for cid in cases:
        f=entry.fixture(cid);pw=entry.merged(cid,'P');qw=entry.merged(cid,'Q')
        p,q=pw['answer'],qw['answer'];before=digest([p,q]);context=execution_context(pw,qw)
        result=entry.assemble_case(cid);dest=OUT/result['path']
        pool=entry.read(dest/'pool.json');data=entry.read(dest/'common.json');trace=entry.read(dest/'D-trace.json')
        # Reproduce the previous problem with the same byte-preserved proposals.
        prior=old_core.apply(f['case'],f['rules'],p,q)
        prior_check=old_check(p,q,prior,f['rules'])
        independent=check(p,q,trace,f['rules'],context)
        assert independent['status']=='OK',independent
        assert before==digest([p,q]),'RAW_P_Q_CHANGED'
        assert trace['semantic_approval'] is False and trace['legal_approval'] is False
        for node in data['graph']['nodes']:
            if node['kind']==2:
                claim=json.loads(node['text'])
                assert not {'proposed_label','verification_state','verifier_reason','verification_execution'} & set(claim)
        injected={d['id']:'SUPPORTED' for d in pool['candidates']}
        finals={}
        for method in 'ACDEFG':
            pred=injected if method in 'EFG' else None
            task=entry.core.final_task(f['case'],f['rules'],method,p,q,pred,execution=context)
            if task['trace']:
                assert check(p,q,task['trace'],f['rules'],context)['status']=='OK'
            assert task['presentation_audit']['exact_roundtrip']
            assert task['source_ids']==[s['id'] for s in f['case']['segments']]
            cap=entry.measured(task['prompt'],tokenizer,8192) if tokenizer else None
            finals[method]={'constructed':True,'generated':False,'capacity':cap,
                            'learner_predictions':'SYNTHETIC_INJECTED_FOR_INTERFACE_ONLY' if pred else None}
            entry.save(OUT/'engineering/fixtures'/cid/(method+'-task.json'),task)
        try:entry.core.final_task(f['case'],f['rules'],'B')
        except ValueError as exc:assert str(exc)=='A_DEPENDENCY_MISSING'
        else:raise AssertionError('B_WITHOUT_A_ACCEPTED')
        invalid=[x for x in trace['application_ledger'] if x.get('invalid_record_dependencies')]
        rows.append({'case_id':cid,'prior_application_check':prior_check,'new_application_check':independent,
                     'input_snapshot':result['snapshot'],'source_coverage':data['coverage'],
                     'verification_coverage':pool['verification_coverage'],'invalid_dependencies_isolated':invalid,
                     'quarantine_reasons':{reason:sum(x['reason']==reason for x in pool['quarantined']) for reason in {x['reason'] for x in pool['quarantined']}},
                     'final_interfaces':finals,'original_proposals_unchanged':True})
    return rows


def main():
    OUT.joinpath('engineering').mkdir(parents=True,exist_ok=True)
    parent_before={str(p.relative_to(ROOT)):entry.sha(p) for p in entry.PARENT.rglob('*') if p.is_file()}
    legacy=entry.read(entry.PARENT/'freeze/protocol.json')
    parent_before.update(legacy['code_hashes'])
    entry.save(OUT/'engineering/parent-before.json',parent_before)
    result=subprocess.run([sys.executable,'-B','-m','unittest',
                           'tests.test_constraint_viability_v20_1','tests.test_source_verification_v20',
                           'tests.test_pipeline_diagnostic_v19_8','tests.test_final_capacity_v19_8_1',
                           'tests.test_source_verification_v20_2','-q'],cwd=ROOT,capture_output=True,text=True)
    entry.text(OUT/'engineering/tests.txt',result.stdout+result.stderr)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    count=int(re.search(r'Ran (\d+) tests',result.stderr)[1])
    entry.save(OUT/'engineering/tests-gate.json',{'status':'PASS','tests':count,'new_model_calls':0,'weights_loaded':False})
    plan=entry.prepare();cfg={**legacy,**plan}
    # Build all cached paths before final freeze so any engineering failure is repairable.
    with patch.object(entry,'frozen',return_value=cfg):
        preliminary=cached_chain(cfg)
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained((ROOT/'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),local_files_only=True)
    protocol=entry.freeze();entry.frozen()
    # Verify actual frozen entry rather than treating a patched configuration as acceptance.
    rows=cached_chain(protocol,tokenizer)
    assert all(row['new_application_check']['status']=='OK' for row in rows)
    assert digest([{k:v for k,v in row.items() if k!='final_interfaces'} for row in preliminary])==digest([{k:v for k,v in row.items() if k!='final_interfaces'} for row in rows])
    pauses={stage:entry.run_generation(stage) for stage in ('P','Q','final')}
    pauses.update(fit=entry.fit(),fit_one=entry.fit_one('Flat',1),encode=entry.encode())
    assert all(value=='PAUSED' for value in pauses.values())
    for cid in protocol['TRAIN']+protocol['DEV']:
        assert entry.fixture(cid)['case']['split'] in ('TRAIN','DEV')
    changed=[rel for rel,h in parent_before.items() if entry.sha(ROOT/rel)!=h]
    assert not changed,changed
    preservation=[x for x in entry.read(OUT/'preserved-parent-cache.json') if entry.sha(ROOT/x['copy'])!=x['sha256'] or entry.sha(ROOT/x['original'])!=x['sha256']]
    assert not preservation,preservation
    expected=local_closure(ROOT,protocol['explicit_entries'])
    assert set(expected)==set(protocol['code_hashes'])
    acceptance={'status':'PASS','version':entry.core.VERSION,'tests':count,'cached_cases':len(rows),
                'old_application_rejections':sum(row['prior_application_check']['status']!='OK' for row in rows),
                'new_application_rejections':0,'cached_chain':rows,'paused_entry_results':pauses,
                'code_dependency_files':len(protocol['code_hashes']),'configuration_files':len(protocol['configuration_hashes']),
                'parent_files_and_legacy_sources_verified':len(parent_before),'copied_cache_files_verified':len(entry.read(OUT/'preserved-parent-cache.json')),
                'F01_to_F10':'ALL_ENGINEERING_REGRESSIONS_PASSED','raw_proposals_and_failures_preserved':True,
                'new_neural_generations':0,'new_embedding_inference':0,'new_fits':0,'web_submissions':0,'weights_loaded':False,
                'trained_prediction_interfaces':'INJECTED_SYNTHETIC_LABELS_ONLY','semantic_success':False,
                'no_TEST_or_SEALED_data_read':True,'budget_reset':False,'commit_or_push':False}
    entry.save(OUT/'engineering/acceptance.json',acceptance)
    print(json.dumps({'status':'PASS','tests':count,'cached_cases':len(rows),'old_rejected':acceptance['old_application_rejections'],
                      'new_rejected':0,'code_files':len(protocol['code_hashes']),'new_model_calls':0},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
