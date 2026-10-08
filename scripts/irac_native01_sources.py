"""Source envelopes preserved; local discovery fields are never substituted."""
import json
from pathlib import Path
from legal_bench.rules_verdict_v1.source_identity_v2 import parse_responses, merge_windows
from scripts.irac_native01_prepare import ROOT, save, sha

def merge():
    responses=[]
    for p in sorted((ROOT/'sources/raw').glob('*.txt')):
        responses.extend(parse_responses(p.read_text(),p))
    documents=merge_windows(responses)
    # This directory is working acquisition state, not a frozen experiment.
    # Each raw response remains immutable, freezing makes another version.
    for cid,d in documents.items():
        p=ROOT/'sources/documents'/f'{cid}.json';p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
    return documents

if __name__=='__main__':
    docs=merge()
    print(json.dumps({cid:{'status':d['status'],'count':len(d['segments']),'total':d['totals'],'next_missing':(min(d['missing_lines']) if d['missing_lines'] else None)} for cid,d in docs.items()},indent=2))
