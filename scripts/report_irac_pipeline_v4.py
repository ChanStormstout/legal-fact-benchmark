"""Read-only aggregate after the one frozen v4 batch; no model or semantic changes."""
import json,csv,hashlib,sys
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.irac_pipeline_v4 import R,V,CASES,read,save,verify

def main():
 ledger=read(R/'run-ledger.json');assert ledger['status'] in ['COMPLETE','STOPPED','ENVIRONMENT_BLOCKED']
 results=[];table=[]
 for slot in read(R/'protocol.json')['order']:
  cid,stage=slot.split('/');p=R/'runs'/cid/stage;r=read(p/'result.json') if (p/'result.json').exists() else {'run_status':'NOT_RUN','prediction':None};meta=read(p/'run.json') if (p/'run.json').exists() else {};inputmeta=read(p/'input-before-generation.json') if (p/'input-before-generation.json').exists() else {}
  row={'slot':slot,'run_status':r['run_status'],'prediction':r.get('prediction'),'reason':r.get('reason',r.get('error',meta.get('error'))),'input_tokens':meta.get('prompt_tokens'),'output_tokens':meta.get('output_tokens'),'seconds':meta.get('elapsed_seconds'),'peak_mlx_gb':meta.get('peak_mlx_memory_gb'),'peak_rss_gb':meta.get('peak_rss_gb'),'finish_reason':meta.get('finish_reason'),'max_tokens':meta.get('effective_max_tokens',inputmeta.get('max_tokens')),'material_hash':inputmeta.get('material_sha256'),'law_hash':inputmeta.get('law_sha256'),'path':str(p),'called':(p/'start.json').exists()};results.append(row)
 save(R/'all-results.json',results)
 for cid in CASES:
  methods={x['slot'].split('/')[1]:x for x in results if x['slot'].startswith(cid+'/')}
  for st in ['A','B','C']:
   x=methods[st];pr=methods['P'];table.append({'case_id':cid,'method':st,'run_status':x['run_status'],'prediction':';'.join(a['prediction'] for a in x['prediction']['answers']) if x['prediction'] else None,'seconds':x['seconds'],'pipeline_seconds':(x['seconds'] or 0)+((pr['seconds'] or 0) if st!='A' else 0),'input_tokens':x['input_tokens'],'output_tokens':x['output_tokens'],'pipeline_input_tokens':(x['input_tokens'] or 0)+((pr['input_tokens'] or 0) if st!='A' else 0),'pipeline_output_tokens':(x['output_tokens'] or 0)+((pr['output_tokens'] or 0) if st!='A' else 0),'material_hash':x['material_hash'],'law_hash':x['law_hash']})
  active=[x for st,x in methods.items() if st in ['A','P','B','C'] and x['material_hash']];assert len({x['material_hash'] for x in active})<=1 and len({x['law_hash'] for x in active})<=1,'UNEQUAL_MATERIALS'
  save(R/'review-dossiers'/f'{cid}.json',{'sources':read(R/'sources'/f'{cid}.json'),'results':methods,'program_checks':read(R/'runs'/cid/'P/checks-full.json') if (R/'runs'/cid/'P/checks-full.json').exists() else None})
 with (R/'technical-comparison.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
 attempted=[x for x in results if x['called']];cost={'calls':len(attempted),'seconds':sum(x['seconds'] or 0 for x in attempted),'input_tokens':sum(x['input_tokens'] or 0 for x in attempted),'output_tokens':sum(x['output_tokens'] or 0 for x in attempted),'peak_mlx_gb':max((x['peak_mlx_gb'] or 0 for x in attempted),default=0),'peak_rss_gb':max((x['peak_rss_gb'] or 0 for x in attempted),default=0),'status_counts':dict(Counter(x['run_status'] for x in results)),'load_seconds':read(R/'freeze/token-preflight.json')['load_seconds'],'web_calls':0,'retries':0,'gnn_training':0,'note':'Shared proposal counted once in experiment total, once in each B/C method cost; RSS and MLX have distinct meanings.'};save(R/'cost.json',cost)
 before=read(R/'preservation-before.json');bad=[p for p,h in before.items() if not Path(p).exists() or hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h];save(R/'preservation-after.json',{'checked':len(before),'changed':bad});assert not bad
 verify();save(R/'freeze-integrity.json',{'passed':True,'all_live_and_snapshot_hashes_unchanged':True})
 with (R/'answer-slots.md').open('w') as f:
  f.write('# 原始答案入口\n\n')
  for x in results:f.write(f"- {x['slot']}: {x['run_status']} — [结果](runs/{x['slot']}/result.json)\n")
 print(json.dumps(cost,indent=2))
if __name__=='__main__':main()
