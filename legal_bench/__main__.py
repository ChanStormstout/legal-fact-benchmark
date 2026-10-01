import argparse
import json
from pathlib import Path
from .core import audit, read, write_new, validate, compare, log_run
from .engine import execute, mine, cooccurrence_query
from .tasks import prepare, import_reply
from .experiment import check_manifest, freeze, select_split, score, ablate
from .abstraction import abstract


def annotation(path):
    v = read(path)
    if 'annotation' in v:
        if not v.get('validation', {}).get('valid'):
            raise ValueError('Invalid imported annotation: ' + path)
        return v['annotation']
    return v


def main():
    p = argparse.ArgumentParser(description='Local source-grounded legal benchmark; no model APIs')
    sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('audit'); s.add_argument('--input', required=True); s.add_argument('--out', required=True)
    s = sub.add_parser('prepare'); s.add_argument('--source', required=True); s.add_argument('--pass-name', default='A'); s.add_argument('--out', required=True)
    s = sub.add_parser('import');
    for a in ['task', 'source', 'reply', 'metadata', 'out']: s.add_argument('--' + a, required=True)
    s = sub.add_parser('validate'); s.add_argument('--annotation', required=True); s.add_argument('--source', required=True); s.add_argument('--out', required=True)
    s = sub.add_parser('compare'); s.add_argument('--a', required=True); s.add_argument('--b', required=True); s.add_argument('--out', required=True)
    s = sub.add_parser('query'); s.add_argument('--annotation', required=True); s.add_argument('--query', required=True); s.add_argument('--unit'); s.add_argument('--out', required=True)
    s = sub.add_parser('mine'); s.add_argument('--manifest', required=True); s.add_argument('--budget', type=int, default=1000); s.add_argument('--out', required=True)
    s = sub.add_parser('evaluate'); s.add_argument('--manifest', required=True); s.add_argument('--queries', required=True); s.add_argument('--freeze'); s.add_argument('--out', required=True)
    s = sub.add_parser('abstract'); s.add_argument('--annotation', required=True); s.add_argument('--policy', required=True); s.add_argument('--out', required=True)
    s = sub.add_parser('split'); s.add_argument('--eligible', required=True); s.add_argument('--dev-ids', nargs=5, required=True); s.add_argument('--out', required=True)
    s.add_argument('--check-count', type=int, default=100); s.add_argument('--seed', type=int, default=20260930)
    s = sub.add_parser('freeze'); s.add_argument('--manifest', required=True); s.add_argument('--files', nargs='+', required=True); s.add_argument('--out', required=True)
    s = sub.add_parser('score'); s.add_argument('--predictions', required=True); s.add_argument('--references', required=True); s.add_argument('--out', required=True)
    args = p.parse_args(); cmd = args.command
    inputs = []
    if cmd == 'audit':
        result = audit(args.input, args.out); inputs = [args.input]
    elif cmd == 'prepare':
        result = prepare(read(args.source), args.out, args.pass_name); inputs = [args.source]
    elif cmd == 'import':
        result = import_reply(args.task, args.source, args.reply, args.metadata, args.out)
        inputs = [args.task, args.source, args.reply, args.metadata]
    elif cmd == 'validate':
        result = validate(annotation(args.annotation), read(args.source)); inputs = [args.annotation, args.source]
    elif cmd == 'compare':
        result = compare(annotation(args.a), annotation(args.b)); inputs = [args.a, args.b]
    elif cmd == 'query':
        result = execute(annotation(args.annotation), read(args.query), args.unit); inputs = [args.annotation, args.query]
    elif cmd == 'abstract':
        result = abstract(annotation(args.annotation), read(args.policy)); inputs = [args.annotation, args.policy]
    elif cmd == 'split':
        result = select_split(read(args.eligible), args.dev_ids, args.seed, args.check_count); inputs = [args.eligible]
    elif cmd == 'freeze':
        result = freeze(args.manifest, args.files, args.out); inputs = [args.manifest] + args.files
    elif cmd == 'score':
        result = score(read(args.predictions), read(args.references)); inputs = [args.predictions, args.references]
    else:
        manifest = read(args.manifest)
        check_manifest(manifest)
        paths = [r['annotation'] for r in manifest['cases']]
        anns = [annotation(x) for x in paths]
        inputs = [args.manifest] + paths
        groups = [r['dispute_group'] for r in manifest['cases']]
        if len(groups) != len(set(groups)):
            raise ValueError('Duplicate dispute groups in run')
        if cmd == 'mine':
            if any(r['split'] != 'dev' for r in manifest['cases']):
                raise ValueError('Mining may only read development annotations')
            result = mine(anns, args.budget)
        else:
            inputs.append(args.queries)
            if any(r['split'] == 'check' for r in manifest['cases']):
                if not args.freeze:
                    raise ValueError('Check evaluation requires a frozen configuration')
                from .core import digest
                frozen = read(args.freeze)
                saved = frozen['files'].get(Path(args.queries).name)
                if not saved or saved['sha256'] != digest(Path(args.queries).read_bytes()):
                    raise ValueError('Queries differ from frozen configuration')
                expected = {(r['case_id'], r['dispute_group'], r['split']) for r in frozen['manifest']['cases']}
                if any((r['case_id'], r['dispute_group'], r['split']) not in expected for r in manifest['cases']):
                    raise ValueError('Evaluation cases differ from frozen split')
                inputs.append(args.freeze)
            queries = read(args.queries)
            result = {'results': [], 'note': 'Execution results, not accuracy without independent reference answers.'}
            for ann in anns:
                for u in ann['units']:
                    if not u.get('primary', False): continue
                    for q in queries:
                        result['results'].append({'case_id': ann['case_id'], 'unit_id': u['id'], 'query_id': q['id'],
                                                  'relational': execute(ann, q['query'], u['id']),
                                                  'cooccurrence': execute(ann, cooccurrence_query(q['query']), u['id']),
                                                  'ablations': {mode: ablate(q['query'], dict(ann, units=[u], events=[e for e in ann['events'] if e['unit_id'] == u['id']]), mode)
                                                                for mode in ['remove_identity', 'ignore_status', 'unknown_as_negative']}})
    if cmd not in ['audit', 'prepare', 'import']:
        write_new(args.out, result)
    log_run(Path(args.out) if cmd in ['audit', 'prepare', 'import'] else Path(args.out).parent,
            cmd, inputs, [args.out])
    print(json.dumps({k: v for k, v in result.items() if k not in ['prompt', 'patterns', 'results', 'raw_reply', 'annotation']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
