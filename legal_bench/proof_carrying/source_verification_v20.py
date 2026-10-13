"""Source-supported declarations, immutable supplements and conditional recomputation.
No reference files, training labels or case-specific branches are read here.
"""
import copy
import hashlib
import json
import re
from . import local_pipeline_v19_8 as core, local_checker_v19_8 as independent
from .local_pipeline_v17 import obj, arr, enum, STR
from .object_types_v19 import normalize
from .rule_contracts_v19_7 import digest
from .rule_contracts_v19_8 import validate_rules
from .schema_contract_v19_6 import validate

VERSION = 'SOURCE_VERIFICATION_V20_1'
LABELS = ('SUPPORTED', 'UNSUPPORTED', 'UNRESOLVED')
KINDS = ('OBJECT_BINDING', 'ATTRIBUTION', 'EVIDENCE_USE', 'PREMISE_BASIS')

def compact(x):
    return json.dumps(x, ensure_ascii=False, separators=(',', ':'))

def adapt_rules(rules):
    """Only explicit structure. Whole text is one component; no inferred equality."""
    result = copy.deepcopy(rules)
    for r in result:
        if all('input_contract' in p for p in r['premises']) and 'slot_variables' in r:
            continue
        supplied = r.get('slot_variables', {})
        r['slot_variables'] = {}
        r['unmapped_shared_variable_contract'] = len(r['premises']) > 1 and not supplied
        for p in r['premises']:
            raw = copy.deepcopy(p['variables'])
            p['original_variable_descriptions'] = raw
            p['variables'] = {k: normalize(v)['canonical'] or 'UNMAPPED' for k, v in raw.items()}
            # A role type is never interpreted as a variable address.
            m = supplied.get(p['id'], {})
            r['slot_variables'][p['id']] = {
                role: m[role] if isinstance(m.get(role), str) and m[role].startswith(r['id']+'::')
                else r['id']+'::'+re.sub('[^A-Za-z0-9_]', '_', p['id']+'_'+role)
                for role in raw}
            p['input_contract'] = {
                'fixed_proposition': p['text'], 'target_kind': 'UNMAPPED',
                'role_types': p['variables'], 'required_roles': list(raw), 'optional_roles': [],
                'components': [{'id': p['id']+'.K1', 'text': p['text']}],
                'whole_basis_statuses': list(p.get('allowed_statuses', [])),
                'semantic_approval': False, 'adaptation': 'WHOLE_EXISTING_PROPOSITION_NO_DECOMPOSITION'}
        r['input_contract_version'] = VERSION
    validate_rules(result)
    return result

# Self-evaluations are absent from the verification input and learner features.
# Judgment state/basis are the substantive claim being checked, not removed.
def hide_self(x):
    if isinstance(x, list): return [hide_self(v) for v in x]
    if isinstance(x, dict):
        return {k: hide_self(v) for k, v in x.items() if k not in
                ('self_assessment', 'verification_label', 'confidence', 'review_decision', 'reference_label')}
    return x

