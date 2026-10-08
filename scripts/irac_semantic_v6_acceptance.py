"""One concentrated engineering gate and immutable historical replay."""
import json
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.irac_semantic_v6 import R, inputs, read, save, hf
from scripts.irac_semantic_v6_run import CODE, preserved
from legal_bench.irac_application.semantic_v6 import process, legacy_projection


def run():
    out=R/'engineering';out.mkdir(parents=True,exist_ok=True)
    test=subprocess.run([sys.executable,'-m','unittest','tests.test_irac_semantic_v6','tests.test_irac_contract_v5_run','tests.test_mlx_constraint_v2','-v'],text=True,capture_output=True)
    (out/'tests.txt').write_text(test.stdout+test.stderr)
    assert test.returncode==0,test.stdout+test.stderr
    fixture=read(out/'real-tokenizer.json');assert fixture['passed'] and fixture['model_calls']==0
    replay=[]
    for cid in ('112400','188721101'):
        m,t,l,sm=inputs(cid);origin=Path('outputs/irac-contract-repair-v5/continuation-01/runs')/cid/'P'
        raw=read(origin/'result.json')['prediction'];projection=legacy_projection(raw,t)
        imp,c=process(projection,t,m,l)
        save(out/'replay'/cid/'mapping.json',projection);save(out/'replay'/cid/'import.json',imp);save(out/'replay'/cid/'checks-full.json',c)
        assert len(imp['records'])==len(raw['evidence'])
        replay.append({'case_id':cid,'raw_origin':str(origin/'raw-response.txt'),'raw_sha256':hf(origin/'raw-response.txt'),
                       'records_preserved':len(imp['records']),'quarantines':len(imp['quarantine']),
                       'original_model_summaries':len(raw['conditions']),
                       'new_condition_statuses':[r['program_input_state']['status'] for r in c['conditions']],
                       'new_case_answer':False,'migration':'Address/index mapping only; no inferred judgment from edge sign. Old legal answers unchanged.'})
    save(out/'replay-summary.json',replay)
    assert preserved()['passed']
    result={'E':'PASS','model_calls':0,'tests_command':test.args,'tests_returncode':0,
            'tokenizer_fixtures':len(fixture['rows']),'replay':replay,
            'code_hashes':{p:hf(p) for p in CODE},'semantic_correctness_verified':False,
            'limits':'Tests certify declared interface handling and source delivery, not the meaning of model proposals or legal answers.'}
    save(out/'acceptance.json',result);print('E PASS; ready to freeze')


if __name__=='__main__':run()
