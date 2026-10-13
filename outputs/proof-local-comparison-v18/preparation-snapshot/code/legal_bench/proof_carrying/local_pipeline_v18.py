"""V18: source-use packets and conditional composition, never legal approval.
No supervision or evaluation references are accepted by this interface.
"""
import copy
import itertools
import json
from collections import Counter
from .local_pipeline_v17 import obj, arr, enum, STR, validate, FINAL_SCHEMA, FINAL_INSTRUCTION, source_text, directory as legacy_directory
from .local_evaluation_v17 import LABELS, hash_value
from .semantic_interface_v13 import recover, position
from .quote_locator_v16 import source_match


def directory(rules):
    rows=legacy_directory(rules)
    for view,rule in zip(rows,rules):
        for field in ('version','jurisdiction','limits','authority','authority_status','rule_kind','description','slot_variables'):
            if field in rule:view[field]=copy.deepcopy(rule[field])
    return rows

STATES = ('TRUE','FALSE','UNKNOWN','CONFLICTED')
STATUS = ('PARTY_CLAIM','TESTIMONY','ADMISSION','RECORDED_DOCUMENT','COURT_FINDING','COURT_LEGAL_REASONING','COURT_PROCEDURAL_ACCOUNT','UNKNOWN')
RELATIONS = ('FACT_APPLICATION','RULE_APPLICATION','RULE_DEPENDENCY','REQUEST_APPLICATION','OBJECT_FACT','SUPPORT','OPPOSE','CONTEXT')

def role_directory(rules):
    return [{'address':p['id']+'::'+role,'premise_id':p['id'],'role':role,'type':typ,
             'variable':r.get('slot_variables',{}).get(p['id'],{}).get(role,role),
             'mapping_status':'EXPLICIT_RULE_ROLE; IDENTITY_REQUIRES_PROPOSED_OBJECT_AND_SOURCE_BASIS'}
            for r in rules for p in r['premises'] for role,typ in p.get('variables',{}).items()]

def schema(rules):
    pids=[p['id'] for r in rules for p in r['premises']]
    addresses=[x['address'] for x in role_directory(rules)]
    index={'type':'integer','minimum':1}
    bindings=arr(obj({'address':enum(addresses or ['NO_DECLARED_ROLE']),'object':index}))
    statuses=sorted(set(STATUS)|{s for r in rules for p in r['premises'] for s in p.get('allowed_statuses',[])})
    record=obj({'text':STR,'status':enum(statuses),'stage':STR,'refs':arr(STR,1)})
    entity=obj({'label':STR,'type':STR,'refs':arr(STR,1),'identity_basis':STR})
    use=obj({'premise':enum(pids),'records':arr(index,1),'bindings':bindings,
             'direction':enum(('SUPPORT','OPPOSE','CONTEXT')),'claim':STR,'stage':STR,
             'witnesses':arr(obj({'refs':arr(STR,1),'quote':STR,'necessity':enum(('REQUIRED','SUPPLEMENTARY'))}),1),
             'self_assessment':enum(LABELS),'limits':arr()})
    judgment=obj({'premise':enum(pids),'bindings':bindings,'uses':arr(index),
                  'state':enum(STATES),'complete':{'type':'boolean'},'stage':STR,'basis':STR,
                  'opposition_uses':arr(index),'gaps':arr(),'necessary_limits':arr()})
    return obj({'records':arr(record),'objects':arr(entity),'uses':arr(use),
                'premises':arr(judgment),'coverage_limits':arr()})

