"""Freeze the exact two-task same-source comparison, without model generation."""
import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.rule_application_v17 import build_pair

ROOT = pathlib.Path('outputs/rules-verdict-v17-rule-application')
BASE = pathlib.Path('outputs/rules-verdict-v14-web-direct/tasks/1134266')
V16 = pathlib.Path('outputs/rules-verdict-v16-rule-transfer')
PLAN = pathlib.Path('docs/plans/rule-card-debug-v17')
NAMES = ['GENERAL_RADIO', 'HINDUSTAN_PETROLEUM', 'TELESOUND']
ORDER = ['A_COMMON', 'B_PLUS_V16']
CODE = ['legal_bench/rules_verdict_v1/rule_application_v17.py',
        'scripts/prepare_v17_rule_application.py', 'scripts/report_v17_rule_application.py',
        'tests/test_rule_application_v17.py', 'legal_bench/rules_verdict_v1/contracts.py']
EXECUTION = ('只依据本任务提供的完整允许案情和法律材料回答，不进行外部搜索，不查找该案件的其他版本，不依赖其他对话。'
             '请一次性按给定格式提供完整最终答案。可使用文件工具生成可下载JSON，但不要额外补充法律资料。'
             '网页端没有本地逐token的Schema约束。')
WRAPPER = '请完整读取所附单一自包含任务文件，按其中固定问题和JSON合同一次性回答。' + EXECUTION
read = lambda p: json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def save(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2); f.write('\n')


def prepare(test_record):
    if ROOT.exists():
        raise FileExistsError('Continue an existing frozen round; never overwrite or resubmit')
    if str(ROOT) not in read('docs/repository-artifacts.json')['artifact_roots']:
        raise ValueError('Register new output root first')
    tests = read(test_record)
    if tests['exit_code'] != 0 or tests['tests_passed'] != 4:
        raise ValueError('Necessary tests did not pass')
    audit = read(PLAN/'audit-at-plan.json')
    for name, h in {**audit['input_files_sha256'], **audit['inspected_code_sha256']}.items():
        if sha(name) != h:
            raise ValueError('Plan input or inspected existing code changed: ' + name)
    baseline = (BASE/'prompt.txt').read_text(encoding='utf-8')
    case, law = read(BASE/'source.json'), read(BASE/'law-package.json')
    authorities = [read(V16/'sources'/f'{n}.json') for n in NAMES]
    collection = read(V16/'rule-collection.json')
    pair = build_pair(baseline, read(BASE/'schema.json'), case, law, authorities, collection)
    if pair['checks']['common_old_cards'] != 3 or pair['checks']['new_cards_B'] != 9:
        raise ValueError('Actual comparison differs from the approved plan')
    history = {str(p): sha(p) for p in pathlib.Path('outputs').rglob('*')
               if p.is_file() and '__pycache__' not in p.parts}
    code_at_start = {str(p): sha(p) for b in ['legal_bench', 'scripts', 'tests']
                     for p in pathlib.Path(b).rglob('*.py') if '__pycache__' not in p.parts}
    save(ROOT/'start-audit.json', {'time': datetime.now(timezone.utc).isoformat(),
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'branch': subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip(),
        'historical_files': history, 'code_at_start': code_at_start})
    (ROOT/'starting-git-status.txt').write_text(subprocess.check_output(['git', 'status', '--short'], text=True))
    shutil.copyfile(BASE/'source.json', ROOT/'source-allowed.json')
    (ROOT/'sources').mkdir()
    shutil.copyfile(BASE/'source.json', ROOT/'sources/1134266.json')
    (ROOT/'authority-sources').mkdir()
    for n in NAMES:
        shutil.copyfile(V16/'sources'/f'{n}.json', ROOT/'authority-sources'/f'{n}.json')
    shutil.copyfile(V16/'rule-collection.json', ROOT/'rule-collection.json')
    save(ROOT/'prepared/1134266/law-package.json', {'original_common_package': law, 'additional_original_authorities': authorities})
    shutil.copyfile(BASE/'retrieval.json', ROOT/'prepared/1134266/retrieval-reused.json')
    (ROOT/'base-prompt.txt').write_text(baseline, encoding='utf-8')
    save(ROOT/'source-registry.json', {'case': pair['case_source_map'], 'law': pair['law_source_map'],
        'originals_unchanged': True, 'no_semantic_certification': True})
    save(ROOT/'material-equality.json', pair['checks'])
    save(ROOT/'program-checks.json', {'kind': 'MATERIAL_REFERENCE_CHECKS_ONLY',
        'material_checks': pair['checks'], 'legal_condition_execution': False, 'not_model_input': True})
    lengths = {}
    for method in ORDER:
        task = ROOT/'tasks'/method
        save(task/'schema.json', pair['schema'])
        (task/'prompt.txt').write_text(pair['prompts'][method], encoding='utf-8')
        content = pair['prompts'][method] + '\n\nOUTPUT SCHEMA (same contract both conditions; no local web token mask)\n'
        content += json.dumps(pair['schema'], ensure_ascii=False, indent=2)
        content += '\n\nWEB EXECUTION REQUIREMENTS\n' + EXECUTION
        (task/'task.txt').write_text(content, encoding='utf-8')
        (task/'submission-text.txt').write_text(WRAPPER, encoding='utf-8')
        lengths[method] = {'prompt_characters': len(pair['prompts'][method]),
                           'task_characters': len(content), 'task_bytes': len(content.encode('utf-8')),
                           'task_sha256': sha(task/'task.txt'), 'input_tokens': None}
    protocol = read(PLAN/'protocol-proposed.json')
    protocol.update({'status': 'FROZEN_BEFORE_FIRST_GENERATION', 'version_label': 'V17',
                     'user_execution_authorized': True, 'task_sizes': lengths,
                     'actual_prepared_material_check': pair['checks'],
                     'plan_creation_is_not_model_execution_authorization': False})
    save(ROOT/'protocol.json', protocol)
    save(ROOT/'engineering-tests.json', tests)
    save(ROOT/'evaluation-rules.json', {'not_model_input': True,
        'reference_status': 'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD', 'passes': 1,
        'check': ['decisive known facts and omitted source', 'speaker and court/stage attribution',
                  'object connections and event dates', 'statutory scope and reserved opinions',
                  'support AND opposition', 'AND/OR, necessity, polarity', 'real gap versus model omission',
                  'point-assessment-explanation-reason consistency'],
        'historical_review_is_locator_not_gold': True, 'no_case_accuracy_rank': True,
        'no_full_intermediate_annotation': True, 'no_expectation_of_withheld_historical_outcome': True,
        'possible_decisions': protocol['decisions']})
    save(ROOT/'freeze.json', {'time': datetime.now(timezone.utc).isoformat(), 'before_first_generation': True,
        'files': {str(p): sha(p) for p in ROOT.rglob('*') if p.is_file()},
        'actual_code_hashes': {name: sha(name) for name in CODE}, 'order': ORDER,
        'max_web_generations': 2, 'retries': 0})
    print(json.dumps({'root': str(ROOT), 'lengths': lengths, 'checks': pair['checks']}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--test-record', required=True)
    prepare(parser.parse_args().test_record)
