"""Save final-only results and costs; no inference or semantic completion."""
import csv,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import write_new,digest
R=Path('outputs/rules-verdict-v9-final-examples')
def read(p):return json.loads(p.read_text())
def main():
 result=read(R/'results.json');review=read(R/'final-source-review.json');rows=[];answers=[];restore={};lengths={}
 source=read(R/'sources/69305.json');law=read(R/'prepared/69305/law-package.json');byid={x['id']:x['text'] for x in source['segments']+law['law_segments']}
 for r in result['rows']:
  arm=r['method'];p=R/'runs'/arm/'parsed.json';ans=read(p) if r['run_status']=='OK' and p.exists() else None
  v=next((x for x in review['rows'] if x['method']==arm),{})
  rows.append({'case_id':'69305','method':arm,'run_status':r['run_status'],'outcome':ans['outcome'] if ans else None,'input_tokens':r.get('prompt_tokens_actual',r.get('prompt_tokens',0)),'output_tokens':r.get('output_tokens',0),'seconds':round(r.get('elapsed_seconds',0),3),'finish_reason':r.get('finish_reason'),'repetition_field':(r.get('repetition_guard') or {}).get('field'),**v})
  answers.append('## '+arm+'\n\nRun status: '+r['run_status']+'\n\n```json\n'+json.dumps(ans,ensure_ascii=False,indent=2)+'\n```\n')
  if ans:
   restore[arm]=[{'ground_index':i,'point':g['point'],'references':{sid:byid[sid] for sid in g['case_refs']+g['law_refs']}} for i,g in enumerate(ans['grounds'])]
   lengths[arm]={'grounds':[{ 'index':i,'point_words':len(g['point'].split()),'point_chars':len(g['point']),'explanation_words':len(g['explanation'].split()),'explanation_chars':len(g['explanation'])} for i,g in enumerate(ans['grounds'])],'reason_words':len(ans['reason'].split()),'no_string_cutting':True,'writing_targets_not_pass_fail_thresholds':True}
 write_new(R/'comparison-table.json',rows)
 with (R/'comparison-table.csv').open('x',newline='') as f:
  w=csv.DictWriter(f,list(dict.fromkeys(k for row in rows for k in row)));w.writeheader();w.writerows(rows)
 (R/'final-answer-slots.md').write_text('# V9 complete final answers only\n\nFailed outputs retain null answers; raw is saved without repairs.\n\n'+'\n'.join(answers))
 write_new(R/'final-restored-sources.json',restore);write_new(R/'output-lengths.json',lengths)
 write_new(R/'costs.json',{'local_calls':result['local_generation_calls'],'web_calls':0,'retries':0,'input_tokens':sum(x['input_tokens'] for x in rows),'output_tokens':sum(x['output_tokens'] for x in rows),'inference_seconds':result['inference_seconds'],'round_wall_seconds':result['round_wall_seconds'],'peak_mlx_memory_gb':max([x.get('peak_mlx_memory_gb',0) for x in result['rows']] or [0]),'load_seconds':next((x.get('loaded_seconds',0) for x in result['rows'] if 'identity' in x),0),'preflight':read(R/'freeze/token-preflight.json'),'equal_max_output_not_equal_input_cost':True})
 audit=read(R/'start-audit.json');changed=[p for p,h in audit['old_output_hashes'].items() if not Path(p).exists() or digest(Path(p).read_bytes())!=h]
 oldcode=[p for p,h in audit['preexisting_changes'].items() if p.startswith('legal_bench/') or p in ['scripts/pipeline_v8.py','scripts/report_pipeline_v8.py','tests/test_intermediate_v8.py'] if not Path(p).exists() or digest(Path(p).read_bytes())!=h]
 assert not changed and not oldcode
 write_new(R/'preservation-check.json',{'prior_V1_V8_output_files':len(audit['old_output_hashes']),'changed_old_output_files':changed,'modified_preexisting_experiment_code':oldcode,'original_local_chunk_v11_unchanged':digest(Path('legal_bench/local_chunk_v11.py').read_bytes())==audit['preexisting_changes']['legal_bench/local_chunk_v11.py']})
 write_new(R/'source-hashes.json',{str(p.relative_to(R)):{'sha256':digest(p.read_bytes()),'same_bytes_as_v8':p.read_bytes()==(Path('outputs/rules-verdict-v8-paired')/p.relative_to(R)).read_bytes()} for p in [R/'sources/69305.json',R/'prepared/69305/law-package.json',R/'retrieval/69305/result.json',R/'inherited-scope-audit.json']})
if __name__=='__main__':main()