INSTRUCTION='''Reconstruct the fixed Q1 in English, using only the allowed source and unchanged rule drafts. This is a bounded part of one judgment reconstruction, not prospective prediction. Record each material statement once and attribute its speaker/status and court stage. A judgment recording a document is not independent inspection of the original document. Distinct evaluations of one arrangement do not create distinct transactions; shared names/types do not establish identity. Objects are explicit local 1-based declarations with source identity bases, not automatic name matching. Bind an object only at a legal address in the directory. Do not produce hashes, versions or internal IDs.
A use is ONE declared use of its exact cited passages, for one proposition/binding/stage and one SUPPORT/OPPOSE/CONTEXT direction. Correct opposition and correct reporting of a party claim can be SUPPORTED. It does not mean a whole premise is TRUE. Do not mix support and opposition in one use. Cite short exact witnesses; never rescue a wrong citation using a different passage. The original source and rules are supplied by code; do not copy their full text into each explanation.
Whole-premise judgments are separate from uses. State TRUE/FALSE only with an explicit complete judgment and its basis, objects and required components; partial support/background does not suffice. UNKNOWN is not FALSE; TRUE plus UNKNOWN is not a conflict. Do not count evidence votes. Keep counterevidence, exceptions, necessary proposition limits and unknown connections. An external court evaluation retains its actual court/stage, is not independently proved by code and cannot use a disposition to prove itself. OPEN_TEXT remains open interpretation. Use 1-based local indices for records/objects/uses. Do not infer an object from two missing values. Whole-premise necessary_limits apply to the exact judgment, while a use limit affects only that use. Output a complete JSON once. There is no quota of uses or mandatory all-premise completion. A failed part will be retained as uncovered, not guessed. Write compact claims/bases, normally one or two sentences, and avoid repeating the source. A source range or rule-group boundary limits this part; list cross-part links that remain unresolved in coverage_limits.
COMPLETE SYNTHETIC EXAMPLE, fictional source and rule, not target facts/law:
SYN:L1: Mira said she returned the key on Friday.
SYN:L2: At trial the court found Mira retained the key on Saturday.
SYN.P1 asks whether trial found retained Saturday control; role tenant:person. A separate SYN.P2 asks whether the appellate court adopted that finding.
Output: {"records":[{"text":"Mira claimed Friday return.","status":"PARTY_CLAIM","stage":"pleading","refs":["SYN:L1"]},{"text":"The trial court found retained control on Saturday.","status":"COURT_FINDING","stage":"trial","refs":["SYN:L2"]}],"objects":[{"label":"Mira","type":"person","refs":["SYN:L1","SYN:L2"],"identity_basis":"Both explicitly name Mira in this key dispute."}],"uses":[{"premise":"SYN.P1","records":[2],"bindings":[{"address":"SYN.P1::tenant","object":1}],"direction":"SUPPORT","claim":"Report the attributed trial finding of Saturday control.","stage":"trial","witnesses":[{"refs":["SYN:L2"],"quote":"the court found Mira retained the key on Saturday","necessity":"REQUIRED"}],"self_assessment":"SUPPORTED","limits":[]},{"premise":"SYN.P1","records":[1],"bindings":[{"address":"SYN.P1::tenant","object":1}],"direction":"OPPOSE","claim":"Report Mira's contrary claim, without adopting its truth.","stage":"pleading","witnesses":[{"refs":["SYN:L1"],"quote":"Mira said she returned the key on Friday","necessity":"REQUIRED"}],"self_assessment":"SUPPORTED","limits":["This establishes an allegation, not actual return."]}],"premises":[{"premise":"SYN.P1","bindings":[{"address":"SYN.P1::tenant","object":1}],"uses":[1,2],"state":"TRUE","complete":true,"stage":"trial","basis":"The premise is narrowly the trial's finding, retaining the contradictory allegation as attributed.","opposition_uses":[2],"gaps":[],"necessary_limits":[]},{"premise":"SYN.P2","bindings":[],"uses":[],"state":"UNKNOWN","complete":false,"stage":"appeal","basis":"No appellate adoption is supplied.","opposition_uses":[],"gaps":["Appellate adoption not established."],"necessary_limits":[]}],"coverage_limits":["No conclusion on title or legal liability."]}
'''

def proposal_prompt(case,rules,part):
    selected=[r for r in rules if r['id'] in part['rule_ids']]
    segments=[s for s in case['segments'] if s['id'] in part['source_ids']]
    view={**case,'segments':segments}
    return INSTRUCTION+'\nFIXED REQUEST:\n'+json.dumps(next(q for q in case['targets'] if q['id']=='Q1'))+'\nPART BOUNDARY:\n'+json.dumps(part)+'\nGIVEN RULES:\n'+json.dumps(directory(selected))+'\nLEGAL ROLE ADDRESSES:\n'+json.dumps(role_directory(selected))+'\nALLOWED SOURCE:\n'+source_text(view)+'\nOUTPUT SCHEMA:\n'+json.dumps(schema(selected))

