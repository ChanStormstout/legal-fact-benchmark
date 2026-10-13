"""Source-pack review -> exact final ordering -> immutable renderer -> whole review."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.proof_final_bindings_v20_8 import OUT as BASE,inputs,read,verify as verify_base
from legal_bench.proof_carrying import final_statement_pack_v20_9 as core
from legal_bench.proof_carrying.artifact_state_v20_2 import immutable,freeze_files,verify_files
from legal_bench.proof_carrying.provider_runtime_v20_6_1 import Runner

OUT=BASE/'statement-pack-01'
FILES=['legal_bench/proof_carrying/final_statement_pack_v20_9.py',
       'scripts/proof_final_statement_pack_v20_9.py',
       'legal_bench/proof_carrying/final_bindings_v20_8.py',
       'legal_bench/proof_carrying/final_source_guard_v20_7.py',
       'legal_bench/proof_carrying/schema_contract_v19_6.py',
       'legal_bench/proof_carrying/provider_runtime_v20_6_1.py']


def prepare(cid,review_path):
    verify_base();case,old,_,_=inputs(cid);p=BASE/'cases'/cid;d=OUT/'cases'/cid
    review=read(review_path);pack=read(d/'proposal.json')
    task=core.final_task(case,old,read(p/'bridge.json'),read(p/'frame-proposal.json'),read(p/'frame-review/parsed.json'),pack,review)
    immutable(d/'source-review/parsed.json',review);immutable(d/'source.json',case);immutable(d/'task.json',task)
    paths=[str((d/f).relative_to(ROOT)) for f in ('source.json','task.json','proposal.json','source-review/parsed.json')]
    immutable(d/'freeze/protocol.json',freeze_files(ROOT,d,FILES,paths))
    print(cid,'SOURCE_PACK_ACCEPTED',len(pack['records']),'RECORDS',len(task['prompt']),'INPUT_CHARS')


def verify(cid):
    verify_base();d=OUT/'cases'/cid;verify_files(ROOT,read(d/'freeze/protocol.json'))
    core.verify_task(read(d/'task.json'),read(d/'source.json'))


def generate(cid):
    verify(cid);d=OUT/'cases'/cid;t=read(d/'task.json');case=read(d/'source.json')
    runner=Runner(out=BASE,maximum_cost_usd=read(BASE/'budget.json')['remaining_budget_usd'])
    run=runner.run(t['prompt'],t['schema'],d/'generation',1024,900)
    path=d/'generation/raw-response.txt';raw=path.read_text() if path.exists() else ''
    result=core.accept_final(t,raw,run['run_status'],case=case)
    immutable(d/'pre-review-acceptance.json',result)
    if result['contract_status']=='PENDING_WHOLE_ANSWER_SOURCE_REVIEW':
        plan=core.loads(raw);answer=core.render(t,plan,case)
        immutable(d/'rendered-candidate.json',answer)
        rt=core.review_task(t,plan,case);immutable(d/'whole-answer-review/task.json',rt)
        (d/'whole-answer-review/prompt.txt').write_text(rt['prompt'])
    print(json.dumps({'case':cid,'technical':run['run_status'],'contract':result['contract_status'],'cost':run.get('listed_price_token_cost_usd'),'error':result.get('error')}))


def accept(cid,path):
    verify(cid);d=OUT/'cases'/cid;review=read(path)
    result=core.accept_final(read(d/'task.json'),(d/'generation/raw-response.txt').read_text(),read(d/'generation/run.json')['run_status'],case=read(d/'source.json'),review=review)
    immutable(d/'whole-answer-review/parsed.json',review);immutable(d/'final-acceptance.json',result)
    print(cid,result['contract_status'],result.get('source_review_issues'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare','generate','accept','verify'))
    p.add_argument('--case-id',choices=('1187427','1954254','569555'),required=True);p.add_argument('--review');a=p.parse_args()
    if a.action=='prepare':
        if not a.review:p.error('--review required')
        prepare(a.case_id,a.review)
    elif a.action=='generate':generate(a.case_id)
    elif a.action=='verify':verify(a.case_id);print('VERIFIED')
    elif a.review:accept(a.case_id,a.review)
    else:p.error('--review required')
