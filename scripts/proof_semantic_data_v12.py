"""Bounded metadata inventory; source bodies of historical SEALED IDs are never opened."""
import json,re,hashlib,sqlite3
from pathlib import Path
ROOT=Path('outputs/proof-semantic-search-v12')
def save(n,x):
 p=ROOT/n;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise FileExistsError(p)
 p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def main():
 old={'789051','1418721','1841885','840688','161859415','74028','522414','1144022'}
 manifest=json.loads(Path('outputs/rgcn-data-expansion-09/continuation-03/split-manifest.json').read_text())
 deny={r['case_id'] for r in manifest['cases'] if 'SEALED' in r.get('split','')}
 save('sealed-denylist.json',{'ids':sorted(deny),'source':'existing split metadata only; no payload read'})
 roots=['outputs/rgcn-data-expansion-09/continuation-01/freeze/full','outputs/gnn-irac-native-data-01/sources/documents','outputs/proof-carrying-calibration-v5/sources','outputs/legal-rule-support-study-02/sources','outputs/rgcn-data-expansion-09/target-source-screen/documents-v2','outputs/rgcn-data-expansion-09/target-source-screen/documents']
 files={};inventory=[]
 for folder in roots:
  for p in sorted(Path(folder).glob('*.json'),key=lambda p:(int(p.stem) if p.stem.isdigit() else 10**20,p.name)):
   cid=p.stem
   if not cid.isdigit() or cid in deny or cid in old or cid in files:continue
   # Known full-source filenames only; do not inspect arbitrary historical output payloads.
   d=json.loads(p.read_text())
   if str(d.get('document_id'))!=cid or not d.get('segments'):continue
   files[cid]=str(p)
   inventory.append({'case_id':cid,'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'title':d.get('titles',[]),'source_status':d.get('status'),'segments':len(d['segments']),'conflicts':len(d.get('conflicts',[])),'missing_lines':len(d.get('missing_lines',[])),'exposure':'PRIOR_SOURCE_PREPARATION; detailed method-use audit required','allocation':'TRAIN_ONLY_UNLESS_PROVEN_SCREEN_ONLY','qualification':'NOT_YET_DETAILED'})
 save('local-source-inventory.json',inventory)
 # Database records are derived metadata. Only facts/issues locate candidates; not used as judgment bodies.
 db=sqlite3.connect('file:outputs/benchmark-pilot/data/cases.sqlite?mode=ro',uri=True)
 schema=db.execute('pragma table_info(cases)').fetchall();save('database-schema.json',schema)
 print('LOCAL_COMPLETE_PATHS',len(inventory),'DENIED',len(deny),'SCHEMA',schema)
 save('candidate-order-local.json',{'frozen_before_detailed_review':True,'rows':inventory,'max_detailed':150,'database_metadata_followup':'PENDING_SCHEMA_ADAPTER','old_eight_excluded':sorted(old)})
if __name__=='__main__':main()