def sources(case):
    return {s['id']:{'document':s['source_document'],'original_line':s.get('original_line'),'text':s['text'],
                         **{k:s[k] for k in ('role','document_role','court_level','stage') if k in s}}
            for s in case['segments']}

def packet(case,rules,p,use_index):
    u=p['uses'][use_index];refs=[];missing=[]
    for key in ('records','opposition_records'):
        for i in u.get(key,[]):
            if type(i) is not int or not 1<=i<=len(p['records']):missing.append('RECORD_INDEX_INVALID');continue
            refs+=p['records'][i-1]['refs']
    for w in u['witnesses']:refs+=w['refs']
    objects=[]
    for b in u['bindings']:
        i=b['object']
        if type(i) is not int or not 1<=i<=len(p['objects']):missing.append('OBJECT_INDEX_INVALID');continue
        ob=p['objects'][i-1];refs+=ob['refs'];objects.append({'address':b['address'],'id':i,**ob})
    selected_rules=[r for r in rules if any(x['id']==u['premise'] for x in r['premises'])]
    refs += [ref for r in selected_rules for ref in r.get('source_refs',[])]
    m=recover(case,list(dict.fromkeys(refs)))
    m['scope']='NEIGHBOUR_CONTEXT_ONLY';m['limits'] += [{'reason':'NEIGHBOUR_CONTEXT_ONLY_NOT_COMPLETE_SPEAKER_OR_STAGE_RECOVERY'}]
    return {'use_id':'K%03d'%(use_index+1),'use':copy.deepcopy(u),'records':[{'index':i,**p['records'][i-1]} for i in u['records'] if type(i) is int and 1<=i<=len(p['records'])],
            'objects':objects,'rules':selected_rules,'actual_restored_source':m,'structural_input_limits':missing,
            'directions_retained':True,'omission_detection_scope':'LOCAL_PACKET_NOT_FULL_JUDGMENT'}

def bind(bindings,objects,roles,pid):
    result={};errors=[]
    for b in bindings:
        r=roles.get(b['address']);i=b['object']
        if r is None or r['premise_id']!=pid:errors.append('INVALID_ROLE_ADDRESS');continue
        if type(i) is not int or not 1<=i<=len(objects):errors.append('OBJECT_INDEX_INVALID');continue
        ob=objects[i-1]
        if not ob.get('label') or not ob.get('identity_basis') or not ob.get('refs'):errors.append('OBJECT_IDENTITY_BASIS_MISSING');continue
        if r['variable'] in result and result[r['variable']]!=i:errors.append('OBJECT_CONFLICT')
        result[r['variable']]=i
    return result,errors

