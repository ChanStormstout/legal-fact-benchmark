"""Exact final re-review with complete identity evidence; no new generation."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.proof_final_bindings_v20_8 import OUT as BASE,inputs,read,verify as verify_base
from legal_bench.proof_carrying import final_statement_review_v20_9_1 as core
from legal_bench.proof_carrying.artifact_state_v20_2 import immutable,freeze_files,verify_files,digest

OLD=BASE/'statement-pack-01'
OUT=BASE/'statement-pack-02'
FILES=['legal_bench/proof_carrying/final_statement_review_v20_9_1.py',
       'scripts/proof_final_statement_review_v20_9_1.py',
       'legal_bench/proof_carrying/final_statement_pack_v20_9.py',
       'legal_bench/proof_carrying/final_bindings_v20_8.py',
       'legal_bench/proof_carrying/final_source_guard_v20_7.py']


def replay(cid,combined=None):
    verify_base();case,old,_,_=inputs(cid);b=read(BASE/'cases'/cid/'bridge.json');d=OUT/'cases'/cid
    if combined:
        reviews=read(combined);frame=read(d/'frame-proposal.json');pack=read(d/'proposal.json')
        fr,pr=reviews['frame_review'],reviews['pack_review']
        immutable(d/'frame-review/parsed.json',fr);immutable(d/'source-review/parsed.json',pr)
    else:
        frame=read(BASE/'cases'/cid/'frame-proposal.json');fr=read(BASE/'cases'/cid/'frame-review/parsed.json')
        pack=read(OLD/'cases'/cid/'proposal.json');pr=read(OLD/'cases'/cid/'source-review/parsed.json')
        immutable(d/'frame-proposal.json',frame);immutable(d/'proposal.json',pack)
    task=core.final_task(case,old,b,frame,fr,pack,pr)
    previous=read(OLD/'cases'/cid/'task.json');plan=read(OLD/'cases'/cid/'generation/parsed.json')
    if previous['schema']!=task['schema'] or previous['pack']!=task['pack']:
        raise ValueError('ORDER_REPLAY_STATEMENT_OR_SCHEMA_CHANGED')
    immutable(d/'source.json',case);immutable(d/'task.json',task);immutable(d/'ordering-plan.json',plan)
    immutable(d/'replay-receipt.json',{'actual_new_model_calls':0,'old_generation':str((OLD/'cases'/cid/'generation/run.json').relative_to(ROOT)),
        'all_statement_text_and_ordering_schema_unchanged':True,'ordering_prompt_unchanged':previous['prompt']==task['prompt'],
        'frame_changed_and_separately_source_rechecked':previous['frame']!=frame,
        'old_task_sha256':previous['input_sha256'],'new_task_sha256':task['input_sha256']})
    answer=core.render(task,plan,case);immutable(d/'rendered-candidate.json',answer)
    rt=core.review_task(task,plan,case);immutable(d/'whole-answer-review/task.json',rt)
    (d/'whole-answer-review/prompt.txt').write_text(rt['prompt'])
    paths=[str((d/p).relative_to(ROOT)) for p in ('source.json','task.json','ordering-plan.json','rendered-candidate.json','whole-answer-review/task.json','replay-receipt.json')]
    immutable(d/'freeze/protocol.json',freeze_files(ROOT,d,FILES,paths))
    print(cid,'EXACT_REVIEW_READY',len(rt['units']),len(rt['prompt']))


def verify(cid):
    verify_base();d=OUT/'cases'/cid;verify_files(ROOT,read(d/'freeze/protocol.json'))
    core.verify_task(read(d/'task.json'),read(d/'source.json'))


def accept(cid,path):
    verify(cid);d=OUT/'cases'/cid;review=read(path)
    result=core.accept_final(read(d/'task.json'),json.dumps(read(d/'ordering-plan.json')),'OK',case=read(d/'source.json'),review=review)
    immutable(d/'whole-answer-review/parsed.json',review);immutable(d/'final-acceptance.json',result)
    print(cid,result['contract_status'],result.get('source_review_issues'),result.get('error'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('replay','accept','verify'))
    p.add_argument('--case-id',choices=('1954254','1187427','569555'),required=True);p.add_argument('--review');a=p.parse_args()
    if a.action=='replay':replay(a.case_id,a.review)
    elif a.action=='verify':verify(a.case_id);print('VERIFIED')
    elif a.review:accept(a.case_id,a.review)
    else:p.error('--review required')
