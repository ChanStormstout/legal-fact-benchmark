"""Prepare isolated reviews and import source-addressed pilot records. No model calls."""
import json, hashlib, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_location_v3 import locate_all
from legal_bench.rules_verdict_v1 import rgcn_development_v3 as graph
R=Path('outputs/rgcn-ranking-diagnostic-07/pilot')
def read(p): return json.loads(p.read_text())
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True)
 body=x if isinstance(x,str) else json.dumps(x,ensure_ascii=False,indent=2)+'\n'
 if p.exists():
  if p.read_text()==body:return
  raise FileExistsError(p)
 p.write_text(body)
def reviews():
 samples=read(R/'samples.json')
 for i,s in enumerate(samples,1):
  for first,second,template in [('GRAPH','GREV','graph-review'),('LABEL','LREV','label-review')]:
   tid=first+str(i).zfill(2);path=R/'parsed'/f'{tid}.json'
   if not path.exists():continue
   p=read(path)
   if p.get('case_id')!=s['case_id']:continue
   base=read(R/'task-material'/f"{s['case_id']}.json")
   if first=='GRAPH':base['law_conditions']=read(R/'source-reviewed-law-proposals.json')
   base['proposal']=p
   rid=second+str(i).zfill(2)
   text=(R/'templates/common.txt').read_text()+'TASK '+rid+'\n'+(R/f'templates/{template}.txt').read_text()+'\nMATERIAL\n'+json.dumps(base,ensure_ascii=False)+'\nEND_OF_INPUT '+rid
   save(R/'tasks'/f'{rid}.txt',text)
   save(R/'review-task-freezes'/f'{rid}.json',{'proposal_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'task_sha256':hashlib.sha256(text.encode()).hexdigest(),'other_path_visible':False})
def quality():
 units=read(R/'sources/laws.json');um={u['id']:u for u in units};pairs=read(R/'comparison-pairs.json');reports=[]
 def located(q,text):
  r=locate_all(text,q)
  return r['status'] in ['EXACT','WHITESPACE_ONLY'] and r.get('unique',False)
 for i,s in enumerate(read(R/'samples.json'),1):
  cid=s['case_id'];source=read(R/'sources'/f'{cid}.json');refs={x['id'] for x in source['segments']};report={'case_id':cid,'reference':'MODEL_GENERATED_SOURCE_REVIEW_NOT_HUMAN_GOLD','accepted_preferences':0,'accepted_uses':0,'graph_status':'PENDING','labels_status':'PENDING'}
  paths={k:R/'parsed'/f'{k}{i:02}.json' for k in ['GRAPH','GREV','LABEL','LREV']}
  if paths['GRAPH'].exists() and paths['GREV'].exists():
   try:
    p,rv=read(paths['GRAPH']),read(paths['GREV'])
    assert p['case_id']==rv['case_id']==cid
    assert len(p['alignments'])==len(um) and {a['unit_id']for a in p['alignments']}==set(um)
    g=graph.make_graph(p,read(R/'source-reviewed-law-proposals.json'),source,units,[x['id'] for x in rv['rejections']])
    save(R/'graphs'/f'{cid}.json',g);report.update(graph_status='PROVISIONAL_SOURCE_REVIEWED',graph_quarantine=len(g['quarantine']),graph_review_rejections=len(rv['rejections']),graph_review_omissions=rv['omissions'])
   except Exception as e:report.update(graph_status='IMPORT_ERROR',graph_error=repr(e))
  if paths['LABEL'].exists() and paths['LREV'].exists():
   try:
    p,rv=read(paths['LABEL']),read(paths['LREV']);assert p['case_id']==rv['case_id']==cid
    assert len(p['uses'])==14 and {x['unit_id']for x in p['uses']}==set(um)
    assert len(p['preferences'])==16 and {(x['a'],x['b'])for x in p['preferences']}=={(x['a'],x['b'])for x in pairs}
    ur={x['unit_id']:x for x in rv['use_reviews']};pr={(x['a'],x['b']):x for x in rv['preference_reviews']}
    assert len(ur)==len(rv['use_reviews']) and len(pr)==len(rv['preference_reviews'])
    accepted=[];uses=[];isolated=[];abstentions=[]
    def validrefs(x):return bool(x.get('case_refs')) and all(k in refs for k in x['case_refs'])
    for x in p['uses']:
     rr=ur.get(x['unit_id'],{});u=um[x['unit_id']]
     if rr.get('decision')=='SUPPORTED' and validrefs(x) and validrefs(rr) and located(x.get('law_quote'),u['text']) and located(rr.get('law_quote'),u['text']):uses.append(x)
     else:isolated.append({'type':'use','record':x,'review':rr,'reason':'Review, unique quote address or case source reference not satisfied'})
    for x in p['preferences']:
     rr=pr.get((x['a'],x['b']),{})
     if x['decision'] not in ['A','B']:abstentions.append({'record':x,'review':rr});continue
     ok=rr.get('decision')=='SUPPORTED' and validrefs(x) and validrefs(rr) and located(x.get('a_quote'),um[x['a']]['text']) and located(x.get('b_quote'),um[x['b']]['text']) and any(located(rr.get('law_quote'),um[k]['text']) for k in [x['a'],x['b']])
     if ok:
      a,b=(x['a'],x['b'])if x['decision']=='A'else(x['b'],x['a']);accepted.append({'preferred':a,'other':b,'source':x,'review':rr})
     else:isolated.append({'type':'preference','record':x,'review':rr,'reason':'Review or source address failed; not converted to a negative'})
    save(R/'labels'/f'{cid}.json',{'uses':uses,'preferences':accepted,'abstentions':abstentions,'isolated':isolated,'reference':report['reference']})
    report.update(labels_status='REVIEWED_WITH_ISOLATION',accepted_preferences=len(accepted),accepted_uses=len(uses),abstentions=len(abstentions),isolated=len(isolated),review_omissions=rv['omissions'])
   except Exception as e:report.update(labels_status='IMPORT_ERROR',labels_error=repr(e))
  reports.append(report)
 save(R/'quality-report.json',{'cases':reports,'expansion_gate':all(x['accepted_preferences']>=2 and x['graph_status']=='PROVISIONAL_SOURCE_REVIEWED' for x in reports),'semantic_accuracy_not_established':True,'unmarked_units_not_negatives':True})
if __name__=='__main__':
 if sys.argv[1]=='reviews':reviews()
 elif sys.argv[1]=='quality':quality()
