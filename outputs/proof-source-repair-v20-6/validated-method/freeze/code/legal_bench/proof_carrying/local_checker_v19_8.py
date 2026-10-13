"""Independent full conversion/merge/trace checks. No producer functions imported.

Shared vocabulary and source locator are permitted; expected transformation,
offsets, judgments and rule routes are recomputed here.
"""
import copy
import itertools
import json
import re
from collections import Counter
from .source_contract_v19 import witness_location as source_match
from .object_types_v19 import normalize as normalize_type


def differences(expected, actual, path='$'):
    if type(expected) is not type(actual): return [path + ':TYPE']
    if isinstance(expected, dict):
        out = [path + ':KEYS'] if set(expected) != set(actual) else []
        for k in expected.keys() & actual.keys(): out += differences(expected[k], actual[k], path+'/'+k)
        return out
    if isinstance(expected, list):
        out = [path + ':COUNT'] if len(expected) != len(actual) else []
        for i in range(min(len(expected), len(actual))): out += differences(expected[i], actual[i], path+'/'+str(i))
        return out
    return [] if expected == actual else [path + ':VALUE']


def expected_conversion(raw, case, version, rules):
    src = {'SRC:'+str(i): s for i,s in enumerate(case['segments'],1)}
    out = copy.deepcopy(raw)
    out['analyses'] = [{**copy.deepcopy(u), 'premise': pid} for pid,u in raw['analyses'].items()]
    definitions = {p['id']: p['input_contract'] for r in rules for p in r['premises']}
    def ordinal(v, prefix, count):
        m = re.fullmatch(prefix+r':([1-9][0-9]*)', v) if isinstance(v,str) else None
        return int(m[1]) if m and int(m[1]) <= count else 0
    def restore_refs(v):
        if isinstance(v, dict):
            for k,x in v.items():
                if k == 'refs': v[k] = [src[z]['id'] if z in src else 'UNMAPPED_SOURCE:'+str(z) for z in x]
                else: restore_refs(x)
        elif isinstance(v, list):
            for x in v: restore_refs(x)
    for unit in out['analyses']:
        for rec in unit['records']:
            rec['text'] = rec.pop('proposition')
            rec['text_origin'] = 'MODEL_INTERPRETATION_NOT_VERBATIM_SOURCE'
            rec['restored_source'] = [{'address':src[z]['id'], 'text':src[z]['text'],
                'source_document':src[z]['source_document'], 'original_line':src[z].get('original_line'),
                'origin':'PROGRAM_RESTORED_ORIGINAL'} for z in rec['refs'] if z in src]
        for row in unit['uses'] + unit['judgments']:
            mapping = row.pop('role_objects')
            row['bindings'] = [{'address':unit['premise']+'::'+role, 'object':ordinal(ref,'OBJ',len(unit['objects']))}
                               for role,ref in mapping.items() if ref != 'UNMAPPED']
        for use in unit['uses']:
            use['records'] = [ordinal(x,'EV',len(unit['records'])) for x in use['records']]
            for w in use['witnesses']:
                ref = w.pop('source'); w['refs'] = [ref]
                w['quote'] = src[ref]['text'] if ref in src else ''
                w['witness_origin'] = 'CODE_RESTORED_SOURCE_ANCHOR'; w['semantic_approval'] = False
        for j in unit['judgments']:
            for field in ('uses','opposition_uses'): j[field] = [ordinal(x,'USE',len(unit['uses'])) for x in j[field]]
            for c in j['components']:
                if version in ('V19_7','V19_8'):
                    fixed = {a['id']:a['text'] for a in definitions[unit['premise']]['components']}
                    c['description'] = fixed.get(c['component_id'],'UNMAPPED_COMPONENT')
                c['alternatives'] = [[ordinal(x,'USE',len(unit['uses'])) for x in b] for b in c['alternatives']]
            for limit in j['necessary_limits']:
                limit['component'] = 0 if limit['component'] == 'WHOLE_JUDGMENT' else ordinal(limit['component'],'COMP',len(j['components'])) or -1
                if limit['component'] == -1: limit['kind'] = 'UNMAPPED'
    for link in out['object_links']:
        for side in ('left','right'):
            rows = [u for u in out['analyses'] if u['premise'] == link[side+'_premise']]
            size = len(rows[0]['objects']) if len(rows) == 1 else 0
            link[side+'_object'] = ordinal(link[side+'_object'],'OBJ',size)
    restore_refs(out)
    for u in out['analyses']:
        for j in u['judgments']: j['limit_scope_audit'] = copy.deepcopy(j['necessary_limits'])
    return out


