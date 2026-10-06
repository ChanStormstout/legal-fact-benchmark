"""Uniform TRAIN/DEV construction, versioned locations/quality; no SEALED body access."""
import sys,json,copy,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from legal_bench.rules_verdict_v1 import coarse_label_v10 as lab,rgcn_development_v4 as graph,authority_index
from scripts.rgcn09_import import inspect_graph
R=Path('outputs/rgcn-dev-contract-repair-10');B=Path('outputs/rgcn-data-expansion-09');I=B/'continuation-03/imports/final-01';D=Path('outputs/rgcn-ranking-development-06');O=Path('outputs/rgcn-ranking-diagnostic-07/pilot')
def read(p):return json.loads(Path(p).read_text())
def save(p,v):
 p=R/p;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise FileExistsError(p)
 p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def compact(row):return {k:row[k] for k in lab.FIELDS if k in row}
def train_source(cid,oldids):return read(O/'sources'/f'{cid}.json') if cid in oldids else read(B/'continuation-01/freeze/allowed'/f'{cid}.json')
def run(stage="all"):
 cfg=read(R/'protocol.json');units=read(R/'sources-laws.json');ids=[u['id'] for u in units];conditions=read(R/'source-conditions.json');oldids=cfg['train'][:10]
 reviews=[]
 for p in sorted((R/'web').glob('TRAIN*.raw.json')):
  x=read(p)
  for r in x.get('reviews',[]):reviews.append(dict(r,review_file=str(p)))
 reviewmap={(str(x['case_id']),x['unit_id']):x for x in reviews};quality=[];changes=[];report=[]
 authority_index.build(units,R/'index.sqlite')
 for split,cids in [('TRAIN',cfg['train']),('DEV',cfg['dev'])]:
  if stage!='all' and split!=stage:continue
  for cid in cids:
   if split=='TRAIN':
    source=train_source(cid,oldids);old=read(R/'train-original-labels'/f'{cid}.json');originals=old['uses']+[x['record'] for x in old.get('isolated',[])]+old.get('unknown',[])
    original_by={x['unit_id']:x for x in originals};assert len(original_by)==len(originals)
    proposal=read(I/'graph-inputs'/f'{cid}.json');rejected=[]
    if cid in oldids:
     rev=next(read(f) for f in (O/'parsed').glob('GREV*.json') if str(read(f)['case_id'])==cid);rejected=[x['id'] for x in rev['rejections']]
    v=lab.inspect({'case_id':cid,'uses':[compact(x) for x in originals]},source,units)
    for uid,s in v['slots'].items():
     layer='OLD_SOURCE_REVIEWED' if cid in oldids and not uid.startswith('LAW:V09:') else 'NEW_SINGLE_PASS_ANCHOR_CHECKED'
     if cid=='125596702':layer='DUPLICATE_PROVENANCE_PARTIAL_LABELS'
     s['semantic_quality']=layer;s['original_record']=original_by.get(uid)
     reviewed=reviewmap.get((cid,uid))
     if reviewed:
      s['sample_source_review']=reviewed
      if reviewed['decision'] in ('CORRECTION_NEEDED','UNRESOLVED') or reviewed.get('suggested_category')!=s.get('canonical_category'):
       s['prior_state']=s['state'];s['state']='ISOLATED';s['reason']='LIMITED_SOURCE_REVIEW_DISPUTE_NO_SEMANTIC_REWRITE'
     quality.append({'case_id':cid,'unit_id':uid,'layer':layer,'state':s['state'],'sample_review':None if not reviewed else reviewed['decision']})
     was=uid in {x['unit_id'] for x in old['uses']};now=s['state']=='KNOWN'
     if was!=now:changes.append({'case_id':cid,'unit_id':uid,'old_entered_loss':was,'new_entered_loss':now,'locator':v['locations'].get(uid,{}).get('status'),'reason':s.get('reason'),'quality_not_upgraded':True})
    question=read(O/'task-material'/f'{cid}.json')['question'] if cid in oldids else json.loads((B/'continuation-01/tasks'/f'GRAPH-{cid}.txt').read_text().split('\nMATERIAL\n')[1].rsplit('\nEND_OF_INPUT',1)[0])['question']
   else:
    source=read(R/'dev-sources'/f'{cid}.json');fixed=read(R/'dev-fixed'/f'{cid}.json');a=read(R/'web'/f'ALIGN-{cid}.raw.json');rv=read(R/'web'/f'REVIEW-{cid}.raw.json')
    assert str(a['case_id'])==cid and len(a['alignments'])==30 and {a['unit_id'] for a in a['alignments']}==set(ids)
    proposal=copy.deepcopy(fixed);proposal['alignments']=a['alignments'];proposal['coverage_limits']+=a['coverage_limits']
    rejected=list({x['id'] for x in read(R/'dev-old-review'/f'{cid}.json')['rejections']}|{x['id'] for x in rv.get('rejections',[])})
    v=lab.inspect(rv,source,units);v['review_type']='INDEPENDENT_MODEL_SOURCE_REVIEW_NOT_HUMAN_GOLD'
    first=lab.inspect(read(R/'web'/f'LABEL-{cid}.raw.json'),source,units);save(f'dev-first-reference/{cid}.json',first)
    v['disagreements']=rv.get('disagreements',[]);v['coverage_limits']=rv.get('coverage_limits',[])
    samples=read(D/'sources/samples.json');question=next(s['question'] for s in samples if s['case_id']==cid)
   inspect_graph(proposal,source,units)
   g=graph.make_graph(proposal,conditions,source,units,rejected);query=question+'\n'+'\n'.join(s['text'] for s in source['segments']);ranking=authority_index.search(R/'index.sqlite',query,40);numeric=graph.numeric(g,ranking,units)
   assert numeric['z'].shape==(30,18) and all(np.isfinite(a).all() for a in numeric.values())
   save(f'sources/{cid}.json',source);save(f'labels/{cid}.json',v);save(f'graph-inputs/{cid}.json',proposal);save(f'graphs/{cid}.json',g);save(f'retrieval/{cid}.json',{'query':query,'ranking':ranking,'labels_visible':False});save(f'rejections/{cid}.json',rejected)
   p=R/'numeric'/f'{cid}.npz';p.parent.mkdir(exist_ok=True);np.savez_compressed(p,**numeric)
   report.append({'case_id':cid,'split':split,'slots':{s:sum(r['state']==s for r in v['slots'].values()) for s in ['KNOWN','UNKNOWN','ISOLATED','UNPROCESSED']},'nodes':len(g['nodes']),'edges':len(g['edges']),'quarantine':len(g['quarantine']),'pending':len(g['pending']),'all30_alignments':len(g['alignments']),'labels_in_feature_path':False})
 save('import-report-'+stage+'.json',report)
 if stage in ('TRAIN','all'):save('train-location-changes.json',changes);save('quality-ledger.json',quality)
 print(report)
if __name__=='__main__':run(sys.argv[1] if len(sys.argv)>1 else 'all')
