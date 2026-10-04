"""One local candidate location pass, without inference of legal eligibility."""
import json,re,sqlite3
from pathlib import Path
ROOT=Path('outputs/legal-rule-support-study-02')

def read(p):return json.loads(Path(p).read_text())
def save(name,d):
 p=ROOT/name
 if p.exists():raise FileExistsError(p)
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
act=re.compile(r'Delhi\s+Rent\s+Control|\bDRC\s+Act',re.I)
section=re.compile(r'14\s*\(?\s*1\s*\)?\s*\(?\s*b\s*\)?',re.I)
issue=re.compile(r'sub[\s-]*let|assign(?:ed|ment)?|part(?:ed|ing)?\s+with\s+possession|consent',re.I)
save('candidate-location-rule.json',dict(act=act.pattern,section=section.pattern,issue=issue.pattern,
 mode='AND all three, anywhere in existing record; candidate signal only, including possible cited precedent. No outcome selection.',
 metadata='outputs/benchmark-pilot/data/cases.sqlite raw_json',local_source_roots=['outputs/benchmark-pilot-v04/sampling-v1/sources','outputs/rules-verdict-v19-historical-pairs/sources'],
 ordering='Existing qualification-only relevant candidates first, saved primary_read_order; then saved broad rank or numeric ID.'))
old=read('outputs/legal-rule-support-study-01/candidate-order-final.json');exposed=set(old['known_exposed_ids'])|{'1064407','184866874','1988625','755721','934120','157278563','34625760'}
v21=read('outputs/rules-verdict-v21-rule-retrieval/candidate-decisions.json')
related={r['case_id']:r['related_to'] for r in v21['known_related_prefilters']}
queue=read('outputs/benchmark-pilot-v04/sampling-v1/candidate-queue.json')['cases']; ranks={r['case_id']:r['rank'] for r in queue}
rows=[]
# Existing screening evidence makes these recheck leads, not accepted cases.
for r in v21['primary_read_order']:
 if r['case_id'] in {'110204406','172908545','58386394'}:
  rows.append(dict(case_id=r['case_id'],tier=1,saved_order=r['order'],basis=r,prior_use='QUALIFICATION_SCREENING_ONLY'))
hits=[]
c=sqlite3.connect('file:outputs/benchmark-pilot/data/cases.sqlite?mode=ro',uri=True)
for cid,title,url,raw in c.execute('select doc_id,title,url,raw_json from cases'):
 if act.search(raw) and section.search(raw) and issue.search(raw):
  hit=dict(case_id=cid,title=title,url=url,saved_rank=ranks.get(cid),basis='LOCAL_ACT_SECTION_ISSUE_METADATA_HIT',
    exposed=cid in exposed,known_related_to=related.get(cid),full_local_source=str(Path('outputs/benchmark-pilot-v04/sampling-v1/sources')/cid/'segments.json'))
  hit['full_local_available']=Path(hit['full_local_source']).exists();hits.append(hit)
for r in sorted(hits,key=lambda r:(r['saved_rank'] is None,r['saved_rank'] or int(r['case_id']))):
 if r['exposed'] or r['known_related_to'] or r['case_id'] in {x['case_id'] for x in rows}:continue
 rows.append(dict(r,tier=2))
save('local-candidate-hits.json',dict(hits=hits,records_scanned=c.execute('select count(*) from cases').fetchone()[0],eligibility_not_established=True))
save('candidate-order.json',dict(rows=rows,known_exposed_ids=sorted(exposed),known_related=related,selection_not_based_on_answers=True))
print(json.dumps(rows,ensure_ascii=False,indent=2))
