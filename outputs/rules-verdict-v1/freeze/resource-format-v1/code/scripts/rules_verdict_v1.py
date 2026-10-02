"""Stage runner. Does not alter historical sources or completed attempts."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import write_new, digest, windows
from legal_bench.rules_verdict_v1.extract import prompt, import_records
from legal_bench.rules_verdict_v1.contracts import extraction_schema, decision_schema
from legal_bench.rules_verdict_v1.apply_rules import execute


def read(path):
    return json.loads(Path(path).read_text())


def check_case(root, case_id):
    from legal_bench.rules_verdict_v1.runtime import Runner
    root = Path(root)
    protocol = read(root / 'protocol/task.json')
    case = next(c for c in read(root / 'protocol/sample.json')['development'] if c['case_id'] == case_id)
    view = read(root / case['input_view'])
    out = root / 'runs/resource-format-v1' / case_id
    if (out / 'complete.json').exists():
        print('REUSE', case_id, flush=True)
        return read(out / 'complete.json')
    config = read(root / 'protocol/config-candidate.json')
    model_path = Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip()
    runner = Runner(model_path, config)
    pieces = windows(view, runner.count, config['window_tokens'], config['overlap_tokens'])
    write_new(out / 'windows.json', {'windows': pieces})
    public_task = {k: protocol[k] for k in ['task_id', 'question', 'analysis_stage', 'input_contract']}
    direct_prompt = prompt(view, public_task, 'direct')
    prompts = [prompt(piece, public_task, 'extract') for piece in pieces]
    counts = {'direct': len(runner.tokenizer.encode(runner.render(direct_prompt))),
              'extract': [len(runner.tokenizer.encode(runner.render(p))) for p in prompts]}
    write_new(out / 'preflight.json', {'counts': counts, 'total_budget': config['total_budget'],
                                      'source_tokens': runner.count('\n'.join(s['text'] for s in view['segments']))})
    if counts['direct'] + config['direct_max_tokens'] > config['total_budget'] or any(n + config['extract_max_tokens'] > config['total_budget'] for n in counts['extract']):
        result = {'case_id': case_id, 'gate_passed': False, 'run_status': 'INPUT_TOO_LONG', 'answer_status': None, 'reason': 'COMMON_SCOPE_PREFLIGHT_FAILED'}
        write_new(out / 'complete.json', result)
        return result
    direct = runner.run(direct_prompt, decision_schema(view), out / 'direct', config['direct_max_tokens'])
    collected = {'case_id': case_id, 'objects': [], 'records': [], 'relations': [], 'quarantine': [], 'coverage_limited': False}
    statuses = []
    for piece, rendered_prompt in zip(pieces, prompts):
        destination = out / piece['window_id']
        run = runner.run(rendered_prompt, extraction_schema(piece), destination, config['extract_max_tokens'])
        statuses.append(run['run_status'])
        if run['run_status'] != 'OK':
            collected['coverage_limited'] = True
            continue
        imported = import_records(read(destination / 'parsed.json'), piece, piece['window_id'])
        write_new(destination / 'import.json', imported)
        for field in ['objects', 'records', 'relations', 'quarantine']:
            collected[field].extend(imported[field])
        collected['coverage_limited'] |= imported['coverage_limited']
    # Initial format check never guesses cross-window identity. A separate merge
    # contract is required before treating multi-window identity as resolved.
    collected['cross_window_identity_status'] = 'NOT_NEEDED' if len(pieces) == 1 else 'PENDING_SOURCE_GROUNDED_CONSOLIDATION'
    if len(pieces) > 1:
        collected['coverage_limited'] = True
    write_new(out / 'facts.json', collected)
    queries = read(root / 'protocol/diagnostic-queries.json')['queries']
    answers = [{'query_id': q['id'], 'result': execute(collected, q['query'])} for q in queries]
    write_new(out / 'execution.json', answers)
    imported_ok = bool(collected['records'])
    result = {'case_id': case_id, 'role': 'DEVELOPMENT_RESOURCE_FORMAT_ONLY',
              'gate_passed': direct['run_status'] == 'OK' and all(s == 'OK' for s in statuses) and imported_ok,
              'direct_run_status': direct['run_status'], 'extraction_run_statuses': statuses,
              'source_view_hash': view['input_view_hash'], 'record_count': len(collected['records']),
              'quarantined_count': len(collected['quarantine']), 'coverage_limited': collected['coverage_limited'],
              'semantic_accuracy_measured': False, 'new_case_runs_authorized_by_gate': False,
              'cross_window_identity_status': collected['cross_window_identity_status']}
    write_new(out / 'complete.json', result)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    check = sub.add_parser('check-dev')
    check.add_argument('--root', default='outputs/rules-verdict-v1')
    check.add_argument('--case', required=True)
    args = parser.parse_args()
    if args.command == 'check-dev':
        check_case(args.root, args.case)


if __name__ == '__main__':
    main()
