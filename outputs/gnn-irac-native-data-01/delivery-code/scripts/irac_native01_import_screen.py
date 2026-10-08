"""Import screening without semantic repair; finite discovery gate."""
import json
from pathlib import Path
from scripts.irac_native01_prepare import ROOT,save,sha
from scripts.irac_native01_screen import CRITERIA
from legal_bench.rules_verdict_v1.irac_native_schema_v1 import quote_errors

def main():
    candidates=json.loads((ROOT/'candidate-cohort-16.json').read_text())['cases'];byid={c['case_id']:c for c in candidates};cases=[];audit=[]
    for n in range(1,5):
        p=ROOT/'web'/f'SCREEN-{n}.json';raw=json.loads(p.read_text());rows=raw['cases']
        expected={c['case_id'] for c in candidates[(n-1)*4:n*4]}
        assert {c['case_id'] for c in rows}==expected, (p,expected)
        for c in rows:
            assert c['status'] in {'SUITABLE','BORDERLINE','REJECT'}
            assert set(c['criteria'])==set(CRITERIA)
            assert type(c['acceptable_borderline']) is bool
            d=json.loads((ROOT/'sources/documents'/f"{c['case_id']}.json").read_text());lookup={s['id']:{'text':s['text']} for s in d['segments']}
            errors=[]
            for key,r in c['criteria'].items():
                assert r['assessment'] in {'SUPPORTED','QUALIFIED','BLOCKING_GAP'}
                qe=quote_errors(r.get('source_refs'),lookup)
                # Criterion source gaps may explicitly lack refs; do not
                # fabricate quotes, promote screening or request semantic retry.
                errors += [key+':'+e for e in qe]
            audit.append({'case_id':c['case_id'],'locator_errors':errors,'meaning_not_certified_by_locator':True})
            cases.append(c)
    ordered=sorted(cases,key=lambda c:next(i for i,x in enumerate(candidates) if x['case_id']==c['case_id']))
    accepted=[c for c in ordered if c['full_source_read'] is True and (c['status']=='SUITABLE' or c['status']=='BORDERLINE' and c['acceptable_borderline'])]
    accepted.sort(key=lambda c:(-c['application_clarity_score'],-c['independent_source_score'],-c['partition_clarity_score'],-c['element_coverage_score'],int(c['case_id'])))
    gate=len(accepted)>=6
    save('suitability-screening.json',{'reference_role':'MODEL_GENERATED_INDEPENDENT_SCREENING_NOT_HUMAN_GOLD','cases':ordered,'raw_reply_hashes':{str(p):sha(p) for p in (ROOT/'web').glob('SCREEN-*.json')},'eligible_before_full_construction':[c['case_id'] for c in accepted],'screening_not_READY':True})
    save('screening-source-check.json',{'cases':audit,'whitespace_location_only':True,'semantic_repairs':0})
    save('construction-cohort.json',{'status':'FROZEN_READY_TO_START' if gate else 'NOT_RUN_BELOW_SIX_ELIGIBLE','case_ids':[c['case_id'] for c in accepted[:8]] if gate else [],'eligible_count':len(accepted),'minimum':6,'replacement_allowed':False,'screening_candidates':[c['case_id'] for c in accepted],'reason':'Independent candidate screen gate; no failed candidate replaced.'})
    print('ELIGIBLE',len(accepted),[c['case_id'] for c in accepted],'START_CONSTRUCTION',gate)
    print([(c['case_id'],c['status'],c['reason']) for c in ordered])

if __name__=='__main__':main()
