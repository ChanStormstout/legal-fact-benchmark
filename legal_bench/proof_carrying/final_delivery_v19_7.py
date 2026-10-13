"""Same V19_7 frozen semantics, complete final presentation and saved entry.

Post-P delivery snapshot: adds the missing mechanical SRC directory to every
final condition. No P prompt/schema, judgment policy or prediction is changed.
No generation is started by importing this module.
"""
from pathlib import Path
from . import local_pipeline_v19_7 as core
from .rule_contracts_v19_7 import digest

VERSION = core.VERSION
PRESENTATION_VERSION = 'V19_7_FINAL_PRESENTATION_1'


def task(case, rules, entry, method, part, prediction=None, full_rules=None):
    if method == 'B' and (prediction is None or prediction.get('case_id') != case['id']):
        raise ValueError('SELF_REVIEW_PRIOR_CASE_UNCONFIRMED')
    value = core.final_task(case,rules,entry,method,prediction,full_rules)
    ids = set(part['source_ids'])
    view = {**case, 'segments':[s for s in case['segments'] if s['id'] in ids]}
    if {s['id'] for s in view['segments']} != ids:
        raise ValueError('P_SOURCE_DIRECTORY_OUTSIDE_ALLOWED_CASE')
    aliases = [{'choice':r['choice'],'address':r['address']} for r in core.source_directory(view)]
    import json
    prefix = ('PROGRAM SOURCE ALIASES for the fixed P part '+part['id']+
              '. SRC:n is a source choice, not an original line number. '
              'The mapping verifies addresses only, not model semantics.\n'+json.dumps(aliases,separators=(',',':'))+'\n')
    value['prompt'] = prefix + value['prompt']
    value['input_sha256'] = digest({'prompt':value['prompt'],'schema':value['schema']})
    value['presentation_version'] = PRESENTATION_VERSION
    value['P_source_aliases'] = aliases
    return value


def run(case,rules,entry,method,part,dest,perform,prediction=None,full_rules=None):
    from scripts.proof_pipeline_contract_v19_7 import save,text,read,utc
    dest=Path(dest);value=task(case,rules,entry,method,part,prediction,full_rules)
    save(dest/'task.json',value);text(dest/'prompt.txt',value['prompt']);save(dest/'schema.json',value['schema'])
    if (dest/'formal-answer.json').exists():return read(dest/'formal-answer.json')
    if (dest/'start.json').exists():raise ValueError('UNKNOWN_SUBMISSION_STATE_NO_RESEND')
    save(dest/'start.json',{'version':VERSION,'presentation_version':PRESENTATION_VERSION,'started_at':utc(),'input_sha256':value['input_sha256']})
    try:
        raw,receipt=perform(value)
        text(dest/'raw-response.txt',raw);save(dest/'run.json',receipt)
        result=core.accept_final(value,raw,receipt['run_status'])
    except Exception as exc:
        failure={'run_status':'TECHNICAL_FAILURE','error':type(exc).__name__+':'+str(exc)}
        save(dest/'failure.json',failure)
        result=core.accept_final(value,'','TECHNICAL_FAILURE')
    save(dest/'formal-answer.json',result)
    return result
