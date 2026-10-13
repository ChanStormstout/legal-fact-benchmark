"""Premise-local V19 proposals. Model dependencies remain unverified assumptions."""
import copy,json
from collections import Counter
from . import local_pipeline_v18_recovery as old
from .local_pipeline_v17 import obj,arr,enum,STR,validate as legacy_validate,FINAL_SCHEMA,FINAL_INSTRUCTION,source_text
from .local_evaluation_v17 import LABELS,hash_value
from .source_contract_v19 import witness_location as source_match, catalog
from .reference_addresses_v19 import source_directory, contract as reference_contract, convert
from . import local_pipeline_v19_types as old_transport
from .object_types_v19 import compare as type_compare, contract as type_contract
STATES=old.STATES
STATUS=old.STATUS
sources=old.sources
packet=old.packet
compact_json=old.compact_json
compact_checks=old.compact_checks
display_material=old.display_material
DISPLAY_POLICY={**old.DISPLAY_POLICY,'version':'V19_DISPLAY_1'}

def directory(rules):
    result=old.directory(rules)
    for view,r in zip(result,rules):
        for key in ('stage','court_level'):view[key]=r.get(key)
    return result

def role_directory(rules):
    out=[]
    for r in rules:
        for p in r['premises']:
            for role,typ in p.get('variables',{}).items():
                explicit=r.get('slot_variables',{}).get(p['id'],{}).get(role)
                # No inferred equalities between slots. Type declarations are never variables.
                out.append({'address':p['id']+'::'+role,'premise_id':p['id'],'role':role,'type':typ,
                            'variable':explicit or p['id']+'::'+role,
                            'mapping_status':'RULE_DECLARED_VARIABLE' if explicit else 'LOCAL_ROLE_ONLY_NO_CROSS_PREMISE_EQUALITY'})
    return out

def validate(data,schema,path='$'):
    old_transport.validate(data,schema,path)
    import re
    defs=schema.get('$defs',{})
    def walk(value,spec,path):
        if '$ref' in spec:spec=defs[spec['$ref'].split('/')[-1]]
        if 'pattern' in spec and (not isinstance(value,str) or re.fullmatch(spec['pattern'],value) is None):raise ValueError('REFERENCE_NAMESPACE_SYNTAX:'+path)
        if isinstance(value,dict):
            for key,part in spec.get('properties',{}).items():
                if key in value:walk(value[key],part,path+'/'+key)
        elif isinstance(value,list):
            for i,item in enumerate(value):walk(item,spec.get('items',{}),path+'/'+str(i))
    walk(data,schema,path)

def schema(rules,case=None):
    result=old_transport.schema(rules,case)
    source={'type':'string','enum':[s['choice'] for s in source_directory(case)]} if case is not None else {'type':'string','pattern':r'^SRC:[1-9][0-9]*$'}
    def ref(prefix):return {'type':'string','pattern':'^'+prefix+r':[1-9][0-9]*$'}
    result['$defs']={'source_choice':source}
    unit=result['properties']['analyses']['items'];pp=unit['properties']
    for name in ('records','objects'):pp[name]['items']['properties']['refs']['items']={'$ref':'#/$defs/source_choice'}
    up=pp['uses']['items']['properties'];up['records']['items']=ref('EV');up['bindings']['items']['properties']['object']=ref('OBJ')
    up['witnesses']['items']['properties']['refs']['items']={'$ref':'#/$defs/source_choice'}
    jp=pp['judgments']['items']['properties'];jp['bindings']['items']['properties']['object']=ref('OBJ')
    for name in ('uses','opposition_uses'):jp[name]['items']=ref('USE')
    jp['components']['items']['properties']['alternatives']['items']['items']=ref('USE')
    lp=jp['necessary_limits']['items']['properties'];lp['component']={'type':'string','pattern':r'^(WHOLE_JUDGMENT|COMP:[1-9][0-9]*)$'};lp['refs']['items']={'$ref':'#/$defs/source_choice'}
    lk=result['properties']['object_links']['items']['properties']
    for name in ('left_object','right_object'):lk[name]=ref('OBJ')
    lk['refs']['items']={'$ref':'#/$defs/source_choice'}
    return result

