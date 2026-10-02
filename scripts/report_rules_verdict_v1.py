"""Summarize the two immutable development attempts; never runs a model."""
import collections
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import write_new


def read(path):
    return json.loads(path.read_text())


def main():
    root = Path('outputs/rules-verdict-v1')
    sample = read(root / 'protocol/sample.json')
    rows = []
    for case in sample['format_check_cases']:
        folder = root / 'runs/resource-format-v1' / case
        complete = read(folder / 'complete.json')  # Requires both completed attempts.
        direct = read(folder / 'direct/run.json')
        parsed = read(folder / 'direct/parsed.json') if (folder / 'direct/parsed.json').exists() else {}
        facts = read(folder / 'facts.json')
        calls = []
        declarations = []
        generated_records = generated_relations = 0
        for name in ['direct'] + [w['window_id'] for w in read(folder / 'windows.json')['windows']]:
            run = read(folder / name / 'run.json')
            calls.append(dict(stage=name, run_status=run['run_status'],
                              input_tokens=run['prompt_tokens'], output_tokens=run.get('output_tokens'),
                              elapsed_seconds=run.get('elapsed_seconds'),
                              peak_mlx_memory_gb=run.get('peak_mlx_memory_gb'),
                              thinking_disabled=run['thinking_disabled_template_verified'],
                              thinking_output_present=run.get('thinking_output_present')))
            if name != 'direct' and (folder / name / 'parsed.json').exists():
                payload = read(folder / name / 'parsed.json')
                generated_records += len(payload['records'])
                generated_relations += len(payload['relations'])
                for r in payload['records']:
                    for f in r['known']:
                        value = next((x['object'] for x in r['roles'] if x['name'] == f[6:]), None) if f.startswith('roles.') else r.get(f)
                        if value is None or value == 'UNKNOWN':
                            declarations.append({'record_id': r['id'], 'field': f, 'value': value})
        rows.append({'case_id': case, 'gate': complete, 'calls': calls,
                     'generated_assertions': generated_records, 'generated_relations': generated_relations,
                     'imported_assertions': len(facts['records']), 'imported_relations': len(facts['relations']),
                     'quarantine_reasons': dict(collections.Counter(r['reason'] for r in facts['quarantine'])),
                     'invalid_known_declarations': declarations,
                     'direct_reason_characters': len(parsed.get('reason', '')),
                     'direct_reason_at_schema_cap': len(parsed.get('reason', '')) == 700,
                     'direct_outcome': parsed.get('outcome'),
                     'direct_assessment_status': parsed.get('assessment_status'),
                     'execution_file': str(folder / 'execution.json')})
    prior = read(root / 'protocol/legacy-preservation.json')
    changed = [r['path'] for r in prior['files'] if not Path(r['path']).exists() or
               hashlib.sha256(Path(r['path']).read_bytes()).hexdigest() != r['sha256']]
    draft = Path('legal_bench/local_chunk_v11.py')
    preserved = {'files_checked': len(prior['files']), 'changed': changed,
                 'unfinished_draft_unchanged': hashlib.sha256(draft.read_bytes()).hexdigest() == prior['unfinished_draft_sha256']}
    result = {'role': 'DEVELOPMENT_RESOURCE_FORMAT_ONLY', 'cases': rows,
              'local_model_calls': sum(len(r['calls']) for r in rows), 'web_model_calls': 0,
              'retries': 0, 'new_cases_started': 0, 'legacy_preservation': preserved,
              'generation_elapsed_seconds': sum(c['elapsed_seconds'] or 0 for r in rows for c in r['calls']),
              'resource_format_gate_passed': all(r['gate']['gate_passed'] and not r['direct_reason_at_schema_cap'] for r in rows),
              'interpretation': 'Schema completion, import usability and answer prose completeness are distinct; no legal accuracy scoring.',
              'legal_end_to_end_completed': False}
    write_new(root / 'runs/resource-format-v1/summary.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
