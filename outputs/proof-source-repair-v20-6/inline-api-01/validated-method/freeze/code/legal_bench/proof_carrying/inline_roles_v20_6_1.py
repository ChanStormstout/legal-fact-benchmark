"""Role-first transport: code assigns local addresses, model supplies semantics.

No reference answers or case-specific entity corrections. Explicit entity keys
are model-proposed identity links, not identities inferred from matching labels.
"""
import copy
from . import source_repair_v20_6 as repair
from . import local_pipeline_v19_8 as core
from . import evidence_binding_gate_v20_5 as binding
from .schema_contract_v19_6 import validate
from .rule_contracts_v19_7 import digest

VERSION = 'V20_6_1_INLINE_ROLE_SOURCE_REPAIR'


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties),
        'additionalProperties': False}


def text():
    return {'type': 'string', 'minLength': 1}


def arr(items, maximum=256, minimum=0):
    return {'type': 'array', 'items': items, 'minItems': minimum, 'maxItems': maximum,
        'uniqueItems': True}


def task(case, rules, part):
    selected=[r for r in rules if r['id'] in part['rule_ids']]
    view={**case,'segments':[s for s in case['segments'] if s['id'] in part['source_ids']]}
    original=core.schema(selected,view)
    definitions={'source_choice':{'type':'string','enum':binding.citation_choices(view)}}
    refs=arr({'$ref':'#/$defs/source_choice'},len(definitions['source_choice']['enum']))
    units={}
    for rule in selected:
        for p in rule['premises']:
            pid=p['id'];old=original['properties']['analyses']['properties'][pid]['properties']
            object_type=old['objects']['items']['properties']['type']
            roles={}
            for role in p['variables']:
                expected=binding.role_types(selected)[pid][role]
                type_spec=copy.deepcopy(object_type)
                # An explicit known type constrains a mapped value. Unknown role
                # descriptions remain unknown rather than guessed from names.
                if expected!='UNMAPPED':
                    allowed=[v for v in type_spec['enum']
                        if binding.compare(v,expected)['status']!='EXPLICIT_TYPE_CONFLICT']
                    type_spec['enum']=allowed
                roles[role]=obj({'value':text(),'type':type_spec,'refs':copy.deepcopy(refs),
                    'identity_basis':text(),'entity_key':text()})
            evidence=copy.deepcopy(old['records']['items'])
            evidence['properties'].update({'direction':{'type':'string','enum':['SUPPORT','OPPOSE','CONTEXT']},
                'component_ids':arr({'type':'string','enum':[c['id'] for c in p['input_contract']['components']]}),
                'application':text()})
            evidence['required'] += ['direction','component_ids','application']
            units[pid]=obj({'roles':obj(roles),'evidence':arr(evidence),
                'state':copy.deepcopy(old['judgments']['items']['properties']['state']),
                'stage':text(),'basis':text(),'gaps':arr(text(),8),
                'necessary_limits':copy.deepcopy(old['judgments']['items']['properties']['necessary_limits'])})
    schema=repair.metadata_schema(obj({'units':obj(units),'coverage_limits':arr(text(),8)}))
    schema['$defs']=definitions
    prompt=('''Read the COMPLETE allowed judgment and assess EVERY supplied fixed premise.
There is no previous answer or reference in this task. Fill each named role directly
with its particular entity/event, source refs and identity basis. Code assigns all
OBJ/EV/USE positions; never generate those positions yourself. Use actual names,
dates with event descriptions, amounts with units, and document purposes. Different
dates for different events must be different values. Do not call a party a property,
or a statutory word a person. A missing optional document can be UNMAPPED; a failed
search is not proof of nonexistence. Use value/type/entity_key UNMAPPED with refs=[]
when identity cannot be established. Otherwise refs must point to identifying text.
entity_key is your explicit same-entity claim: reuse it ONLY for the same real entity
or event across units; use distinct keys for different leases, dates or proceedings.
Each evidence item is one attributed proposition and its direction for this exact
premise. Preserve party submissions, reported lower-court findings, and adopted
appellate findings separately. Select the fixed component_ids this evidence bears;
context-only material can have component_ids=[]. Read beyond immediately relevant
passages to find contrary evidence. Court outcomes cannot prove themselves.
Assess the EXACT fixed proposition, not whether an objection was merely made. TRUE
requires source support for all necessary components; FALSE requires an actual
refuted component; UNKNOWN and CONFLICTED preserve missing/contradictory evidence.
Every unit is an assessment, including units genuinely left UNKNOWN after reading.
Write specific concise gaps; no repeated coverage paragraphs, copied examples or
format instructions. Do not enumerate the whole document as a support list.
All identities and legal assessments remain MODEL_PROPOSED, not legal approval.
\nFIXED REQUEST:\n'''+repair.compact(next(q for q in case['targets'] if q['id']=='Q1'))
        +'\nFIXED LEGAL RULES AND ROLE CONTRACTS:\n'+repair.compact(selected)
        +'\nCOMPLETE ALLOWED SOURCE:\n'+repair.sources(view)
        +'\nOUTPUT SCHEMA:\n'+repair.compact(schema))
    return {'version':VERSION,'prompt':prompt,'schema':schema,'original_schema':original,
        'case':view,'rules':selected,'part':part,'source_sha256':digest(view['segments']),
        'reference_used':False,'source_input_truncated':False,
        'previous_proposal_in_input':False,'local_addresses_assigned_by':'PROGRAM',
        'assessment_scope':'Every serialized unit assesses its supplied proposition; source correctness separately reviewed.'}


