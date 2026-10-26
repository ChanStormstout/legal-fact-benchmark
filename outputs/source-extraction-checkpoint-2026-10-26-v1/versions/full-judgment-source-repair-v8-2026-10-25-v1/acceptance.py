"""Offline contract and transport acceptance, not model-quality evidence."""
import copy
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import execute as ex
import source_v8 as s
import latentweaver_repaired as lw
from schema_contract import validate, decoder_schema, violations
from communication import request_wire, compact_schema, expand_schema

def main():
    results=[]
    def check(name,value):
        if not value: raise AssertionError(name)
        results.append(name)
    cfg=ex.read(ex.HERE/'protocol.json');sources=ex.read(ex.PREP/'private/inputs/1251841.json')['sources']
    groups=s.plan(sources)
    check('Every original entry assigned exactly once without clipping',[i for g in groups for i in g]==list(sources))
    sizes=[]
    for focus in groups:
        req=s.reading_request(sources,focus)
        check('Prompt compaction preserves contract',expand_schema(compact_schema(req['schema']))==req['schema'])
        wire=request_wire({'policy':req['policy'],'task':req['task'],'schema':req['schema'],
            'material':{k:v for k,v in req.items() if k not in ('policy','task','schema')},'output_token_cap':65536},cfg)
        check('Every initial wire contains all original source bytes',json.loads(wire['messages'][1]['content'])['sources']==sources)
        sizes.append({'focus_entries':len(focus),'wire_bytes':len(json.dumps(wire).encode()),
                      'message_characters':sum(len(m['content']) for m in wire['messages'])})
    src={'s1':'Court Q. A alleges that B received land.','s2':'The lease binds C only if C consented.'}
    record={'kind':'ALLEGATION','attribution':{'speaker':'A','forum':None,'stage':None,'time':None},
            'proposition':{'subject':'B','relation':'received','object':'land','event_time':None,'layer':'OCCURRENCE'},
            'qualifications':[],'evidence':[{'source_id':'s1','quote':'A alleges that B received land.'}],'uncertainties':[]}
    conditional=copy.deepcopy(record);conditional.update(kind='LEGAL_ARGUMENT',proposition={'subject':'lease','relation':'binds','object':'C','event_time':None,'layer':'LEGAL_EFFECT'},evidence=[{'source_id':'s2','quote':src['s2']}],qualifications=[{'type':'CONDITION','text':'C consented','evidence':[{'source_id':'s2','quote':'only if C consented'}]}])
    initial={'by_source':{'s1':{'state':'RECORDS','records':[record],'basis':'A is the attributed speaker.'},'s2':{'state':'RECORDS','records':[conditional],'basis':'Conditional effect.'}},'conflicts':[]}
    validate(initial,s.read_schema(src,list(src)));validate(initial,decoder_schema(s.read_schema(src,list(src))))
    packet=s.initial_packet(src,list(src),initial)
    review={'by_target':{},'by_source':{sid:{'state':'COMPLETE','source_basis':'The statement and its qualification are explicitly retained.','additions':[]} for sid in src},'conflicts':[]}
    for key,row in packet['records'].items():
        review['by_target'][key]={'decision':'KEEP','checks':{k:'SUPPORTED' for k in s.CHECKS},'source_basis':'Compared the attributed subject and the exact limiting words to the original.','evidence':row['record']['evidence'],'replacements':[]}
    validate(review,decoder_schema(s.review_schema(src,packet)))
    applied=s.apply_review(src,packet,review,packet['snapshot_hash'])
    check('Condition retained through the complete state transition',applied['records']['R0001']['record']['qualifications']==conditional['qualifications'])
    bad=copy.deepcopy(initial);bad['by_source']['s1']['records']=[]
    check('Empty RECORDS branch rejected by both contracts',bool(violations(bad,s.read_schema(src,list(src)))) and bool(violations(bad,decoder_schema(s.read_schema(src,list(src))))))
    bad=copy.deepcopy(initial);bad['by_source']['s1']['records'][0]['record_id']='guessed'
    check('Model-authored record identity rejected',bool(violations(bad,s.read_schema(src,list(src)))))
    replaced=copy.deepcopy(review);r=replaced['by_target']['R0000'];r.update(decision='REPLACE',replacements=[{**record,'kind':'DENIAL'}]);r['checks']['status']='ERROR'
    changed=s.apply_review(src,packet,replaced,packet['snapshot_hash'])
    check('Replacement actually replaces the addressed record without auto-acceptance','R0000' not in changed['records'] and changed['records']['R0000.r0']['state']=='REVISION_NOT_INDEPENDENTLY_REVIEWED')
    check('Unreviewed correction remains counted as pending',any(x.get('target')=='R0000.r0' for x in changed['pending']))
    wrong=copy.deepcopy(review);wrong['by_target']['R0000']['evidence'][0]['quote']='invented words'
    check('Nonliteral review cannot accept source',s.apply_review(src,packet,wrong,packet['snapshot_hash'])['records']['R0000']['state']=='UNRESOLVED')
    try:s.apply_review(src,packet,review,'stale');raise AssertionError('stale accepted')
    except ValueError as err:check('Review bound to original immutable snapshot',str(err)=='STALE_REVIEW_SNAPSHOT')
    old=ex.PREP/'execution-v1/private/run-v1/cases/1251841/LW'
    spans=json.loads((old/'source-spans.json').read_text())
    # Source span index is an ID -> metadata object in the native implementation.
    schema=lw.candidate_wire_schema('1251841',list(spans))
    candidate=json.loads((old/'model-candidate.json').read_text())
    check('Observed forbidden DECIDED_BY output now forbidden during generation',bool(violations(candidate,schema)))
    lw.modules();from jsonschema import Draft202012Validator
    native=json.loads((lw.EXTERNAL/'prompt2_v2/schemas/llm_candidate_schema.json').read_text())
    native['properties']['case_id']={'enum':['1251841']};native['$defs']['source_ref']['properties']['source_span_id']={'enum':list(spans)}
    a=Draft202012Validator(native);b=Draft202012Validator(schema)
    # These are synthetic contract fixtures, never sent to models or used as results.
    fixture=copy.deepcopy(candidate);fixture['edges']=[]
    specimens=[candidate,fixture]
    for kind in ['Conclusion','Fact']:
        for conclusion in ['HOLDING','DISPOSITION',None,'INVALID','ABSENT']:
            item=copy.deepcopy(fixture);node=item['nodes'][0];node['node_type']=kind
            if conclusion=='ABSENT':node.pop('conclusion_kind',None)
            else:node['conclusion_kind']=conclusion
            specimens.append(item)
    for x in specimens:
        check('Compiled and native candidate schemas agree on conditional nodes',a.is_valid(x)==b.is_valid(x))
    dest=ex.HERE/'private/offline-acceptance-v1'
    if dest.exists():raise RuntimeError('ACCEPTANCE_ALREADY_EXISTS')
    def ask(tag,req):
        check('Offline complete-chain request retains original sources',req['sources']==src)
        return copy.deepcopy(initial if tag.startswith('reading') else review)
    result=s.run(src,ask,dest/'mock-chain')
    check('Full offline consumer chain completed',result['technical_complete'] and result['record_count']==2)
    for path in ex.HERE.glob('*.py'):compile(path.read_text(),str(path),'exec')
    ex.save(dest/'report.json',{'status':'PASS','checks':results,'synthetic_fixture_not_method_score':True,'real_model_calls':0,'batch_plan_sizes':sizes,'expected_calls':{'ROLE':2*len(groups),'LW':4},'schema_comparison_fixtures':len(specimens)})
    print(json.dumps({'status':'PASS','assertions':len(results),'groups':len(groups),'max_wire_bytes':max(x['wire_bytes'] for x in sizes),'max_message_chars':max(x['message_characters'] for x in sizes)}))
if __name__=='__main__':main()