def declarations(raw, origin, rules):
    """Stable program addresses point to exact claims; IDs carry no truth labels."""
    out = []
    premises = {p['id']: p for r in rules for p in r['premises']}
    def add(path, kind, content, refs, dependencies=()):
        out.append({'id': origin+'/'+path, 'origin': origin, 'kind': kind,
                    'claim': hide_self(content), 'refs': sorted(set(refs)),
                    'dependencies': list(dict.fromkeys(dependencies)), 'approval': 'MODEL_PROPOSED'})
    for pid, u in raw.get('analyses', {}).items():
        records, objects, uses = u['records'], u['objects'], u['uses']
        def local(values, prefix, data):
            found=[]
            for v in values:
                match = re.fullmatch(prefix+r':([1-9][0-9]*)', v) if isinstance(v,str) else None
                if match and int(match[1]) <= len(data): found.append((int(match[1]),data[int(match[1])-1]))
            return found
        for i, rec in enumerate(records, 1):
            add(pid+'/EV:'+str(i), 'ATTRIBUTION', rec, rec['refs'])
        for coll,prefix in [('uses','USE'),('judgments','J')]:
            for i, row in enumerate(u[coll], 1):
                base=pid+'/'+prefix+':'+str(i);deps=[];refs=[]
                for role, ref in row['role_objects'].items():
                    if ref == 'UNMAPPED': continue
                    matches=local([ref],'OBJ',objects)
                    entity=matches[0][1] if matches else {'unresolved_object_address':ref}
                    key=base+'/ROLE:'+role
                    add(key,'OBJECT_BINDING',{'role':role,'object':entity,'target':premises[pid]['text'],
                        'scope':row.get('stage'),'proposed_local_address':ref},entity.get('refs',[]))
                    deps.append(origin+'/'+key);refs+=entity.get('refs',[])
                if coll=='uses':
                    ev=local(row['records'],'EV',records)
                    deps += [origin+'/'+pid+'/EV:'+str(n) for n,_ in ev]
                    refs += [w['source'] for w in row['witnesses']]
                    content={'fixed_proposition':premises[pid]['text'],'use':row,
                             'attributed_records':[r for _,r in ev]}
                    add(base,'EVIDENCE_USE',content,refs,deps)
                else:
                    for k,use in local(row['uses']+row['opposition_uses'],'USE',uses):
                        deps.append(origin+'/'+pid+'/USE:'+str(k));refs += [w['source'] for w in use['witnesses']]
                    add(base,'PREMISE_BASIS',{'fixed_proposition':premises[pid]['text'],'judgment':row},refs,deps)
    for i,link in enumerate(raw.get('object_links',[]),1):
        endpoints=[]
        for side in ('left','right'):
            u=raw['analyses'].get(link[side+'_premise'],{});ref=link[side+'_object']
            m=re.fullmatch(r'OBJ:([1-9][0-9]*)',ref)
            endpoints.append(u.get('objects',[])[int(m[1])-1] if m and int(m[1])<=len(u.get('objects',[])) else {'unmapped':ref})
        add('LINK:'+str(i),'OBJECT_BINDING',{'link':link,'endpoints':endpoints},link['refs'])
    return out

VERIFY_INSTRUCTION = '''Read the complete allowed source and the fixed legal propositions. Verify the precise original claims in P and check the neutral work directory for omissions. Do not consult external material or other answers. Return compact English JSON once.
Produce a versioned supplement containing only source-grounded alternative bindings, corrected attribution, evidence uses or premise bases needed to address unsupported/missing claims. Original P remains immutable. The supplement uses the exact P contract and every fixed analysis key; NOT_ANALYZED with empty lists is legitimate where there is no supplement. It is not a new legal rule or a manually approved answer. Never copy the whole source or enumerate irrelevant lines.
Give verdicts on the original declarations and on the supplement declarations. A declaration address is P/<premise>/EV:n for record attribution, P/<premise>/USE:n for a specific use, P/<premise>/J:n for a whole premise basis, or these last two followed by /ROLE:<role> for a role binding. P/LINK:n addresses an identity link. Replace P/ with Q/ for supplement declarations. n is one-based local position. Do not declare verdicts on nonexistent items; code validates these dynamic references. Include known contrary evidence in refs or counter_refs.
SUPPORTED means this exact attributed claim, connection, or basis is supported by the allowed evidence in its stated scope. UNSUPPORTED requires a clear attribution, object, direction, stage or scope error. Insufficient information or unresolved interpretation is UNRESOLVED. Valid opposition can be SUPPORTED without the opposed proposition being true. Background and partial support do not establish a whole premise. A court's stated interpretation is external semantic evidence, not proof this program independently derived the interpretation. Final disposition cannot prove itself.
No verdict grants review or legal approval. Do not invent old missing quotes or guess bad local references; propose a separately sourced new witness instead. Preserve counterarguments and unknowns. Do not rewrite rules, exceptions, fixed component meanings, or OPEN_TEXT. Runtime hashes and address offsets are assigned by code.
'''

