"""Prepare and collect two bounded web application-chain development answers."""
import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.application_chain_v18 import (
    APPLICATION_REQUIREMENTS, audit_prompt, audit_view, refine_prompt)
from legal_bench.rules_verdict_v1.law_materials_v2 import citation_checks
from legal_bench.rules_verdict_v1.rule_application_v17 import parse_final, restore_evidence

ROOT = Path('outputs/rules-verdict-v18-application-chain')
CASES = ['661475', '1134266']
V14 = Path('outputs/rules-verdict-v14-web-direct')
V17 = Path('outputs/rules-verdict-v17-rule-application')
CODE = ['scripts/application_chain_v18.py', 'legal_bench/rules_verdict_v1/application_chain_v18.py',
        'tests/test_application_chain_v18.py', 'legal_bench/rules_verdict_v1/rule_application_v17.py',
        'legal_bench/rules_verdict_v1/source_views.py', 'legal_bench/rules_verdict_v1/law_materials_v2.py',
        'legal_bench/rules_verdict_v1/contracts.py']
read = lambda p: json.loads(Path(p).read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.write('\n')


def baselines(cid):
    if cid == '661475':
        return V14/'tasks'/cid/'prompt.txt', V14/'tasks'/cid/'schema.json', V14/'runs'/cid/'answer.json'
    return V17/'tasks/A_COMMON/prompt.txt', V17/'tasks/A_COMMON/schema.json', V17/'runs/A_COMMON/answer.json'


def prepare(test_record):
    if ROOT.exists():
        raise FileExistsError('Continue existing V18; no overwrite or duplicate submissions')
    if str(ROOT) not in read('docs/repository-artifacts.json')['artifact_roots']:
        raise ValueError('Unregistered output directory')
    tests = read(test_record)
    if tests['exit_code'] != 0 or tests['tests_passed'] != 3 or tests['skipped'] != 0:
        raise ValueError('Necessary checks not passed')
    start = read('/tmp/legal-v18-start-audit.json')
    for p, h in {**start['historical_files'], **start['code_at_start']}.items():
        if sha(p) != h: raise ValueError('Existing material/code changed before freeze: '+p)
    full_rows = read('outputs/rules-verdict-v2/protocol/sample.json')['development']
    parents = {r['case_id']: read(r['source_path']) for r in full_rows}
    for r in full_rows:
        if sha(r['source_path']) != r['source_file_sha256']:
            raise ValueError('Parent source file changed')
    ROOT.mkdir(parents=True)
    save(ROOT/'start-audit.json', start)
    (ROOT/'starting-git-status.txt').write_text(start['status'])
    save(ROOT/'engineering-tests.json', tests)
    (ROOT/'generic-analysis-instructions.txt').write_text(APPLICATION_REQUIREMENTS, encoding='utf-8')
    lineage, sizes = [], {}
    for cid in CASES:
        original_path, schema_path, old_answer_path = baselines(cid)
        base = V14/'tasks'/cid
        source, package = read(base/'source.json'), read(base/'law-package.json')
        authorities = [read(V17/'authority-sources'/f'{n}.json') for n in
                       ['GENERAL_RADIO', 'HINDUSTAN_PETROLEUM', 'TELESOUND']] if cid == '1134266' else []
        original = original_path.read_text(encoding='utf-8'); schema = read(schema_path)
        checks = audit_prompt(original, schema, source, package, authorities)
        view_check = audit_view(source, parents[cid])
        legal_origins = []
        for s in package['law_segments']:
            src = parents[s['source_case']]
            parent_id = s['id'].split(':', 2)[2]
            raw = next(x for x in src['segments'] if x['id'] == parent_id)
            if s['text'] != raw['text']: raise ValueError('Law text changed')
            legal_origins.append({'id': s['id'], 'source_case': s['source_case'],
                'parent_id': parent_id, 'text_sha256': sha_text(s['text']), 'source_role': 'OTHER_CASE_LEGAL_MATERIAL_NOT_TARGET_FACT'})
        quote_check = citation_checks(package['cards'], parents)
        if quote_check['not_located']: raise ValueError('RuleCard citation cannot be located')
        prompt = refine_prompt(original)
        registry = {'case': {s['id']: s for s in source['segments']},
                    'law': {s['id']: s for s in package['law_segments']+[s for a in authorities for s in a['segments']]}}
        save(ROOT/'sources'/f'{cid}.json', source)
        save(ROOT/'prepared'/cid/'law-package.json', {'original_common_package': package, 'additional_original_authorities': authorities})
        save(ROOT/'prepared'/cid/'source-registry.json', registry)
        save(ROOT/'prepared'/cid/'checks.json', checks)
        shutil.copyfile(base/'retrieval.json', ROOT/'prepared'/cid/'retrieval-reused.json')
        save(ROOT/'prepared'/cid/'rule-quote-checks.json', quote_check)
        task_dir = ROOT/'tasks'/cid; task_dir.mkdir(parents=True)
        (task_dir/'baseline-prompt.txt').write_bytes(original_path.read_bytes())
        (task_dir/'prompt.txt').write_text(prompt, encoding='utf-8')
        (task_dir/'schema.json').write_bytes(schema_path.read_bytes())
        task = prompt+'\n\nOUTPUT SCHEMA (unchanged contract; no local web token constraint)\n'+json.dumps(schema, ensure_ascii=False, indent=2)
        task += '\n\nWEB EXECUTION REQUIREMENTS\nUse only the complete task attachment. Do not browse, search other versions, use other chats, add materials, or seek corrections. Return the full JSON once. This is ordinary High, not Pro.\n'
        (task_dir/'task.txt').write_text(task, encoding='utf-8')
        wrapper = 'Please read the complete attached self-contained task and answer its fixed question once in the supplied JSON format. Use only the provided materials; do not search externally, use other chats or add law. Read all supplied legal-source blocks. Ordinary High; no Pro.'
        (task_dir/'submission-text.txt').write_text(wrapper, encoding='utf-8')
        sizes[cid] = {'input_characters': len(task), 'input_bytes': len(task.encode()),
            'input_tokens': None, 'task_sha256': sha(task_dir/'task.txt'),
            'baseline_prompt_sha256': sha(original_path), 'added_generic_characters': len(APPLICATION_REQUIREMENTS)}
        lineage.append({'case_id': cid, 'original_parent': next(r for r in full_rows if r['case_id']==cid),
            'view_check': view_check, 'prompt_check': checks, 'legal_segments': legal_origins,
            'rule_quotes_exact': quote_check['exact'], 'rule_quote_support_is_not_entailment': True,
            'baseline_prompt': str(original_path), 'baseline_answer_evaluation_only': str(old_answer_path),
            'additional_authority_provenance': [{k:v for k,v in a.items() if k!='segments'} for a in authorities],
            'retrieval_reused': True, 'ranking_is_not_legal_applicability': True})
    save(ROOT/'data-lineage.json', {'rows': lineage, 'gate_status': 'PASS_WITH_EXPLICIT_SCOPE_LIMITATIONS',
        'no_target_rule_or_answer_restored': True,
        'source_completeness': 'Exact saved allowed text, not visually certified full original judgment',
        'code_roles': {'source_views': 'Deterministic explicit slicing, no keyword semantic filtering',
            'pipeline_v6': 'Old law selection uses top4 candidate cards and their evidence paragraphs; retrospective later sources retained for 661475',
            'V14_V17': 'Exact saved task materials transported; V17 shared authorities added without top-k clipping',
            'V18': 'Adds only generic application instructions; validates lineage/addresses, restores evidence; no legal executor'}})
    save(ROOT/'protocol.json', {'status': 'FROZEN_BEFORE_GENERATION', 'version': 'V18', 'order': CASES,
        'max_web_answers': 2, 'one_per_case': True, 'retries': 0, 'local_model_calls': 0,
        'paid_api_calls': 0, 'new_cases_or_sources_or_cards': 0, 'schema_unchanged': True,
        'ordinary_High_not_Pro': True, 'record_actual_UI_model': True, 'task_sizes': sizes,
        'comparison': 'Historical same-material direct web baseline vs generic application-analysis requirements; not concurrent randomized control, exact model/runtime unavailable',
        'scope': 'Two exposed retrospective development cases, no independent test or outcome prediction',
        'stop': 'One answer per case; format failure does not block independent case; access failure stops, per-case observation limit 15 minutes; no retry, next round, commit or push',
        'review': 'One concentrated final source review. Pre-run diagnostic tables never enter model input; not human gold.'})
    save(ROOT/'evaluation-rules.json', {'not_model_input': True,
        'primary': ['Source-supported premise-to-consequence chain', 'Explicit relevant opposing argument and scope distinction',
                    'Correct speaker and court stage', 'Real decisive gap vs manufactured missing information',
                    'Conditional analysis while keeping genuine unknown', 'Internal proposition-assessment-reason consistency'],
        'secondary': ['Procedural history completeness; omission is consequential only when it affects evidence/status or legal application'],
        'not_success': ['More source IDs', 'More fields', 'Less UNKNOWN', 'Guessing hidden outcome', 'JSON completeness alone'],
        'no_single_case_accuracy': True, 'no_all_fact_reannotation': True,
        'baseline_and_new_answer_same_source_review_standard': True,
        'reference': 'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD'})
    # Pre-generation diagnostics are saved separately by the source review author.
    save(ROOT/'freeze.json', {'time': datetime.now(timezone.utc).isoformat(), 'before_first_generation': True,
        'files': {str(p): sha(p) for p in ROOT.rglob('*') if p.is_file()},
        'code': {p: sha(p) for p in CODE}, 'order': CASES, 'max_calls': 2})
    print(json.dumps({'root': str(ROOT), 'tasks': sizes, 'gate': 'PASS_WITH_EXPLICIT_SCOPE_LIMITATIONS'}))


def sha_text(text): return hashlib.sha256(text.encode('utf-8')).hexdigest()


def verify():
    frozen = read(ROOT/'freeze.json'); start = read(ROOT/'start-audit.json')
    for p,h in {**frozen['files'], **frozen['code'], **start['historical_files'], **start['code_at_start']}.items():
        if sha(p)!=h: raise ValueError('Frozen or historical file changed: '+p)
    return {'frozen_files_unchanged':len(frozen['files']), 'historical_files_unchanged':len(start['historical_files']),
            'starting_code_unchanged':len(start['code_at_start']), 'model_semantic_repairs':0}


def collect():
    preservation = verify(); rows = []
    for cid in CASES:
        run_dir = ROOT/'runs'/cid; run = read(run_dir/'run.json')
        raw = (run_dir/'raw-response.txt').read_text(encoding='utf-8') if (run_dir/'raw-response.txt').exists() else ''
        answer, fmt = None, {'format_status':'NOT_RUN'}
        if run['technical_status']=='OK':
            try:
                answer, _, fmt = parse_final(raw, read(ROOT/'tasks'/cid/'schema.json'))
                save(run_dir/'answer.json', answer)
                registry = read(ROOT/'prepared'/cid/'source-registry.json')
                save(run_dir/'restored-evidence.json', restore_evidence(answer, list(registry['case'].values()), list(registry['law'].values())))
            except ValueError as e:
                fmt = {'format_status':'FORMAT_ERROR', 'error':str(e), 'qualitative_raw_retained': bool(raw)}
        save(run_dir/'format-check.json', fmt)
        if answer is None: save(run_dir/'answer.json', None)
        rows.append({'case_id':cid, 'run':run, 'format':fmt, 'answer':answer,
                     'input_size':read(ROOT/'protocol.json')['task_sizes'][cid], 'output_characters':len(raw)})
    save(ROOT/'results.json', {'rows':rows, 'new_web_generations':sum(r['run'].get('generation_calls',0) for r in rows),
        'retries':0,'local_model_calls':0,'source_review_pending':not (ROOT/'final-source-review.json').exists(),'independent_test':False})
    save(ROOT/'preservation-check.json', preservation)
    print(json.dumps({'complete_JSON_answers':sum(r['answer'] is not None for r in rows), 'preservation':preservation}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','collect','verify']);parser.add_argument('--test-record')
    args=parser.parse_args()
    if args.action=='prepare': prepare(args.test_record)
    elif args.action=='collect': collect()
    else: print(json.dumps(verify()))
