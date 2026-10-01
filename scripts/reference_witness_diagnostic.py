"""Only translate pretest reference MATCH witnesses; never substitute for local B."""
import sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.local_qwen_experiment import ROOT,TASKS,write
from legal_bench.core import read,digest
from legal_bench.field_pipeline_v2 import import_declared,execute_declared
from legal_bench.typed_relations import import_edges
rows=[]
for ref in read(ROOT/'evaluation-sample.json')['rows']:
 if ref['answer']['answer_status']!='MATCH':continue
 source=read(Path(ref['source_file']));binding=ref['answer']['bindings'][0]
 events=[]
 for atom in binding['atoms']:
  e={'id':atom['var'],'unit_id':'u1','kind':'PROCEDURAL_ACT' if atom['type'].startswith('FILE_') else 'FACT','type':atom['type'],'status':atom['status'],'polarity':atom['polarity'],'roles':atom['roles'],'role_evidence':{k:atom['evidence'] for k in atom['roles']},'evidence':atom['evidence'],'status_evidence':atom.get('status_evidence',atom['evidence']),'origin':{'source':'PRETEST_MODEL_REFERENCE_WITNESS'},'scope':{},'scope_parsed':True,'time':None,'attributes':{},'unresolved':[],'scope_dependencies':[]}
  e['known_fields']=[{'field':f,'value':e[f],'evidence':atom['evidence']} for f in ['type','status','polarity']]+[{'field':'roles.'+k,'value':v,'evidence':atom['evidence']} for k,v in e['roles'].items()];events.append(e)
 ann={'case_id':ref['case_id'],'objects':[dict(o,identity_resolved=True) for o in ref['objects']],'units':[{'id':'u1','primary':True,'evidence':ref['main_unit']['evidence']}],'events':events,'edges':[dict(binding['relation'],decision='SUPPORTED')]}
 view=import_declared(ann,source);target={'parent_pairs':[{'left':e['left'],'right':e['right']} for e in ann['edges'] if e['op']=='part_of'],'group_ids':[o['id'] for o in view['objects'] if o['kind']=='GROUP']}
 registry=import_edges(view,source,ann,target);card=next(c for c in TASKS() if c['task_id']==ref['task_id']);result=execute_declared(view,registry,card['query'])
 folder=ROOT/'reference-witness-executor'/ref['case_id']/ref['task_id'];write(folder/'annotation.json',ann);write(folder/'view.json',view);write(folder/'relations.json',registry);write(folder/'result.json',result)
 rows.append({'case_id':ref['case_id'],'task_id':ref['task_id'],'status':result['status'],'path':str(folder),'origin':'PRETEST_REFERENCE_WITNESS_SCHEMA_TRANSLATION_ONLY_NOT_LOCAL_B_NOT_FULL_CASE_EXTRACTION'})
write(ROOT/'reference-witness-executor/results.json',{'rows':rows,'purpose':'Check fixed query/executor compatibility on minimal positive reference witnesses; cannot evaluate local extraction or reference completeness.'});print([(r['case_id'],r['task_id'],r['status']) for r in rows])
