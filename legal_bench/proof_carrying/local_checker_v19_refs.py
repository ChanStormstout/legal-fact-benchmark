"""Independent source/binding/dependency rechecking. No proposer decision function import."""
from .source_contract_v19 import witness_location as source_match
from .object_types_v19 import normalize as normalize_type

def check_import(raw, converted, case, production_version):
    """Independently recompute typed-to-local conversion, not production audit flags."""
    import re
    errors=[]
    if production_version!='V19_4':
        # The legacy production contract is not reinterpreted as typed transport.
        for n,(a,b) in enumerate(zip(raw['analyses'],converted['analyses'])):
            for kind in ('records','objects','uses','judgments'):
                if len(a[kind])!=len(b[kind]):errors.append('LEGACY_RECORD_COUNT:'+str(n)+':'+kind)
            for a_use,b_use in zip(a['uses'],b['uses']):
                if a_use['records']!=b_use['records'] or a_use['bindings']!=b_use['bindings']:errors.append('LEGACY_CONNECTION_WAS_CHANGED')
            for aj,bj in zip(a['judgments'],b['judgments']):
                if any(aj[field]!=bj[field] for field in ('uses','opposition_uses','components','bindings')):errors.append('LEGACY_JUDGMENT_ADDRESS_WAS_CHANGED')
        return {'status':'REJECTED' if errors else 'OK','errors':errors,'legacy_policy':'NO_RENUMBERING_OR_GUESSED_CONNECTION_REPAIR','semantic_approval':False}
    def ordinal(value,prefix,size):
        match=re.fullmatch(prefix+r':([1-9][0-9]*)',value) if isinstance(value,str) else None
        return int(match[1]) if match and int(match[1])<=size else 0
    def compare(path,actual,expected):
        if actual!=expected:errors.append('REFERENCE_CONVERSION_MISMATCH:'+path)
    source_map={'SRC:'+str(i):s['id'] for i,s in enumerate(case['segments'],1)}
    def source_refs(a,b,path):
        if isinstance(a,dict):
            for key,value in a.items():
                if key=='refs':compare(path+'/refs',b.get('refs'),[source_map.get(x,'UNMAPPED_SOURCE:'+str(x)) for x in value])
                elif key=='witnesses':
                    expected=[(source_map.get(ref,'UNMAPPED_SOURCE:'+str(ref)),w['necessity']) for w in value for ref in w['refs']]
                    actual=[(ref,w['necessity']) for w in b.get(key,[]) for ref in w['refs']]
                    compare(path+'/witnesses',actual,expected)
                elif key in b:source_refs(value,b[key],path+'/'+key)
        elif isinstance(a,list):
            for i,(x,y) in enumerate(zip(a,b)):source_refs(x,y,path+'/'+str(i))
    source_refs(raw,converted,'')
    for n,(a,b) in enumerate(zip(raw['analyses'],converted['analyses'])):
        for kind in ('records','objects','uses','judgments'):
            compare(str(n)+'/'+kind+'/count',len(b[kind]),len(a[kind]))
        for k,(au,bu) in enumerate(zip(a['uses'],b['uses'])):
            compare(str(n)+'/uses/'+str(k)+'/records',bu['records'],[ordinal(x,'EV',len(a['records'])) for x in au['records']])
            compare(str(n)+'/uses/'+str(k)+'/objects',[x['object'] for x in bu['bindings']],[ordinal(x['object'],'OBJ',len(a['objects'])) for x in au['bindings']])
        for k,(aj,bj) in enumerate(zip(a['judgments'],b['judgments'])):
            compare(str(n)+'/judgments/'+str(k)+'/objects',[x['object'] for x in bj['bindings']],[ordinal(x['object'],'OBJ',len(a['objects'])) for x in aj['bindings']])
            for field in ('uses','opposition_uses'):compare(str(n)+'/judgments/'+str(k)+'/'+field,bj[field],[ordinal(x,'USE',len(a['uses'])) for x in aj[field]])
            for c,(ac,bc) in enumerate(zip(aj['components'],bj['components'])):
                compare(str(n)+'/components/'+str(c),bc['alternatives'],[[ordinal(x,'USE',len(a['uses'])) for x in z] for z in ac['alternatives']])
            for l,(al,bl) in enumerate(zip(aj['necessary_limits'],bj['necessary_limits'])):
                component=0 if al['component']=='WHOLE_JUDGMENT' else ordinal(al['component'],'COMP',len(aj['components'])) or -1
                compare(str(n)+'/limits/'+str(l),bl['component'],component)
                if component==-1 and bl['kind']!='UNMAPPED':errors.append('UNVERIFIED_LIMIT_SCOPE_WAS_DROPPED')
    for i,(a,b) in enumerate(zip(raw.get('object_links',[]),converted.get('object_links',[]))):
        for side in ('left','right'):
            scope=[u for u in raw['analyses'] if u['premise']==a[side+'_premise']]
            size=len(scope[0]['objects']) if len(scope)==1 else 0
            compare('object_links/'+str(i)+'/'+side,b[side+'_object'],ordinal(a[side+'_object'],'OBJ',size))
    return {'status':'REJECTED' if errors else 'OK','errors':errors,'typed_transport_recomputed':True,'semantic_approval':False,'legal_approval':False}

