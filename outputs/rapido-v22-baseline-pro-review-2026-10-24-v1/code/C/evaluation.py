"""Final-only blinded export and source-adjudicated aggregation. No runtime import."""
import argparse
import json
import random
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path[:0]=[str(ROOT/'src'),str(ROOT.parents[1])]
from common import read,save,digest,source_payload

def export(run,dest):
    cfg=read(run/'run-protocol.json') if (run/'run-protocol.json').exists() else read(ROOT/'protocol.json');rng=random.Random(cfg['parameters']['seed']);items=[];private={}
    for cid in cfg['cases']:
        source=run/'inputs'/(cid+'.json')
        if not source.exists():raise ValueError('MISSING_EVALUATION_INPUT:'+cid)
        snapshot=read(source);arms=list(cfg['arms']);rng.shuffle(arms)
        # Same source view for all anonymous reports of a case. The full eligible
        # catalog is a separate source-only companion, not an intermediate answer.
        shown=set()
        for path in (run/'cases'/cid).glob('*/requests/*.json'):
            shown.update(read(path)['material']['sources'])
        payload=source_payload(snapshot)
        primary={i:s for i,s in payload.items() if s['domain']!='HISTORY' or i in shown}
        companion='sources/'+cid+'-allowed-history.json'
        save(dest/companion,{'case_id':cid,'sources':{i:s for i,s in payload.items() if s['domain']=='HISTORY'},
            'identity':{i:s['metadata'].get('history_identity') for i,s in snapshot['directory'].items() if s['domain']=='HISTORY'}})
        for arm in arms:
            folder=run/'cases'/cid/arm;outcome=folder/'outcome.json';report=folder/'final-report.json'
            if not outcome.exists():continue
            o=read(outcome);text=(folder/'final-report.txt').read_text() if (folder/'final-report.txt').exists() else ''
            ident='R'+str(len(items)+1).zfill(3)
            items.append({'blind_id':ident,'case_id':cid,'question':snapshot['question'],'scope':snapshot['scope'],
                'allowed_sources':primary,'full_allowed_history_companion':companion,'report_text':text,'report_hash':digest(read(report)) if report.exists() else digest(text) if text else None,
                'grading':'Complete important content plus no serious source/binding/procedure errors; unresolved can be valid; empty cannot pass. Check omissions against originals, not generated tasks.'})
            private[ident]={'case_id':cid,'arm':arm,'report_hash':items[-1]['report_hash'],'complete_chain':o.get('complete_chain',o.get('technical_complete',False)),'candidate_available':o.get('candidate_available',bool(text))}
    save(dest/'blinded-final-reports.json',{'items':items,'planned_cases':cfg['cases'],
        'unattempted_slots':[{'case_id':cid,'arm':arm} for cid in cfg['cases'] for arm in cfg['arms'] if not (run/'cases'/cid/arm/'outcome.json').exists()],'reference_status':'MODEL_SOURCE_REVIEW_NOT_HUMAN_GOLD','contains_intermediate_answers':False})
    save(dest/'private-method-map.json',private)

def aggregate(mapping,labels,cfg):
    """Labels must be final source adjudications; never internal checker results."""
    by={x['blind_id']:x for x in labels};rows=[]
    for bid,key in mapping.items():
        label=by.get(bid)
        if label and (label['report_hash']!=key['report_hash'] or label['origin']!='FINAL_SOURCE_ADJUDICATION'):
            raise ValueError('LABEL_BINDING_OR_ORIGIN_MISMATCH')
        score=None
        if not key['complete_chain'] or not key.get('candidate_available',True):score=False
        elif label is not None:
            score=label['complete_important_content'] and label['source_supported'] and not label['serious_error']
        rows.append({**key,'blind_id':bid,'whole_case_success':score,'annotation':label,'legal_approval':False})
    results={}
    for arm in cfg['arms']:
        selected=[x for x in rows if x['arm']==arm];pending=sum(x['whole_case_success'] is None for x in selected)
        results[arm]={'planned_cases':len(cfg['cases']),'attempted_cases':len(selected),'pending_adjudication':pending,
            'whole_case_rate':sum(x['whole_case_success'] is True for x in selected)/len(cfg['cases']) if not pending and len(selected)==len(cfg['cases']) else None,
            'technical_complete':sum(x['complete_chain'] for x in selected)}
    return {'rows':rows,'arms':results,'dataset':'EXPOSED_DEVELOPMENT','human_gold':False,'independent_generalization':False}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--mapping',type=Path);ap.add_argument('--adjudication',type=Path);args=ap.parse_args()
    if not args.output.resolve().is_relative_to((ROOT/'private').resolve()):raise SystemExit('Private evaluation directory required')
    if args.output.exists():raise SystemExit('Existing evaluation preserved')
    if args.run:export(args.run,args.output)
    else:save(args.output/'aggregate.json',aggregate(read(args.mapping),read(args.adjudication),read(ROOT/'protocol.json')))
