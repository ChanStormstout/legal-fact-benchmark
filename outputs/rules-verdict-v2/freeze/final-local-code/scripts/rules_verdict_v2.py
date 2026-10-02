"""Bounded V2 development repair; immutable V1 retained, at most two old cases."""
import argparse
import collections
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import write_new, digest, windows
from legal_bench.rules_verdict_v1.extract_v2 import objects_schema, facts_schema, answer_schema, make_prompt, import_v2, at_string_limits
from legal_bench.rules_verdict_v1.apply_rules import execute

ROOT = Path('outputs/rules-verdict-v2')
OLD = Path('outputs/rules-verdict-v1')
CASES = ['661475', '1134266']


def read(p):
    return json.loads(Path(p).read_text())


def prepare():
    for p in (OLD / 'protocol').glob('*.json'):
        if p.name != 'legacy-preservation.json':
            write_new(ROOT / 'protocol' / p.name, read(p))
    for p in (OLD / 'sources').glob('*.json'):
        write_new(ROOT / 'sources' / p.name, read(p))
    write_new(ROOT / 'protocol/repair-scope.json', {
        'cases': CASES, 'new_cases': [], 'max_attempts_per_case': 1, 'format_generation_calls_per_case': 3,
        'objects_max_tokens': 2048, 'facts_max_tokens': 8192, 'direct_max_tokens': 4096,
        'changes': ['TYPED_OBJECT_REGISTRY_BEFORE_FACTS', 'FIXED_ROLE_KEYS_WITH_MULTIPLE_PARTICIPANTS_PRESERVED',
                    'FIELD_LOCAL_NULL_DECLARATION_ISOLATION', 'DIRECT_SHORT_SENTENCES_WITH_LARGER_STRING_HEADROOM'],
        'same_source_scope_as_v1': True, 'no_semantic_repair_of_old_outputs': True,
        'role': 'EXPOSED_DEVELOPMENT_FORMAT_REPAIR', 'on_failure': 'STOP_NEW_CASE_BATCH',
        'on_success': 'CONTINUE_RULES_AND_AUTHORITIES_WITHIN_EXISTING_PLAN'})
    files = sorted(Path('legal_bench/rules_verdict_v1').glob('*.py')) + [Path(__file__).relative_to(Path.cwd()), Path('legal_bench/mlx_json_constraint.py'),Path('legal_bench/model_output.py')]
    manifest = []
    for p in files:
        raw = p.read_bytes(); target = ROOT / 'freeze/code' / p
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != raw:
            raise FileExistsError('Frozen source differs: ' + str(p))
        target.write_bytes(raw)
        manifest.append({'path': str(p), 'sha256': digest(raw)})
    write_new(ROOT / 'freeze/manifest.json', {'files': manifest, 'configuration': read(ROOT / 'protocol/config-candidate.json')})


def check_case(cid):
    if cid not in CASES:
        raise ValueError('Only two registered development cases allowed')
    for entry in read(ROOT / 'freeze/manifest.json')['files']:
        if digest(Path(entry['path']).read_bytes()) != entry['sha256']:
            raise ValueError('Frozen code changed: ' + entry['path'])
    dest = ROOT / 'runs/format-v2' / cid
    if (dest / 'complete.json').exists():
        return read(dest / 'complete.json')
    from legal_bench.rules_verdict_v1.runtime import Runner
    conf = read(ROOT / 'protocol/config-candidate.json')
    runner = Runner(Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(), conf)
    source = read(ROOT / 'sources' / (cid + '-allowed.json'))
    task = {k: v for k,v in read(ROOT / 'protocol/task.json').items() if k in ['task_id','question','analysis_stage','input_contract']}
    parts = windows(source, runner.count, conf['window_tokens'], conf['overlap_tokens'])
    if len(parts) != 1:
        raise ValueError('V2 repair checks require one existing source window; no truncation allowed')
    prompts = {s: make_prompt(source, task, s) for s in ['direct','objects']}
    calls = {}
    calls['A'] = runner.run(prompts['direct'], answer_schema(source), dest/'direct', conf['direct_max_tokens'])
    calls['objects'] = runner.run(prompts['objects'], objects_schema(source), dest/'objects', 2048)
    usable = {'case_id':cid,'objects':[]}
    object_errors = []
    if calls['objects']['run_status'] == 'OK':
        raw = read(dest/'objects/parsed.json')
        counts = collections.Counter(o['id'] for o in raw['objects'])
        for o in raw['objects']:
            if counts[o['id']] != 1 or not o['evidence']:
                object_errors.append({'raw':o,'reason':'DUPLICATE_OR_UNCITED_OBJECT'})
            else:
                usable['objects'].append(o)
        write_new(dest/'objects/usable-registry.json',{'registry':usable,'isolated':object_errors})
        schema = facts_schema(source, usable['objects'])
        calls['facts'] = runner.run(make_prompt(source,task,'facts',usable['objects']),schema,dest/'facts',conf['extract_max_tokens'])
        if calls['facts']['run_status'] == 'OK':
            raw = read(dest/'facts/parsed.json')
            view = import_v2(raw,usable,source,'w001')
            view['coverage_limited'] |= bool(object_errors)
            write_new(dest/'facts/import.json',view)
            queries = read(ROOT/'protocol/diagnostic-queries.json')['queries']
            write_new(dest/'execution.json',[{'query_id':q['id'],'result':execute(view,q['query'])} for q in queries])
    else:
        calls['facts'] = {'run_status':'UNSUPPORTED','answer_status':None,'reason':'OBJECT_STAGE_FAILED'}
    view = read(dest/'facts/import.json') if (dest/'facts/import.json').exists() else None
    cap = at_string_limits(read(dest/'direct/parsed.json'),answer_schema(source)) if calls['A']['run_status']=='OK' else []
    result = {'case_id':cid,'role':'EXPOSED_DEVELOPMENT_FORMAT_REPAIR',
              'calls':{k:{f:v.get(f) for f in ['run_status','prompt_tokens','output_tokens','elapsed_seconds','peak_mlx_memory_gb']} for k,v in calls.items()},
              'direct_string_caps':cap,'record_count':len(view['records']) if view else 0,
              'relation_count':len(view['relations']) if view else 0,'quarantine_count':len(view['quarantine']) if view else None,
              'isolated_object_count':len(object_errors), 'multi_role_count':len(view['multi_role_bindings']) if view else 0,
              'field_isolation_count':len(view['field_isolation']) if view else 0,
              'gate_passed': all(c['run_status']=='OK' for c in calls.values()) and bool(view and view['records']) and not cap,
              'semantic_accuracy_evaluated':False}
    write_new(dest/'complete.json',result)
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','check']);p.add_argument('--case',choices=CASES);a=p.parse_args()
    if a.command=='prepare': prepare()
    else: print(json.dumps(check_case(a.case),ensure_ascii=False),flush=True)