def type_status(actual,expected):
    # Recompute decision independently; share only declared vocabulary.
    a,b=normalize_type(actual),normalize_type(expected)
    if not a['domain'] or not b['domain']:return 'UNMAPPED_DESCRIPTION'
    if any(t in b['domain'] for t in a['domain']):return 'COMPATIBLE_TYPE_DOMAIN'
    return 'EXPLICIT_TYPE_CONFLICT'

def check(case,rules,p,decisions,analysis):
    src={s['id']:{'document':s['source_document'],'original_line':s.get('original_line'),'text':s['text']} for s in case['segments']}
    specs={q['id']:(q,r) for r in rules for q in r['premises']};uses=[];errors=[]
    # Independently resolve explicit identities, without reading upstream aliases/errors.
    alias={i:i for i in range(1,len(p['objects'])+1)};units={u['scope']:u['premise'] for u in p.get('analysis_units',[])}
    for link in p.get('object_links',[]):
        ids=[]
        for side in ('left','right'):
            scopes={o.get('part_scope') for o in p['objects'] if units.get(o.get('part_scope'))==link[side+'_premise']}
            eligible=[i for i,o in enumerate(p['objects'],1) if units.get(o.get('part_scope'))==link[side+'_premise']] if len(scopes)==1 else []
            idx=link[side+'_object'];ids.append(eligible[idx-1] if 0<idx<=len(eligible) else None)
        if None not in ids and link.get('identity_basis') and link.get('refs') and all(ref in src for ref in link['refs']):
            a,b=ids;oa,ob=p['objects'][a-1],p['objects'][b-1]
            if type_status(oa.get('type'),ob.get('type'))=='COMPATIBLE_TYPE_DOMAIN' and set(link['refs'])&set(oa['refs']) and set(link['refs'])&set(ob['refs']):
                old=alias[b]
                for k in alias:
                    if alias[k]==old:alias[k]=alias[a]
    def binding(row):
        mapped={};ee=[];tt=[];spec,rule=specs.get(row['premise'],({},{}))
        for b in row['bindings']:
            role=b['address'].split('::')[-1];idx=b['object']
            if b['address']!=row['premise']+'::'+role or role not in spec.get('variables',{}):ee.append('ROLE');continue
            if not 0<idx<=len(p['objects']):ee.append('OBJECT');continue
            ob=p['objects'][idx-1]
            ts=type_status(ob.get('type'),spec['variables'][role]);tt.append({'address':b['address'],'object':idx,'status':ts})
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
            if spec.get('allowed_statuses') and rec['status'] not in spec['allowed_statuses']:eligible=False
            if rec['status'] in ('LEGAL_RULE','TARGET_DISPOSITION'):eligible=False
            for field in ('stage','court_level'):
                if spec.get(field):
                    if rec.get(field) in (None,'UNMAPPED'):eligible=False
                    elif rec[field]!=spec[field]:ee.append('SCOPE')
        required=[w for w in u['witnesses'] if w['necessity']=='REQUIRED']
        if not required or any(source_match(w,src).get('error') for w in required):ee.append('REQUIRED_SOURCE')
        if any(source_match(w,src).get('complete_quote_verified') is False for w in required):eligible=False
        label=decisions['K%03d'%i] if decisions is not None else u['self_assessment']
        uses.append({'binding':b,'available':not ee and label=='SUPPORTED','bearing':not ee and label=='SUPPORTED' and eligible and u['direction']!='CONTEXT','premise':u['premise'],'errors':ee,'type_compatibility':tt})
        upstream_use=analysis['checks'][i-1]
        if ([{'address':x['address'],'object':x['object'],'status':x['status']} for x in upstream_use.get('type_compatibility',[])]!=tt or
            (upstream_use['disposition']=='CONDITIONALLY_AVAILABLE_USE')!=uses[-1]['available'] or
            (upstream_use['disposition']=='CONDITIONALLY_AVAILABLE_USE' and upstream_use['full_basis_eligible'] and u['direction']!='CONTEXT')!=uses[-1]['bearing']):errors.append('USE_RECOMPUTATION_MISMATCH:K%03d'%i)
    states={};bindings={};judgment_results=[]
    for i,j in enumerate(p['premises'],1):
        b,ee,tt=binding(j);spec,rule=specs.get(j['premise'],({},{}))
        required={rule.get('slot_variables',{}).get(j['premise'],{}).get(role) or j['premise']+'::'+role for role in spec.get('variables',{})}
        if set(b)!=required:ee.append('ROLE_COVERAGE')
        components=j.get('components',[])
        if not j['complete'] or not j['basis'] or not components:ee.append('COVERAGE')
        for c in components:
            viable=False
            for bundle in c['alternatives']:
                ok=bool(bundle)
                for k in bundle:
                    if k not in j['uses'] or not 0<k<=len(uses):ok=False;continue
                    u=uses[k-1]
                    if not u['bearing'] or u['premise']!=j['premise'] or any(b.get(v)!=val for v,val in u['binding'].items()):ok=False
                viable|=ok
            if not viable:ee.append('DEPENDENCY')
        for lim in j['necessary_limits']:
            if isinstance(lim,str):ee.append('LIMIT_SCOPE_PENDING');continue
            kind=lim.get('kind')
            if kind in ('BLOCK_SCOPE','UNMAPPED'):ee.append('LIMIT')
            elif kind not in ('NOTE','STAGE_SCOPE'):ee.append('LIMIT_SCOPE_PENDING')
        if j.get('analysis_status')=='NOT_ANALYZED':ee.append('LIMIT')
        st='UNKNOWN' if ee else j['state'];key='J%03d'%i;states[key]=st;bindings[key]=b
        upstream=next((x for x in analysis['premise_judgments'] if x['id']==key),None)
        diff=upstream is None or upstream['conditional_state']!=st or upstream['binding']!=b
        if diff:errors.append('PREMISE_RECOMPUTATION_MISMATCH:'+key)
        judgment_results.append({'id':key,'independently_recomputed_state':st,'binding':b,'errors':ee,'matches_upstream':not diff})
    traces=[];rd={r['id']:r for r in rules}
    for t in analysis['conditional_rules']:
        r=rd.get(t['rule_id']);ee=[];vals=[];merged={}
        if not r or len(t['inputs'])!=len(r['premises']):ee.append('RULE_ARITY')
        else:
            for spec,key in zip(r['premises'],t['inputs']):
                if key is not None and key not in states:ee.append('DEPENDENCY')
                if key is not None and p['premises'][int(key[1:])-1]['premise']!=spec['id']:ee.append('DEPENDENCY_TYPE')
                v=states.get(key,'UNKNOWN')
                if spec.get('expected')=='FALSE':v={'TRUE':'FALSE','FALSE':'TRUE'}.get(v,v)
                vals.append(v)
                for var,obj in bindings.get(key,{}).items():
                    if var in merged and merged[var]!=obj:ee.append('OBJECT_CONFLICT')
                    merged[var]=obj
            op=r['operator'];st='UNKNOWN'
            if op=='ALL':st='FALSE' if 'FALSE' in vals else 'CONFLICTED' if 'CONFLICTED' in vals else 'TRUE' if vals and all(v=='TRUE' for v in vals) else 'UNKNOWN'
            elif op=='ANY':st='TRUE' if 'TRUE' in vals else 'CONFLICTED' if 'CONFLICTED' in vals else 'FALSE' if vals and all(v=='FALSE' for v in vals) else 'UNKNOWN'
            if r.get('exceptions') and st=='TRUE':st='UNKNOWN'
            if vals!=t['slot_states'] or merged!=t['binding'] or st!=t['conditional_result'] or t.get('stage')!=r.get('stage'):ee.append('TRACE_MISMATCH')
        traces.append({'rule_id':t['rule_id'],'inputs':t['inputs'],'errors':ee,'status':'REJECTED_TRACE' if ee else 'CONDITIONAL_TRACE_RECOMPUTED','rule_version':r.get('version') if r else None})
        errors+=ee
    return {'status':'REJECTED' if errors else 'OK','errors':errors,'source_use_checks':uses,'premise_checks':judgment_results,'traces':traces,
            'semantic_approval':False,'legal_approval':False,'scope':'Independent exact source/object/dependency/scope/combination recomputation; model semantics not proved.'}
