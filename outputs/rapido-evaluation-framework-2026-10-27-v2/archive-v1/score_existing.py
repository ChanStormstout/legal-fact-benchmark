"""Recompute development scores from explicit source labels; no semantic model calls."""
import csv
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
D = BASE / 'case1251841'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def hmean(p,r):return 100*2*p*r/(p+r) if p+r else 0.0

def compute(name):
    manifest=json.loads((D/'manifest.json').read_text())
    report=D/(name+'.txt');assert sha(report)==manifest[name]['sha256']
    labels_path=D/(name+'-labels.json');labels=json.loads(labels_path.read_text())
    refs=json.loads((D/'allowed-sources.json').read_text())['sources']
    text=report.read_text();keys=labels['keypoint_labels'];claims=labels['assertion_labels']
    for row in keys:
        assert row['credit'] in (0,1)
        assert all(q and q in text for q in row['report_quotes'])
        assert all(ref in refs for ref in row['source_refs'])
        if row['credit']:assert row['report_quotes']
    for row in claims:
        assert row['quote'] in text
        assert all(ref in refs for ref in row['source_refs'])
    correct={row['id'] for row in keys if row['credit']}
    supported=[row for row in claims if row['label']=='SUPPORTED']
    bad=[row for row in claims if row['label'] in ('UNSUPPORTED','CONTRADICTED')]
    unresolved=[row for row in claims if row['label']=='ANNOTATION_UNRESOLVED']
    r=len(correct)/len(keys)
    low=len(supported)/len(claims) if claims else 0
    high=(len(supported)+len(unresolved))/len(claims) if claims else 0
    critical_keys={'K01','K02','K11','K12','K15','K16','K19','K20'}
    denom=sum(2 if row['id'] in critical_keys else 1 for row in keys)
    weighted=sum(row['credit']*(2 if row['id'] in critical_keys else 1) for row in keys)/denom
    return {'report':name,'report_sha256':sha(report),'labels_sha256':sha(labels_path),
        'correct_keypoints':len(correct),'required_keypoints':len(keys),'R_percent':100*r,
        'correct_keypoint_ids':sorted(correct),'supported_assertions':len(supported),
        'assertions':len(claims),'contradicted_assertions':sum(x['label']=='CONTRADICTED' for x in claims),
        'unsupported_assertions':sum(x['label']=='UNSUPPORTED' for x in claims),
        'annotation_unresolved':len(unresolved),'P_percent_interval':[100*low,100*high],
        'F_percent_interval':[hmean(low,r),hmean(high,r)],
        'core_group_double_weight_sensitivity':{'R_percent':weighted*100,'F_interval':[hmean(low,weighted),hmean(high,weighted)]},
        'bad_assertion_episode_groups':sorted({row['error_episode'] for row in bad if row['error_episode']}),
        'episode_groups_are_not_independently_validated_severity_counts':True,
        'new_model_calls':0,'evaluation_status':'NONBLINDED_DEVELOPMENT_REFERENCE_NOT_HUMAN_GOLD'}

if __name__=='__main__':
    result={n:compute(n) for n in ['A0','C38_candidate','C38_delivered']}
    c=result['C38_candidate'];d=result['C38_delivered']
    a=set(c['correct_keypoint_ids']);b=set(d['correct_keypoint_ids'])
    old=json.loads((D/'C38_candidate-labels.json').read_text())['assertion_labels']
    new=json.loads((D/'C38_delivered-labels.json').read_text())['assertion_labels']
    kept={x['label_reused_from'] for x in new}
    result['delivery_transition']={
        'retained_correct_keypoints':sorted(a&b),'lost_correct_keypoints':sorted(a-b),
        'new_correct_keypoints':sorted(b-a),'correct_keypoint_retention_percent':100*len(a&b)/len(a) if a else None,
        'removed_supported_assertions':[x['id'] for x in old if x['label']=='SUPPORTED' and x['id'] not in kept],
        'removed_bad_assertions':[x['id'] for x in old if x['label']!='SUPPORTED' and x['id'] not in kept],
        'retained_bad_assertions':[x['label_reused_from'] for x in new if x['label']!='SUPPORTED'],
        'errors_correctly_rewritten':0,'rewrites_are_not_deletions':True,'repair_body_identical':True,
        'quality_claim':'Filtering improves support ratio but loses half of correctly covered required content under this rubric.'}
    result['scope']={'case':'1251841','exposed_development_case':True,'posthoc_rubric':True,
        'no_population_inference':True,'no_hidden_target_access':True,'no_baseline_changes':True,
        'P_R_harmonic_is_project_summary_not_original_FineSurE_or_FACTSCORE':True}
    (D/'scores.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    with (D/'keypoint-scorecard.csv').open('w') as handle:
        writer=csv.writer(handle);writer.writerow(['id','theme','criterion','A0','C38_candidate','C38_delivered'])
        labels={n:json.loads((D/(n+'-labels.json')).read_text()) for n in result if n.startswith(('A0','C38'))}
        for i,row in enumerate(labels['A0']['keypoint_labels']):
            writer.writerow([row['id'],row['group'],row['condition']]+[labels[n]['keypoint_labels'][i]['credit'] for n in labels])
    print(json.dumps({k:{q:v for q,v in row.items() if q in ('correct_keypoints','required_keypoints','R_percent','supported_assertions','assertions','P_percent_interval','F_percent_interval')} for k,row in result.items() if k in ('A0','C38_candidate','C38_delivered')},indent=2))
    print(json.dumps(result['delivery_transition'],ensure_ascii=False,indent=2))
