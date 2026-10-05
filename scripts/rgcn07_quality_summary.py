"""Summarize the completed pilot without changing labels or training a predictor."""
import json,csv,hashlib,datetime
from pathlib import Path
from collections import defaultdict,Counter
R=Path('outputs/rgcn-ranking-diagnostic-07/pilot')
def read(p):return json.loads(p.read_text())
def save(name,obj):
 p=R/name
 if p.exists():raise FileExistsError(p)
 p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
def main():
 q=read(R/'quality-report.json');pairs=defaultdict(list);summary=[]
 for i,row in enumerate(q['cases'],1):
  cid=row['case_id'];lab=read(R/f'labels/{cid}.json') if (R/f'labels/{cid}.json').exists() else {'preferences':[],'uses':[],'isolated':[],'abstentions':[]}
  graph=read(R/f'graphs/{cid}.json') if (R/f'graphs/{cid}.json').exists()else {'nodes':[],'quarantine':[],'pending':[]}
  for p in lab['preferences']:pairs[tuple(sorted([p['preferred'],p['other']]))].append({'case':cid,'preferred':p['preferred']})
  adjacency=defaultdict(set)
  for p in lab['preferences']:adjacency[p['preferred']].add(p['other'])
  cycles=[]
  def walk(n,path):
   for nxt in adjacency.get(n,()):
    if nxt in path:cycles.append(path[path.index(nxt):]+[nxt])
    else:walk(nxt,path+[nxt])
  for n in list(adjacency):walk(n,[n])
  row2={'case_id':cid,'accepted_uses':len(lab['uses']),'directional_preferences':len(lab['preferences']),'abstentions':len(lab['abstentions']),'isolated_labels':len(lab['isolated']),'review_rejected_graph_records':row.get('graph_review_rejections',None),'graph_quarantine':len(graph['quarantine']),'graph_pending':len(graph['pending']),'graph_nodes':len(graph['nodes']),'direction_cycle_count':len(cycles),'graph_status':row['graph_status'],'labels_status':row['labels_status']}
  summary.append(row2)
  if cycles:save(f'cycle-warning-{cid}.json',{'cycles':cycles,'no_automatic_label_rewrite':True})
 pair_summary=[{'pair':list(k),'cases':len(v),'directions':len({x['preferred']for x in v}),'records':v}for k,v in sorted(pairs.items())]
 save('case-quality-summary.json',summary);save('crosscase-directions.json',pair_summary)
 with (R/'case-quality-summary.csv').open('w')as f:
  w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
 ledger=read(R/'web-ledger.json');assert len(ledger)==len({x['task']for x in ledger})<=40
 start=min(datetime.datetime.fromisoformat(x['at']) for x in ledger)
 done=max(datetime.datetime.fromisoformat(x.get('completed_at',x['at'])) for x in ledger)
 save('cost.json',{'submissions':len(ledger),'model_retries':0,'final_legal_answers':0,'paid_api_calls':0,'local_model_generations':0,'visible_mode':'High / 高','visible_family':'Latest observed at setup','exact_model':None,'tokens':None,'web_peak_memory':None,'observation_elapsed_seconds':(done-start).total_seconds(),'elapsed_is_not_model_compute_time':True,'submitted_task_characters':sum(len((R/f"tasks/{x['task']}.txt").read_text())for x in ledger),'raw_code_characters':sum(sum(map(len,read(p)))for p in (R/'raw').glob('*-code-blocks.json')),'content_preserving_escape_treatments':[p.name for p in (R/'raw').glob('*-format-treatment.json')]})
 save('dataset-manifest.json',{'role':'TRAINING_PILOT_NOT_TEST','quality_limit':'Model-proposed and source-reviewed; no human gold, no guarantee of semantic accuracy','unknown_and_disputed_not_negatives':True,'graph_label_tasks_isolated':True,'fixed_compared_pairs':16,'operational_gate':q['expansion_gate'],'case_count':len(summary),'full_reference_ranking_available':False,'hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest()for d in ['graphs','labels','parsed','sources','review-task-freezes']for p in sorted((R/d).glob('*.json'))}})
 print(json.dumps({'cases':len(summary),'directed_preferences':sum(x['directional_preferences']for x in summary),'uses':sum(x['accepted_uses']for x in summary),'direction_reversals':sum(x['directions']>1 for x in pair_summary),'gate':q['expansion_gate']},indent=2))
if __name__=='__main__':main()
