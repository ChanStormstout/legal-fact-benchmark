#!/usr/bin/env python3
"""Explicit, resumable phases. No browser/network calls or silent model retries."""
import argparse,hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.irac_application.aligned_tasks import ROOT,prepare,prepare_case_tasks,put,HEADER
from legal_bench.irac_application.aligned_graph import build,validate_template,check_refs

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def extract(path):
    text=path.read_text();blocks=re.findall(r'```(?:json)?\s*\n(.*?)```',text,re.S)
    candidates=blocks+[text.strip()];valid=[]
    for b in candidates:
        try:
            d=json.loads(b)
            if isinstance(d,dict):valid.append(d)
        except json.JSONDecodeError:pass
    if len(valid)!=1:raise ValueError('EXPECTED_ONE_COMPLETE_JSON_OBJECT:'+str(len(valid)))
    return valid[0]
def import_template(family,path):
    d=extract(path);law=read(ROOT/'sources'/f'{family}-law.json');errors=validate_template(d,{s['source_id']:s for s in law})
    put(ROOT/'engineering'/f'{family}-template-address-check.json',{'errors':errors,'semantic_correctness':False,'raw_sha256':sha(path)})
    if errors:raise ValueError(errors)
    put(ROOT/'templates'/f'{family}-proposed.json',d)
    prompt=HEADER+'''Independently review this proposed legal structure against ONLY the supplied law. Do not add external law. Check elements vs tests, logic AND/OR/NOT/EXCEPT polarity, scope/version, burden assertions, quote accuracy, overlooked opposing qualifications and unsupported defenses. Return {family,decision,issues,template}. decision ACCEPT, CORRECTED or UNRESOLVED; template must contain the complete proposed or source-groundedly corrected structure with all IDs, no ellipses. Explain corrections in issues; unsupported law remains NOT_COVERED. This is the one budgeted independent review, not an invitation to invent missing law.\n'''+json.dumps(dict(law=law,proposed_template=d),ensure_ascii=False,indent=2)
    put(ROOT/'tasks'/f'template-review-{family}.txt',prompt)
def import_review(family,path):
    d=extract(path);law=read(ROOT/'sources'/f'{family}-law.json');errors=validate_template(d['template'],{s['source_id']:s for s in law})
    put(ROOT/'templates'/f'{family}-review.json',d)
    if errors or d['decision']=='UNRESOLVED':raise ValueError('TEMPLATE_REVIEW_NOT_ADMITTED:'+repr(errors))
    put(ROOT/'templates'/f'{family}.json',d['template']);prepare_case_tasks()
def import_case(kind,cid,path):
    d=extract(path)
    if str(d['case_id'])!=cid:raise ValueError('WRONG_CASE')
    mat=read(ROOT/'sources'/f'{cid}.json');family=mat['family'];law=read(ROOT/'sources'/f'{family}-law.json');template=read(ROOT/'templates'/f'{family}.json');sources=dict(mat['sources']);sources.update({s['source_id']:s for s in law})
    if kind=='proposal':
        put(ROOT/'inputs'/f'{cid}-proposal.json',d)
        g=build(mat,read(ROOT/'inputs'/f'{cid}-legacy-facts.json'),template,d,law);put(ROOT/'graphs'/f'{cid}.json',g)
    else:
        tests={t['id'] for t in template['tests']};rows=[]
        for r in d['tests']:
            errors=check_refs(r.get('support_refs',[])+r.get('opposition_refs',[]),sources)
            if r['test_id'] not in tests:errors.append('UNKNOWN_TEST')
            if r['status'] not in ('SUPPORTED','REFUTED','UNRESOLVED','UNSUPPORTED'):errors.append('INVALID_STATUS')
            if r['status'] in ('SUPPORTED','REFUTED') and not r.get('support_refs') and not r.get('opposition_refs'):errors.append('DEFINITE_WITHOUT_EVIDENCE')
            rows.append(dict(r,automatic_check_errors=errors,supervision_mask=False,admission='PENDING_CONCENTRATED_SOURCE_REVIEW'))
        put(ROOT/'references'/f'{cid}.json',dict(d,tests=rows,reference_kind='MODEL_GENERATED_SOURCE_REVIEW_PENDING'))

def freeze():
    if (ROOT/'freeze/manifest.json').exists():raise ValueError('ALREADY_FROZEN')
    refs=list((ROOT/'references-admitted-v2').glob('*.json'))
    if not refs:raise ValueError('NO_NEW_MATERIAL_REFERENCES')
    if any(any(t.get('admission')=='PENDING_CONCENTRATED_SOURCE_REVIEW' for t in read(p)['tests']) for p in refs):raise ValueError('REFERENCE_REVIEW_PENDING')
    files=[]
    for sub in ('templates','inputs','references','references-admitted-v2','reference-review','reference-review-v2','references-admitted','graphs','sources','packages','tasks','context'):
        files+=list((ROOT/sub).glob('*.json'))+list((ROOT/sub).glob('*.txt'))
    files+=list(Path('legal_bench/irac_application').glob('*.py'))+[Path(__file__),Path('scripts/irac_aligned_train.py'),Path('tests/test_irac_aligned.py'),ROOT/'protocol.json',ROOT/'freeze/splits.json']
    if not (ROOT/'freeze/splits.json').exists():raise ValueError('GROUP_SPLIT_NOT_SAVED')
    files += list(Path('scripts').glob('irac_aligned*.py'))
    files += [ROOT/'text-cache/encoder.json', ROOT/'text-cache/encoding.json', ROOT/'text-cache/vectors.npz', ROOT/'baseline-selection.json',ROOT/'freeze/evaluation.json',ROOT/'freeze/runtime.json',ROOT/'freeze/split-coverage.json']
    put(ROOT/'freeze/manifest.json',{str(p):sha(p) for p in sorted(set(files))})
    for p in files:
        if p.suffix=='.py':
            target=ROOT/'freeze/code'/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())

def main():
    ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['prepare','import-template','import-review','import-proposal','import-reference','freeze']);ap.add_argument('--id');ap.add_argument('--raw',type=Path);a=ap.parse_args()
    if a.phase=='prepare':prepare();prepare_case_tasks()
    elif a.phase=='import-template':import_template(a.id,a.raw)
    elif a.phase=='import-review':import_review(a.id,a.raw)
    elif a.phase.startswith('import-'):import_case(a.phase[7:],a.id,a.raw)
    else:freeze()
if __name__=='__main__':main()