def apply_connection_decisions(case,rules,p,decisions=None):
    roles={x['address']:x for x in role_directory(rules)};prem={x['id']:x for r in rules for x in r['premises']};src=sources(case)
    decisions={} if decisions is None else decisions;checks=[]
    for n,u in enumerate(p['uses']):
        k='K%03d'%(n+1);pkg=packet(case,rules,p,n);errors=list(pkg['structural_input_limits']);warnings=[]
        if u['premise'] not in prem:errors.append('PREMISE_UNKNOWN')
        b,be=bind(u['bindings'],p['objects'],roles,u['premise']);errors+=be
        for ob in pkg['objects']:
            if any(ref not in src for ref in ob['refs']):errors.append('OBJECT_SOURCE_INVALID')
        recs=pkg['records']
        for rec in recs:
            if any(ref not in src for ref in rec['refs']):errors.append('RECORD_SOURCE_INVALID')
            allowed=prem.get(u['premise'],{}).get('allowed_statuses',[])
            if allowed and rec['status'] not in allowed:warnings.append('STATEMENT_STATUS_NOT_ALLOWED_FOR_FULL_PREMISE')
            for field in ('stage','court_level'):
                required=prem.get(u['premise'],{}).get(field)
                if required and rec.get(field)!=required:errors.append('EXPLICIT_SCOPE_MISMATCH:'+field)
            if rec['status'] in ('LEGAL_RULE','TARGET_DISPOSITION'):warnings.append('NOT_A_CASE_FACT_PREMISE')
        locs=[]
        for w in u['witnesses']:
            loc=source_match(w,src);locs.append({'witness':w,'location':loc})
            if loc.get('error'):(errors if w['necessity']=='REQUIRED' else warnings).append('WITNESS_'+loc['error'])
        if not any(w['necessity']=='REQUIRED' for w in u['witnesses']):errors.append('NO_REQUIRED_WITNESS')
        value=decisions.get(k,u['self_assessment'])
        if value not in LABELS:raise ValueError('DECISION_NOT_SUPPORTED_LABEL:'+k)
        disposition='STRUCTURAL_INVALID' if errors else 'MODEL_REJECTED_USE' if value=='UNSUPPORTED' else 'MODEL_PENDING_USE' if value=='UNRESOLVED' else 'CONDITIONALLY_AVAILABLE_USE'
        checks.append({'connection_id':k,'premise':u['premise'],'binding':b,'direction':u['direction'],
                       'P_label':u['self_assessment'],'applied_label':value,'disposition':disposition,'errors':errors,'warnings':warnings,
                       'locations':locs,'model_semantics_verified':False,'source_retained':True,'packet_hash':hash_value(pkg)})
    judgments=[]
    for n,j in enumerate(p['premises']):
        binding,err=bind(j['bindings'],p['objects'],roles,j['premise']);needs={x['variable'] for x in roles.values() if x['premise_id']==j['premise']}
        if set(binding)!=needs:err.append('MISSING_OR_EXTRA_ROLE')
        relevant=[];blocked=[];unknown=[]
        for i in j['uses']:
            if type(i) is not int or not 1<=i<=len(checks):err.append('USE_INDEX_INVALID');continue
            z=checks[i-1]
            if z['premise']!=j['premise'] or any(binding.get(k)!=v for k,v in z['binding'].items()):err.append('USE_BINDING_OR_PREMISE_MISMATCH');continue
            if z['disposition']=='CONDITIONALLY_AVAILABLE_USE':relevant.append(z)
            elif z['disposition']=='MODEL_PENDING_USE':unknown.append(z['connection_id'])
            else:blocked.append(z['connection_id'])
        if not j['basis'] or not j['complete']:err.append('WHOLE_PREMISE_COVERAGE_NOT_ESTABLISHED')
        # Background and usable opposition do not establish the positive whole premise.
        bearing=[z for z in relevant if z['direction']!='CONTEXT' and not z['warnings']]
        if not bearing:err.append('NO_AVAILABLE_FULL_PREMISE_USE')
        state=j['state']
        # Independent valid witness can survive rejected alternative uses; whole necessary limitations cannot.
        if err or j['necessary_limits']:state='UNKNOWN'
        judgments.append({'id':'J%03d'%(n+1),'premise':j['premise'],'binding':binding,'stage':j['stage'],
                           'model_state':j['state'],'conditional_state':state,'errors':err,'necessary_limits':j['necessary_limits'],
                           'available_uses':[z['connection_id'] for z in relevant],'blocked_uses':blocked,'pending_uses':unknown,
                           'basis':j['basis'],'gaps':j['gaps'],'opposition_uses':j['opposition_uses'],
                           'assumption':'UNVERIFIED_MODEL_WHOLE_PREMISE_JUDGMENT_NOT_USE_VOTE'})
    traces=compose(rules,judgments)
    return {'interface':'V18','checks':checks,'premise_judgments':judgments,'conditional_rules':traces,
            'raw_records_retained':len(p['records']),'raw_opposition_retained':[x for x in checks if x['direction']=='OPPOSE'],
            'limitations_retained':p['coverage_limits'],'approval':'NOT_GRANTED','reference_used':False}

def combine_states(values):
    known=set(values)-{'UNKNOWN'}
    if 'CONFLICTED' in known or {'TRUE','FALSE'}<=known:return 'CONFLICTED'
    return next(iter(known)) if known else 'UNKNOWN'

