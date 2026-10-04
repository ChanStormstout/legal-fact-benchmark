#!/usr/bin/env python3
"""Study-02 preparation/assembly. No generation, silent repair, overwrite or publication."""
import json,sys,copy,random,hashlib,datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1 import legal_rule_support_study as method
from legal_bench.rules_verdict_v1.source_identity_v2 import parse_responses,merge_windows,validate_view
from legal_bench.rules_verdict_v1.source_views import write_new
R=Path('outputs/legal-rule-support-study-02')
WRAPPER='Execute the attached complete task once, using only its supplied material and no external search or other conversations. Return the full requested JSON in this chat; a downloadable JSON may also be provided. Do not use other versions of the case.'
def read(p):return json.loads(Path(p).read_text())
def save(p,d):write_new(R/p,d)
def text(p,t):
 p=R/p;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():
  if p.read_text()!=t:raise FileExistsError(p)
 else:p.write_text(t)
def freeze(name,files,extra=None):
 save(name,dict(files_sha256={str(p.relative_to(R)):method.sha(p.read_bytes()) for p in files},**(extra or {})))
def getview(cid,ranges,partials,meta):
 doc=read(R/'sources'/(cid+'-recovered.json'));segs=[]
 for s in doc['segments']:
  n=s['original_line']
  if any(a<=n<=b for a,b in ranges):segs.append(copy.deepcopy(s))
  elif n in partials:
   start,end=partials[n](s['text']);v=copy.deepcopy(s);v.update(id=s['id']+'@%d:%d'%(start,end),source_segment_id=s['id'],start=start,end=end,text=s['text'][start:end]);segs.append(v)
 view=dict(case_id=cid,segments=segs,**meta)
 mapping=validate_view(view,doc)
 save('sources/'+cid+'-allowed-raw.json',view)
 reading=method.legacy.reading_view(segs);view['segments']=reading['segments']
 save('sources/'+cid+'-reading-transform.json',reading)
 save('sources/'+cid+'-source-map.json',mapping)
 save('sources/'+cid+'-allowed.json',view)
 return view

def check_task(task,source):
 raw=read(R/'sources'/(source['case_id']+'-allowed-raw.json'));doc=read(R/'sources'/(source['case_id']+'-recovered.json'))
 mapping=validate_view(raw,doc)
 transformed=method.legacy.reading_view(raw['segments'])['segments']
 if transformed!=source['segments']:raise ValueError('READING_TRANSFORM_MISMATCH')
 for s in transformed:
  # Tasks represent source as either JSON or labeled plaintext. Require the entire encoded record or plaintext line.
  if ('['+s['id']+'] '+s['text']) not in task and json.dumps(s,ensure_ascii=False,separators=(',',':')) not in task:
   raise ValueError('SUBMISSION_SOURCE_OMISSION '+s['id'])
 return dict(case_id=source['case_id'],source_mapping=mapping,actual_task_sha256=method.sha(task),
             reading_transform='V21 balanced citation-markup removal; original raw text/provenance retained',status='PASS_NOT_SEMANTIC_GOLD')

