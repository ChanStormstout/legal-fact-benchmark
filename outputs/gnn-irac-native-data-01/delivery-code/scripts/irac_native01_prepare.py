"""Bounded IRAC-native discovery. Never treats database slices as model input."""
import datetime
import hashlib
import json
import re
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path('outputs/gnn-irac-native-data-01')
PARENT = 'eeda90c1dbf5ac3345f10f08b1152b12b04a612a'
DB = Path('outputs/benchmark-pilot/data/cases.sqlite')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def save(name, value):
    p = ROOT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        raise FileExistsError(p)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def main():
    assert str(ROOT) in json.loads(Path('docs/repository-artifacts.json').read_text())['artifact_roots']
    assert not ROOT.exists()
    split = json.loads(Path('outputs/rgcn-sbc-finalization-11/protocol.json').read_text())
    mandatory = set(split['dev'] + split['sealed_ids']) | {'308216','38604742','1106992','1497837','1859043','111425525','758831','1381386'}
    # Prefer completely new targets; prior main-comparison TRAIN is additionally
    # excluded for this discovery, without opening any sealed document.
    excluded = mandatory | set(split['train']) | {'661475','69305','1134266','157278563','34625760'}
    save('registration.json', {'parent':PARENT, 'branch':subprocess.check_output(['git','branch','--show-current'],text=True).strip(), 'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(), 'starting_status':subprocess.check_output(['git','status','--short'],text=True), 'time':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'training':False,'sealed_body_read':False,'publication':'LOCAL_ONLY_NO_COMMIT_NO_PUSH'})
    historical=[]
    raw=subprocess.check_output(['git','ls-tree','-r',PARENT,'outputs/rgcn-sbc-finalization-11','outputs/gnn-irac-feasibility-01','outputs/gnn-irac-feasibility-02'],text=True)
    for line in raw.splitlines():
        meta,path=line.split('\t'); b=Path(path).read_bytes(); actual=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
        historical.append({'path':path,'parent_blob':meta.split()[2],'sha256':hashlib.sha256(b).hexdigest(),'unchanged':actual==meta.split()[2]})
    assert all(x['unchanged'] for x in historical)
    save('parent-integrity.json',{'parent':PARENT,'all_unchanged':True,'files':historical})
    rule={'act':r'delhi.{0,20}rent','behaviour':r'sub.?lett|sub.?ten|part(?:ed|ing).{0,12}possession','section':r'14.{0,18}1.{0,12}b','discovery_fields':['facts','issues','analysis_of_the_law','courts_reasoning','conclusion'],'order':'Explicit provision in issue/facts, then substantive behaviour discussion in reasoning, then provision anywhere; ties database line_number. No verdict/performance/mechanism balancing. Metadata hits are not eligibility. One cohort, no replacement.', 'max_candidates':16,'mandatory_excluded_ids':sorted(mandatory),'additional_prior_exposed_excluded_ids':sorted(excluded-mandatory),'candidate_discovery_only':True}
    save('discovery-rule.json',rule)
    conn=sqlite3.connect('file:'+str(DB)+'?mode=ro',uri=True); rows=[]
    for cid,line,title,url,record_hash,raw in conn.execute('select doc_id,line_number,title,url,record_sha256,raw_json from cases order by line_number'):
        if cid in excluded:continue
        record=json.loads(raw); fields={k:record.get(k,'') for k in rule['discovery_fields']}; txt=' '.join(str(v) for v in fields.values())
        if not re.search(rule['act'],txt,re.I) or not re.search(rule['behaviour'],txt,re.I):continue
        fi=str(fields['facts'])+' '+str(fields['issues']); reasoning=str(fields['courts_reasoning'])+' '+str(fields['analysis_of_the_law'])
        score=(bool(re.search(rule['section'],fi,re.I)),min(8,len(re.findall(rule['behaviour'],reasoning,re.I))),bool(re.search(rule['section'],txt,re.I)))
        rows.append({'case_id':cid,'database_line':line,'title':title,'url':url,'record_sha256':record_hash,'discovery_score':list(score),'candidate_discovery_only':True,'prior_role':'NOT_IN_CURRENT_SBC_TRAIN_DEV_SEALED_OR_OLD_IRAC; other historic source use not ruled out','known_association':'UNCONFIRMED','discovery_fields':fields})
    rows.sort(key=lambda x:(-int(x['discovery_score'][0]),-x['discovery_score'][1],-int(x['discovery_score'][2]),x['database_line']))
    # Known duplicate judgment from the database title/date, not outcome based.
    seen=set();unique=[]
    for row in rows:
        key=re.sub(r'[^a-z0-9]','',row['title'].lower().replace('s. kartar','kartar').replace('chamanlal','chaman lal'))
        if key in seen:continue
        seen.add(key);unique.append(row)
    chosen=unique[:16]
    save('database-source-manifest.json',{'authoritative_dataset_path':str(DB.resolve()),'sha256':sha(DB),'records':conn.execute('select count(*) from cases').fetchone()[0],'query':'read-only cases ordered by line_number; regex/priority as discovery-rule.json','eligible_locator_hits':len(rows),'deduplicated_locator_hits':len(unique),'selection_rule_hash':sha(ROOT/'discovery-rule.json'),'source_entry_evidence':'scripts/rgcn09_data.py:index; scripts/study02_candidates.py','not_complete_judgments':True})
    save('candidate-cohort-16.json',{'frozen':True,'replacement_allowed':False,'candidate_discovery_only':True,'actual_count':len(chosen),'cases':chosen})
    save('protocol.json',{'parent':PARENT,'scope':'Delhi Rent Control Act 14(1)(b), rule-given retrospective IRAC-native purposive development','candidate_ids':[x['case_id'] for x in chosen],'candidate_max':16,'construction_max':8,'construction_min':6,'calls_max':16,'semantic_retry':0,'technical_retry_max':2,'construction_batching':'If gate passes: independent rule-only, stage-only, blind-only, target-only batches; preserve freeze order, no all-in-one target-aware construction','training':False,'sealed_read':False,'publication':'LOCAL_ONLY','readiness':{'GO':'6+ READY, no systemic blocker','CONDITIONAL_GO':'4-5 READY, one uniform nonsemantic engineering gap','NO_GO':'<4 READY or systemic blocker'},'reference_role':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD'})
    print([(x['case_id'],x['discovery_score'],x['title']) for x in chosen])

if __name__=='__main__':main()