def check_import(raw, converted, case, version, rules):
    expected = expected_conversion(raw,case,version,rules)
    errors = differences(expected,converted)
    return {'status':'REJECTED' if errors else 'OK','errors':errors,'scope':'FULL_NESTED_CONVERSION_INCLUDING_LIMITS_AND_COMPLETE_WITNESSES','semantic_approval':False}


def expected_merge(parts):
    out = {'records':[],'objects':[],'uses':[],'premises':[],'coverage_limits':[], 'analysis_units':[], 'object_links':[], 'adapter_version':'V19_4'}
    for part, raw in parts:
        if raw is None:
            out['coverage_limits'].append('PART_UNAVAILABLE:'+part); continue
        for n,u in enumerate(raw['analyses'],1):
            scope = part+':U'+str(n); nr,no,nu = len(out['records']),len(out['objects']),len(out['uses'])
            out['analysis_units'].append({'scope':scope,'premise':u['premise'],'status':u['analysis_status'],'limits':copy.deepcopy(u['limits'])})
            out['records'] += copy.deepcopy(u['records'])
            out['objects'] += [{**copy.deepcopy(x),'part_scope':scope} for x in u['objects']]
            def bs(rows):
                return [{**x,'object':x['object']+no if 0<x['object']<=len(u['objects']) else 0} for x in rows]
            def ids(rows, count, offset): return [v+offset if 0<v<=count else 0 for v in rows]
            for x in u['uses']:
                out['uses'].append({**copy.deepcopy(x),'premise':u['premise'],'records':ids(x['records'],len(u['records']),nr),'bindings':bs(x['bindings']),'unit_scope':scope})
            for x in u['judgments']:
                row = {**copy.deepcopy(x),'premise':u['premise'],'bindings':bs(x['bindings']),'uses':ids(x['uses'],len(u['uses']),nu),
                       'opposition_uses':ids(x['opposition_uses'],len(u['uses']),nu),'unit_scope':scope,'analysis_status':u['analysis_status']}
                for c in row['components']: c['alternatives'] = [ids(b,len(u['uses']),nu) for b in c['alternatives']]
                out['premises'].append(row)
        out['coverage_limits'] += copy.deepcopy(raw['coverage_limits'])
        out['object_links'] += [{**copy.deepcopy(x),'declared_in_part':part,'identity_status':'MODEL_PROPOSED'} for x in raw['object_links']]
    return out


def check_merge(parts, merged):
    errors = differences(expected_merge(parts),merged)
    return {'status':'REJECTED' if errors else 'OK','errors':errors,'scope':'ALL_PARTS_FULL_CONTENT_AND_OFFSETS','semantic_approval':False}


def type_status(actual,expected):
    a,b=normalize_type(actual),normalize_type(expected)
    if not a['domain'] or not b['domain']: return 'UNMAPPED_DESCRIPTION'
    return 'COMPATIBLE_TYPE_DOMAIN' if set(a['domain']) & set(b['domain']) else 'EXPLICIT_TYPE_CONFLICT'

