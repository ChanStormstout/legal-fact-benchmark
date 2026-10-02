"""Mechanical full-run tables; semantic audit remains separately bounded to three."""
import csv,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import write_new
from legal_bench.rules_verdict_v1.extract_v2 import at_string_limits
R=Path('outputs/rules-verdict-v6-end-to-end')
def read(p):return json.loads(Path(p).read_text())
def main():
 result=read(R/'results.json');table=[];quotes=[]
 for row in result['rows']:
  cid=row['case_id'];a=row['A']['answer'];b=row['B'];view=read(R/'runs'/cid/'B/imported.json') if (R/'runs'/cid/'B/imported.json').exists() else None
  law=read(R/'prepared'/cid/'law-package.json');source=read(R/'sources'/(cid+'.json'));lookup={s['id']:s['text'] for s in source['segments']+law['law_segments']}
  ev=[] if a is None else a['evidence']
  q=[{'evidence':e,'exact':bool(e['quote']) and e['quote'] in lookup.get(e['segment_id'],'')} for e in ev]
  quotes.append({'case_id':cid,'A_quote_checks':q,'source_location_not_entailment':True})
  conditions={p:sorted(set(g['conditions'][p]['state'] for g in b.get('bindings',[]))) for p in ['TENANCY','TRANSFER_MODE','AFTER_1952_06_09','LANDLORD_WRITTEN_CONSENT']}
  table.append({'case_id':cid,'scope':row['scope']['mode'],'rules':','.join(row['retrieval']['selected_card_ids']),'A_run':row['A']['run_status'],'A_outcome':a['outcome'] if a else None,'B_run':b['run_status'],'B_outcome':b['outcome'],'B_condition_states_across_bindings':json.dumps(conditions),'B_usable_objects':len(view['objects']) if view else 0,'B_usable_assertions':len(view['assertions']) if view else 0,'B_quarantine':len(view['quarantine']) if view else 0,'B_bindings':len(b.get('bindings',[])),'A_exact_quotes':sum(x['exact'] for x in q),'A_quotes':len(q),'A_string_limits':json.dumps(at_string_limits(a,read(R/'prepared'/cid/'A/schema.json'))) if a else '[]','historical_direction_only':'SUPPORT_GROUND'})
 write_new(R/'table.json',table);write_new(R/'quote-checks.json',quotes)
 p=R/'table.csv'
 if p.exists():raise FileExistsError('Preserve existing table')
 with p.open('w',newline='') as h:
  w=csv.DictWriter(h,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
 print(json.dumps(table,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