def compatible(parts):
    merged={}
    for part in parts:
        for role,value in part['binding'].items():
            if role in merged and merged[role]!=value:return None
            merged[role]=value
    return merged

def compose(rules,judgments,cap=1000):
    out=[]
    for rule in rules:
        choices=[]
        for p in rule['premises']:
            rows=[j for j in judgments if j['premise']==p['id']]
            choices.append(rows or [{'id':None,'premise':p['id'],'binding':{},'conditional_state':'UNKNOWN','stage':None}])
        count=1
        for c in choices:count*=len(c)
        for route in itertools.islice(itertools.product(*choices),cap):
            binding=compatible(route)
            if binding is None:continue
            vals=[x['conditional_state'] for x in route];op=rule['operator'];v='UNKNOWN'
            for i,p in enumerate(rule['premises']):
                if p.get('expected')=='FALSE':vals[i]={'TRUE':'FALSE','FALSE':'TRUE'}.get(vals[i],vals[i])
            if op=='ALL':v='FALSE' if 'FALSE' in vals else 'CONFLICTED' if 'CONFLICTED' in vals else 'TRUE' if vals and all(x=='TRUE' for x in vals) else 'UNKNOWN'
            elif op=='ANY':v='TRUE' if 'TRUE' in vals else 'CONFLICTED' if 'CONFLICTED' in vals else 'FALSE' if vals and all(x=='FALSE' for x in vals) else 'UNKNOWN'
            if rule.get('exceptions') and v=='TRUE':v='UNKNOWN'
            out.append({'rule_id':rule['id'],'operator':op,'binding':binding,'inputs':[x['id'] for x in route],
                        'slot_states':vals,'conditional_result':v,'not_executed':op not in ('ALL','ANY'),
                        'exceptions':rule.get('exceptions',[]),'limits':rule.get('limits',[]),'enumeration_complete':count<=cap,
                        'stage':rule.get('stage'),'status':'CONDITIONAL_UNVERIFIED_MODEL_SEMANTICS'})
    return out

def compact_checks(a):
    # Each check retained once; repeated locations replaced by stable record IDs.
    loc={};checks=[]
    for z in a['checks']:
        row={k:v for k,v in z.items() if k!='locations'};ids=[]
        for x in z['locations']:
            h=hash_value(x);loc.setdefault(h,x);ids.append(h)
        row['location_ids']=ids;checks.append(row)
    return {**a,'checks':checks,'source_locations':loc}

def final_prompt(case,rules,intermediate):
    return 'INTERMEDIATE MATERIAL (fallible, no approval):\n'+json.dumps(intermediate,ensure_ascii=False)+'\nFIXED REQUEST:\n'+json.dumps(next(q for q in case['targets'] if q['id']=='Q1'))+'\nGIVEN RULES:\n'+json.dumps(directory(rules),ensure_ascii=False)+'\nCOMPLETE ALLOWED SOURCE:\n'+source_text(case)+'\nFINAL TASK:\n'+FINAL_INSTRUCTION+'\nOUTPUT SCHEMA:\n'+json.dumps(FINAL_SCHEMA)

def merge_parts(parts):
    """Only exact identical records can merge. Objects are part-scoped: no name identity.
    Failed tasks have no semantic records; completed tasks survive independently.
    """
    p={'records':[],'objects':[],'uses':[],'premises':[],'coverage_limits':[]};ledger=[]
    for key,raw in parts:
        if raw is None:p['coverage_limits'].append('FAILED_PART:'+key);ledger.append({'part':key,'status':'FAILED'});continue
        rmap={};omap={};umap={}
        for i,rec in enumerate(raw['records'],1):
            if rec not in p['records']:p['records'].append(copy.deepcopy(rec))
            rmap[i]=p['records'].index(rec)+1
        for i,ob in enumerate(raw['objects'],1):
            p['objects'].append({**copy.deepcopy(ob),'part_scope':key});omap[i]=len(p['objects'])
        for i,use in enumerate(raw['uses'],1):
            z=copy.deepcopy(use);z['records']=[rmap.get(j,0) for j in z['records']]
            for b in z['bindings']:b['object']=omap.get(b['object'],0)
            p['uses'].append(z);umap[i]=len(p['uses'])
        for row in raw['premises']:
            z=copy.deepcopy(row)
            for b in z['bindings']:b['object']=omap.get(b['object'],0)
            for field in ('uses','opposition_uses'):z[field]=[umap.get(i,0) for i in z[field]]
            p['premises'].append(z)
        p['coverage_limits']+=raw['coverage_limits'];ledger.append({'part':key,'status':'COMPLETE','record_map':rmap,'object_map':omap,'use_map':umap})
    return p,ledger

