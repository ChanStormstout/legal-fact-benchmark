"""Offline end-to-end source interface acceptance; never a model experiment."""
import copy,json
from pathlib import Path
import execute as ex
import source_v9 as s
from schema_contract import validate,decoder_schema,violations
from communication import request_wire,compact_schema,expand_schema

def main():
 checks=[]
 def check(name,ok):
  assert ok,name;checks.append(name)
 cfg=ex.read(ex.HERE/'protocol.json');full=ex.read(ex.PREP/'private/inputs/1251841.json')['sources'];groups=s.plan(full)
 check('All source entries assigned without deletion',[i for g in groups for i in g]==list(full))
 req=s.reading_request(full,groups[0]);wire=request_wire({'policy':req['policy'],'task':req['task'],'schema':req['schema'],'material':{k:v for k,v in req.items() if k not in ('policy','task','schema')},'output_token_cap':65536},cfg)
 check('Actual wire preserves all original sources',json.loads(wire['messages'][1]['content'])['sources']==full)
 check('Compact display preserves schema',expand_schema(compact_schema(req['schema']))==req['schema'])
 src={'s1':'A alleges that B received land.','s2':'The lease binds C only if C consented.'}
 record={'kind':'ALLEGATION','attribution':{'speaker':'A','forum':None,'stage':None,'time':None},'proposition':{'subject':'B','relation':'received','object':'land','event_time':None,'layer':'OCCURRENCE'},'qualifications':[],'source_ids':['s1'],'uncertainties':[]}
 conditional=copy.deepcopy(record);conditional.update(kind='LEGAL_ARGUMENT',proposition={'subject':'lease','relation':'binds','object':'C','event_time':None,'layer':'LEGAL_EFFECT'},source_ids=['s2'],qualifications=[{'type':'CONDITION','text':'C consented','source_ids':['s2']}])
 initial={'records':[record,conditional],'unresolved_omissions':[],'conflicts':[]}
 packet=s.initial_packet(src,list(src),initial);review={'by_target':{},'additions':[],'unresolved_gaps':[],'conflicts':[]}
 for k,r in packet['records'].items():review['by_target'][k]={'action':'KEEP','issues':[],'source_ids':r['record']['source_ids'],'source_basis':'The source states the attributed proposition and its condition.','new_records':[]}
 validate(review,s.review_schema(src,packet));validate(review,decoder_schema(s.review_schema(src,packet)))
 result=s.apply_review(src,packet,review,packet['snapshot_hash'])
 check('Program resolves literal original without model retyping',result['records']['R0000']['source_text_by_id']=={'s1':src['s1']})
 check('Condition remains attached',result['records']['R0001']['record']['qualifications']==conditional['qualifications'])
 bad=copy.deepcopy(initial);bad['records'][0]['source_ids']=['missing']
 check('Undeclared source rejected',bool(violations(bad,s.reading_schema(src))))
 bad=copy.deepcopy(initial);bad['records'][0]['quote']='invented quote'
 check('Model cannot generate a quote field',bool(violations(bad,s.reading_schema(src))))
 for action in ['REPLACE','WITHDRAW','UNRESOLVED']:
  bad=copy.deepcopy(review);bad['by_target']['R0000']['action']=action
  check('Non-KEEP requires an identified issue: '+action,bool(violations(bad,s.review_schema(src,packet))))
 bad=copy.deepcopy(review);bad['by_target']['R0000']['checks']={'attribution':'SUPPORTED'}
 check('Redundant per-component verdict vector cannot be generated',bool(violations(bad,s.review_schema(src,packet))))
 changed=copy.deepcopy(review);changed['by_target']['R0000'].update(action='REPLACE',issues=[{'aspect':'status','explanation':'Incorrect record kind'}],new_records=[{**record,'kind':'DENIAL'}])
 replaced=s.apply_review(src,packet,changed,packet['snapshot_hash'])
 check('Correction changes the actual addressed record',replaced['records']['R0000.r0']['record']['kind']=='DENIAL' and 'R0000' not in replaced['records'])
 check('Correction not silently accepted',replaced['records']['R0000.r0']['state']=='REVISION_NOT_INDEPENDENTLY_REVIEWED')
 unchanged=copy.deepcopy(changed);unchanged['by_target']['R0000']['new_records']=[record]
 check('Unchanged replacement remains unresolved',s.apply_review(src,packet,unchanged,packet['snapshot_hash'])['records']['R0000']['state']=='UNRESOLVED')
 try:s.apply_review(src,packet,review,'stale');raise AssertionError('stale accepted')
 except ValueError as err:check('Snapshot binding retained',str(err)=='STALE_REVIEW_SNAPSHOT')
 unary=copy.deepcopy(initial);unary['records'][0]['proposition']['object']=None
 validate(unary,s.reading_schema(src));check('Unary statements do not require invented object text',True)
 dest=ex.HERE/'private/offline-acceptance-v1'
 def ask(tag,r):
  check('Whole chain retains exact sources',r['sources']==src)
  return copy.deepcopy(initial if tag.startswith('reading') else review)
 out=s.run(src,ask,dest/'mock-chain')
 check('Complete offline chain delivers referenced records',out['technical_complete'] and out['record_count']==2)
 for f in ex.HERE.glob('*.py'):compile(f.read_text(),str(f),'exec')
 ex.save(dest/'report.json',{'status':'PASS','checks':checks,'model_calls':0,'fixtures_not_quality_evidence':True,'planned_semantic_calls':2*len(groups),'initial_wire_bytes':len(json.dumps(wire).encode()),'initial_message_chars':sum(len(m['content']) for m in wire['messages'])})
 print(json.dumps({'status':'PASS','checks':len(checks),'wire_bytes':len(json.dumps(wire).encode())}))
if __name__=='__main__':main()
