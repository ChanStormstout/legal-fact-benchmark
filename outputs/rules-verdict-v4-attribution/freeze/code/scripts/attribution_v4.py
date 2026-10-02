"""Six preselected old-case spans: attribution diagnostic, not factual re-extraction."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.contracts import obj, array, enum, string, validate
from legal_bench.rules_verdict_v1.source_views import digest, write_new
from legal_bench.rules_verdict_v1.runtime import SETTINGS
ROOT = Path('outputs/rules-verdict-v4-attribution')
OLD = Path('outputs/rules-verdict-v3')
CASES = ['661475', '69305', '1134266']
TARGETS = [
 ('661475','T1','p0001.s004','Hence he has come to the conclusion that the first appellant has parted with possession of their portion to them.','COURT_FOUND','LOWER_COURT','V3 Q3'),
 ('661475','T2','p0002.s002@0:412','permitted them to occupy a half portion of the shop for that purpose.','PARTY_CLAIMED','NOT_SHOWN','V3 Q2'),
 ('69305','T3','p0003.s003','An unregis- tered deed of lease was executed on that occasion','NARRATED','NOT_SHOWN','V3 Q1'),
 ('69305','T4','p0004.s004','it merely amounts to a written permission to the appellant to create a sub-lease','PARTY_CLAIMED','NOT_SHOWN','V3 Q2'),
 ('1134266','T5','p0002.s001','without obtaining any written consent from the landlord','PARTY_CLAIMED','NOT_SHOWN','V3 Q2'),
 ('1134266','T6','p0003.s003','consequently there was no sub-letting or parting with possession','PARTY_CLAIMED','NOT_SHOWN','V2 RC02 rejected_party_submission; scope rechecked against V3 allowed source'),
]
def read(p): return json.loads(Path(p).read_text())
def schema(source, targets):
    ev = obj({'segment_id':enum([s['id'] for s in source['segments']]),'quote':string(700)})
    item = obj({'status':enum(['NARRATED','PARTY_CLAIMED','COURT_FOUND','UNKNOWN']),
                'speaker':string(120),'adoption':enum(['LOWER_COURT','CURRENT_COURT','BOTH','NOT_SHOWN','UNCLEAR']),
                'attribution_evidence':array(ev,2),'adoption_evidence':array(ev,2),'reason':string(300)})
    return obj({t['id']:item for t in targets})
def prompt(source, targets):
    instructions = '''Classify ONLY the supplied target propositions, using all supplied source segments. Do not decide their truth or the lawsuit outcome. Return JSON conforming to the schema.
status describes how the target proposition is presented: PARTY_CLAIMED for a litigant's allegation, submission or counsel argument; COURT_FOUND for an explicitly attributed court finding of that exact proposition; NARRATED for unembedded background narration; UNKNOWN if unclear. Reporting an allegation inside a judgment does not make it narration or a finding. A party may quote a precedent: distinguish that precedent from a finding about this dispute.
Identify the original speaker. Separately record whether the supplied scope explicitly shows a court adopting THIS precise proposition: LOWER_COURT, CURRENT_COURT, BOTH, NOT_SHOWN, or UNCLEAR. An eviction outcome alone does not prove adoption. NOT_SHOWN is not rejection. A narrated fact need not have an explicit adoption.
Give exact source quotes including attribution cues (e.g. the clause introducing counsel's argument). Quotes must be substrings of a single segment. adoption_evidence must be empty if adoption is NOT_SHOWN. Do not invent a court or infer adoption from overall outcome. If adoption is explicit elsewhere, quote it separately. Short reasons; no legal advice or extra prose.
Complete synthetic format example (not a source fact): for target 'the roof leaked', source segment s1 'Counsel for the tenant argued that the roof leaked.', output {"EX":{"status":"PARTY_CLAIMED","speaker":"Counsel for the tenant","adoption":"NOT_SHOWN","attribution_evidence":[{"segment_id":"s1","quote":"Counsel for the tenant argued that the roof leaked."}],"adoption_evidence":[],"reason":"This is counsel's argument; no court adoption is supplied."}}. Use only actual target IDs and source segments below.
'''
    return instructions+'\nTARGETS\n'+json.dumps(targets,ensure_ascii=False)+'\nSOURCE (unchanged prior allowed scope, not a full judgment)\n'+json.dumps(source,ensure_ascii=False)
def quote_check(evidence, source):
    segments={s['id']:s['text'] for s in source['segments']}
    return bool(evidence) and all(e['quote'] and e['quote'] in segments.get(e['segment_id'],'') for e in evidence)
def prepare():
    refs=[]
    for cid in CASES:
        source=read(OLD/'sources'/(cid+'-allowed.json'))
        targets=[]
        for c,tid,sid,quote,status,adoption,provenance in TARGETS:
            if c!=cid: continue
            assert quote_check([{'segment_id':sid,'quote':quote}],source)
            targets.append({'id':tid,'segment_id':sid,'quote':quote})
            refs.append({'case_id':cid,'id':tid,'status':status,'adoption':adoption,'basis':provenance})
        write_new(ROOT/'sources'/(cid+'.json'),source)
        write_new(ROOT/'prepared'/cid/'targets.json',targets)
        write_new(ROOT/'prepared'/cid/'schema.json',schema(source,targets))
        p=ROOT/'prepared'/cid/'prompt.txt'; value=prompt(source,targets)
        if p.exists() and p.read_text()!=value: raise ValueError('Changed prompt')
        p.write_text(value)
    write_new(ROOT/'references.json',{'provenance':'DEVELOPER_TRANSCRIPTION_OF_EXISTING_MODEL_SOURCE_REVIEW_NOT_HUMAN_GOLD','rows':refs})
    files=[Path(__file__),Path('legal_bench/rules_verdict_v1/runtime.py'),Path('legal_bench/rules_verdict_v1/contracts.py'),Path('legal_bench/mlx_json_constraint.py'),Path('legal_bench/model_output.py')]
    for p in files:
        target=ROOT/'freeze/code'/p.relative_to(Path.cwd()) if p.is_absolute() else ROOT/'freeze/code'/p
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and target.read_bytes()!=p.read_bytes(): raise ValueError('Changed frozen code')
        target.write_bytes(p.read_bytes())
    paths=list((ROOT/'prepared').rglob('*'))+list((ROOT/'sources').rglob('*'))+list((ROOT/'freeze/code').rglob('*'))+[ROOT/'references.json',OLD/'references/condition-reference-v3.json',Path('outputs/rules-verdict-v2/references/rule-materials-reference-v2.json')]
    write_new(ROOT/'freeze/config.json',{'settings':SETTINGS,'max_output_tokens':1600,'max_calls':3,'new_cases':0,
       'scope':'TARGETED_EXPOSED_CASE_ATTRIBUTION_DIAGNOSTIC; no full re-extraction, no condition replay',
       'scoring':'Report status and adoption agreement separately from exact quote location and source support. Selected targets do not estimate overall accuracy.',
       'files':{str(p):digest(p.read_bytes()) for p in paths if p.is_file()}})
def run(cid):
    from legal_bench.rules_verdict_v1.runtime import Runner
    frozen=read(ROOT/'freeze/config.json')
    for p,h in frozen['files'].items():
        if digest(Path(p).read_bytes())!=h: raise ValueError('Frozen input changed: '+p)
    runner=Runner(Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),frozen['settings'])
    runner.run((ROOT/'prepared'/cid/'prompt.txt').read_text(),read(ROOT/'prepared'/cid/'schema.json'),ROOT/'runs'/cid,frozen['max_output_tokens'])
def collect():
    rows=[];runs=[]
    for cid in CASES:
        meta=read(ROOT/'runs'/cid/'run.json');runs.append(meta)
        data=read(ROOT/'runs'/cid/'parsed.json') if meta['run_status']=='OK' else {}
        source=read(ROOT/'sources'/(cid+'.json'))
        for ref in read(ROOT/'references.json')['rows']:
            if ref['case_id']!=cid: continue
            result=data.get(ref['id']);rows.append({'reference':ref,'run_status':meta['run_status'],'result':result,
             'status_agreement':None if result is None else result['status']==ref['status'],
             'adoption_agreement':None if result is None else result['adoption']==ref['adoption'],
             'attribution_quotes_located':None if result is None else quote_check(result['attribution_evidence'],source),
             'adoption_quotes_located':None if result is None else (not result['adoption_evidence'] if result['adoption']=='NOT_SHOWN' else quote_check(result['adoption_evidence'],source))})
    write_new(ROOT/'results.json',{'rows':rows,'local_calls':3,'web_calls':0,'generation_seconds':sum(r.get('elapsed_seconds',0) for r in runs),'peak_memory_gb':max(r.get('peak_mlx_memory_gb',0) for r in runs)})
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run','collect']);p.add_argument('--case',choices=CASES);a=p.parse_args()
    if a.action=='prepare': prepare()
    elif a.action=='run': run(a.case)
    else: collect()