def check(case,rules,p,decisions,analysis):
    if len(analysis.get('checks',[])) != len(p['uses']) or len(analysis.get('premise_judgments',[])) != len(p['premises']):
        return {'status':'REJECTED','errors':['RESULT_COUNT'],'semantic_approval':False,'legal_approval':False}
    src={s['id']:{'document':s['source_document'],'original_line':s.get('original_line'),'text':s['text']} for s in case['segments']}
    specs={q['id']:(q,r) for r in rules for q in r['premises']};uses=[];errors=[]
    # Independently resolve explicit identities, without reading upstream aliases/errors.
    link_results=[]
    alias={i:i for i in range(1,len(p['objects'])+1)};units={u['scope']:u['premise'] for u in p.get('analysis_units',[])}
    for link in p.get('object_links',[]):
        ids=[]
        for side in ('left','right'):
            scopes={o.get('part_scope') for o in p['objects'] if units.get(o.get('part_scope'))==link[side+'_premise']}
            eligible=[i for i,o in enumerate(p['objects'],1) if units.get(o.get('part_scope'))==link[side+'_premise']] if len(scopes)==1 else []
            idx=link[side+'_object'];ids.append(eligible[idx-1] if 0<idx<=len(eligible) else None)
        link_errors=[];link_pending=[];type_audit=None
        if None in ids:link_errors.append('OBJECT_LINK_ADDRESS_UNMAPPED')
        if not link.get('identity_basis') or not link.get('refs') or any(ref not in src for ref in link['refs']):link_errors.append('OBJECT_LINK_SOURCE_UNVERIFIED')
        if not link_errors:
            a,b=ids;oa,ob=p['objects'][a-1],p['objects'][b-1]
            ts=type_status(oa.get('type'),ob.get('type'))
            type_audit={'actual':normalize_type(oa.get('type')),'expected':normalize_type(ob.get('type')),
                        'status':ts,'identity_established':False,'semantic_approval':False}
            if ts=='EXPLICIT_TYPE_CONFLICT':link_errors.append('OBJECT_LINK_TYPE_CONFLICT')
            elif ts=='UNMAPPED_DESCRIPTION':link_pending.append('OBJECT_LINK_TYPE_UNMAPPED')
            if not set(link['refs'])&set(oa['refs']) or not set(link['refs'])&set(ob['refs']):link_errors.append('OBJECT_LINK_BASIS_NOT_SHARED')
            if not link_errors and not link_pending:
                old=alias[b]
                for k in alias:
                    if alias[k]==old:alias[k]=alias[a]
        link_results.append({'proposal':link,'errors':link_errors,'pending':link_pending,'type_audit':type_audit,
            'accepted_for_conditional_binding':not link_errors and not link_pending,'semantic_approval':False})
    if analysis.get('object_links')!=link_results:errors.append('IDENTITY_AUDIT_FIDELITY')
    def binding(row):
        mapped={};ee=[];tt=[];spec,rule=specs.get(row['premise'],({},{}))
        for b in row['bindings']:
            role=b['address'].split('::')[-1];idx=b['object']
            if b['address']!=row['premise']+'::'+role or role not in spec.get('variables',{}):ee.append('ROLE');continue
            if not 0<idx<=len(p['objects']):ee.append('OBJECT');continue
            ob=p['objects'][idx-1]
            ts=type_status(ob.get('type'),spec['variables'][role]);tt.append({'address':b['address'],'object':idx,'status':ts,
                'actual':normalize_type(ob.get('type')),'expected':normalize_type(spec['variables'][role]),
                'identity_established':False,'semantic_approval':False})
            if ts=='EXPLICIT_TYPE_CONFLICT':ee.append('OBJECT_TYPE_CONFLICT')
            if not ob.get('identity_basis') or not ob.get('refs') or any(ref not in src for ref in ob['refs']):ee.append('OBJECT_SOURCE')
            var=rule.get('slot_variables',{}).get(row['premise'],{}).get(role) or row['premise']+'::'+role
            if var in mapped and mapped[var]!=alias[idx]:ee.append('OBJECT_CONFLICT')
            mapped[var]=alias[idx]
        return mapped,ee,tt
    for i,u in enumerate(p['uses'],1):
        b,ee,tt=binding(u);spec,rule=specs.get(u['premise'],({},{}));eligible=True
        if not spec:ee.append('PREMISE')
        for idx in u['records']:
            if not 0<idx<=len(p['records']):ee.append('RECORD');continue
            rec=p['records'][idx-1]
            if any(ref not in src for ref in rec['refs']):ee.append('RECORD_SOURCE')
            if rec['status'] not in spec['input_contract']['whole_basis_statuses']:eligible=False
            if rec['status'] in ('LEGAL_RULE','TARGET_DISPOSITION'):eligible=False
            for field in ('stage','court_level'):
                if spec.get(field):
                    if rec.get(field) in (None,'UNMAPPED'):eligible=False
                    elif rec[field]!=spec[field]:ee.append('SCOPE')
        required=[w for w in u['witnesses'] if w['necessity']=='REQUIRED']
        if not required or any(source_match(w,src).get('error') for w in required):ee.append('REQUIRED_SOURCE')
        if any(source_match(w,src).get('complete_quote_verified') is False for w in required):eligible=False
        label=decisions['K%03d'%i] if decisions is not None else u['self_assessment']
        uses.append({'binding':b,'available':not ee and label=='SUPPORTED','bearing':not ee and label=='SUPPORTED' and eligible and u['direction']!='CONTEXT','premise':u['premise'],'errors':ee,'type_compatibility':tt,'full_basis_eligible':eligible,'direction':u['direction'],'label':label})
        upstream_use=analysis['checks'][i-1]
        expected_meta={'connection_id':'K%03d'%i,'premise':u['premise'],'binding':b,
                       'direction':u['direction'],'P_label':u['self_assessment'],'applied_label':label,
                       'full_basis_eligible':eligible,'model_semantics_verified':False,'source_retained':True}
        reason_map={'INVALID_ROLE_ADDRESS':'ROLE','OBJECT_INDEX_INVALID':'OBJECT',
            'OBJECT_IDENTITY_BASIS_MISSING':'OBJECT_SOURCE','OBJECT_SOURCE_INVALID':'OBJECT_SOURCE',
            'RECORD_INDEX_INVALID':'RECORD','RECORD_SOURCE_INVALID':'RECORD_SOURCE','PREMISE_UNKNOWN':'PREMISE',
            'OBJECT_CONFLICT':'OBJECT_CONFLICT','OBJECT_TYPE_CONFLICT':'OBJECT_TYPE_CONFLICT',
            'NO_REQUIRED_WITNESS':'REQUIRED_SOURCE'}
        def reason_category(v):
            if v.startswith('EXPLICIT_SCOPE_MISMATCH:'):return 'SCOPE'
            if v.startswith('WITNESS_'):return 'REQUIRED_SOURCE'
            return reason_map.get(v,'UNRECOGNIZED_REASON:'+v)
        if {reason_category(v) for v in upstream_use.get('errors',[])}!=set(ee):errors.append('USE_AUDIT_FIDELITY:'+str(i)+':error_categories')
        expected_disposition='STRUCTURAL_INVALID' if ee else 'MODEL_REJECTED_USE' if label=='UNSUPPORTED' else 'MODEL_PENDING_USE' if label=='UNRESOLVED' else 'CONDITIONALLY_AVAILABLE_USE'
        expected_meta['disposition']=expected_disposition
        for field,value in expected_meta.items():
            if upstream_use.get(field)!=value:errors.append('USE_AUDIT_FIDELITY:'+str(i)+':'+field)
        expected_scopes=[{'rule_stage':rule.get('stage'),'record_stage':p['records'][k-1].get('stage'),
                'record_court':p['records'][k-1].get('court_level'),
                'status':'EXPLICIT_PREMISE_SCOPE_CHECK' if spec.get('stage') or spec.get('court_level') else 'RULE_SCOPE_RECORDED_SEMANTIC_COMPATIBILITY_UNVERIFIED'}
                for k in u['records'] if 0<k<=len(p['records'])]
        if upstream_use.get('scope_checks')!=expected_scopes:errors.append('USE_AUDIT_FIDELITY:'+str(i)+':scope_checks')
        expected_locations=[{'witness':w,'location':source_match(w,src)} for w in u['witnesses']]
        if upstream_use.get('locations')!=expected_locations:errors.append('USE_AUDIT_FIDELITY:'+str(i)+':locations')

        if ([{'address':x['address'],'object':x['object'],'status':x['status']} for x in upstream_use.get('type_compatibility',[])]!=[{'address':x['address'],'object':x['object'],'status':x['status']} for x in tt] or
            (upstream_use['disposition']=='CONDITIONALLY_AVAILABLE_USE')!=uses[-1]['available'] or
            (upstream_use['disposition']=='CONDITIONALLY_AVAILABLE_USE' and upstream_use['full_basis_eligible'] and u['direction']!='CONTEXT')!=uses[-1]['bearing']):errors.append('USE_RECOMPUTATION_MISMATCH:K%03d'%i)
    states={};bindings={};judgment_results=[]
    for i,j in enumerate(p['premises'],1):
        b,ee,tt=binding(j);spec,rule=specs.get(j['premise'],({},{}))
        required={rule.get('slot_variables',{}).get(j['premise'],{}).get(role) or j['premise']+'::'+role for role in spec['input_contract']['required_roles']}
        if not required.issubset(b):ee.append('ROLE_COVERAGE')
        components=j.get('components',[])
        if not j['complete'] or not j['basis'] or not components:ee.append('COVERAGE')
        evaluated=[]
        for c in components:
            alternatives=[]
            for bundle in c['alternatives']:
                ok=bool(bundle)
                for k in bundle:
                    if k not in j['uses'] or not 0<k<=len(uses):ok=False;continue
                    u=uses[k-1]
                    if not u['bearing'] or u['premise']!=j['premise'] or any(b.get(v)!=val for v,val in u['binding'].items()):ok=False
                supports=ok and any(uses[k-1]['direction']=='SUPPORT' for k in bundle)
                refutes=ok and any(uses[k-1]['direction']=='OPPOSE' for k in bundle)
                alternatives.append({'uses':bundle,'available':ok,'supports':supports,'refutes':refutes})
            evaluated.append({'component_id':c.get('component_id'),'description':c['description'],
                'alternatives':alternatives,'covered':any(x['available'] for x in alternatives),
                'support_basis':any(x['supports'] for x in alternatives),'refuting_basis':any(x['refutes'] for x in alternatives)})
        if j['state']=='FALSE':
            if not any(c['refuting_basis'] for c in evaluated):ee.append('REFUTATION_BASIS')
        elif j['state']=='TRUE':
            if any(not c['support_basis'] for c in evaluated):ee.append('SUPPORT_BASIS')
        elif any(not c['covered'] for c in evaluated):ee.append('DEPENDENCY')
        for lim in j['necessary_limits']:
            if isinstance(lim,str):ee.append('LIMIT_SCOPE_PENDING');continue
            kind=lim.get('kind')
            if kind in ('BLOCK_SCOPE','UNMAPPED'):ee.append('LIMIT')
            elif kind not in ('NOTE','STAGE_SCOPE'):ee.append('LIMIT_SCOPE_PENDING')
        if j.get('analysis_status')=='NOT_ANALYZED':ee.append('LIMIT')
        contract=spec['input_contract']
        permitted_mode=j.get('basis_mode')=='ASSESS_FIXED_PROPOSITION' or (j.get('basis_mode')=='REPORT_STATEMENT_ONLY' and contract['target_kind']=='ATTRIBUTED_REPORT')
        if not permitted_mode:ee.append('CORRESPONDENCE_MODE')
        component_ids=[x.get('component_id') for x in j['components']]
        valid_ids={x['id'] for x in contract['components']}
        if len(component_ids)!=len(set(component_ids)) or any(x not in valid_ids for x in component_ids):ee.append('CORRESPONDENCE_ADDRESS')
        if j['state']=='TRUE' and set(component_ids)!=valid_ids:ee.append('CORRESPONDENCE_COVERAGE')
        if not component_ids:ee.append('CORRESPONDENCE_EMPTY')
        st='UNKNOWN' if ee else j['state'];key='J%03d'%i;states[key]=st;bindings[key]=b
        upstream=next((x for x in analysis['premise_judgments'] if x['id']==key),None)
        diff=upstream is None or upstream['conditional_state']!=st or upstream['binding']!=b
        if upstream is not None:
            retained={'premise':j['premise'],'stage':j['stage'],'model_state':j['state'],
                      'basis':j['basis'],'gaps':j['gaps'],'necessary_limits':j['necessary_limits'],
                      'components':evaluated,'type_compatibility':tt,
                      'unverified_type_assumptions':[x for x in tt if x['status']=='UNMAPPED_DESCRIPTION'],
                      'assumption':'UNVERIFIED_MODEL_WHOLE_PREMISE_JUDGMENT_NOT_USE_VOTE'}
            def available(k):
                return 0<k<=len(uses) and uses[k-1]['available'] and uses[k-1]['premise']==j['premise'] and all(b.get(v)==val for v,val in uses[k-1]['binding'].items())
            limit_rows=[];blocked=False;pending=False
            for lim in j['necessary_limits']:
                if isinstance(lim,str):
                    limit_rows.append({'original':lim,'kind':'UNMAPPED_LEGACY_NOTE','effect':'SCOPE_PENDING_NOT_REFUTED'});pending=True;continue
                kind=lim.get('kind');idx=lim.get('component');in_scope=type(idx) is int and 0<=idx<=len(j['components'])
                sourced=bool(lim.get('refs')) and all(ref in src for ref in lim['refs'])
                if kind=='BLOCK_SCOPE':
                    if in_scope and sourced and lim.get('reason'):blocked=True;effect='DECLARED_LOCAL_BLOCKER'
                    else:pending=True;effect='BLOCKER_SCOPE_OR_SOURCE_PENDING'
                elif kind in ('NOTE','STAGE_SCOPE'):effect='RECORDED_QUALIFICATION_NOT_TRUTH_CHANGE'
                else:pending=True;effect='SCOPE_PENDING_NOT_REFUTED'
                limit_rows.append({**lim,'effect':effect,'semantic_approval':False})
            retained['limit_scope_audit']={'rows':limit_rows,'blocked':blocked,'scope_pending':pending,'no_keyword_semantics':True}
            keys=list(dict.fromkeys(j['uses']+j['opposition_uses']))
            retained['available_uses']=['K%03d'%k for k in keys if available(k)]
            retained['blocked_uses']=[];retained['pending_uses']=[]
            for k in keys:
                if not 0<k<=len(uses):retained['blocked_uses'].append({'index':k,'reason':'USE_INDEX_INVALID'})
                elif available(k):pass
                elif uses[k-1]['label']=='UNRESOLVED' and not uses[k-1]['errors']:retained['pending_uses'].append('K%03d'%k)
                else:retained['blocked_uses'].append({'connection_id':'K%03d'%k,'reason':'UNAVAILABLE_OR_BINDING_MISMATCH'})

            retained['opposition_uses']=[{'index':k,'retained':True,'available':available(k)} for k in j['opposition_uses']]
            for field,value in retained.items():
                if upstream.get(field)!=value:errors.append('JUDGMENT_AUDIT_FIDELITY:'+key+':'+field)

        if diff:errors.append('PREMISE_RECOMPUTATION_MISMATCH:'+key)
        judgment_results.append({'id':key,'independently_recomputed_state':st,'binding':b,'errors':ee,'matches_upstream':not diff})
    if len(analysis['checks'])!=len(p['uses']) or len(analysis['premise_judgments'])!=len(p['premises']):errors.append('RESULT_COUNT')
    retained_top={'interface':'V19_8','analysis_units':p.get('analysis_units',[]),'raw_records_retained':len(p['records']),
                  'raw_opposition_retained':[a for a in analysis['checks'] if a['direction']=='OPPOSE'],
                  'limitations_retained':p['coverage_limits'],'approval':'NOT_GRANTED','reference_used':False}
    for key,value in retained_top.items():
        if analysis.get(key)!=value:errors.append('TOP_LEVEL_AUDIT_FIDELITY:'+key)

    traces=[];coverage=[]
    for r in rules:
        choices=[[x for x in judgment_results if p['premises'][int(x['id'][1:])-1]['premise']==q['id']] or [{'id':None,'binding':{},'independently_recomputed_state':'UNKNOWN'}] for q in r['premises']]
        total=1
        for rows in choices:total*=len(rows)
        rule_traces=[]
        for route in itertools.islice(itertools.product(*choices),1000):
            by_variable={}
            for row in route:
                for var,oid in row['binding'].items():
                    by_variable.setdefault(var,[])
                    if oid not in by_variable[var]:by_variable[var].append(oid)
            pending=[];conflicts=[]
            for var,oids in by_variable.items():
                if len(oids)>1:
                    domains=[set(normalize_type(p['objects'][idx-1].get('type'))['domain']) for idx in oids]
                    if all(domains) and not set.intersection(*domains):conflicts.append(var)
                    else:pending.append(var)
            vals=[]
            for q,row in zip(r['premises'],route):
                state=row['independently_recomputed_state']
                if q.get('expected')=='FALSE':state={'TRUE':'FALSE','FALSE':'TRUE'}.get(state,state)
                vals.append(state)
            state='UNKNOWN';op=r['operator'];winning=[]
            if op=='ALL' and not pending and not conflicts:state='FALSE' if 'FALSE' in vals else 'CONFLICTED' if 'CONFLICTED' in vals else 'TRUE' if vals and all(v=='TRUE' for v in vals) else 'UNKNOWN'
            elif op=='ANY':
                winning=[i for i,v in enumerate(vals) if v=='TRUE']
                state='TRUE' if winning else 'CONFLICTED' if 'CONFLICTED' in vals else 'FALSE' if vals and all(v=='FALSE' for v in vals) else 'UNKNOWN'
            if r.get('exceptions') and state=='TRUE':state='UNKNOWN'
            rule_traces.append({'rule_id':r['id'],'operator':op,'binding':{v:ids[0] for v,ids in by_variable.items() if len(ids)==1},
                'binding_candidates':by_variable,'branch_bindings':[row['binding'] for row in route],
                'identity_pending':pending,'explicit_type_conflicts':conflicts,
                'join_status':'INDEPENDENT_ALTERNATIVES' if op=='ANY' else 'EXPLICIT_TYPE_CONFLICT' if conflicts else 'IDENTITY_PENDING' if pending else 'CONNECTED',
                'winning_branch_inputs':[route[i]['id'] for i in winning],
                'inputs':[x['id'] for x in route],'slot_states':vals,'conditional_result':state,'not_executed':op not in ('ALL','ANY'),
                'exceptions':r.get('exceptions',[]),'limits':r.get('limits',[]),'enumeration_complete':total<=1000,
                'stage':r.get('stage'),'status':'CONDITIONAL_UNVERIFIED_MODEL_SEMANTICS'})
        traces+=rule_traces
        coverage.append({'rule_id':r['id'],'cartesian_routes':total,'routes_examined':len(rule_traces),
            'identity_pending_routes':sum(bool(t['identity_pending']) for t in rule_traces),
            'explicit_type_conflict_routes':sum(bool(t['explicit_type_conflicts']) for t in rule_traces),
            'retained_routes':len(rule_traces),'enumeration_complete':total<=1000})
    def bag(rows):return Counter(json.dumps(x,sort_keys=True,separators=(',',':')) for x in rows)
    if bag(traces)!=bag(analysis['conditional_rules']):errors.append('RULE_TRACE_MISSING_DUPLICATE_EXTRA_OR_CHANGED')
    if coverage!=analysis.get('rule_coverage'):errors.append('RULE_ENUMERATION_COVERAGE_CHANGED')
    return {'status':'REJECTED' if errors else 'OK','errors':errors,'source_use_checks':uses,'premise_checks':judgment_results,
            'expected_trace_count':len(traces),'rule_coverage':coverage,'semantic_approval':False,'legal_approval':False,
            'scope':'Conversion, merge, computed bindings/directions/basis/gaps/component dependencies and all bounded rule routes. Source meaning and model truth not proved.'}
