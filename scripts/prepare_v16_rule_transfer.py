"""Freeze a bounded source-only extraction round and auditable sample shortage."""
import hashlib, json, pathlib, re, subprocess, sys
from datetime import datetime, timezone
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.rule_transfer_v16 import prompt, schema

ROOT = pathlib.Path('outputs/rules-verdict-v16-rule-transfer')
BASE = pathlib.Path('outputs/rules-verdict-v15-rule-supplement')
SAMPLING = pathlib.Path('outputs/benchmark-pilot-v04/sampling-v1')
NAMES = ['GENERAL_RADIO', 'HINDUSTAN_PETROLEUM', 'TELESOUND']
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(pathlib.Path(p).read_text(encoding='utf-8'))

def save(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2); f.write('\n')

def prepare():
    assert not ROOT.exists(), 'Do not overwrite a prior round'
    history = {str(p): sha(p) for p in pathlib.Path('outputs').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    code = {str(p): sha(p) for base in ['legal_bench','scripts','tests'] for p in pathlib.Path(base).rglob('*.py')}
    save(ROOT/'start-audit.json', {'time': datetime.now(timezone.utc).isoformat(),
         'head': subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
         'branch': subprocess.check_output(['git','branch','--show-current'], text=True).strip(),
         'historical_files': history, 'code_at_start': code})
    (ROOT/'starting-git-status.txt').write_text(subprocess.check_output(['git','status','--short'], text=True), encoding='utf-8')
    for name in NAMES:
        folder = BASE/'authorities'/name
        segments = []
        if (folder/'pages.json').exists():
            for page in read(folder/'pages.json'):
                segments.append({'id': 'LAW:V16:'+name+':P'+str(page['page']), 'text': page['text'], 'page': page['page']})
            coverage = 'Complete existing PDF text extraction, including headnotes and OCR; distinguish headnotes from judicial reasoning.'
        else:
            for number, text in read(folder/'selected-passages.json').items():
                segments.append({'id': 'LAW:V16:'+name+':PAR'+number, 'text': text, 'paragraph': number})
            coverage = 'Only saved selected complete sentences of paragraph 12 and complete paragraph 16; NOT full judgment.'
        source = {'case_id': name, 'metadata': read(folder/'metadata.json'), 'source_coverage': coverage, 'segments': segments}
        save(ROOT/'sources'/f'{name}.json', source)
        task = ROOT/'tasks'/name
        save(task/'schema.json', schema(source)); (task/'prompt.txt').write_text(prompt(source), encoding='utf-8')
    q = read(SAMPLING/'candidate-queue.json'); used = set(map(str,q['development_case_ids']))
    for name in ['outputs/development-20-single-pass-v1/sample.json', 'outputs/new-10-pattern-matching-v1/sample.json', 'outputs/local-qwen-pattern-eval-v1/evaluation-sample.json']:
        used.update(str(x['case_id'] if isinstance(x,dict) else x) for x in read(name)['cases'])
    for p in pathlib.Path('outputs/local-qwen-pattern-eval-v1').rglob('*reference*.json'):
        used.update(str(x['case_id']) for x in read(p).get('cases',[]) if isinstance(x,dict) and 'case_id' in x)
    refs = {}
    for p in sorted((SAMPLING/'web-tasks').glob('*/reply-v1/screening-reference.json')):
        for x in read(p).get('cases',[]): refs[str(x['case_id'])] = x
    eligible = []; hits = []
    for c in q['cases']:
        cid = str(c['case_id']); source_path = SAMPLING/'sources'/cid/'segments.json'; ref = refs.get(cid,{})
        if cid in used or not source_path.exists() or ref.get('eligibility') != 'ELIGIBLE' or ref.get('source_completeness') != 'VERIFIED_FULL': continue
        eligible.append({'case_id':cid, 'rank':c['rank'], 'title':c['title'], 'source_path':str(source_path), 'source_sha256':sha(source_path)})
        source = read(source_path)
        matched = [s for s in source['segments'] if re.search(r'amalgamat|merger|vesting|acquisition.*undertaking',s['text'],re.I)]
        if matched: hits.append({'case_id':cid, 'rank':c['rank'], 'matches':matched})
    save(ROOT/'sample-availability.json', {'existing_queue_hash':sha(SAMPLING/'candidate-queue.json'), 'prior_used_ids': sorted(used),
         'fixed_order_existing_complete_candidates':eligible, 'lexical_issue_hits':hits,
         'selected_cases':[], 'confirmed_compatible_corporate_transfer_cases':0,
         'availability_assessment':'Saved lexical hits concern land-reform vesting, administrative powers, or regional merger, not company amalgamation/tenancy transfer. No two compatible new targets are confirmed. This is not a recall claim over all unprepared records.',
         'no_new_downloads_or_web_screening':True, 'not_independence_certified':True})
    save(ROOT/'protocol.json', {'version':'V16', 'requested_max_web_calls':7, 'executed_plan_on_shortage':NAMES,
         'maximum_calls_until_stop':3, 'ordinary_High_not_Pro':True, 'local_model_calls':0, 'paid_API_calls':0, 'retries':0,
         'extraction_targets':'Corporate amalgamation/statutory acquisition and rent-law transfer consequences',
         'source_only_extractions':True, 'manual_V15_cards_not_supplied':True, 'target_answers_not_supplied':True,
         'application_pair_contract':'Same allowed case and retrieved original law excerpts, A excerpts only, B identical excerpts plus automatically extracted cards; no program verdict.',
         'sample_shortage_stop':'Three source-only extractions and concentrated source review; no irrelevant case substitution, old case rerun or broader screening.',
         'source_status_extension':'Retain V2 RuleCard fields; add PRIMA_FACIE_RESERVED and REPORTED_PRECEDENT source_kind to avoid collapsing provenance.',
         'retrieval':'Existing SQLite FTS5/BM25 over extracted card content; candidate relevance only, not certified applicability.',
         'source_review':'MODEL_ASSISTED_NOT_HUMAN_GOLD', 'no_commit_push_or_automatic_next_round':True})
    save(ROOT/'evaluation-rules.json', {'not_model_input':True, 'review_once_after_extraction':True,
         'check':['supported source proposition and conditions', 'headnote/argument/adoption distinction', 'prima facie reservation', 'special statutory protection versus general immunity', 'reported precedent versus independently read authority', 'cross-statute scope', 'extraction completeness within stated coverage'],
         'no_full_fact_annotation':True,'no_rule_induction_claim':True,'no_accuracy_or_generalization_claim':True})
    save(ROOT/'freeze.json', {'time':datetime.now(timezone.utc).isoformat(), 'before_first_generation':True,
         'files':{str(p):sha(p) for p in ROOT.rglob('*') if p.is_file()}, 'actual_code_hashes':code})
    print(json.dumps({'root':str(ROOT),'source_tasks':NAMES,'available_candidates':len(eligible),'compatible_cases':0,'max_calls':3}))

if __name__ == '__main__': prepare()
