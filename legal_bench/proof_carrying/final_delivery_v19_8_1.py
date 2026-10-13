"""One final entry: full preparation, capacity, saved call and failure receipt.

This module never starts a model without an explicitly supplied runner. Actual
cost/token/elapsed data are retained from the runner, never inferred from mocks.
"""
import json
from pathlib import Path
from . import local_pipeline_v19_8 as core
from .rule_contracts_v19_7 import digest

VERSION=core.VERSION
DELIVERY_VERSION='V19_8_FINAL_DELIVERY_2'

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
    from .presentation_v19_8 import unpack as unpack_v1
    from .presentation_v19_8_1 import pack, audit as presentation_audit
    prefix,body=value['prompt'].split('INTERMEDIATE MATERIAL:\n',1)
    material,suffix=body.split('\nFIXED REQUEST:\n',1)
    original=unpack_v1(json.loads(material));encoded=pack(original)
    old_instruction='An object {"$exact_text":"TXT:n"} means the exact unchanged string in exact_text_pool. Resolve it as that string; it does not omit, summarize or approve content.\n'
    new_instruction='An object {"$exact_value":"VAL:n"} means the exact unchanged JSON value in exact_value_pool. Resolve it as that value. It does not omit, summarize or approve content; pool entries contain no further references.\n'
    if old_instruction not in prefix:raise ValueError('PRESENTATION_PREFIX_CONTRACT')
    prefix=prefix.replace(old_instruction,new_instruction)
    value['prompt']=prefix+'INTERMEDIATE MATERIAL:\n'+json.dumps(encoded,ensure_ascii=False,separators=(',',':'))+'\nFIXED REQUEST:\n'+suffix
    value['presentation_audit']=presentation_audit(original,encoded)
    value['delivery_version']=DELIVERY_VERSION
    value['input_sha256']=digest({'prompt':value['prompt'],'schema':value['schema']})
    value['P_source_aliases']=aliases
    return value

from .capacity_v19_8_1 import capacity

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
