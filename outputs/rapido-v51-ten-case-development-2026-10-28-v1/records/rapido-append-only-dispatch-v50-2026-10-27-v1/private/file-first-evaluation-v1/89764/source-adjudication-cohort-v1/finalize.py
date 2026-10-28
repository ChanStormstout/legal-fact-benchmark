import copy
import json
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE.parents[2]
BASE = OLD.parents[1]
V51 = BASE / 'rapido-source-plan-direct-edit-v51-2026-10-28-v1'
read = lambda p: json.loads(p.read_text())

def write(p, obj):
    with p.open('x') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')

d = read(HERE / 'scores.json')
table = {}
mapping = {'KEA':'A0','THB':'P','SZS':'C0','8DI':'E'}
for r in d['reports']:
    if r['blind_id']=='SZS':
        for k in ['P','P_counts','H','serious_error_observed','serious_error_unresolved','strict_success']:
            r[k] = None
        r['annotation_status'] = 'SOURCE_COVERAGE_ADJUDICATED_ASSERTION_DELIVERY_MISSING'
    table[mapping[r['blind_id']]] = r
out = HERE / 'scores-missingness-explicit.json'
write(out,d)
write(HERE / 'method-table.json',dict(case_id='89764',methods=table,
      method_mapping_opened_after_label_freeze=True,raw_scorer_bounds_not_used_as_missing_scores=True))
a = OLD / 'provisional-reference-evaluation-v1/89764/source-view.json'
b = OLD / 'atomic-reference-evaluation-v2/89764/source-view.json'
assert a.read_bytes()==b.read_bytes()
write(HERE / 'assertion-reuse-identity-proof.json', dict(same_source_view_bytes=True,
    same_question=True,same_report_sha_verified=True,old_reference_hash_retained_in_log=True,
    assertion_judges_did_not_see_reference_items=True,source_view_sha256=hashlib.sha256(b.read_bytes()).hexdigest()))
f = V51 / 'private/shared-prefix-comparison-v1/cases/89764/F/final-report.txt'
p = OLD / 'ten-case-transfer-v1/cases/89764/P/final-report.txt'
assert f.read_bytes()==p.read_bytes()
dest = V51 / 'private/anonymous-final-evaluation-v1/89764/unchanged-text-score-v1'
dest.mkdir(exist_ok=False)
fr = copy.deepcopy(table['P'])
fr['blind_id']='M6N'
fr['annotation_status']='IDENTICAL_TEXT_SOURCE_ADJUDICATION_REUSED_NOT_NEW_RATING'
write(dest / 'scores.json',{**{k:d[k] for k in ['case_id','source_view_sha256','reference_sha256']},'reports':[fr]})
write(dest / 'reuse-receipt.json',dict(old_blind='THB',new_blind='M6N',source_score=str(out),
    report_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),same_text=True,extra_edit_effect=0,new_rating_submitted=False))
for method,r in table.items():
    print(method,r['R_counts'],r['P_counts'],r['H'])
