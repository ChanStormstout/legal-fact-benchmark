"""Provide actual original-object definitions to the exact whole-answer reviewer.

An opaque business ID is machine metadata; its original definition and primary
source must be available to verify identity. No acceptance condition is relaxed.
"""
from . import final_statement_pack_v20_9 as base
from . import final_bindings_v20_8 as bindings
from .artifact_state_v20_2 import digest

VERSION='V20_9_IDENTITY_REVIEW_MATERIAL_1'


def final_task(case,old,bridge,frame,frame_review,pack,pack_review):
    task=base.final_task(case,old,bridge,frame,frame_review,pack,pack_review)
    originals={d['id']:d['original'] for d in bridge['declarations'] if d['kind']=='OBJ'}
    used={x for r in frame['actors']+frame['properties'] for x in r['origin_object_ids']}
    if used-set(originals):raise ValueError('REVIEW_IDENTITY_DEFINITION_MISSING')
    evidence={'version':VERSION,'bridge_sha256':bridge['sha256'],
              'original_object_definitions':{k:originals[k] for k in sorted(used)},
              'source_aliases':{k:v for k,v in bindings.prior.source_map(case).items() if k.startswith('SRC:')},
              'frame_review_sha256':digest(frame_review)}
    v=task['review_proxy']['verification_task']
    v['review_context']['identity_review_evidence']=evidence
    v['input_sha256']=digest({k:v[k] for k in ('prompt','schema','review_context')})
    proxy=task['review_proxy'];proxy['input_sha256']=digest({k:x for k,x in proxy.items() if k!='input_sha256'})
    task['review_material_version']=VERSION
    task['input_sha256']=digest({k:x for k,x in task.items() if k!='input_sha256'})
    return task


verify_task=base.verify_task
render=base.render
accept_final=base.accept_final


def review_task(task,plan,case):
    rt=base.review_task(task,plan,case)
    rt['prompt']='''For origin_object_ids, independently compare each actual original
definition in request_and_rules.identity_review_evidence with the complete source
and new frame identity. Do not demand that a judgment literally print a machine
ID; do not accept an opaque ID without its definition either. The supplied source
aliases resolve old SRC addresses. An original object's erroneous old type does
not approve its old declaration; the NEW source-reviewed frame has its own type.
Retirement date, historical in-office occupation and post-retirement occupation
must remain separately scoped. No acceptance criterion is waived.\n'''+rt['prompt']
    return rt
