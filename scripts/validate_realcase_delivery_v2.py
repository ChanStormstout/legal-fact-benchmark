"""One local integrity pass over completed artifacts, not legal evaluation."""
import datetime as dt
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from legal_bench.proof_carrying.realcase_contracts import read_json,write_once,byte_hash,content_hash,schemas,validate
from legal_bench.proof_carrying.realcase_tasks_v2_2 import CASES,KINDS
OUT=ROOT/'outputs/proof-carrying-realcase-v2'

class Links(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.links=[]
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if 'id' in d:self.ids.append(d['id'])
        if tag=='a' and d.get('href','').startswith('#'):self.links.append(d['href'][1:])

def main():
    reg=read_json(OUT/'registration.json');faults=[]
    historical=[p for p,h in reg['historical_hashes'].items() if byte_hash(ROOT/p)!=h]
    faults+=['HISTORICAL_CHANGED:'+p for p in historical]
    f=read_json(OUT/'freeze/interface-02/config.json')
    frozen=[p for p,h in {**f['code_hashes'],**f['material_hashes']}.items() if byte_hash(ROOT/p)!=h]
    faults+=['FROZEN_CHANGED:'+p for p in frozen]
    calls=read_json(OUT/'run-index.json')['calls'];deliveries=[]
    if len(calls)!=15:faults.append('CALL_COUNT')
    for c in calls:
        cid,kind=c['case'],c['task'];p=Path(c['task_path']);p=p if p.is_absolute() else OUT/p
        text=p.read_text();m=read_json(p.parent/'manifest.json');d=read_json(p.parent/'delivery.json')
        if byte_hash(p)!=m['sha256'] or byte_hash(p)!=d['sha256']:faults.append('TASK_HASH:'+str(p))
        if f'END_OF_TASK_{cid}_{kind}' not in text:faults.append('END_MARKER:'+str(p))
        doc=read_json(OUT/'sources'/f'{cid}.json')
        body=[x for x in doc['segments'] if CASES[cid]['body'][0]<=x['original_line']<=CASES[cid]['body'][1]]
        mapped=[x['source_segment_id'] for x in d['mapping']]
        if set(mapped)!=set(x['id'] for x in body):faults.append('SOURCE_COVERAGE:'+str(p))
        for x in body:
            if ('['+x['id']+'] '+x['text']) not in text:faults.append('SOURCE_TEXT:'+x['id'])
        validate(read_json(OUT/'runs'/cid/kind/'parsed.json'),schemas(kind))
        if kind=='reference' and m['attachments_hash']!=content_hash({}):faults.append('REFERENCE_ATTACHMENT')
        deliveries.append({'case':cid,'task':kind,'body_lines':len(body),'mapping_complete':True,'task_sha256':byte_hash(p)})
    for cid in CASES:
        p=OUT/'cases'/cid
        if read_json(p/'review-order.json')!=read_json(p/'review-order-before-evaluation.json'):faults.append('RANKING_CHANGED:'+cid)
        for name in ('S1','S2'):
            q=p/'runs'/name/'check.json'
            if not q.exists():continue
            x=read_json(q)
            if x['status']!='COMPLETED':faults.append('CHECKER_FAILURE:'+cid+name)
            if x['legal_approval'] or any(a['formal_status']!='APPROVAL_PENDING' for a in x['requests']):faults.append('APPROVAL_UPGRADE')
    parser=Links();parser.feed((OUT/'walkthrough.html').read_text())
    broken=sorted(set(parser.links)-set(parser.ids))
    duplicate_ids=len(parser.ids)-len(set(parser.ids))
    if broken or duplicate_ids:faults.append('WALKTHROUGH_LINKS')
    current_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if current_head!=reg['head']:faults.append('HEAD_CHANGED')
    result={'validated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'PASS' if not faults else 'FAIL',
        'faults':faults,'historical_files_checked':len(reg['historical_hashes']),'historical_changes':historical,
        'frozen_code_and_materials':len(f['code_hashes'])+len(f['material_hashes']),'frozen_changes':frozen,
        'calls':len(calls),'source_task_deliveries':deliveries,
        'html_internal_links':len(parser.links),'html_broken_links':broken,'html_duplicate_ids':duplicate_ids,
        'head':current_head,'no_commit_or_push':True,
        'semantic_correctness_or_legal_approval_validated':False}
    write_once(OUT/'delivery-validation.json',result)
    print({k:v for k,v in result.items() if k!='source_task_deliveries'})
    if faults:raise SystemExit(1)

if __name__=='__main__':main()
