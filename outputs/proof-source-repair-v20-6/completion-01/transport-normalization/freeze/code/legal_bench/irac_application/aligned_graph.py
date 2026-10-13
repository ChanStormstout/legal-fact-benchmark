"""Input-only aligned graph. All signed relevance edges remain model proposals."""
import copy,hashlib,json
from .graph_builder import reject_supervision
from .aligned_anco import project,anco
TYPES=('Claim','Issue','Element','Test','Rule','Authority','Burden','Fact','Evidence','Entity','Pattern','Logic','Proposal')
BASE_RELATIONS=('HAS_ELEMENT','HAS_TEST','HAS_RULE','HAS_BURDEN','SOURCE_OF','FACT_ENTITY','EVIDENCE_RECORDS','PROPOSED_SUPPORT','PROPOSED_OPPOSE','PROPOSED_UNKNOWN','PROPOSED_IRRELEVANT','PATTERN_MEMBER','LOGIC_AND','LOGIC_OR','LOGIC_NOT','LOGIC_EXCEPT','LOGIC_REF')
RELATIONS=tuple(sorted(BASE_RELATIONS+tuple('INVERSE_'+r for r in BASE_RELATIONS)))

def check_refs(refs,sources):
    failures=[]
    for r in refs:
        if r.get('source_id') not in sources:failures.append('SOURCE_ID_NOT_ALLOWED:'+str(r.get('source_id')))
        elif not r.get('quote') or r['quote'] not in sources[r['source_id']]['text']:failures.append('QUOTE_NOT_LOCATED:'+r['source_id'])
    return failures

def validate_template(template,sources):
    errors=[];ids=[]
    for key in ('claims','elements','tests','rules','burdens'):
        for item in template[key]:
            ids.append(item['id']);errors+=check_refs(item.get('source_refs',[]),sources)
    if len(set(ids))!=len(ids):errors.append('DUPLICATE_TEMPLATE_ID')
    for t in template['tests']:
        if t['element_id'] not in {e['id'] for e in template['elements']}:errors.append('MISSING_ELEMENT:'+t['id'])
    def walk(e):
        errors.extend(check_refs(e.get('source_refs',[]),sources))
        if e['op']=='REF' and e['id'] not in ids:errors.append('MISSING_LOGIC_REFERENCE:'+e['id'])
        for a in e.get('args',[]):walk(a)
        for k in ('arg','base','exception'):
            if k in e:walk(e[k])
    for c in template['claims']+template['elements']:walk(c['expression'])
    return errors

