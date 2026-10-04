"""Fixed V11 no-thinking methods on two old cases; dependency-local failure only."""
import json
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import digest, write_new
from legal_bench.rules_verdict_v1.final_v9 import prompt, final_schema, FINAL, EXAMPLES
from legal_bench.rules_verdict_v1.intermediate_v8 import first_prompt
from legal_bench.rules_verdict_v1.checks_v8 import fact_schema, check_facts

ROOT = Path('outputs/rules-verdict-v13-crosscase')
V11 = Path('outputs/rules-verdict-v11-intermediate-ablation')
V12 = Path('outputs/rules-verdict-v12-thinking')
MATERIALS = Path('outputs/rules-verdict-v7-intermediate')
CASES = ['661475', '1134266']
ORDER = [(c,m) for c in CASES for m in ['D','B-proposal','B-P']]
CODE = ['scripts/pipeline_v13_crosscase.py'] + [str(p.relative_to(V11/'freeze/code')) for p in (V11/'freeze/code').rglob('*.py') if p.name != 'pipeline_v11_ablation.py']
read = lambda p: json.loads(Path(p).read_text())

def copy(a,b):
    b.parent.mkdir(parents=True, exist_ok=True)
    if b.exists(): assert b.read_bytes() == a.read_bytes(), str(b)
    else:b.write_bytes(a.read_bytes())

def inputs(c):return read(ROOT/'sources'/f'{c}.json'),read(ROOT/'prepared'/c/'law-package.json')