INSTRUCTION='''Reconstruct fixed Q1 in English from only the unchanged allowed source and rule drafts. This is historical judgment reasoning reconstruction, not prospective prediction. Work LOCALLY by premise in the fixed work directory: finish a local analysis (records, objects, exact uses, whole-premise judgments and gaps) before starting another. Do not first build a global case-wide fact list. Do not repeat full rules or source paragraphs. A premise may have several object/arrangement judgments; do not collapse them into one case-wide state. Use EV:n for records, OBJ:n for objects, and USE:n for uses WITHIN EACH ANALYSIS. Code assigns n from the one-based array position; do not add duplicate ID fields. SRC:n selects only a source-directory entry and can never be used as an EV/OBJ/USE address. Internal IDs, hashes and versions are attached by code. Output compact complete JSON in the response body, without commentary or indentation. Missing analysis is NOT_ANALYZED, distinct from ANALYZED with UNKNOWN. No quota of facts and no requirement to find every premise TRUE. Keep decisive counterevidence, independent alternatives, source status and restrictions.
Each record attributes speaker, court/stage and the exact source. court_level and stage describe the particular recorded judgment, not automatically the court issuing the whole source document; write UNMAPPED if not established. A recorded document is not independently inspected original evidence. A party claim directly supports that the claim was made, not automatically the underlying event. Do not upgrade a lower-court finding to appellate adoption. A final disposition cannot prove itself. Object type/name equality or two missing values never establish identity. Bind at legal addresses only; explicit cross-analysis object_links require a specific source identity basis and remain MODEL_PROPOSED, not approved. Preserve different arrangements between the same people. Unknown objects remain gaps, not wildcard matches.
A use specifies ONE exact evidentiary connection: proposition, binding, stage and SUPPORT/OPPOSE/CONTEXT direction. SUPPORTED means that connection is grounded, including legitimate opposition, NOT the entire premise TRUE. Select REQUIRED source witnesses preserving negation, attribution and scope; code restores each selected fragment separately. SUPPLEMENTARY witnesses are independent. Cite only relevant source IDs, not every line of the judgment. Do not duplicate identical records within a unit; the same record can serve separate uses. Source is supplied by code; concise explanations normally need one or two sentences, without deleting substantive counterarguments.
Whole-premise state is a separate fallible model judgment. complete:true requires explicit coverage: components are ALL necessary parts of that judgment's basis; within a component alternatives are OR; each alternative is a bundle of USE:n addresses that must ALL remain available. These are your proposed evidentiary dependencies, not new legal rules. Background or partial support alone cannot establish the whole premise. Include opposing uses in opposition_uses and address them in basis. Rejecting an opposition use does not prove the positive proposition. Explain how directions relate to the EXACT proposition, especially negated propositions and reports of court findings; do not count votes. A use rejected later invalidates the component only if no independent compatible alternative remains. With unknown necessity, keep incomplete/UNKNOWN and a specific gap. Keep OPEN_TEXT as open interpretation; do not change rules, exceptions or legal conditions. Formal approval is NOT granted.
COMPLETE FICTIONAL EXAMPLE (unrelated facts/rule):
SYN:L1: Rowan claimed he did not enter Garden Z on Monday.
SYN:L2: The trial court found Rowan entered Garden Z on Monday.
SYN:L3: A witness saw Rowan leave Garden Z on Tuesday.
SYN.P1: The trial court made a finding of Monday entry; role actor:person. SYN.P2: Actual Monday entry is established independently of that court finding. SYN.P3: Appellate adoption of the finding; role actor:person.
EXAMPLE SOURCE DIRECTORY: SRC:1=SYN:L1, SRC:2=SYN:L2, SRC:3=SYN:L3.
EXAMPLE OUTPUT: {"analyses":[{"premise":"SYN.P1","analysis_status":"ANALYZED","records":[{"text":"Trial found Monday entry.","status":"COURT_FINDING","stage":"trial","court_level":"Trial Court","refs":["SRC:2"]},{"text":"Rowan denied Monday entry.","status":"PARTY_CLAIM","stage":"pleading","court_level":"UNMAPPED","refs":["SRC:1"]},{"text":"Witness saw Tuesday departure.","status":"TESTIMONY","stage":"trial","court_level":"Trial Court","refs":["SRC:3"]}],"objects":[{"label":"Rowan","type":"person","refs":["SRC:1","SRC:2"],"identity_basis":"Both statements explicitly identify Rowan in this garden dispute."}],"uses":[{"records":["EV:1"],"bindings":[{"address":"SYN.P1::actor","object":"OBJ:1"}],"direction":"SUPPORT","claim":"Report the trial's finding of Monday entry, not independent proof of entry.","stage":"trial","witnesses":[{"refs":["SRC:2"],"necessity":"REQUIRED"}],"self_assessment":"SUPPORTED","limits":[]},{"records":["EV:2"],"bindings":[{"address":"SYN.P1::actor","object":"OBJ:1"}],"direction":"CONTEXT","claim":"Rowan denied entry; this does not deny that the court made the recorded finding.","stage":"pleading","witnesses":[{"refs":["SRC:1"],"necessity":"REQUIRED"}],"self_assessment":"SUPPORTED","limits":["Claim content is not independently established."]},{"records":["EV:3"],"bindings":[{"address":"SYN.P1::actor","object":"OBJ:1"}],"direction":"CONTEXT","claim":"Tuesday departure neither disproves Monday entry nor the making of the trial finding.","stage":"trial","witnesses":[{"refs":["SRC:3"],"necessity":"REQUIRED"}],"self_assessment":"SUPPORTED","limits":[]}],"judgments":[{"bindings":[{"address":"SYN.P1::actor","object":"OBJ:1"}],"uses":["USE:1","USE:2","USE:3"],"state":"TRUE","complete":true,"stage":"trial","basis":"L2 directly records the narrowly attributed finding. L1 is a denial of the event, not of the court having made its finding. L3 is about another date.","components":[{"description":"The attributed trial finding of Monday entry.","alternatives":[["USE:1"]]}],"opposition_uses":[],"gaps":[],"necessary_limits":[]}],"limits":[]},{"premise":"SYN.P2","analysis_status":"ANALYZED","records":[],"objects":[],"uses":[],"judgments":[{"bindings":[],"uses":[],"state":"UNKNOWN","complete":false,"stage":"trial","basis":"The event, its denial, and the report of a finding are distinct propositions; independent proof is not supplied here.","components":[],"opposition_uses":[],"gaps":["Independent event evidence and acceptance policy."],"necessary_limits":[]}],"limits":[]},{"premise":"SYN.P3","analysis_status":"NOT_ANALYZED","records":[],"objects":[],"uses":[],"judgments":[],"limits":["No appellate record provided."]}],"object_links":[],"coverage_limits":["No title or liability conclusion."]}
'''

