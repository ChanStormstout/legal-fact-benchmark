"""Same complete ordering request, conservative calibrated token-cost preflight."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.proof_final_statement_pack_v20_9 import OUT,BASE,read,verify
from legal_bench.proof_carrying import final_statement_pack_v20_9 as core
from legal_bench.proof_carrying.provider_token_budget_v20_9 import Runner
from legal_bench.proof_carrying.artifact_state_v20_2 import immutable,freeze_files,byte_hash


def generate(cid):
    verify(cid)
    calibration=read(BASE/'engineering/token-budget-calibration-v2.json')
    if not calibration['all_within_bound'] or len(calibration['calibration'])<6:
        raise ValueError('TOKEN_BUDGET_CALIBRATION_NOT_VALID')
    # Recheck the more stringent 1.5x + wrapper bound against all saved API uses.
    if any(x['server_tokens']>(3*(x['client_tokens']+x['schema_tokens'])+1)//2+4096
           for x in calibration['calibration']):raise ValueError('TOKEN_BUDGET_MARGIN_NOT_VALID')
    d=OUT/'cases'/cid;t=read(d/'task.json');case=read(d/'source.json')
    immutable(d/'preflight/freeze/protocol.json',freeze_files(ROOT,d/'preflight',
        ['scripts/proof_final_statement_budget_v20_9.py','legal_bench/proof_carrying/provider_token_budget_v20_9.py'],
        [str((BASE/'engineering/token-budget-calibration-v2.json').relative_to(ROOT))]))
    runner=Runner(out=BASE,maximum_cost_usd=read(BASE/'budget.json')['remaining_budget_usd'])
    run=runner.run(t['prompt'],t['schema'],d/'generation',1024,900)
    raw_path=d/'generation/raw-response.txt';raw=raw_path.read_text() if raw_path.exists() else ''
    result=core.accept_final(t,raw,run['run_status'],case=case)
    immutable(d/'pre-review-acceptance.json',result)
    if result['contract_status']=='PENDING_WHOLE_ANSWER_SOURCE_REVIEW':
        plan=core.loads(raw);immutable(d/'rendered-candidate.json',core.render(t,plan,case))
        rt=core.review_task(t,plan,case);immutable(d/'whole-answer-review/task.json',rt)
        (d/'whole-answer-review/prompt.txt').write_text(rt['prompt'])
    print(json.dumps({'case':cid,'technical':run['run_status'],'contract':result['contract_status'],
                      'cost':run.get('listed_price_token_cost_usd'),'token_preflight':run['token_budget_preflight']}))


if __name__=='__main__':generate('569555')
