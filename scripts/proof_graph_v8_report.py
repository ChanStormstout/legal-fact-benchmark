"""Post-run accounting only; never alters inputs, labels, ranking or certificates."""
import json,csv,hashlib,re,datetime
from pathlib import Path
R=Path('outputs/proof-carrying-graph-integration-v8')
def read(p):return json.loads(p.read_text())
def main():
    transport=[]
    for p in sorted((R/'web').glob('*/*/transport.json')):
        d=read(p);tool=p.parent/'submission-tool.txt'
        if tool.exists():
            m=re.search(r'### Result\n(.*?)\n### Ran',tool.read_text(),re.S)
            if m:d['submitted_at']=json.loads(m.group(1)).get('submitted_at')
        cid=p.parts[-3];kind=p.parts[-2];d.update(case=cid,kind=kind,task_bytes=(R/'tasks'/cid/(kind+'.txt')).stat().st_size,response_bytes=(p.parent/'response.txt').stat().st_size)
        if d.get('submitted_at') and d.get('observed_completed_at'):
            d['observed_wall_seconds']=(datetime.datetime.fromisoformat(d['observed_completed_at'].replace('Z','+00:00'))-datetime.datetime.fromisoformat(d['submitted_at'].replace('Z','+00:00'))).total_seconds()
        transport.append(d)
    (R/'transport-summary.json').write_text(json.dumps(transport,indent=2))
    rows=read(R/'comparison.json') if (R/'comparison.json').exists() else []
    reports=[]
    for r in rows:
        folder=R/'results'/r['method']/r['case'];check=read(folder/'checker-result.json');q=check.get('requests',[])
        reports.append({**{k:r[k] for k in ('case','method','known_usable_selected','known_unusable_selected','known_usable_total','unlabelled_selected')},
            'selected_count':len(r['selected']),'selected_hash':hashlib.sha256(json.dumps(r['selected']).encode()).hexdigest(),
            'requests':len(r['requests']),'true_conditional_or_explicit':sum(x.get('answer')=='TRUE' for x in q),
            'unknown':sum(x.get('answer')=='UNKNOWN' for x in q),'invalid':sum(x.get('draft_status')=='INVALID' for x in q),
            'open_uncomputed':sum(bool(x.get('uncomputed')) for x in q),'not_selected':sum(x.get('technical_status')=='NOT_SELECTED' for x in r['requests']),
            'legal_approval':False,'answer_path':str(folder/'analysis.json')})
    if reports:
        with (R/'comparison.csv').open('w') as f:
            w=csv.DictWriter(f,fieldnames=list(reports[0]));w.writeheader();w.writerows(reports)
    fits=[read(p) for p in sorted((R/'fits').glob('*/training-complete.json'))] if (R/'fits').exists() else []
    cost={'web_tasks':len(transport),'exact_web_tokens':None,'exact_web_generation_time':None,'web_time_scope':'observed send-to-retrieval latency, not GPU time; tasks overlapped',
          'fits':len(fits),'training_seconds':sum(x['seconds'] for x in fits),'all_parameters_updated':bool(fits) and all(x['updated'] for x in fits),
          'encoder':[read(p) for p in sorted((R/'encoding').glob('*/complete.json'))],
          'parameter_counts':{x['kind']:x['parameter_count'] for x in fits}}
    (R/'cost.json').write_text(json.dumps(cost,indent=2));print(json.dumps({'tasks':len(transport),'fits':len(fits),'analyses':len(reports),'training_seconds':cost['training_seconds']}))
if __name__=='__main__':main()