def proposal_prompt(case,rules,part):
    selected=[r for r in rules if r['id'] in part['rule_ids']]
    view={**case,'segments':[s for s in case['segments'] if s['id'] in part['source_ids']]}
    notice='\nV19_4 REFERENCE CONTRACT:\n'+compact_json(reference_contract())+'\nALLOWED SOURCE ADDRESS DIRECTORY (one-based array position n has typed address SRC:n):\n'+compact_json([s['address'] for s in source_directory(view)])
    notice+='\nnecessary_limits: NOTE and STAGE_SCOPE are explanations, BLOCK_SCOPE is a specific missing prerequisite, and UNMAPPED is unclear scope. component is WHOLE_JUDGMENT or COMP:n for a declared component. Do not use SOURCE, EV, OBJ or USE addresses in that field. No note or source presence proves a premise.\n'
    return INSTRUCTION+notice+'\nFIXED REQUEST:\n'+compact_json(next(q for q in case['targets'] if q['id']=='Q1'))+'\nPART BOUNDARY:\n'+compact_json(part)+'\nUNCHANGED RULES AND PREMISE WORK DIRECTORY:\n'+compact_json(directory(selected))+'\nROLE ADDRESSES (TYPE IS NOT IDENTITY):\n'+compact_json(role_directory(selected))+'\nALLOWED SOURCE:\n'+source_text(view)+'\nOUTPUT SCHEMA:\n'+compact_json(schema(selected,view))