def q_schema(rules, case):
    proposal_schema=core.schema(rules,case)
    definitions=proposal_schema.pop('$defs')
    result=obj({'supplement':proposal_schema, 'verdicts':arr(obj({
        'declaration':{'type':'string','pattern':r'^(P|Q)/.+$'},'label':enum(LABELS),
        'refs':{**arr(enum(s['choice'] for s in core.source_directory(case))), 'uniqueItems':True},
        'counter_refs':{**arr(enum(s['choice'] for s in core.source_directory(case))), 'uniqueItems':True},
        'reason':STR})), 'coverage_limits':arr()})
    result['$defs']=definitions
    return result

def verification_prompt(case,rules,p):
    part={'rule_ids':[r['id'] for r in rules],'source_ids':[s['id'] for s in case['segments']]}
    base=core.proposal_prompt(case,rules,part)
    return VERIFY_INSTRUCTION+'\nSHARED P CONTRACT AND FULL SOURCE:\n'+base+\
        '\nORIGINAL P (self-use labels hidden):\n'+compact(hide_self(p))+\
        '\nORIGINAL DECLARATION DIRECTORY:\n'+compact(declarations(p,'P',rules))+\
        '\nOutput object has supplement, verdicts, coverage_limits. The separately supplied schema is authoritative.'

def candidates(case,rules,p,q):
    """Read-only import. Bad verdicts remain audit records, never delete evidence."""
    ds=declarations(p,'P',rules)+declarations(q['supplement'],'Q',rules)
    by={d['id']:d for d in ds};src={s['choice']:s for s in core.source_directory(case)}
    accepted={};quarantined=[];duplicates=set()
    for v in q['verdicts']:
        k=v['declaration']
        if k in accepted: duplicates.add(k)
        if k not in by or v['label'] not in LABELS or any(x not in src for x in v['refs']+v['counter_refs']):
            quarantined.append({'verdict':v,'reason':'INVALID_DECLARATION_OR_SOURCE'});continue
        if v['label']!='UNRESOLVED' and not v['refs']:
            quarantined.append({'verdict':v,'reason':'NO_SOURCE_FOR_DECISIVE_VERDICT'});continue
        accepted[k]=v
    for k in duplicates:
        accepted.pop(k,None);quarantined.append({'declaration':k,'reason':'DUPLICATE_VERDICTS_NO_VOTE'})
    for d in ds:
        v=accepted.get(d['id']);d['proposed_label']=v['label'] if v else 'UNRESOLVED'
        # Evidence candidates are semantic proposals, not hidden reference-selected inputs.
        d['verification_refs']=(v['refs']+v['counter_refs']) if v else []
        d['verifier_reason']=v['reason'] if v else None
        d['semantic_input_complete']=all(x in src for x in d['refs'])
    return {'version':VERSION,'candidates':ds,'quarantined':quarantined,'source_sha256':digest(case['segments']),
            'original_P_sha256':digest(p),'Q_sha256':digest(q),'legal_approval':False}

