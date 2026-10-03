"""Post-run artifact collection only; no inference or semantic repair."""
import csv,json,sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import write_new,digest
R=Path('outputs/rules-verdict-v8-paired')
def read(p):return json.loads(p.read_text())
def main():
 data=read(R/'results.json');review=read(R/'final-source-review.json');table=[];answers=[]
 for arm in ['A','B']:
  runs=[x for x in data['rows'] if x['method']==arm];final=runs[-1];p=R/'runs'/arm/'final/parsed.json';answer=read(p) if p.exists() else None
  rev=next((x for x in review.get('rows',[]) if x['method']==arm),{})
  table.append({'case_id':'69305','method':arm,'outcome':answer['outcome'] if answer else None,'technical_status':final['run_status'],'failed_or_skipped_reason':final.get('reason',data['stop_reason']),'calls':sum('identity' in x for x in runs),'input_tokens':sum(x.get('prompt_tokens_actual',x.get('prompt_tokens',0)) for x in runs),'output_tokens':sum(x.get('output_tokens',0) for x in runs),'seconds':round(sum(x.get('elapsed_seconds',0) for x in runs),3),**rev})
  answers.append('## '+arm+'\n\n'+final['run_status']+'\n\n```json\n'+json.dumps(answer,ensure_ascii=False,indent=2)+'\n```\n')
 write_new(R/'comparison-table.json',table)
 fields=list(dict.fromkeys(k for row in table for k in row))
 with (R/'comparison-table.csv').open('x',newline='') as h:w=csv.DictWriter(h,fields);w.writeheader();w.writerows(table)
 (R/'final-answer-slots.md').write_text('# V8 69305 final answers\n\nTechnical failure and SKIPPED have null answers, never reconstructed from partial output.\n\n'+'\n'.join(answers))
 write_new(R/'costs.json',{'calls':data['calls'],'web_calls':0,'retries':0,'inference_seconds':data['inference_seconds'],'round_wall_seconds':data['round_wall_seconds'],'input_tokens':sum(x['input_tokens'] for x in table),'output_tokens':sum(x['output_tokens'] for x in table),'peak_mlx_memory_gb':max(x.get('peak_mlx_memory_gb',0) for x in data['rows']),'intermediate_sizes':{a:read(R/'runs'/a/'intermediate-size.json') for a in ['A','B'] if (R/'runs'/a/'intermediate-size.json').exists()},'equal_calls_not_equal_cost':True})
 # Recover every final source address, without certifying support.
 s=read(R/'sources/69305.json');law=read(R/'prepared/69305/law-package.json');source={x['id']:x['text'] for x in s['segments']+law['law_segments']}
 recovered={}
 for a in ['A','B']:
  p=R/'runs'/a/'final/parsed.json'
  if p.exists():recovered[a]=[{ 'ground_index':i,'references':{sid:source[sid] for sid in g['case_refs']+g['law_refs']}} for i,g in enumerate(read(p)['grounds'])]
 write_new(R/'final-restored-sources.json',recovered)
 audit=read(R/'start-audit.json');bad=[p for p,h in audit['prior_V1_V7_files'].items() if not Path(p).exists() or digest(Path(p).read_bytes())!=h]
 draft='legal_bench/local_chunk_v11.py'
 write_new(R/'preservation-check.json',{'prior_files_checked':len(audit['prior_V1_V7_files']),'changed_prior_files':bad,'existing_untracked_draft_unchanged':digest(Path(draft).read_bytes())==audit['code_hashes_before'][draft],'historical_outputs_byte_preserved':not bad})
 assert not bad
if __name__=='__main__':main()