def adapt(raw,part_id):
    p={'records':[],'objects':[],'uses':[],'premises':[],'coverage_limits':list(raw['coverage_limits']),
       'analysis_units':[],'object_links':copy.deepcopy(raw['object_links']),'adapter_version':'V19_4'}
    for n,unit in enumerate(raw['analyses'],1):
        ro,oo,uo=len(p['records']),len(p['objects']),len(p['uses']);scope=part_id+':U'+str(n)
        p['analysis_units'].append({'scope':scope,'premise':unit['premise'],'status':unit['analysis_status'],'limits':unit['limits']})
        p['records'] += [copy.deepcopy(r) for r in unit['records']]
        p['objects'] += [{**copy.deepcopy(o),'part_scope':scope} for o in unit['objects']]
        def bs(bb):return [{**b,'object':b['object']+oo if 1<=b['object']<=len(unit['objects']) else 0} for b in bb]
        def ids(ii,kind):
            size,offset={'records':(len(unit['records']),ro),'uses':(len(unit['uses']),uo)}[kind]
            return [i+offset if 1<=i<=size else 0 for i in ii]
        for u in unit['uses']:
            p['uses'].append({**copy.deepcopy(u),'premise':unit['premise'],'records':ids(u['records'],'records'),'bindings':bs(u['bindings']),'unit_scope':scope})
        for j in unit['judgments']:
            z={**copy.deepcopy(j),'premise':unit['premise'],'bindings':bs(j['bindings']),'uses':ids(j['uses'],'uses'),
               'opposition_uses':ids(j['opposition_uses'],'uses'),'unit_scope':scope,'analysis_status':unit['analysis_status']}
            for c in z['components']:c['alternatives']=[ids(bundle,'uses') for bundle in c['alternatives']]
            p['premises'].append(z)
    return p

def merge_parts(parts):
    p={'records':[],'objects':[],'uses':[],'premises':[],'coverage_limits':[],'analysis_units':[],'object_links':[],'adapter_version':'V19_4'};ledger=[]
    for key,raw in parts:
        if raw is None:p['coverage_limits'].append('PART_UNAVAILABLE:'+key);ledger.append({'part':key,'status':'UNAVAILABLE'});continue
        z=adapt(raw,key);ro,oo,uo=len(p['records']),len(p['objects']),len(p['uses'])
        p['records']+=z['records'];p['objects']+=z['objects']
        for u in z['uses']:
            for b in u['bindings']:b['object']=b['object']+oo if b['object'] else 0
            u['records']=[i+ro if i else 0 for i in u['records']];p['uses'].append(u)
        for j in z['premises']:
            for b in j['bindings']:b['object']=b['object']+oo if b['object'] else 0
            for field in ('uses','opposition_uses'):j[field]=[i+uo if i else 0 for i in j[field]]
            for c in j['components']:c['alternatives']=[[i+uo if i else 0 for i in bundle] for bundle in c['alternatives']]
            p['premises'].append(j)
        for field in ('analysis_units','coverage_limits'):p[field]+=z[field]
        for link in z['object_links']:p['object_links'].append({**link,'declared_in_part':key,'identity_status':'MODEL_PROPOSED'})
        ledger.append({'part':key,'status':'COMPLETE','record_offset':ro,'object_offset':oo,'use_offset':uo})
    return p,ledger

