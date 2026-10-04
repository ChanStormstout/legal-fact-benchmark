"""Import frozen replies and render an explicit source review, never infer correctness."""
import csv
import hashlib
import json
import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.rule_application_v17 import parse_final, restore_evidence

ROOT = pathlib.Path('outputs/rules-verdict-v17-rule-application')
ORDER = ['A_COMMON', 'B_PLUS_V16']
read = lambda p: json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def save(p, value):
    data = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        if p.read_text(encoding='utf-8') != data:
            raise FileExistsError('Preserve existing record: ' + str(p))
        return
    with p.open('x', encoding='utf-8') as f: f.write(data)


def import_condition(method):
    folder, task = ROOT/'runs'/method, ROOT/'tasks'/method
    run = read(folder/'run.json')
    result = {**run, 'method': method, 'answer': None, 'format_status': 'NOT_RUN'}
    raw_path = folder/'raw-response.txt'
    if raw_path.exists():
        result['raw_sha256'] = sha(raw_path)
    if run['technical_status'] != 'OK':
        return result
    try:
        answer, text, check = parse_final(raw_path.read_text(encoding='utf-8'), read(task/'schema.json'))
    except (ValueError, KeyError) as error:
        result.update({'format_status': 'FORMAT_ERROR', 'format_error': str(error),
                       'qualitative_text_retained': raw_path.exists()})
        return result
    save(folder/'answer.json', answer); save(folder/'format-check.json', check)
    registry = read(ROOT/'source-registry.json')
    evidence = restore_evidence(answer, list(registry['case'].values()), list(registry['law'].values()))
    save(folder/'restored-evidence.json', evidence)
    result.update({'answer': answer, 'format_status': 'OK', 'grounds_empty': check['grounds_empty'],
                   'semantic_correctness_certified': False})
    return result


def main():
    frozen = read(ROOT/'freeze.json'); start = read(ROOT/'start-audit.json')
    for path, h in {**frozen['files'], **frozen['actual_code_hashes']}.items():
        if sha(path) != h: raise ValueError('Frozen material changed: ' + path)
    for path, h in {**start['historical_files'], **start['code_at_start']}.items():
        if sha(path) != h: raise ValueError('Historical file changed: ' + path)
    review = read(ROOT/'source-review.json')
    if review['reference_status'] != 'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD':
        raise ValueError('Source review provenance missing')
    if review['review_passes'] != 1:
        raise ValueError('Only one concentrated source review authorized')
    runs = [import_condition(m) for m in ORDER]
    executed = sum(r['generation_calls'] for r in runs)
    if executed > 2: raise ValueError('Call budget exceeded')
    rows = []
    for run in runs:
        method = run['method']; qualitative = review['conditions'][method]
        submitted = run.get('submitted_at'); complete = run.get('observed_complete_at')
        observed = ((datetime.fromisoformat(complete.replace('Z', '+00:00')) -
                     datetime.fromisoformat(submitted.replace('Z', '+00:00'))).total_seconds()
                    if submitted and complete else None)
        rows.append({'case': '1134266', 'method': method, 'technical_status': run['technical_status'],
            'format_status': run['format_status'], 'outcome': run['answer']['outcome'] if run['answer'] else None,
            'supported_decisive_analysis': qualitative['supported_decisive_analysis'],
            'confirmed_errors': qualitative['confirmed_errors'], 'omissions': qualitative['omissions'],
            'internal_consistency': qualitative['internal_consistency'], 'real_gaps': qualitative['real_gaps'],
            'source_use': qualitative['source_use'], 'conversation_url': run.get('conversation_url'),
            'input_characters': read(ROOT/'protocol.json')['task_sizes'][method]['task_characters'],
            'output_characters': len((ROOT/'runs'/method/'raw-response.txt').read_text()) if (ROOT/'runs'/method/'raw-response.txt').exists() else None,
            'input_tokens': None, 'output_tokens': None, 'precise_generation_seconds': None,
            'observed_submit_to_complete_upper_bound_seconds': observed,
            'displayed_thinking_duration': run.get('displayed_thinking_duration'),
            'peak_memory': None, 'generation_calls': run['generation_calls'], 'retries': 0})
    results = {'runs': runs, 'web_generations': executed, 'local_generations': 0, 'paid_api_calls': 0,
        'retries': 0, 'new_rule_extractions': 0, 'same_case_and_law_information_scope': True,
        'A_contains_three_historical_common_cards': True, 'B_adds_nine_V16_candidate_cards': True,
        'legal_applicability_certified': False, 'independent_test': False, 'source_review': 'source-review.json'}
    save(ROOT/'results.json', results); save(ROOT/'comparison-table.json', rows)
    csv_path = ROOT/'comparison-table.csv'
    with csv_path.open('x', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in row.items()})
    save(ROOT/'decision.json', {'decision': review['decision'], 'decision_zh': review['decision_zh'],
        'boundary': review['boundary'], 'no_automatic_next_round': True})
    save(ROOT/'preservation-check.json', {'historical_files_unchanged': len(start['historical_files']),
        'code_at_start_unchanged': len(start['code_at_start']), 'frozen_files_unchanged': len(frozen['files']),
        'semantic_or_JSON_completion_repairs': 0, 'new_generations': executed})
    save(ROOT/'stop.json', {'round_complete': True, 'reason': 'TWO_BOUNDED_CONDITIONS_AND_ONE_SOURCE_REVIEW',
        'generations': executed, 'maximum': 2, 'retries': 0, 'additional_experiment': False,
        'semantic_fixes_applied_after_outputs': False, 'commit_or_push': False})
    (ROOT/'report-zh.txt').write_text(review['report_zh'], encoding='utf-8')
    pieces = ['# V17 完整回答\n\n两边共享3张历史卡和相同原文，B另有9张V16候选卡。不是无规则对有规则的纯比较。\n']
    for run in runs:
        pieces.append('\n## ' + run['method'] + '\n\n技术状态：' + run['technical_status'] + '；格式状态：' + run['format_status'] + '\n\n')
        pieces.append('```json\n' + json.dumps(run['answer'], ensure_ascii=False, indent=2) + '\n```\n')
        pieces.append('\n[原始回复](runs/' + run['method'] + '/raw-response.txt)\n')
    (ROOT/'final-answer-slots.md').write_text(''.join(pieces), encoding='utf-8')
    print(json.dumps({'conditions': len(runs), 'calls': executed, 'decision': review['decision']}, ensure_ascii=False))


if __name__ == '__main__': main()