def expand(value, task):
    validate(value,task['schema'])
    raw={'analyses':{},'object_links':[],'coverage_limits':copy.deepcopy(value['coverage_limits'])}
    endpoints={}
    for pid,u in value['units'].items():
        objects=[];bindings={}
        for role,b in u['roles'].items():
            missing=b['value']=='UNMAPPED'
            if missing:
                if b['type']!='UNMAPPED' or b['refs'] or b['entity_key']!='UNMAPPED':
                    raise ValueError('INCONSISTENT_UNMAPPED_ROLE:'+pid+'/'+role)
                bindings[role]='UNMAPPED';continue
            if not b['refs'] or b['entity_key']=='UNMAPPED':
                raise ValueError('MAPPED_ROLE_WITHOUT_SOURCE_OR_EXPLICIT_IDENTITY:'+pid+'/'+role)
            objects.append({'label':b['value'],'type':b['type'],'refs':b['refs'],
                'identity_basis':b['identity_basis']+'; model entity key: '+b['entity_key']})
            address='OBJ:'+str(len(objects));bindings[role]=address
            endpoints.setdefault(b['entity_key'],[]).append((pid,address,b))
        records=[];uses=[];components={};opposition=[]
        for item in u['evidence']:
            records.append({k:copy.deepcopy(item[k]) for k in
                ('proposition','status','stage','court_level','refs')})
            use_id='USE:'+str(len(uses)+1)
            uses.append({'records':['EV:'+str(len(records))], 'role_objects':copy.deepcopy(bindings),
                'direction':item['direction'],'claim':item['application'],'stage':item['stage'],
                'witnesses':[{'source':r,'necessity':'REQUIRED'} for r in item['refs']],
                'self_assessment':'UNRESOLVED','limits':[]})
            for cid in item['component_ids']:
                components.setdefault(cid,[]).append([use_id])
            if item['direction']=='OPPOSE':opposition.append(use_id)
        judgment={'role_objects':bindings,'uses':['USE:'+str(i) for i in range(1,len(uses)+1)],
            'state':u['state'],'complete':bool(components), 'stage':u['stage'],'basis':u['basis'],
            'components':[{'component_id':cid,'alternatives':alternatives} for cid,alternatives in components.items()],
            'opposition_uses':opposition,'gaps':u['gaps'],'necessary_limits':u['necessary_limits'],
            'basis_mode':'ASSESS_FIXED_PROPOSITION'}
        raw['analyses'][pid]={'analysis_status':'ANALYZED','records':records,'objects':objects,
            'uses':uses,'judgments':[judgment],'limits':[]}
    for key,rows in endpoints.items():
        left=rows[0]
        for right in rows[1:]:
            if right[0]==left[0]:continue
            refs=list(dict.fromkeys(left[2]['refs']+right[2]['refs']))
            raw['object_links'].append({'left_premise':left[0],'left_object':left[1],
                'right_premise':right[0],'right_object':right[1], 'refs':refs,
                'identity_basis':'Explicit model same-entity key '+key+': '+left[2]['identity_basis']+' / '+right[2]['identity_basis']})
    validate(raw,task['original_schema'])
    return raw