def object_aliases(p,src):
    alias={i:i for i in range(1,len(p['objects'])+1)};checks=[]
    # Explicit links only: require unique address, real citations and common source basis.
    unit_pid={u['scope']:u['premise'] for u in p.get('analysis_units',[])}
    for link in p.get('object_links',[]):
        sides=[]
        for side in ('left','right'):
            scopes={o.get('part_scope') for o in p['objects'] if unit_pid.get(o.get('part_scope'))==link[side+'_premise']}
            objs=[i for i,o in enumerate(p['objects'],1) if unit_pid.get(o.get('part_scope'))==link[side+'_premise']] if len(scopes)==1 else []
            k=link[side+'_object'];sides.append(objs[k-1] if 1<=k<=len(objs) else None)
        errors=[];type_audit=None;pending=[]
        if None in sides:errors.append('OBJECT_LINK_ADDRESS_UNMAPPED')
        if not link.get('identity_basis') or not link.get('refs') or any(ref not in src for ref in link['refs']):errors.append('OBJECT_LINK_SOURCE_UNVERIFIED')
        if not errors:
            a,b=sides;oa,ob=p['objects'][a-1],p['objects'][b-1]
            type_audit=type_compare(oa.get('type'),ob.get('type'))
            if type_audit['status']=='EXPLICIT_TYPE_CONFLICT':errors.append('OBJECT_LINK_TYPE_CONFLICT')
            elif type_audit['status']=='UNMAPPED_DESCRIPTION':pending.append('OBJECT_LINK_TYPE_UNMAPPED')
            if not set(link['refs'])&set(oa['refs']) or not set(link['refs'])&set(ob['refs']):errors.append('OBJECT_LINK_BASIS_NOT_SHARED')
            if not errors and not pending:
                av,bv=alias[a],alias[b]
                for k in alias:
                    if alias[k]==bv:alias[k]=av
        checks.append({'proposal':link,'errors':errors,'pending':pending,'type_audit':type_audit,'accepted_for_conditional_binding':not errors and not pending,'semantic_approval':False})
    return alias,checks

def bind(bindings,objects,roles,pid,aliases):
    b,e=old.bind(bindings,objects,roles,pid)
    for row in bindings:
        role=roles.get(row['address']);index=row['object']
        if role and 0<index<=len(objects) and type_compare(objects[index-1].get('type'),role.get('type'))['status']=='EXPLICIT_TYPE_CONFLICT':e.append('OBJECT_TYPE_CONFLICT')
    return {k:aliases.get(v,v) for k,v in b.items()},e

def binding_type_audit(bindings,objects,roles,pid):
    rows=[]
    for row in bindings:
        role=roles.get(row['address']);index=row['object']
        if role and role['premise_id']==pid and type(index) is int and 0<index<=len(objects):
            rows.append({'address':row['address'],'object':index,**type_compare(objects[index-1].get('type'),role.get('type'))})
    return rows

def validate_predictions(rows,expected,manifest,input_hash):
    if manifest.get('version')!='V19_4' or manifest.get('class_order')!=list(LABELS) or manifest.get('input_sha256')!=input_hash:raise ValueError('PREDICTION_CONTRACT_OR_INPUT_MISMATCH')
    keys=[r['key'] for r in rows]
    if len(keys)!=len(set(keys)) or set(keys)!=set(expected):raise ValueError('PREDICTION_MISSING_DUPLICATE_OR_EXTRA_ID')
    import math
    if any(len(r.get('probabilities',[]))!=len(LABELS) or any(not math.isfinite(v) or v<0 or v>1 for v in r['probabilities']) or abs(sum(r['probabilities'])-1)>1e-4 for r in rows):raise ValueError('PREDICTION_PROBABILITIES_INVALID')
    return {r['key']:LABELS[max(range(len(LABELS)),key=lambda i:r['probabilities'][i])] for r in rows}

