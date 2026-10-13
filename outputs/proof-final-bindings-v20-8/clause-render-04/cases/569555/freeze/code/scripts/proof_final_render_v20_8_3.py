"""Replay unchanged real selector outputs under the corrected multiple-use policy.

No hidden regeneration: binds the old raw/request/source hashes, then independently
reviews the exact newly rendered answer. This cannot be reported as a new model run.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.proof_final_bindings_v20_8 import OUT as BASE,inputs,read,verify as verify_base
from legal_bench.proof_carrying import final_render_v20_8_3 as core
from legal_bench.proof_carrying.artifact_state_v20_2 import immutable,byte_hash,freeze_files,verify_files

OLD=BASE/'clause-render-03'
OUT=BASE/'clause-render-04'
FILES=['legal_bench/proof_carrying/final_render_v20_8_3.py',
       'scripts/proof_final_render_v20_8_3.py',
       'legal_bench/proof_carrying/final_bindings_v20_8.py',
       'legal_bench/proof_carrying/final_source_guard_v20_7.py',
       'legal_bench/proof_carrying/schema_contract_v19_6.py']


def replay(cid):
    verify_base()
    case,old_task,_,_=inputs(cid)
    previous=BASE/'cases'/cid
    task=core.final_task(case,old_task,read(previous/'bridge.json'),
                         read(previous/'frame-proposal.json'),read(previous/'frame-review/parsed.json'))
    source=OLD/'cases'/cid
    prior=read(source/'task.json')
    if task['schema']!=prior['schema'] or task['clauses']!=prior['clauses'] or task['frame']!=prior['frame'] or task['source_sha256']!=prior['source_sha256']:
        raise ValueError('REPLAY_SEMANTIC_INPUT_CHANGED')
    run=read(source/'generation/run.json')
    raw=(source/'generation/raw-response.txt').read_text()
    plan=core.loads(raw)
    if run['run_status']!='OK' or byte_hash(source/'generation/raw-response.txt')!=run['raw_sha256']:
        raise ValueError('REPLAY_FAILED_OR_CHANGED_REAL_GENERATION')
    dest=OUT/'cases'/cid
    immutable(dest/'source.json',case);immutable(dest/'task.json',task)
    immutable(dest/'selector-plan.json',plan)
    receipt={'version':core.VERSION,'actual_new_model_calls':0,
             'real_generation_run':str((source/'generation/run.json').relative_to(ROOT)),
             'raw_sha256':run['raw_sha256'],'old_request_sha256':run['identity']['request_sha256'],
             'old_task_sha256':prior['input_sha256'],'new_task_sha256':task['input_sha256'],
             'source_and_clauses_and_selector_schema_unchanged':True,
             'change':'Allow one unchanged fact to serve separately in both argument accounts.'}
    immutable(dest/'replay-receipt.json',receipt)
    result=core.accept_final(task,raw,'OK',case=case)
    immutable(dest/'pre-review-acceptance.json',result)
    if result['contract_status']!='PENDING_WHOLE_ANSWER_SOURCE_REVIEW':
        raise ValueError('REPLAY_RENDER_REJECTED:'+str(result))
    answer=core.render(task,plan,case)
    immutable(dest/'rendered-candidate.json',answer)
    rt=core.review_task(task,plan,case)
    immutable(dest/'whole-answer-review/task.json',rt)
    (dest/'whole-answer-review/prompt.txt').write_text(rt['prompt'])
    paths=[str((dest/p).relative_to(ROOT)) for p in ('source.json','task.json','selector-plan.json','replay-receipt.json','rendered-candidate.json','whole-answer-review/task.json')]
    immutable(dest/'freeze/protocol.json',freeze_files(ROOT,dest,FILES,paths))
    print(cid,'REPLAY_CHECK_OK',len(answer['conclusion']),'SUMMARY_CHARS',len(rt['units']),'REVIEW_UNITS',len(rt['prompt']),'REVIEW_CHARS')


def verify(cid):
    verify_base();dest=OUT/'cases'/cid
    verify_files(ROOT,read(dest/'freeze/protocol.json'))
    core.verify_task(read(dest/'task.json'),read(dest/'source.json'))


def accept(cid,path):
    verify(cid);dest=OUT/'cases'/cid
    review=read(path);plan=read(dest/'selector-plan.json')
    result=core.accept_final(read(dest/'task.json'),json.dumps(plan),'OK',case=read(dest/'source.json'),review=review)
    immutable(dest/'whole-answer-review/parsed.json',review)
    immutable(dest/'final-acceptance.json',result)
    print(cid,result['contract_status'],result.get('source_review_issues'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('replay','accept','verify'))
    p.add_argument('--case-id',choices=('1954254','569555','1187427'),required=True);p.add_argument('--review')
    a=p.parse_args()
    if a.action=='replay':replay(a.case_id)
    elif a.action=='verify':verify(a.case_id);print('VERIFIED')
    elif a.review:accept(a.case_id,a.review)
    else:p.error('--review required')
