"""Three exposed cases, nine frozen conditions, six serial local calls maximum."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import digest, write_new
from legal_bench.rules_verdict_v1.conditions_v3 import (
    prompt, direct_schema, extraction_schema, import_facts, execute, evidence_ok)

ROOT = Path('outputs/rules-verdict-v3')


def read(p): return json.loads(Path(p).read_text())


def prepare():
    from legal_bench.rules_verdict_v1.runtime import SETTINGS
    protocol = read(ROOT/'protocol/tasks.json')
    for cid in protocol['cases']:
        source = read(ROOT/'sources'/(cid+'-allowed.json'))
        for method, schema in [('A', direct_schema), ('B', extraction_schema)]:
            dest = ROOT/'prepared'/cid/method
            dest.mkdir(parents=True, exist_ok=True)
            value = prompt(source, protocol, method)
            if (dest/'prompt.txt').exists() and (dest/'prompt.txt').read_text() != value:
                raise ValueError('Existing prepared prompt changed')
            (dest/'prompt.txt').write_text(value)
            write_new(dest/'schema.json', schema(source))
    files = ['legal_bench/rules_verdict_v1/conditions_v3.py', 'scripts/conditions_v3.py',
             'legal_bench/rules_verdict_v1/runtime.py', 'legal_bench/rules_verdict_v1/contracts.py',
             'legal_bench/mlx_json_constraint.py', 'legal_bench/model_output.py',
             'tests/test_conditions_v3.py']
    snapshots = []
    for name in files:
        raw = Path(name).read_bytes(); target = ROOT/'freeze/code'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != raw: raise ValueError('Frozen code changed')
        target.write_bytes(raw); snapshots.append({'path': name, 'sha256': digest(raw)})
    prepared = [p for p in (ROOT/'prepared').rglob('*') if p.is_file()]
    write_new(ROOT/'freeze/config.json', {'files': snapshots, 'settings': SETTINGS,
        'max_output_tokens': {'A': 2048, 'B': 6144}, 'calls': 6, 'new_cases': 0,
        'protocol_hash': digest(protocol), 'prepared': {str(p): digest(p.read_bytes()) for p in prepared},
        'source_manifest_hash': digest(read(ROOT/'protocol/source-manifest.json')),
        'scoring': 'Status agreement is separate from valid binding/evidence. No inferred accuracy from agreement.',
        'review_budget': 'At most three discrepancies after running; no new model revisions or replays.'})


def freeze_reference():
    reference = read(ROOT/'references/condition-reference-v3.json')
    protocol = read(ROOT/'protocol/tasks.json')
    required = {(c, q['id']) for c in protocol['cases'] for q in protocol['questions']}
    keys = [(r['case_id'], r['question_id']) for r in reference['answers']]
    if len(keys) != 9 or set(keys) != required: raise ValueError('Reference keys missing/duplicated')
    checks = []
    for row in reference['answers']:
        source = read(ROOT/'sources'/(row['case_id']+'-allowed.json'))
        if row['answer_status'] not in ['SUPPORTED','REFUTED','UNKNOWN','CONFLICT']:
            raise ValueError('Reference status unsupported')
        checks.append({'case_id':row['case_id'],'question_id':row['question_id'],
                       'quotes_located':evidence_ok(row['evidence'], source)})
    # A reference may need explanation of absence instead of an invented quote.
    # Unlocatable supplied quotes prevent its use in scoring; do not edit quotes.
    if any(not x['quotes_located'] for x in checks): raise ValueError('Reference quote check failed: '+repr(checks))
    write_new(ROOT/'references/frozen.json', {'reference_hash':digest(reference),
        'protocol_hash':digest(protocol),'checks':checks,
        'provenance':'MODEL_GENERATED_SOURCE_REVIEW_NOT_HUMAN_GOLD'})


def run_case(cid):
    from legal_bench.rules_verdict_v1.runtime import Runner
    protocol = read(ROOT/'protocol/tasks.json'); config = read(ROOT/'freeze/config.json')
    if cid not in protocol['cases']: raise ValueError('Case outside fixed protocol')
    if digest(protocol) != config['protocol_hash']: raise ValueError('Protocol changed')
    ref = read(ROOT/'references/frozen.json')
    if digest(read(ROOT/'references/condition-reference-v3.json')) != ref['reference_hash']:
        raise ValueError('Reference changed')
    for item in config['files']:
        if digest(Path(item['path']).read_bytes()) != item['sha256']: raise ValueError('Frozen code changed')
    for p, sha in config['prepared'].items():
        if digest(Path(p).read_bytes()) != sha: raise ValueError('Prepared input changed')
    source = read(ROOT/'sources'/(cid+'-allowed.json'))
    expected = next(x for x in read(ROOT/'protocol/source-manifest.json') if x['case_id']==cid)
    if digest((ROOT/'sources'/(cid+'-allowed.json')).read_bytes()) != expected['sha256']:
        raise ValueError('Source changed')
    out = ROOT/'runs'/cid
    if (out/'complete.json').exists(): return read(out/'complete.json')
    runner = Runner(Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(), config['settings'])
    results = {}
    for method in ['A','B']:
        base = ROOT/'prepared'/cid/method
        results[method] = runner.run((base/'prompt.txt').read_text(), read(base/'schema.json'),
                                     out/method, config['max_output_tokens'][method])
        if method=='B' and results[method]['run_status']=='OK':
            view = import_facts(read(out/'B/parsed.json'),source)
            write_new(out/'B/imported.json',view)
            write_new(out/'B/execution.json',[execute(view,q['id'],expected_case=cid) for q in protocol['questions']])
    complete = {'case_id':cid,'runs':results,'reference_used_in_model_prompts':False}
    write_new(out/'complete.json',complete);return complete


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','freeze-reference','run']);parser.add_argument('--case')
    args=parser.parse_args()
    if args.command=='prepare':prepare()
    elif args.command=='freeze-reference':freeze_reference()
    else:run_case(args.case)