def apply_connection_decisions(case,rules,p,decisions=None):
    expected={'K%03d'%(i+1) for i in range(len(p['uses']))}
    if decisions is not None and set(decisions)!=expected:raise ValueError('PREDICTION_ID_COVERAGE_NO_P_FALLBACK')
    src=sources(case);aliases,linkchecks=object_aliases(p,src);roles={r['address']:r for r in role_directory(rules)}
    prem={x['id']:(x,r) for r in rules for x in r['premises']};checks=[]
    for i,u in enumerate(p['uses']):
        k='K%03d'%(i+1);pkg=packet(case,rules,p,i);errors=list(pkg['structural_input_limits']);warnings=[];b,ee=bind(u['bindings'],p['objects'],roles,u['premise'],aliases);errors+=ee
        spec,rule=prem.get(u['premise'],({},{}))
        type_rows=binding_type_audit(u['bindings'],p['objects'],roles,u['premise'])
        if not spec:errors.append('PREMISE_UNKNOWN')
        for o in pkg['objects']:
            if any(ref not in src for ref in o['refs']):errors.append('OBJECT_SOURCE_INVALID')
        scopechecks=[];full_eligible=True
        if any(x['status']=='UNMAPPED_DESCRIPTION' for x in type_rows):warnings.append('OBJECT_TYPE_UNMAPPED_UNVERIFIED_MODEL_BINDING_ASSUMPTION')
        for rec in pkg['records']:
            if any(ref not in src for ref in rec['refs']):errors.append('RECORD_SOURCE_INVALID')
            allowed=spec.get('allowed_statuses',[])
            if allowed and rec['status'] not in allowed:full_eligible=False;warnings.append('STATUS_NOT_FULL_PREMISE_BASIS')
            if rec['status'] in ('LEGAL_RULE','TARGET_DISPOSITION'):full_eligible=False;warnings.append('NOT_INDEPENDENT_CASE_FACT')
            # Rule stage is scope of legal use; do not assert every evidence item occurred there.
            scopechecks.append({'rule_stage':rule.get('stage'),'record_stage':rec.get('stage'),'record_court':rec.get('court_level'),
                                'status':'EXPLICIT_PREMISE_SCOPE_CHECK' if spec.get('stage') or spec.get('court_level') else 'RULE_SCOPE_RECORDED_SEMANTIC_COMPATIBILITY_UNVERIFIED'})
            for field in ('stage','court_level'):
                if spec.get(field):
                    if rec.get(field) in (None,'UNMAPPED'):full_eligible=False;warnings.append('SCOPE_UNMAPPED:'+field)
                    elif spec[field]!=rec[field]:errors.append('EXPLICIT_SCOPE_MISMATCH:'+field)
        locations=[]
        for w in u['witnesses']:
            loc=source_match(w,src)
            if loc.get('complete_quote_verified') is False:full_eligible=False;warnings.append('DISCONTINUOUS_QUOTE_NOT_COMPLETE_PREMISE_BASIS')
            locations.append({'witness':w,'location':loc})
            if loc.get('error'):(errors if w['necessity']=='REQUIRED' else warnings).append('WITNESS_'+loc['error'])
        if not any(w['necessity']=='REQUIRED' for w in u['witnesses']):errors.append('NO_REQUIRED_WITNESS')
        value=u['self_assessment'] if decisions is None else decisions[k]
        if value not in LABELS:raise ValueError('LABEL_INVALID')
        disposition='STRUCTURAL_INVALID' if errors else 'MODEL_REJECTED_USE' if value=='UNSUPPORTED' else 'MODEL_PENDING_USE' if value=='UNRESOLVED' else 'CONDITIONALLY_AVAILABLE_USE'
        checks.append({'connection_id':k,'premise':u['premise'],'binding':b,'direction':u['direction'],'P_label':u['self_assessment'],'applied_label':value,
                       'disposition':disposition,'errors':errors,'warnings':warnings,'locations':locations,'scope_checks':scopechecks,
                       'type_compatibility':type_rows,'type_coverage':'PENDING' if any(x['status']=='UNMAPPED_DESCRIPTION' for x in type_rows) else 'MAPPED',
                       'full_basis_eligible':full_eligible,'model_semantics_verified':False,'source_retained':True,'packet_hash':hash_value(pkg)})
    judgments=[]
    for i,j in enumerate(p['premises']):
        b,errors=bind(j['bindings'],p['objects'],roles,j['premise'],aliases);need={x['variable'] for x in roles.values() if x['premise_id']==j['premise']}
        type_rows=binding_type_audit(j['bindings'],p['objects'],roles,j['premise'])
        if set(b)!=need:errors.append('MISSING_OR_EXTRA_ROLE')
        def valid_use(k,basis=False):
            if not 1<=k<=len(checks):return False
            z=checks[k-1]
            return z['premise']==j['premise'] and all(b.get(var)==val for var,val in z['binding'].items()) and z['disposition']=='CONDITIONALLY_AVAILABLE_USE' and (not basis or (z['direction']!='CONTEXT' and z['full_basis_eligible']))
        ids=list(dict.fromkeys(j['uses']+j['opposition_uses']));available=[];blocked=[];pending=[]
        for k in ids:
            if not 1<=k<=len(checks):blocked.append({'index':k,'reason':'USE_INDEX_INVALID'});continue
            z=checks[k-1]
            if valid_use(k):available.append(z['connection_id'])
            elif z['disposition']=='MODEL_PENDING_USE':pending.append(z['connection_id'])
            else:blocked.append({'connection_id':z['connection_id'],'reason':'UNAVAILABLE_OR_BINDING_MISMATCH'})
        components=[]
        for component in j.get('components',[]):
            alternatives=[]
            for bundle in component['alternatives']:
                usable=bool(bundle) and all(k in j['uses'] and valid_use(k,True) for k in bundle)
                alternatives.append({'uses':bundle,'available':usable})
            components.append({'description':component['description'],'alternatives':alternatives,'covered':any(a['available'] for a in alternatives)})
        if not j['complete'] or not j['basis'] or not components:errors.append('WHOLE_PREMISE_DEPENDENCIES_UNESTABLISHED')
        if any(not c['covered'] for c in components):errors.append('NECESSARY_COMPONENT_WITHOUT_AVAILABLE_BASIS')
        if j.get('analysis_status')=='NOT_ANALYZED':errors.append('NOT_ANALYZED')
        limit_audit=limit_effects(j,src)
        state='UNKNOWN' if errors or limit_audit['blocked'] or limit_audit['scope_pending'] else j['state']
        judgments.append({'id':'J%03d'%(i+1),'premise':j['premise'],'binding':b,'stage':j['stage'],'model_state':j['state'],'conditional_state':state,
                          'errors':errors,'type_compatibility':type_rows,'unverified_type_assumptions':[x for x in type_rows if x['status']=='UNMAPPED_DESCRIPTION'],'necessary_limits':j['necessary_limits'],'limit_scope_audit':limit_audit,'available_uses':available,'blocked_uses':blocked,'pending_uses':pending,
                          'basis':j['basis'],'gaps':j['gaps'],'components':components,'opposition_uses':[{'index':k,'retained':True,'available':valid_use(k)} for k in j['opposition_uses']],
                          'direction_check':'EXACT_PROPOSITION_MODEL_BASIS_RETAINED; NO_SUPPORT_TO_TRUE_SHORTCUT; SEMANTICS_NOT_PROVED',
                          'assumption':'UNVERIFIED_MODEL_WHOLE_PREMISE_JUDGMENT_NOT_USE_VOTE'})
    return {'interface':'V19_4','object_type_policy':type_contract(),'checks':checks,'premise_judgments':judgments,'conditional_rules':old.compose(rules,judgments),
            'object_links':linkchecks,'analysis_units':p.get('analysis_units',[]),'raw_records_retained':len(p['records']),
            'raw_opposition_retained':[c for c in checks if c['direction']=='OPPOSE'],'limitations_retained':p['coverage_limits'],
            'approval':'NOT_GRANTED','reference_used':False,'rule_scope_policy':'Rule-level stage/court recorded in actual checks; only explicit premise restrictions are mechanically enforceable. No source-document stage inheritance.'}

