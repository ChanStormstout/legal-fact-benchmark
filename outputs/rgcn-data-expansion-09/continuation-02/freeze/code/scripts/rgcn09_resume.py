"""Resume frozen V09 data tasks; reuse validators and keep old bytes unchanged."""
import datetime
import hashlib
import json
import shutil
import sys
from pathlib import Path
from scripts import rgcn09_import as imp

BASE=Path('outputs/rgcn-data-expansion-09')
OUT=BASE/'continuation-02'

def collect_downloads():
    ledgers=sorted(OUT.glob('download-recovery*.json'))
    old=[row for ledger in ledgers for row in imp.read(ledger)]
    recorded={(row.get('task_id'),row.get('sha256')) for row in old}
    manifest=imp.read(BASE/'continuation-01/split-manifest.json')['cases']
    wanted={str(x['case_id']) for x in manifest if x['split']=='TRAIN' and not x.get('status','').startswith('EXISTING')}|{'1106992'}
    found=[]
    for path in Path('/Users/victor/Downloads').glob('*.json'):
        if not any(c in path.name for c in wanted):continue
        try:p=imp.read(path)
        except (ValueError,UnicodeError):continue
        if not isinstance(p,dict) or str(p.get('case_id')) not in wanted:continue
        cid=str(p['case_id'])
        role='LABEL' if 'uses' in p else 'GRAPH' if 'alignments' in p and 'facts' in p else None
        if not role:continue
        tid=role+'-'+cid
        target=OUT/'web'/(tid+'.download.json')
        if target.exists():
            if target.read_bytes()!=path.read_bytes():
                found.append({'task_id':tid,'path':str(path),'status':'CONFLICT_PRESERVED_NOT_OVERWRITTEN'})
                continue
            if (tid,imp.digest(path)) in recorded:continue
        expected=16 if cid=='1106992' else 30
        if role=='LABEL' and len(p.get('uses',[]))!=expected:continue
        if not target.exists():shutil.copyfile(path,target)
        found.append({'task_id':tid,'download_path':str(path),'mtime_utc':datetime.datetime.fromtimestamp(path.stat().st_mtime,datetime.timezone.utc).isoformat(),'sha256':imp.digest(path),'status':'RAW_JSON_COPIED_UNCHANGED'})
    if found:imp.save(OUT/('download-recovery-%03d.json'%len(ledgers)),found)
    return found

original_payload=imp.payload

def recovered(tid):
    if tid == 'LABEL-125596702':
        raise ValueError('PROTOCOL_DEVIATION_DUPLICATE_USER_INSTRUCTION; preserve raw; not single-pass accepted data')
    for root in (OUT,BASE/'recovery-03'):
        path=root/'web'/(tid+'.download.json')
        if path.exists():return imp.read(path),str(path),'DOWNLOADED_JSON_UNCHANGED'
        path=root/'web'/(tid+'.codeblocks.json')
        if path.exists():
            matches=[]
            for block in imp.read(path):
                try:p=json.loads(block)
                except (ValueError,TypeError):continue
                if isinstance(p,dict) and str(p.get('case_id'))==tid.split('-',1)[1]:matches.append(p)
            if len(matches)==1:return matches[0],str(path),'COMPLETE_JSON_CODE_BLOCK_UNCHANGED'
            if len(matches)>1:raise ValueError('AMBIGUOUS_COMPLETE_PAYLOADS')
    if tid=='ALIGN-1859043':
        path=BASE/'recovery-02/web/ALIGN-1859043.json'
        return imp.read(path),str(path),'PRIOR_RECOVERY_UNCHANGED_JSON'
    return original_payload(tid)

if __name__=='__main__':
    print(json.dumps({'downloads':collect_downloads()},ensure_ascii=False))
    if len(sys.argv)>1:
        version=sys.argv[1]
        if not version.replace('-','').isalnum():raise ValueError('VERSION_NAME')
        if (OUT/'imports'/version).exists():raise ValueError('OUTPUT_VERSION_ALREADY_EXISTS')
        imp.payload=recovered
        imp.import_all('../../continuation-02/imports/'+version)