def apply(case,rules,p,q,predictions=None):
    """Decline only the targeted use/binding/basis; keep full immutable sources."""
    pool=candidates(case,rules,p,q);ds=pool['candidates'];expected={d['id'] for d in ds}
    labels={d['id']:d['proposed_label'] for d in ds} if predictions is None else predictions
    if set(labels)!=expected or any(v not in LABELS for v in labels.values()):raise ValueError('PREDICTION_COVERAGE')
    raws={'P':copy.deepcopy(p),'Q':copy.deepcopy(q['supplement'])};changes=[]
    def decision(k):return labels.get(k,'UNRESOLVED')
    for origin,raw in raws.items():
        for pid,u in raw['analyses'].items():
            for prefix,collection in [('USE','uses'),('J','judgments')]:
                for i,row in enumerate(u[collection],1):
                    key=origin+'/'+pid+'/'+prefix+':'+str(i)
                    for role,ref in list(row['role_objects'].items()):
                        if ref!='UNMAPPED' and decision(key+'/ROLE:'+role)!='SUPPORTED':
                            row['role_objects'][role]='UNMAPPED'
                            changes.append({'declaration':key+'/ROLE:'+role,'effect':'LOCAL_BINDING_PENDING','original':ref})
                    if prefix=='USE':
                        deps=[origin+'/'+pid+'/EV:'+str(int(m[1])) for v in row['records']
                              if (m:=re.fullmatch(r'EV:([1-9][0-9]*)',v))]
                        value=decision(key)
                        if any(decision(d)!='SUPPORTED' for d in deps):value='UNRESOLVED'
                        row['self_assessment']=value
                        changes.append({'declaration':key,'effect':'USE_DECISION','value':value})
                    elif decision(key)!='SUPPORTED':
                        # Refusal of the claim does not mean the legal proposition is false.
                        row['state']='UNKNOWN';row['complete']=False
                        changes.append({'declaration':key,'effect':'WHOLE_BASIS_UNVERIFIED'})
        raw['object_links']=[v for i,v in enumerate(raw['object_links'],1) if decision(origin+'/LINK:'+str(i))=='SUPPORTED']
    parts=[];import_checks=[]
    for origin,raw in raws.items():
        canonical,ledger=core.convert(raw,case,'V19_8',rules)
        check=independent.check_import(raw,canonical,case,'V19_8',rules)
        if check['status']!='OK':raise ValueError('INDEPENDENT_IMPORT:'+compact(check))
        parts.append((origin,canonical));import_checks.append(check)
    merged,ledger=core.merge_parts(parts)
    merge_check=independent.check_merge(parts,merged)
    if merge_check['status']!='OK':raise ValueError('INDEPENDENT_MERGE')
    audit=core.apply_connection_decisions(case,rules,merged)
    check=independent.check(case,rules,merged,None,audit)
    if check['status']!='OK':raise ValueError('INDEPENDENT_COMPUTATION:'+compact(check))
    # No inferred shared-role contract or cross-production identity merges.
    limited=[]
    for route in audit['conditional_rules']:
        rule=next((r for r in rules if r['id']==route.get('rule_id')),None)
        if rule and rule.get('unmapped_shared_variable_contract'):
            route['conditional_result']='UNKNOWN';route['contract_limit']='SHARED_VARIABLE_MAPPING_NOT_DECLARED';limited.append(rule['id'])
    return {'version':VERSION,'pool':pool,'predictions':labels,'application_ledger':changes,
            'applied_proposals':raws,'canonical':merged,'audit':audit,'independent':check,
            'undeclared_shared_contracts':sorted(set(limited)),
            'structure_checked':True,'semantic_approval':False,'legal_approval':False,
            'assumption':'UNVERIFIED_MODEL_SOURCE_SEMANTICS'}

def common_inputs(case,rules,pool):
    """Exact common blocks and relations; label/reason/acceptance are not features."""
    directory=core.source_directory(case);src={s['choice']:s for s in directory}
    index={s['choice']:i for i,s in enumerate(directory)}
    candidates_=pool['candidates'];chosen=set()
    for d in candidates_:
        for ref in d['refs']+d['verification_refs']:
            if ref not in index:continue
            i=index[ref];chosen.add(i)
            for j in (i-1,i+1):
                if 0<=j<len(directory) and directory[j]['address'].split(':')[0]==directory[i]['address'].split(':')[0]:chosen.add(j)
    nodes=[{'id':'Q1','kind':3,'text':compact(next(q for q in case['targets'] if q['id']=='Q1'))}]
    nodes += [{'id':'S/'+s['choice'],'kind':0,'text':s['choice']+' | '+s['address']+'\n'+s['text']} for i,s in enumerate(directory) if i in chosen]
    nodes += [{'id':'R/'+r['id'],'kind':1,'text':compact(r)} for r in rules]
    nodes += [{'id':d['id'],'kind':2,'text':compact({'kind':d['kind'],'claim':d['claim'],'refs':d['refs'],'scope':'MODEL_PROPOSED'})} for d in candidates_]
    ix={n['id']:i for i,n in enumerate(nodes)};edges=[]
    for d in candidates_:
        edges.append((ix[d['id']],ix['Q1'],3))
        for ref in sorted(set(d['refs']+d['verification_refs'])):
            if 'S/'+ref in ix:edges.append((ix['S/'+ref],ix[d['id']],0))
        for dep in d['dependencies']:
            if dep in ix:edges.append((ix[dep],ix[d['id']],2))
        pid=d['id'].split('/')[1]
        for r in rules:
            if any(p['id']==pid for p in r['premises']):edges.append((ix['R/'+r['id']],ix[d['id']],1))
        use=d['claim'].get('use',{})
        # Sign is P/Q proposed direction, not verification output.
        if use.get('direction') in ('SUPPORT','OPPOSE'):
            rel=5 if use['direction']=='SUPPORT' else 6
            for dep in d['dependencies']:
                if dep in ix:edges.append((ix[dep],ix[d['id']],rel))
    edges=list(dict.fromkeys(edges));edges += [(b,a,r+8) for a,b,r in list(edges)]
    graph={'nodes':nodes,'edges':edges,'ids':[d['id'] for d in candidates_],
           'candidate_indices':[ix[d['id']] for d in candidates_],'request_indices':{'Q1':0}}
    blocks=[{'id':n['id'],'text':n['text']} for n in nodes]+[{'id':'RELATIONS','text':compact([{'from':nodes[a]['id'],'to':nodes[b]['id'],'type':r} for a,b,r in edges])}]
    h=digest(blocks)
    pairs=[{'id':d['id'],'left':nodes[ix[d['id']]]['text'],'shared_material_blocks':blocks,'shared_material_hash':h} for d in candidates_]
    return {'graph':graph,'ce_pairs':pairs,'input_sha256':h,'source_mapping':[s for i,s in enumerate(directory) if i in chosen],
            'coverage':{'allowed_source_units':len(directory),'restored_units':len(chosen),'encoded':False,
                        'P_Q_labels_and_verdict_reasons_removed':True,'full_document_omission_detection':False}}