def prepare():
    assert not (ROOT/'freeze/config.json').exists(), 'No refreeze'
    assert not (ROOT/'runs').exists(), 'Existing run must be reused, not restarted'
    old=read(V11/'freeze/config.json')
    for p,h in old['live_code'].items():
        if p!='scripts/pipeline_v11_ablation.py':assert digest(Path(p).read_bytes())==h,p
    for p in ['legal_bench/rules_verdict_v1/runtime_constraint_diag_v1.py','legal_bench/mlx_json_constraint_v2.py']:
        assert Path(p).read_bytes()==(V11/'freeze/code'/p).read_bytes()
    s=read(V11/'sources/69305.json');l=read(V11/'prepared/69305/law-package.json')
    assert prompt(s,l,{})==(V11/'runs/D/prompt.txt').read_text()
    assert prompt(s,l,read(V11/'prepared/B-P/intermediate.json'))==(V11/'runs/B-P/prompt.txt').read_text()
    assert first_prompt(s,l,'B')==(V11/'runs/B-proposal/prompt.txt').read_text()
    assert fact_schema([x['id'] for x in s['segments']])==read(V11/'runs/B-proposal/schema.json')
    assert final_schema([x['id'] for x in s['segments']],[x['id'] for x in l['law_segments']])==read(V11/'runs/D/schema.json')
    original=Path('legal_bench/rules_verdict_v1/runtime_thinking_v12.py').read_text()
    fixed=Path('legal_bench/rules_verdict_v1/runtime_thinking_v12_logging.py').read_text()
    assert fixed==original.replace("'actual_parameters': kwargs","'actual_parameters': dict(kwargs)")
    regression=(ROOT/'gate/regression.txt').read_text()
    assert 'Ran 5 tests' in regression and regression.rstrip().endswith('OK') and 'skipped' not in regression
    for name in ['offline-fix-audit.json','post-run-token-replay.json']:
        copy(V11/'gate'/name,ROOT/'gate'/name)
    replay=read(ROOT/'gate/post-run-token-replay.json')
    assert replay['prefix_tracking_matches_actual_token_ids'] and replay['all_generated_tokens_allowed_by_corrected_mask']
    fixture=read(ROOT/'gate/offline-fix-audit.json')
    assert not fixture['invalid_tokens_after_fix'] and fixture['eos_allowed_after_complete']
    for c in CASES:
        for rel in [f'sources/{c}.json',f'prepared/{c}/law-package.json',f'retrieval/{c}/result.json']:
            copy(MATERIALS/rel,ROOT/rel)
        source,law=inputs(c)
        assert source==read(Path('outputs/rules-verdict-v6-end-to-end')/'sources'/f'{c}.json')
        assert len({x['id'] for x in source['segments']})==len(source['segments'])
        assert all(x['text'] for x in source['segments'])
        assert not any(x['source_case']==c for x in law['cards'])
        ids=[x['id'] for x in source['segments']]
        write_new(ROOT/'prepared'/c/'final-schema.json',final_schema(ids,[x['id'] for x in law['law_segments']]))
        write_new(ROOT/'prepared'/c/'proposal-schema.json',fact_schema(ids))
        for method,text in [('D',prompt(source,law,{})),('B-proposal',first_prompt(source,law,'B'))]:
            p=ROOT/'prepared'/c/method;p.mkdir(parents=True,exist_ok=True);(p/'prompt.txt').write_text(text)
    copy(MATERIALS/'inherited-scope-audit.json',ROOT/'inherited-scope-audit.json')
    write_new(ROOT/'method-audit.json',{
        'V11_actual_final_D_and_B_P_reconstructed_exactly':True,
        'V11_actual_stage1_prompt_schema_reconstructed_exactly':True,
        'runtime_exact_V11_no_thinking_not_V12_thinking_adapter':True,
        'fixed_quote_mask_hash':old['mask_sha256'],
        'V12_log_fix_only_two_dictionary_copies':True,
        'V11_runtime_serializes_filtered_actual_parameters_no_mask_object':True,
        'budget_parameters_exact_V11':True,
        'case_packages_not_identical_to_each_other':True,
        'materials_policy':'Each case retains exact V7/V6 allowed source and its existing law package, same across D/B. No own cards or withheld target final reasoning restored.',
        'historical_source_knowledge':'Cases previously exposed in development; not independent tests.'})
    write_new(ROOT/'protocol.json',{'cases':CASES,'order':ORDER,'max_calls':6,'max_tokens_each':3072,
        'context_budget':32768,'round_generation_time_limit_seconds':1800,
        'failure_policy':'Format/truncation/repetition/input failures affect only dependencies. B proposal failure skips same B-P; independent conditions continue. Resource/framework failure or shared deadline stops remainder.',
        'B_P_intermediate':'Only unmodified current-case newly generated proposal; no check block or reference facts',
        'offline_checks':'Existing check_facts only, saved independently; semantic or local-check failures do not replace proposal or gate legal answer',
        'web_calls':0,'retries':0,'extra_model_pre_runs':0,'new_law_or_cases':0,
        'review':'One concentrated final decisive-source and omission review after generation; not a full intermediate reannotation',
        'publication':'NO_COMMIT_NO_PUSH','next_round':False})
    write_new(ROOT/'evaluation-rules.json',{'reference':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD',
        'checks':['decisive allowed-source facts and omissions beyond cited paragraphs','party/court/procedural attribution','prior finding retained without promotion to target final endorsement','object event direction and rule scope','real fact/law gaps versus model reading errors','point assessment explanation reason consistency','omitted opposition or indiscriminate unknown'],
        'not_given_to_model':True,'two_case_accuracy_ranking':False,
        'decision_options':['KEEP_LIGHT_PROPOSAL_AS_CANDIDATE','PRIORITIZE_D_PAUSE_MANDATORY_STRUCTURE','COMMON_UNDERSTANDING_INTEGRATION_FAILURE','SOURCE_GROUNDED_UNCERTAINTY_REAL_LAW_GAPS','MIXED_CASE_DIRECTIONS_NO_WINNER']})
    write_new(ROOT/'freeze/templates.json',{'final':FINAL,'examples':EXAMPLES,
        'dynamic_B_final':'final_v9.prompt(source,law,{"proposal":actual_new_B})'})
    for p in CODE:copy(Path(p),ROOT/'freeze/code'/p)
    write_new(ROOT/'freeze/config.json',{'settings':old['settings'],'actual_parameters':old['actual_parameters'],
        'constraint_mode':'FIXED','live_code':{p:digest(Path(p).read_bytes()) for p in CODE},
        'files':{str(p):digest(p.read_bytes()) for p in ROOT.rglob('*') if p.is_file()},'frozen_epoch':time.time()})

def verify():
    frozen=read(ROOT/'freeze/config.json')
    for p,h in {**frozen['files'],**frozen['live_code']}.items():assert digest(Path(p).read_bytes())==h,p
    return frozen