def prepare():
 if (R/'source-freeze.json').exists():return
 question='On the supplied allowed record, does the alleged subletting, assignment or parting with possession support eviction under Delhi Rent Control Act section 14(1)(b), considering written consent and the limits of the supplied law? Address the fixed ground only, not unrelated eviction grounds or the withheld historical final outcome.'
 specs=[('110204406',[(40,157)],{},'Delhi Additional Rent Controller','2011-11-28','Insurance tenant and former employee or relatives occupy portions; parties dispute control and permission.'),
 ('172908545',[(40,155)],{},'Delhi Additional Rent Controller','2013-08-29','Partnership tenant and a company operated by its partners use the premises; parties dispute possession and permission.'),
 ('58386394',[(40,164),(168,200)],{},'Delhi Rent Control Tribunal','2023-01-20','Bank tenant and several occupiers dispute licences, subtenancies and written permission; lower decision and appellate submissions supplied.'),
 ('890045',[(192,195),(230,230),(260,263)],{229:lambda t:(t.index('The other argument'),len(t)),278:lambda t:(0,t.index(' I cannot accept'))},'Supreme Court of India','1965-04-19','Corporate tenant assigned the lease and was dissolved during proceedings; the assignee disputes eviction and relies on lease consent wording.'),
 ('1908519',[(142,149),(161,161),(163,163)],{150:lambda t:(0,t.index(' cite')),162:lambda t:(t.index('The learned counsel'),len(t))},'Supreme Court of India','1989-12-08','Tenant and alleged adopted relative dispute possession of a shop and written consent; earlier courts reached differing findings.'),
 ('869439',[(163,171),(176,176),(225,232)],{177:lambda t:(0,t.index(' Apart from')),233:lambda t:(0,t.index(' We are unable'))},'Supreme Court of India','1987-11-12','Tenant and contractor company shared premises under a lease clause; tenant disputes subletting and argues written permission.')]
 samples=[]
 for cid,ranges,partial,court,date,neutral in specs:
  meta=dict(court=court,date=date,input_scope='Retrospective allowed record: pleadings, evidence, contracts, submissions and identified prior-court findings; target final reasoning/outcome and headnotes excluded.',limitations=['Not independent prospective prediction; qualification screening previously occurred for the first three targets.','Complete selected allowed scope, not complete judgment. Original complete rendering kept in audit only.','Historical/current legal versions and later authorities require scope caution; source review is model assisted.'])
  v=getview(cid,ranges,partial,meta)
  samples.append(dict(case_id=cid,question=question,issue='Delhi Rent Control Act 14(1)(b) subletting assignment parting with possession written consent',explicit_act_names=['Delhi Rent Control Act, 1958'],neutral_description=neutral,source='sources/'+cid+'-allowed.json',relatedness='NO_KNOWN_DUPLICATE_IN_SELECTED_SET; broader relationship unconfirmed',query=method.legacy.query_text('Delhi Rent Control Act 14(1)(b) subletting assignment parting with possession written consent',['Delhi Rent Control Act, 1958'],neutral),body_identity_review='Response URL/title, case caption/parties and proceeding reviewed; not a website authenticity certificate',range_decision=dict(whole_lines=ranges,partial_lines=list(partial),basis='Keep facts/pleadings/lower-stage findings; remove target judicial application and disposition, including mixed-paragraph conclusion prefixes/suffixes.')))
 # Fixed existing library; no target-derived precedents added.
 units=read('outputs/legal-rule-support-study-01/v23-development/library/original-units.json')
 rs=[]
 for p in [R/'sources/raw/DRC14.txt',R/'sources/raw/DRC-body125.txt']:rs.extend(parse_responses(p.read_text(),p))
 docs=merge_windows(rs);save('library/statute-recovered.json',docs)
 d=docs['18143401'];line=next(s for s in d['segments'] if s['original_line']==39)
 pre=line['text']; a=pre.index('Notwithstanding');b=pre.index('cite10†(a)');c=pre.index('cite11†(b)');e=pre.index('cite12†(c)')
 def unit(key,doc,segments,scope,deps=()):
  return dict(id=key,text='\n'.join(s['text'] for s in segments),source=dict(document_id=doc['document_id'],url=doc['url'],raw_provenance=[s['provenance'] for s in segments]),version_status='INDIAN_KANOON_STATUTORY_REPRODUCTION_CURRENT_SNAPSHOT_HISTORICAL_VERSION_UNVERIFIED',scope=scope,dependencies=list(deps),coverage_limit='Not an authenticated historical consolidation; only displayed provisions included. No target judicial interpretation.',source_status='STATUTORY_REPRODUCTION_NOT_OFFICIAL_GAZETTE')
 # Keep introductory proviso and complete clause b with two exact source slices.
 chunks=[]
 for x,y in [(a,b),(c,e)]:
  s=copy.deepcopy(line);s['text']=pre[x:y];s['source_char_range']=[x,y];chunks.append(s)
 base=unit('LAW:S02:DRC14:1b',d,chunks,'Delhi s14(1) opening/proviso and complete clause (b). Other grounds deliberately outside fixed question.')
 units=[base]+units
 act=docs['152548910']
 for num,lno in [(16,139),(17,141),(18,143)]:
  s=next(s for s in act['segments'] if s['original_line']==lno)
  units.append(unit('LAW:S02:DRC:'+str(num),act,[s],'Delhi Rent Control Act section '+str(num)+'; read its own date/notice/consent conditions.', ['LAW:S02:DRC14:1b']))
 # Body-only rendering strips tool citation decorations, with immutable raw original saved above.
 for u in units:
  if u['id'].startswith('LAW:S02:'):
   save('library/raw-units/'+u['id'].replace(':','_')+'.json',u)
   u['text']=method.legacy.reading_view([dict(id=u['id'],text=u['text'],source_document=u['source']['document_id'])])['segments'][0]['text']
 save('library/original-units.json',units)
 save('library/coverage.json',dict(existing_sources='V21 development library unchanged; target precedents not added based on their final citations',mandatory=['LAW:S02:DRC14:1b'],adjacent_sections=[16,17,18],official_fetch_failure='IndiaCode PDF timed out; reproduction status explicit in every new unit.',target_final_source_ids_excluded=[s['case_id'] for s in samples],version_limit='Later and current source versions; retrospective development only',units=len(units),characters=len(method.render(units))))
 save('samples.json',samples)
 rng=random.Random(20261003);repeats=rng.sample([s['case_id'] for s in samples],2);audit=rng.sample([s['case_id'] for s in samples],2)
 save('selection-config.json',dict(seed=20261003,repeat_cases=repeats,independent_review_cases=audit,order='Saved candidate order; A/G/L cyclic rotation across cases; repetitions reverse original order',model_visible='High; exact model pending UI verification',max_new_calls=58))
 ref_instructions='''Read ONLY this allowed target record and the entire common legal library. Do not search, use other conversations, or infer the withheld target final outcome. This is source-grounded model reference construction, not human gold. Identify at most six substantive reference propositions relevant to the fixed ground, grouping all units needed for one proposition together. Zero supported references is allowed. Give 3-5 analysis points and genuine gaps. Relevance does not require a satisfied condition. Distinguish controlling candidate, interpretation, opposing authority and analogy, actual adoption status, jurisdiction, date and limits. A quoted predecessor is not automatically its full opinion. Output JSON: {"case_id":"...","reference_items":[{"id":"r1","unit_ids":["..."],"role":"interpretation","proposition":"...","evidence":[{"unit_id":"...","quote":"exact source words"}],"relevance":"...","limits":"..."}],"analysis_points":["..."],"gaps":["..."],"disputes":["..."]}. Each filled value must be substantive; empty lists permitted. Finish once; no external resources.'''
 for i,s in enumerate(samples):
  v=read(R/s['source']);record='\n'.join('['+x['id']+'] '+x['text'] for x in v['segments'])
  t=ref_instructions+'\nQUESTION\n'+s['question']+'\nTARGET METADATA\n'+json.dumps({k:v[k] for k in ['case_id','court','date','input_scope','limitations']},ensure_ascii=False)+'\nALLOWED TARGET RECORD\n'+record+'\nENTIRE COMMON LEGAL LIBRARY\n'+method.render(units)
  name='REF%02d'%(i+1);text('tasks/'+name+'.txt',t);save('audit/'+name+'-assembly.json',check_task(t,v))
 save('reference-order.json',[dict(id='REF%02d'%(i+1),case_id=s['case_id'],status='NOT_STARTED',path='tasks/REF%02d.txt'%(i+1)) for i,s in enumerate(samples)])
 # Freeze evaluation and descriptions before any reference/model result.
 save('evaluation-rules.json',read(R/'preparation-protocol.json'))
 for name in ['scripts/legal_rule_support_study02.py','scripts/study02_candidates.py','legal_bench/rules_verdict_v1/source_identity_v2.py','legal_bench/rules_verdict_v1/legal_rule_support_study.py','legal_bench/rules_verdict_v1/rule_retrieval_v21.py']:
  text('freeze/code/'+name,Path(name).read_text())
 freeze('source-freeze.json',[p for p in R.rglob('*') if p.is_file() and 'runs' not in p.parts],dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),references_before_rankings=True,model_calls_so_far=0))
 print('Prepared',len(samples),'references; library',len(units),'units',len(method.render(units)),'chars')
if __name__=='__main__':prepare()