def build(material,legacy,template,proposal,law_sources):
    reject_supervision(proposal)
    if str(proposal['case_id'])!=str(material['case_id']):raise ValueError('CASE_ID_MISMATCH')
    sources=copy.deepcopy(material['sources']);sources.update({s['source_id']:s for s in law_sources})
    for sid,s in material['sources'].items():
        if str(s['document_id'])!=str(material['case_id']):raise ValueError('CASE_SOURCE_OWNERSHIP')
        if s.get('semantic_stage') in ('TARGET_REASONING','TARGET_OUTCOME'):raise ValueError('FORBIDDEN_TARGET_SOURCE')
    errors=validate_template(template,sources)
    if errors:raise ValueError('INVALID_TEMPLATE:'+repr(errors))
    nodes=[];edges=[];audit=[];byid={}
    def node(item,typ,origin):
        rid=item['id']
        if rid in byid:raise ValueError('DUPLICATE_NODE:'+rid)
        refs=item.get('source_refs',[]);fail=check_refs(refs,sources)
        n=dict(id=rid,type=typ,text=item.get('text',item.get('proposition','')),features={k:item[k] for k in ('statement_status','semantic_stage','court_level','party_side','polarity','prospective_availability') if k in item},source_refs=copy.deepcopy(refs),source_grounded=bool(refs) and not fail,origin=origin,semantic_verified=False)
        n['features']['source_status']=item.get('source_status','MODEL_PROPOSAL');n['features']['coverage_status']=item.get('coverage_status','UNKNOWN')
        byid[rid]=n;nodes.append(n)
        if fail:audit.append(dict(record_id=rid,action='LOCAL_SOURCE_ADDRESS_FAILURE',reasons=fail))
        return n
    def edge(s,t,kind,refs,origin,record=None):
        if s not in byid or t not in byid:
            audit.append(dict(record_id=record,action='EDGE_ISOLATED',reason='INVALID_ENDPOINT',source=s,target=t));return
        e=dict(source=s,target=t,type=kind,source_refs=copy.deepcopy(refs),origin=origin,provenance_record_id=record,semantic_verified=False)
        edges.append(e);edges.append(dict(e,source=t,target=s,type='INVERSE_'+kind,origin='COMPUTATIONAL_REVERSE_OF_'+origin))
    for section,typ in [('claims','Claim'),('elements','Element'),('tests','Test'),('rules','Rule'),('burdens','Burden')]:
        for item in template[section]:node(item,typ,'GIVEN_RULE_STRUCTURE')
    for s in law_sources:node(dict(id=s['source_id'],text=s['text'],source_refs=[dict(source_id=s['source_id'],quote=s['text'])]),'Authority','SUPPLIED_LAW')
    node(legacy['issue'],'Issue','LEGACY_SOURCE_PROPOSAL')
    for section,typ in [('entities','Entity'),('facts','Fact'),('evidence','Evidence')]:
        for item in legacy[section]:node(item,typ,'LEGACY_SOURCE_PROPOSAL')
    for item in proposal.get('additional_facts',[]):node(item,'Fact','NEW_MODEL_PROPOSAL')
    for item in legacy['facts']:
        for eid in item.get('entity_ids',[]):edge(item['id'],eid,'FACT_ENTITY',item['source_refs'],'MODEL_PROPOSAL',item['id'])
    for item in legacy['evidence']:
        for fid in item.get('supports_fact_ids',[]):edge(item['id'],fid,'EVIDENCE_RECORDS',item['source_refs'],'MODEL_PROPOSAL',item['id'])
    for test in template['tests']:edge(test['element_id'],test['id'],'HAS_TEST',test['source_refs'],'GIVEN_RULE_STRUCTURE')
    def expression(owner,e,path='root'):
        lid=owner+'::logic::'+path
        node(dict(id=lid,text=json.dumps(e,sort_keys=True),source_refs=e.get('source_refs',[]),source_status='RESEARCHER_TRANSLATION'),'Logic','GIVEN_RULE_EXPRESSION')
        edge(owner,lid,'LOGIC_'+e['op'] if e['op'] in ('AND','OR','NOT','EXCEPT') else 'LOGIC_REF',e.get('source_refs',[]),'RESEARCHER_TRANSLATION')
        if e['op']=='REF':edge(lid,e['id'],'LOGIC_REF',e.get('source_refs',[]),'RESEARCHER_TRANSLATION');return
        for i,a in enumerate(e.get('args',[])):expression(lid,a,str(i))
        for key in ('arg','base','exception'):
            if key in e:expression(lid,e[key],key)
    for item in template['claims']+template['elements']:expression(item['id'],item['expression'])
    for section in ('claims','elements','tests','rules','burdens'):
        for item in template[section]:
            for r in item.get('source_refs',[]):edge(r['source_id'],item['id'],'SOURCE_OF',[r],'LAW_ADDRESS_LINK')
    accepted=[]
    testids={t['id'] for t in template['tests']}
    for link in proposal['links']:
        fail=check_refs(link.get('source_refs',[]),sources)
        if link.get('test_id') not in testids or link.get('instance_id') not in byid:fail.append('INVALID_LINK_ENDPOINT')
        elif byid[link['instance_id']]['type'] not in ('Fact','Evidence','Pattern'):fail.append('INVALID_LINK_NODE_TYPE')
        elif not byid[link['instance_id']]['source_grounded']:fail.append('INSTANCE_SOURCE_ADDRESS_FAILED')
        if link.get('direction') not in ('SUPPORT','OPPOSE','UNKNOWN','IRRELEVANT'):fail.append('INVALID_DIRECTION')
        if not link.get('source_refs'):fail.append('UNSOURCED_PROPOSAL')
        if fail:audit.append(dict(record_id=link.get('id'),action='LINK_ISOLATED',reasons=fail));continue
        pid='PROPOSAL::'+link['id']
        node(dict(id=pid,text=json.dumps(link,ensure_ascii=False,sort_keys=True),source_refs=link['source_refs'],source_status='MODEL_PROPOSAL'),'Proposal','MODEL_ANALYSIS_PROPOSAL')
        edge(link['instance_id'],pid,'PROPOSED_'+link['direction'],link['source_refs'],'MODEL_ANALYSIS_PROPOSAL',link['id'])
        edge(pid,link['test_id'],'PROPOSED_'+link['direction'],link['source_refs'],'MODEL_ANALYSIS_PROPOSAL',link['id']);accepted.append(link)
    for combination in proposal.get('combinations',[]):
        pid='COMBINATION::'+combination['id']
        refs=[r for w in combination.get('identity_witnesses',[]) for r in w.get('source_refs',[])]
        node(dict(id=pid,text=json.dumps(combination,ensure_ascii=False,sort_keys=True),source_refs=refs,source_status='MODEL_PROPOSAL'),'Pattern','MODEL_PROPOSED_COMBINATION_NOT_DISCOVERED_PATTERN')
        for lid in combination.get('test_links',[]):edge(pid,'PROPOSAL::'+lid,'PATTERN_MEMBER',refs,'MODEL_PROPOSED_COMBINATION',combination['id'])
    fids=sorted(n['id'] for n in nodes if n['type'] in ('Fact','Evidence','Pattern'))
    view=project(sorted(testids),fids,accepted);scores=anco(view['matrix'],n_columns=len(fids))
    for ids,key in ((view['test_ids'],'x'),(view['instance_ids'],'y')):
        for i,rid in enumerate(ids):byid[rid]['anco']={'score':scores[key][i] if scores[key] is not None else 0.,'valid':scores['status']=='CONVERGED','conflict':any(rid in (c['test_id'],c['instance_id']) for c in view['conflicts'])}
    return dict(schema_version='ALIGNED_INPUT_GRAPH_V1',case_id=material['case_id'],nodes=nodes,edges=edges,audit=audit,anco_view=view,anco=scores,proposal=proposal,legal_structure=template,source_manifest=sources,supervision_read=False,canonical_integration='NATIVE_ONLY_REAL_GROUP_SAMPLE_PENDING')