def final_prompt(case,rules,intermediate):
    return 'Exact presentation aliases refer to earlier items in the same array. Intermediate material is fallible and unapproved.\nINTERMEDIATE MATERIAL:\n'+compact_json(intermediate)+'\nFIXED REQUEST:\n'+compact_json(next(q for q in case['targets'] if q['id']=='Q1'))+'\nGIVEN RULES:\n'+compact_json(directory(rules))+'\nCOMPLETE ALLOWED SOURCE:\n'+source_text(case)+'\nFINAL TASK:\n'+FINAL_INSTRUCTION+'\nOUTPUT SCHEMA:\n'+compact_json(FINAL_SCHEMA)

def learner_inputs(case,rules,p):
    data=old.learner_inputs(case,rules,p)
    # Intern repeated restored source, not semantic fields; all methods consume this same representation.
    shared=data['ce_pairs'][0]['shared_case_context'] if data['ce_pairs'] else {'raw_P':p,'rules':rules,'packets':data['materials'],'relations':[]}
    source_pool={s['id']:s for pkg in data['materials'].values() for s in pkg['actual_restored_source']['segments']}
    from .semantic_interface_v13 import recover
    all_refs=[]
    def collect(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key=='refs' and isinstance(item,list):all_refs.extend(item)
                else:collect(item)
        elif isinstance(value,list):
            for item in value:collect(item)
    collect(p)
    common_recovery=recover(case,list(dict.fromkeys(all_refs)))
    source_pool.update({s['id']:s for s in common_recovery['segments']})
    shared=copy.deepcopy(shared)
    for pkg in shared['packets'].values():
        pkg['actual_restored_source']['segments']=[{'source_pool_id':s['id']} for s in pkg['actual_restored_source']['segments']]
    shared['source_pool']=source_pool
    roles={x['address']:x for x in role_directory(rules)}
    type_view={'policy':type_contract(),'uses':[{'id':'K%03d'%(i+1),'bindings':binding_type_audit(u['bindings'],p['objects'],roles,u['premise'])} for i,u in enumerate(p['uses'])]}
    blocks=[{'id':'request','text':compact_json(shared.get('request',{}))},{'id':'P','text':compact_json(p)},{'id':'relations','text':compact_json(shared['relations'])},{'id':'object-type-contract','text':compact_json(type_view)}]
    blocks += [{'id':'rule:'+r['id'],'text':compact_json(r)} for r in rules]
    blocks += [{'id':'packet:'+k,'text':compact_json(pkg)} for k,pkg in shared['packets'].items()]
    blocks += [{'id':'source:'+k,'text':compact_json(s)} for k,s in source_pool.items()]
    common='\n'.join(b['id']+'\n'+b['text'] for b in blocks)
    for node in data['graph']['nodes']:
        if node['id']=='Q:Q1':node['text']=common
        elif node['id'].startswith('C:'):node['text']=compact_json(shared['packets'][node['id'][2:]])
    for pair in data['ce_pairs']:
        pair.pop('shared_case_context',None);pair['right']=compact_json(shared['packets'][pair['id']]);pair['shared_material_blocks']=blocks;pair['shared_material_hash']=hash_value(blocks)
    data['common_material_manifest']={'version':'V19_4','object_type_policy':type_contract()['version'],'saved_source_ids':sorted(source_pool),'planned_encoding_source_ids':sorted(source_pool),'actual_encoded_source_ids':None,'encoding_status':'PREPARED_NOT_YET_ENCODED','blocks':[{'id':b['id'],'sha256':hash_value(b['text']),'characters':len(b['text'])} for b in blocks],
                                     'shared_for':['RawP','Flat','CrossEncoder','RGCN'],'all_P_reference_recovery':common_recovery,'missing_context':[{'use':k,'limits':x['actual_restored_source']['limits']} for k,x in data['materials'].items()],
                                     'unique_source_characters':sum(len(s['text']) for s in source_pool.values()),'common_characters':len(common),'semantic_scope':'Only cited and fixed neighbouring source; no whole-document omission detection.'}
    return data


def limit_effects(j,src):
    rows=[];blocked=False;pending=False
    for lim in j.get('necessary_limits',[]):
        if isinstance(lim,str):rows.append({'original':lim,'kind':'UNMAPPED_LEGACY_NOTE','effect':'SCOPE_PENDING_NOT_REFUTED'});pending=True;continue
        kind=lim.get('kind');component=lim.get('component');valid=type(component) is int and 0<=component<=len(j.get('components',[]))
        source_valid=bool(lim.get('refs')) and all(r in src for r in lim['refs'])
        if kind=='BLOCK_SCOPE':
            if valid and source_valid and lim.get('reason'):blocked=True;effect='DECLARED_LOCAL_BLOCKER'
            else:pending=True;effect='BLOCKER_SCOPE_OR_SOURCE_PENDING'
        elif kind in ('NOTE','STAGE_SCOPE'):effect='RECORDED_QUALIFICATION_NOT_TRUTH_CHANGE'
        else:pending=True;effect='SCOPE_PENDING_NOT_REFUTED'
        rows.append({**lim,'effect':effect,'semantic_approval':False})
    return {'rows':rows,'blocked':blocked,'scope_pending':pending,'no_keyword_semantics':True}
