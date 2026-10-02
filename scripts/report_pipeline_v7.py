"""Reporting only, after immutable model run and one decisive-source review."""
import csv,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import write_new
R=Path('outputs/rules-verdict-v7-intermediate')
def read(p):return json.loads(p.read_text())
def main():
 data=read(R/'results.json');review=read(R/'final-source-review.json');by={(x['case_id'],x['method']):x for x in review['rows']};table=[];answers=[]
 for r in data['rows']:
  key=(r['case_id'],r['method']);v=by[key];d=R/'runs'/r['case_id']/r['method'];der=read(d/'final-input-derivation.json') if (d/'final-input-derivation.json').exists() else {}
  table.append({'case_id':r['case_id'],'method':r['method'],'outcome':r['answer_status'],'decisive_basis':v['decisive_basis'],'critical_gaps':v['critical_gaps'],'review':v['assessment'],'comparison':v['comparison'],'technical_status':r['run_status'],'calls':r['calls'],'input_tokens':r['input_tokens'],'output_tokens':r['output_tokens'],'seconds':round(r['seconds'],2),'program_tokens':der.get('program_tokens',0),'intermediate_tokens':der.get('intermediate_tokens',0)})
  answers.append('## '+r['case_id']+' / '+r['method']+'\n\nTechnical status: '+r['run_status']+'\n\nRaw attempts: runs/'+r['case_id']+'/'+r['method']+'/stage1 and (when attempted) stage2. Null is a technical failure, not a legal answer.\n\n```json\n'+json.dumps(r.get('answer'),ensure_ascii=False,indent=2)+'\n```\n')
 write_new(R/'comparison-table.json',table)
 with (R/'comparison-table.csv').open('x',newline='') as h:
  w=csv.DictWriter(h,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
 with (R/'final-answer-slots.md').open('x') as h:h.write('# V7 six method slots: two complete answers and four technical failures\n\n'+'\n'.join(answers))
 costs={}
 for arm in ['A2','B2']:
  rows=[x for x in table if x['method']==arm];costs[arm]={k:sum(x[k] for x in rows) for k in ['calls','input_tokens','output_tokens','seconds','program_tokens','intermediate_tokens']}
 write_new(R/'costs.json',{'methods':costs,'overall_generation_seconds':data['seconds'],'peak_mlx_memory_gb':data['peak_memory_gb'],'equal_calls_not_equal_cost':True,'load_and_preparation_excluded_from_generation_time':True})
if __name__=='__main__':main()