def final_task(case,rules,method,p=None,q=None,predictions=None,prior_answer=None):
    from .local_pipeline_v19_refs import final_prompt
    from .presentation_v19_8_1 import pack,audit as presentation_check
    material={};trace=None
    if method=='B':
        if prior_answer is None:raise ValueError('A_DEPENDENCY_MISSING')
        material={'self_review':prior_answer}
    elif method=='C':
        if p is None:raise ValueError('P_DEPENDENCY_MISSING')
        material={'original_P_model_proposed':p}
    elif method in 'DEFG':
        if p is None or q is None:raise ValueError('P_Q_DEPENDENCY_MISSING')
        if method in 'EFG' and predictions is None:raise ValueError('PREDICTIONS_MISSING')
        trace=apply(case,rules,p,q,predictions)
        # One normalized semantic view; no repeated raw, restored source or check logs.
        material={'declarations':[{'id':d['id'],'kind':d['kind'],'claim':d['claim'],'refs':d['refs'],
                    'verification_refs':d['verification_refs'],'machine_decision':trace['predictions'][d['id']]} for d in trace['pool']['candidates']],
                  'premise_judgments':trace['audit']['premise_judgments'],'conditional_rules':trace['audit']['conditional_rules'],
                  'identity_checks':trace['audit']['object_links'],'coverage_limits':p['coverage_limits']+q['coverage_limits']+q['supplement']['coverage_limits'],
                  'assumption':'UNVERIFIED_MODEL_SOURCE_SEMANTICS; not legal approval; source can correct machine mistakes'}
    elif method!='A':raise ValueError('METHOD')
    encoded=pack(material)
    aliases=[{'alias':x['choice'],'source':x['address']} for x in core.source_directory(case)]
    prompt='Source aliases apply to intermediate declarations only. Final references use original source addresses.\n'+compact(aliases)+'\nV20 complete reconstruction. $exact_value points to the exact unchanged JSON value in exact_value_pool. Resolve aliases. Machine decisions are fallible conditional hypotheses; preserve contrary evidence.\n'+final_prompt(case,rules,encoded)
    return {'method':method,'prompt':prompt,'schema':core.FINAL_SCHEMA,'source_ids':[s['id'] for s in case['segments']],
            'rule_addresses':sorted({x for r in rules for x in [r['id'],*r.get('source_refs',[]),*[p['id'] for p in r['premises']]]}),
            'input_sha256':digest({'prompt':prompt,'schema':core.FINAL_SCHEMA}),
            'presentation_audit':presentation_check(material,encoded),'trace':trace}
