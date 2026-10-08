"""Complete synthetic parser/tokenizer fixtures; zero inference calls."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from transformers import AutoTokenizer
from lmformatenforcer import JsonSchemaParser
from legal_bench.mlx_json_constraint import tokenizer_data
from legal_bench.mlx_json_constraint_v2 import CompositeQuoteEnforcer
from legal_bench.irac_application.semantic_v6 import catalogue
from legal_bench.irac_application.semantic_v6_tasks import schema, prompt
from scripts.irac_semantic_v6 import R, inputs, save, read, hf


def run():
    path=Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip()
    tok=AutoTokenizer.from_pretrained(path,local_files_only=True)
    data=tokenizer_data(tok,tok.eos_token_id)
    rows=[]; budgets=[]
    for cid in ('112400','188721101'):
        m,t,l,sm=inputs(cid);sid=next(iter(m['sources']))
        for key in catalogue(t):
            value={'records':[{'text':'Synthetic fixture with a closed quote.', 'statement_status':'UNKNOWN','refs':[sid]}],
                   'arrangements':[{'description':'Synthetic arrangement.', 'refs':[sid]}],
                   'conditions':[{'arrangement':1,'condition':key,'assessment':'UNRESOLVED',
                                  'evidence':[{'record':1,'role':'UNRESOLVED','connection':'Syntax fixture only.'}],
                                  'law_refs':[],'explanation':'No case judgment in this fixture.','gaps':[]}],
                   'limitations':[], 'coverage_limits':['Fixture only.']}
            sc=schema('proposal',m,t,l)
            ids=tok.encode(json.dumps(value),add_special_tokens=False)
            mask=CompositeQuoteEnforcer(data,JsonSchemaParser(sc))
            for i,x in enumerate(ids):assert x in mask.get_allowed_tokens(ids[:i]).allowed_tokens,(cid,key,i)
            assert tok.eos_token_id in mask.get_allowed_tokens(ids).allowed_tokens
            assert json.loads(tok.decode(ids))==value
            rows.append({'case_schema':cid,'condition':key,'tokens':len(ids),'closed_json_eos_allowed':True})
        sc=schema('final',m,t,l)
        claim=next(c['id'] for c in t['claims'] if c['expression']['op']!='UNSUPPORTED')
        v={'answers':[{'claim_id':claim,'prediction':'PREDICT_DENY','conditions':[{
            'test_id':t['tests'][0]['id'],'binding_id':'synthetic','binding':'Fixture objects only.',
            'assessment':'UNRESOLVED','refs':[sid],'explanation':'Fixture does not state a real case result.'}],
            'opposition':{'record':'Fixture only.','refs':[],'response':'No legal judgment.'},'gaps':['Fixture.'],
            'reason':'Synthetic syntax check, not a case answer.','intermediate_correction':'None.'}]}
        ids=tok.encode(json.dumps(v),add_special_tokens=False);mask=CompositeQuoteEnforcer(data,JsonSchemaParser(sc))
        for i,x in enumerate(ids):assert x in mask.get_allowed_tokens(ids[:i]).allowed_tokens,(cid,'final',i)
        assert tok.eos_token_id in mask.get_allowed_tokens(ids).allowed_tokens
        rows.append({'case_schema':cid,'final_complete_request':True,'tokens':len(ids),'closed_json_eos_allowed':True})
        for stage,maxout in [('proposal',4096),('final',3072)]:
            text=prompt(stage,m,t,l,sm)
            rendered=tok.apply_chat_template([{'role':'user','content':text}],tokenize=False,add_generation_prompt=True,enable_thinking=False)
            n=len(tok.encode(rendered));assert n+maxout<=32768
            assert '<think>\n\n</think>' in rendered[-150:]
            budgets.append({'case_id':cid,'stage':stage,'template_input_tokens':n,'max_output':maxout,'total_within_32768':True,
                            'actual_runner_will_recheck_before_each_generation':True})
    save(R/'engineering/real-tokenizer.json',{'passed':True,'model_calls':0,'rows':rows,'budgets':budgets,
         'tokenizer_revision':Path(path).name,'constraint_sha256':hf('legal_bench/mlx_json_constraint_v2.py')})
    print('PASS',len(rows),'complete fixtures; no model load or inference')


if __name__=='__main__':run()
