"""Join the recovered first coverage reply with the existing source-adjudicated assertion axis."""
import copy
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
RAW = HERE.parent
OLD = RAW.parent.parent
SRC = OLD / 'atomic-reference-evaluation-v2/701211'
read = lambda p:json.loads(p.read_text())
covpath = RAW/'6HO-coverage-delayed-original.json'
apath = SRC/'three-report-blind-score-v2/6HO-assertions-source-adjudicated.json'
cov=read(covpath)
a=read(apath)
packet=read(SRC/'packet.json')
view=read(SRC/'source-view.json')
report=next(r for r in packet['reports'] if r['blind_id']=='6HO')
for obj in [cov,a]:
    assert all(obj[k]==packet[k] for k in ['case_id','source_view_sha256','reference_sha256'])
    assert obj['report_sha256']==report['report_sha256']==hashlib.sha256(report['text'].encode()).hexdigest()
assert len(cov['coverage'])==74
assert len(a['assertions'])==77
merged=copy.deepcopy(a)
merged['coverage']=copy.deepcopy(cov['coverage'])
merged['main_answer']='PARTIAL'
merged['annotation_status']='RECOVERED_ORIGINAL_COVERAGE_SOURCE_ADJUDICATED_JOINED_EXISTING_ASSERTIONS'
literal=[]
for axis in ['coverage','assertions','serious_errors']:
    for x in merged[axis]:
        qs=[x['report_quote']] if axis=='assertions' else x.get('report_quotes',[])
        for q in qs:
            if q not in report['text']:
                literal.append(dict(axis=axis,id=x.get('item_id',x.get('id')),type='REPORT_WITNESS_REVIEW',quote=q))
        for field in ['evidence','source_evidence']:
            for ev in x.get(field,[]):
                if ev['source_id']=='SCOPE':ev['source_id']='scope'
                original=view['scope'] if ev['source_id']=='scope' else view['sources'][ev['source_id']]['text']
                if ev['quote'] not in original:
                    at=original.casefold().find(ev['quote'].casefold())
                    if at>=0:
                        before=ev['quote'];ev['quote']=original[at:at+len(before)]
                        literal.append(dict(type='CASE_ONLY_SOURCE_WITNESS',before=before,after=ev['quote']))
                    else:literal.append(dict(axis=axis,id=x.get('item_id',x.get('id')),type='SOURCE_WITNESS_REVIEW',evidence=ev))

def write(name, obj):
    with (HERE/name).open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2)

write('labels-source-adjudicated.json',{k:packet[k] for k in ['case_id','source_view_sha256','reference_sha256']}|{'reports':[merged]})
write('source-adjudication-log.json',dict(at=datetime.now(timezone.utc).isoformat(),
    reading='All43allowedCASE passages,74frozenreferencecriteria and uncertainties, actual6HOreport, recovered74coveragejudgments and previously source-adjudicated77assertions; relevant ICA7/20/73, GOI30, EA50 and TPA112 originals checked. No target outcome or outside facts.',
    coverage_decisions='All74original coverage labels retained after source comparison; every missing relationship remains missing, including Dalmia roles/objections, distinct waiver clauses, injunction/nonparty status, draft nonproduction, conditional damages framework.',
    assertion_axis_changed=False, assertion_axis_source=str(apath), assertion_axis_sha256=hashlib.sha256(apath.read_bytes()).hexdigest(),
    coverage_axis_source=str(covpath),coverage_axis_sha256=hashlib.sha256(covpath.read_bytes()).hexdigest(),
    model_reference_not_human_gold=True,parent_not_perfectly_blind=True,
    existing_coverage_not_regraded=True,new_model_calls=0,intervals_not_confidence_intervals=True))
write('literal-witness-review.json',literal)
print(json.dumps(literal,ensure_ascii=False,indent=2))
