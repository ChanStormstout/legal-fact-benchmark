"""One final entry: full preparation, capacity, saved call and failure receipt.

This module never starts a model without an explicitly supplied runner. Actual
cost/token/elapsed data are retained from the runner, never inferred from mocks.
"""
import json
from pathlib import Path
from . import local_pipeline_v19_8 as core
from .rule_contracts_v19_7 import digest

VERSION=core.VERSION

def task(case,rules,entry,method,part,prediction=None,full_rules=None):
    identifier=case.get('id',case.get('case_id'))
    if identifier is None or ('id' in case and 'case_id' in case and case['id']!=case['case_id']):raise ValueError('CASE_IDENTITY_CONTRACT')
    if method=='B' and (prediction is None or prediction.get('case_id')!=identifier):
        raise ValueError('SELF_REVIEW_PRIOR_CASE_UNCONFIRMED')
    value=core.final_task(case,rules,entry,method,prediction,full_rules)
    ids=set(part['source_ids']);view={**case,'segments':[s for s in case['segments'] if s['id'] in ids]}
    if {s['id'] for s in view['segments']}!=ids:raise ValueError('P_SOURCE_DIRECTORY_OUTSIDE_ALLOWED_CASE')
    aliases=[{'choice':r['choice'],'address':r['address']} for r in core.source_directory(view)]
    value['prompt']=('PROGRAM SOURCE ALIASES for '+part['id']+'. SRC:n is not an original line number. '
        'This checks addresses only, not semantics.\n'+json.dumps(aliases,separators=(',',':'))+'\n'+value['prompt'])
    value['input_sha256']=digest({'prompt':value['prompt'],'schema':value['schema']})
    value['P_source_aliases']=aliases
    return value

def capacity(value,tokenizer,config):
    messages=[{'role':'user','content':value['prompt']}]
    # Same pinned Qwen chat template and disabled thinking as the local runner.
    ids=tokenizer.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=False)
    count=len(ids)
    required=count+config['max_output_tokens']+config['template_margin']
    return {'input_tokens':count,'reserved_output_tokens':config['max_output_tokens'],
            'template_margin':config['template_margin'],'required_context':required,
            'context_budget':config['context_budget'],'fits':required<=config['context_budget'],
            'no_truncation':True,'model_loaded':False}

def run(case,rules,entry,method,part,dest,perform,prediction=None,full_rules=None,*,tokenizer,config):
    from scripts.proof_pipeline_contract_v19_8 import save,text,read,utc
    dest=Path(dest)
    if (dest/'formal-answer.json').exists():return read(dest/'formal-answer.json')
    if (dest/'start.json').exists():raise ValueError('UNKNOWN_SUBMISSION_STATE_NO_RESEND')
    began=utc();phase='PREPARATION';value=None;raw=None
    try:
        value=task(case,rules,entry,method,part,prediction,full_rules)
        save(dest/'task.json',value);text(dest/'prompt.txt',value['prompt']);save(dest/'schema.json',value['schema'])
        check=capacity(value,tokenizer,config);save(dest/'capacity.json',check)
        if not check['fits']:
            receipt={'run_status':'INPUT_TOO_LONG','submitted':False,'phase':'CAPACITY','capacity':check,
                     'started_at':began,'completed_at':utc()}
            result=core.accept_final(value,'',receipt['run_status'])
        else:
            phase='RUNNER'
            save(dest/'start.json',{'version':VERSION,'started_at':began,'input_sha256':value['input_sha256']})
            raw,receipt=perform(value)
            if not isinstance(raw,str) or not isinstance(receipt,dict) or 'run_status' not in receipt:
                raise ValueError('RUNNER_RECEIPT_CONTRACT')
            text(dest/'raw-response.txt',raw)
            save(dest/'runner-receipt.json',receipt)
            phase='ACCEPTANCE';result=core.accept_final(value,raw,receipt['run_status'])
    except Exception as exc:
        receipt={'run_status':'TECHNICAL_FAILURE','error':type(exc).__name__+':'+str(exc),'phase':phase,
                 'submitted':False if phase=='PREPARATION' else None,
                 'submission_state':'NOT_SUBMITTED' if phase=='PREPARATION' else 'UNKNOWN_AFTER_CALLBACK_OR_ACCEPTANCE_FAILURE',
                 'started_at':began,'completed_at':utc(),'tokens':None,'cost':None}
        save(dest/'failure.json',receipt)
        result=core.accept_final(value,'',receipt['run_status']) if value else {
            'version':VERSION,'method':method,'answer':None,'technical_status':'TECHNICAL_FAILURE',
            'contract_status':'PREPARATION_FAILED','legal_approval':False,'semantic_evaluation':'NOT_DONE'}
    # A durable receipt exists even if preparation or the callback failed.
    save(dest/'run.json',receipt)
    result['run_status']=receipt['run_status'];result['failure_phase']=receipt.get('phase')
    save(dest/'formal-answer.json',result)
    return result