def learner_inputs(case,rules,p):
    # Preserve the 8+8 relation dimensions, but do not mislabel background as unresolved.
    REL = RELATIONS
    nodes=[];edges=[];idx={};materials={};pairs=[];ids=[]
    def add(key,value,kind):idx[key]=len(nodes);nodes.append({'id':key,'text':json.dumps(value,sort_keys=True,ensure_ascii=False),'kind':kind})
    q=next(q for q in case['targets'] if q['id']=='Q1');add('Q:Q1',q,3)
    for i,r in enumerate(p['records'],1):add('F:'+str(i),r,0)
    for rule in rules:
        for prem in rule['premises']:add('R:'+prem['id'],{'premise':prem,'rule':rule},1)
    for i,u in enumerate(p['uses']):
        k='K%03d'%(i+1);pkg=packet(case,rules,p,i);materials[k]=pkg;add('C:'+k,pkg,2);ids.append(k)
        edges.append((idx['C:'+k],idx['Q:Q1'],3))
        if 'R:'+u['premise'] in idx:edges.append((idx['R:'+u['premise']],idx['C:'+k],1))
        for j in u['records']:
            if 'F:'+str(j) in idx:edges += [(idx['F:'+str(j)],idx['C:'+k],0),(idx['F:'+str(j)],idx['C:'+k],{'SUPPORT':5,'OPPOSE':6,'CONTEXT':7}[u['direction']])]
        for j,ob in enumerate(pkg['objects']):add('O:'+k+':'+str(j),ob,4);edges.append((len(nodes)-1,idx['C:'+k],4))
        pairs.append({'id':k,'left':json.dumps({'use':u['claim'],'premise':u['premise'],'direction':u['direction']},ensure_ascii=False),'right':json.dumps(pkg,sort_keys=True,ensure_ascii=False)})
    edges += [(b,a,r+len(REL)) for a,b,r in list(edges)]
    # Flat globally pools all graph nodes; CE sees the exact same full node content.
    shared={'request':q,'raw_P':p,'rules':rules,'packets':materials,
            'relations':[{'from':nodes[a]['id'],'to':nodes[b]['id'],'type':REL[r] if r<len(REL) else REL[r-len(REL)]+'_REVERSE'} for a,b,r in edges]}
    nodes[idx['Q:Q1']]['text']=json.dumps(shared,sort_keys=True,ensure_ascii=False)
    for pair in pairs:pair['shared_case_context']=shared
    return {'graph':{'nodes':nodes,'edges':edges,'ids':ids,'candidate_indices':[idx['C:'+k] for k in ids],'request_indices':{'Q1':idx['Q:Q1']}},
            'ce_pairs':pairs,'materials':materials,'information_contract':'SAME_FULL_P_RULES_PACKETS_AND_TYPED_RELATIONS; NO_REFERENCE',
            'relation_counts':dict(Counter(REL[r] if r<len(REL) else REL[r-len(REL)]+'_REVERSE' for _,_,r in edges)),
            'reference_used':False,'coverage':'LOCAL_RESTORED_PACKETS_PLUS_SHARED_CASE_RECORDS; NOT_FULL_SOURCE_OMISSION_DETECTOR'}

def annotation_material(p):
    v=copy.deepcopy(p)
    for u in v['uses']:u.pop('self_assessment',None)
    # Whole judgments/bases would encourage agreement, so omit them from source-use supervision.
    v.pop('premises',None)
    return v