def run():
    from legal_bench.rules_verdict_v1.runtime_constraint_diag_v1 import Runner
    frozen=verify()
    assert not (ROOT/'results.json').exists() and not (ROOT/'runs').exists(),'Do not duplicate completed or partial attempts'
    runner=Runner(Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),frozen['settings'])
    preflight={}
    for c in CASES:
        for m in ['D','B-proposal']:
            text=(ROOT/'prepared'/c/m/'prompt.txt').read_text()
            preflight[c+'/'+m]=len(runner.tokenizer.encode(runner.render(text)))
    write_new(ROOT/'freeze/actual-load-preflight.json',{'input_tokens':preflight,
        'max_tokens':3072,'dynamic_B_final_full_budget_checked_before_call':True,
        'versions':runner.versions,'model_config_hash':runner.model_config_hash,'loaded_seconds':runner.loaded_seconds})
    began=time.monotonic();rows=[];proposals={};stop=None;calls=0
    for c,m in ORDER:
        verify();out=ROOT/'runs'/c/m
        if stop or (m=='B-P' and c not in proposals):
            row={'run_status':'SKIPPED','answer_status':None,'reason':stop or 'CURRENT_B_PROPOSAL_TECHNICAL_FAILURE'}
            write_new(out/'run.json',row)
        elif 1800-(time.monotonic()-began)<=0:
            stop='SHARED_TIME_BUDGET_EXHAUSTED';row={'run_status':'SKIPPED','answer_status':None,'reason':stop};write_new(out/'run.json',row)
        else:
            source,law=inputs(c)
            schema=read(ROOT/'prepared'/c/('proposal-schema.json' if m=='B-proposal' else 'final-schema.json'))
            material={} if m=='D' else {'proposal':proposals[c]} if m=='B-P' else None
            if m=='B-P':
                write_new(ROOT/'prepared'/c/m/'intermediate.json',material)
                text=prompt(source,law,material)
            else:text=(ROOT/'prepared'/c/m/'prompt.txt').read_text()
            if m=='D':write_new(ROOT/'prepared'/c/m/'intermediate.json',{})
            count=len(runner.tokenizer.encode(runner.render(text)))
            write_new(ROOT/'preflight'/c/(m+'.json'),{'input_tokens':count,'max_tokens':3072,
                'source_and_law_hashes':{'source':digest(source),'law':digest(law)},
                'prompt_hash':digest(text.encode()),'schema_hash':digest(schema),
                'source_truncated':False,'budget_ok':count+3072<=32768})
            row=runner.run(text,schema,out,3072,1800-(time.monotonic()-began),constraint_mode='FIXED')
            if 'output_tokens' in row:calls+=1
            if row['run_status'] in ['OUT_OF_MEMORY','UNSUPPORTED','TIMEOUT']:
                stop=c+'/'+m+':'+row['run_status']
            if row['run_status']=='OK':
                assert row['actual_parameters']==frozen['actual_parameters'] and row['schema_mask_calls']>0
                if m=='B-proposal':
                    proposals[c]=read(out/'parsed.json');write_new(ROOT/'intermediates'/f'{c}-proposal.json',proposals[c])
                    try:
                        checks,restored=check_facts(proposals[c],source)
                        write_new(ROOT/'offline-checks'/c/'full.json',checks)
                        write_new(ROOT/'offline-checks'/c/'restored-sources.json',restored)
                    except Exception as e:
                        write_new(ROOT/'offline-checks'/c/'failure.json',{'error':type(e).__name__+':'+str(e),'not_model_failure_or_semantic_repair':True})
        rows.append({'case':c,'slot':m,**row})
        write_new(ROOT/'progress'/f'{len(rows)}.json',{'rows':rows,'stop_reason':stop,'calls':calls})
    write_new(ROOT/'results.json',{'rows':rows,'new_model_calls':calls,'web_calls':0,'retries':0,
        'extra_model_pre_runs':0,'stop_reason':stop,'round_wall_seconds':time.monotonic()-began,
        'inference_seconds':sum(r.get('elapsed_seconds',0) for r in rows),
        'model_load_seconds':runner.loaded_seconds,'review_required':True})
    write_new(ROOT/'stop.json',{'reason':stop or 'SIX_SLOTS_FINISHED','extra_calls':0,
        'skipped':[r['case']+'/'+r['slot'] for r in rows if r['run_status']=='SKIPPED'],
        'no_auto_retry_next_round_commit_or_push':True})

if __name__=='__main__':{'prepare':prepare,'verify':verify,'run':run}[sys.argv[1]]()
