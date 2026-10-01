"""Integrate five-case side review, gated abstractions and fixed development runs."""
import argparse
import copy
import csv
import importlib.util
import json
import platform
import random
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.core import read, write_new, digest, log_run
from legal_bench.reviewed_pipeline import registry, normalize_view, oracle_view, CARDS
from legal_bench.scoped_engine import execute, projection_view, field_value
from legal_bench.scoped_mining import mine, seed_annotation
from legal_bench.conditional_engine import generate_from_seeds, candidate_order
from legal_bench.development_experiment import without_identity
from legal_bench.engine import cooccurrence_query
from legal_bench import exhaustive_oracle as oracle


def execution_check(views, candidates):
    translated = [oracle_view(v) for v in views]
    errors, count = [], 0
    for serialized in candidates:
        q = json.loads(serialized)
        for view, independent in zip(views, translated):
            actual = execute(view, dict(q, mode='SCOPED_EXISTENTIAL'))
            truth = oracle.answer(independent, q)
            matches = {tuple(sorted(w['binding'].items())) for w in actual['witnesses']}
            pending = {tuple(sorted(w['binding'].items())) for w in actual['uncertain_bindings']}
            count += 1
            if actual['status'] != truth['status'] or matches != set(truth['matches']) or pending != set(truth['unknown']):
                errors.append({'case_id': view['case_id'], 'query': q, 'result': actual, 'oracle': truth})
    return {'comparisons': count, 'errors': errors, 'passed': not errors,
            'boundary': 'Independent program semantics, not independent legal gold'}


def discovery_view(view):
    result = copy.deepcopy(view)
    result['events'] = [e for e in view['events'] if e['task_stratum'] != 'LEGAL_STATE']
    result['discovery_excluded_legal_states'] = [e['id'] for e in view['events'] if e['task_stratum'] == 'LEGAL_STATE']
    return result


def pattern_info(pattern, views):
    index = {v['case_id']: {e['id']: e for e in v['events']} for v in views}
    kinds = Counter()
    ids, assertions, anchors = [], {}, {}
    for result in pattern['results']:
        if result['relation']['status'] != 'MATCH':
            continue
        cid = result['case_id']
        ids.append(cid)
        assertions[cid], anchors[cid] = set(), set()
        for witness in result['relation']['witnesses']:
            events = [index[cid][aid] for aid in witness['binding'].values()]
            group = {e['source_assertion']['kind'] for e in events}
            kinds['PROCEDURAL_ONLY' if group == {'PROCEDURAL_ACT'} else 'FACT_ONLY' if group == {'FACT'} else 'MIXED'] += 1
            for event in events:
                assertions[cid].add(event['id'])
                anchors[cid].update(x['segment_id'] for x in event['evidence'])
    joins = [c for c in pattern['query']['constraints'] if c['op'] == 'same']
    court_only = bool(joins) and all(c['left'].split('.', 1)[1] in ['roles.court', 'roles.prior_court']
                                   and c['right'].split('.', 1)[1] in ['roles.court', 'roles.prior_court'] for c in joins)
    return {'matching_case_ids': ids, 'witness_kind_composition': dict(kinds), 'court_only_joins': court_only,
            'assertion_ids_by_case': {k: sorted(v) for k, v in assertions.items()},
            'source_segment_ids_by_case': {k: sorted(v) for k, v in anchors.items()},
            'same_type_record_pair': pattern['same_type_pair'],
            'meaning_boundary': 'Recorded-ID structure; not equal extent/time, same proceeding, distinct real events or legal rule'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', default='outputs/semantic-audit-side-20260930')
    parser.add_argument('--prior', default='outputs/benchmark-pilot-v03/experiments/conditional-repair-v2')
    parser.add_argument('--out', required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    audit, prior, out = Path(args.audit), Path(args.prior), Path(args.out)
    if out.exists() and not args.resume:
        raise ValueError('Use a fresh output directory or --resume')
    out.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    spec = importlib.util.spec_from_file_location('side_review_validator', audit / 'check_reviews.py')
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    manifest, earlier_mapping, query_source = (read(path) for path in
              [audit / 'input-manifest.json', prior / 'mapping-config.json', prior / 'queries.json'])
    code = [Path(__file__)] + [Path('legal_bench') / (name + '.py') for name in
            ['reviewed_pipeline', 'scoped_engine', 'scoped_mining', 'conditional_engine', 'engine', 'exhaustive_oracle', 'core']]
    config = {'version': 'source-reviewed-five-case-v2', 'audit_manifest_hash': digest(manifest),
              'prior_mapping_hash': digest(earlier_mapping), 'queries_hash': digest(query_source),
              'code_hashes': {str(p): digest(p.read_bytes()) for p in code}, 'validator_hash': digest((audit / 'check_reviews.py').read_bytes()),
              'budget': 1000, 'min_support': 2, 'max_joins': 2, 'seed': 20260930,
              'profiles': ['CORE', 'ATLAS', 'NATIVE'], 'held_out': False,
              'annotation_origin': 'MODEL_SOURCE_REVIEW_WITH_CODEX_TARGETED_CHECKS_NOT_HUMAN_GOLD',
              'temporal_amount_fields': 'NOT_APPROVED_BY_THIS_AUDIT',
              'scope': 'Full-judgment retrospective scoped records; no current/global truth or outcome prediction'}
    write_new(out / 'config.json', config)
    write_new(out / 'input-manifest.json', manifest)
    write_new(out / 'type-cards.json', CARDS)
    queries = [dict(q, query=dict(q['query'], mode='SCOPED_EXISTENTIAL'),
                    answer_scope='Source-reviewed scoped record existence, within approved fields',
                    not_found_meaning='No matching usable recorded binding; not real-world absence') for q in query_source]
    write_new(out / 'queries.json', queries)
    for path in code + [audit / 'check_reviews.py']:
        destination = out / 'code' / path.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and destination.read_bytes() != path.read_bytes():
            raise ValueError('Resume code mismatch')
        if not destination.exists():
            destination.write_bytes(path.read_bytes())

    def stage(relative, compute):
        path = out / relative
        if path.exists():
            return read(path)
        value = compute()
        write_new(path, value)
        return value

    corpus, checks, file_checks = {'A': [], 'B': []}, [], []
    inputs = [audit / 'input-manifest.json', prior / 'mapping-config.json', prior / 'queries.json']
    for case in manifest['cases']:
        cid = case['case_id']
        source = read(audit / cid / 'source.json')
        if digest(source['segments']) != case['source_hash'] or source['text_sha256'] != case['source_hash']:
            raise ValueError('Segmented source content differs from audit snapshot')
        if digest(source) != digest(read(case['source_path'])):
            raise ValueError('Source snapshot differs from original segmented source')
        raw = {side: read(audit / cid / (side + '-annotation.json')) for side in ['A', 'B']}
        check = validator.check(read(audit / cid / 'web-review-raw.json'), raw, source)
        if not check['valid']:
            raise ValueError(check['errors'])
        checks.append(dict(check, case_id=cid))
        for name in ['source.json', 'web-review-raw.json', 'local-adjudication.json'] + [
                side + suffix for side in ['A', 'B'] for suffix in ['-annotation.json', '-query-review.json', '-query-view.json']]:
            path = audit / cid / name
            value = read(path)
            write_new(out / 'inputs' / cid / name, value)
            inputs.append(path)
            file_checks.append({'path': str(path), 'byte_hash': digest(path.read_bytes()), 'object_hash': digest(value)})
        for side in ['A', 'B']:
            path = audit / cid / (side + '-annotation.json')
            if digest(path.read_bytes()) != case['annotation_raw_hashes'][side]:
                raise ValueError('Annotation changed')
            parent = Path(case['input_paths'][side])
            if digest(parent.read_bytes()) != case['annotation_raw_hashes'][side]:
                raise ValueError('Parent source annotation changed')
            review = read(audit / cid / (side + '-query-review.json'))
            if digest(projection_view(raw[side], review)) != digest(read(audit / cid / (side + '-query-view.json'))):
                raise ValueError('Side query view does not reproduce')
            cards = registry(raw[side], earlier_mapping['mappings'][side][cid], side)
            write_new(out / side / cid / 'registry.json', cards)
            corpus[side].append({'raw': raw[side], 'review': review, 'registry': cards})
    write_new(out / 'review-input-validation.json', checks)
    write_new(out / 'input-verification.json', file_checks)
    summary = {'state': 'SOURCE_REVIEW_INTEGRATED_DEVELOPMENT_ONLY', 'held_out': False,
               'real_accuracy': None, 'cases': 5, 'annotation_versions': 10,
               'reviewed_fact_procedure_records': sum(sum(v.values()) for row in checks for v in row['decision_counts'].values()),
               'review_quote_occurrences': sum(row['quote_occurrences_checked'] for row in checks), 'runs': {}}
    fixed_csv, pattern_csv = [], []
    for side in ['A', 'B']:
        all_views = {profile: [normalize_view(c['raw'], c['review'], c['registry'], profile)
                              for c in corpus[side]] for profile in config['profiles']}
        for profile in config['profiles']:
            views = all_views[profile]
            write_new(out / side / profile / 'views.json', views)
            discovery = [discovery_view(v) for v in views]
            write_new(out / side / profile / 'discovery-views.json', discovery)
            seeds = [seed_annotation(v) for v in discovery]
            candidates = generate_from_seeds(seeds)
            write_new(out / side / profile / 'candidates.json', candidates)
            print(side, profile, 'candidates', len(candidates), flush=True)
            proof = stage(side + '/' + profile + '/execution-oracle.json',
                          lambda: execution_check(discovery, candidates[:config['budget']]))
            if not proof['passed']:
                raise AssertionError('Independent executor disagreement')
            if profile != 'NATIVE':
                coverage = stage(side + '/' + profile + '/search-oracle.json',
                                 lambda: oracle.check([oracle_view(v) for v in discovery], candidates))
                if not coverage['exact']:
                    raise AssertionError('Finite candidate enumeration disagreement')
            else:
                coverage = {'exact': None, 'scope': 'Full native template enumeration not run'}
            mined = stage(side + '/' + profile + '/mining.json',
                          lambda: mine(discovery, config['budget'], config['min_support'], candidates=candidates))
            for pattern in mined['patterns']:
                expected = [oracle.answer(oracle_view(v), {k: val for k, val in pattern['query'].items() if k != 'mode'}) for v in discovery]
                if pattern['support'] != sum(r['status'] == 'MATCH' for r in expected) or pattern['unknown'] != sum(r['status'] == 'UNKNOWN' for r in expected):
                    raise AssertionError('Support or unknown count disagreement')
            repeats = [dict(p, diagnostic=pattern_info(p, discovery)) for p in mined['patterns'] if p['repeated']]
            write_new(out / side / profile / 'repeated-with-evidence.json', repeats)
            ranking = mined['patterns'][:20]
            remaining = mined['patterns'][20:]
            sample = random.Random(config['seed']).sample(remaining, min(10, len(remaining)))
            write_new(out / side / profile / 'pattern-review-selection.json',
                      {'selection': [{'id': p['id'], 'source': 'FIXED_RANK_TOP20', 'query': p['query']} for p in ranking] +
                       [{'id': p['id'], 'source': 'FIXED_SEED_RANDOM10_REMAINDER', 'query': p['query']} for p in sample],
                       'source_binding_checks': 'PASSED_INDEPENDENT_EXECUTION_CHECK',
                       'legal_usefulness_review': 'NOT_CLAIMED_FROM_PROGRAM_MATCHING', 'seed': config['seed']})
            for p in mined['patterns']:
                pattern_csv.append([side, profile, p['id'], p['support'], p['cooccurrence_support'], p['unknown'], p['repeated'], p['same_type_pair']])
            info = {'records_in_view': sum(len(v['events']) for v in views),
                    'accepted_records': sum(e['review_decision'] == 'ACCEPT' for v in views for e in v['events']),
                    'positive_seed_records': sum(len(s['events']) for s in seeds),
                    'generated': mined['generated'], 'executed': mined['executed'], 'search_complete': mined['search_complete'],
                    'remaining_candidates': len(mined['frontier']), 'repeated': len(repeats),
                    'repeated_same_type_record_pairs': sum(p['same_type_pair'] for p in repeats),
                    'repeated_court_only': sum(p['diagnostic']['court_only_joins'] for p in repeats),
                    'repeated_with_fact_witnesses': sum(bool(set(p['diagnostic']['witness_kind_composition']) & {'FACT_ONLY', 'MIXED'}) for p in repeats),
                    'cooccurrence_match_without_relation_match': sum(r['cooccurrence']['status'] == 'MATCH' and r['relation']['status'] != 'MATCH'
                                                                  for p in mined['patterns'] for r in p['results']),
                    'execution_oracle': proof, 'candidate_coverage_exact': coverage['exact'],
                    'templates_checked': coverage.get('templates_checked'),
                    'legal_state_records_excluded_from_discovery': sum(len(v['discovery_excluded_legal_states']) for v in discovery)}
            summary['runs'][side + '/' + profile] = info
            print(side, profile, info, flush=True)

        fixed = []
        for view in all_views['CORE']:
            independent = oracle_view(view)
            for item in queries:
                q = item['query']
                result, baseline, identity = execute(view, q), execute(view, dict(cooccurrence_query(q), mode='SCOPED_EXISTENTIAL')), execute(view, without_identity(q))
                truth = oracle.answer(independent, {k: v for k, v in q.items() if k != 'mode'})
                if result['status'] != truth['status']:
                    raise AssertionError('Fixed query oracle disagreement')
                old_rows = read(prior / side / 'core/fixed-queries.json')
                earlier = next(r['conditional'] for r in old_rows if r['case_id'] == view['case_id'] and r['query_id'] == item['id'])
                fixed.append({'case_id': view['case_id'], 'query_id': item['id'], 'meaning': item['meaning'], 'query': q,
                              'relation': result, 'cooccurrence': baseline, 'remove_identity_only': identity, 'oracle': truth,
                              'previous_assumed_accurate_status': earlier['status'],
                              'answer_boundary': 'Usable scoped records only; missing/unapproved fields not read; empty result is not absence'})
                fixed_csv.append([side, view['case_id'], item['id'], result['status'], baseline['status'], identity['status'], earlier['status']])
        write_new(out / side / 'fixed-queries.json', fixed)
        summary['runs'][side + '/CORE']['fixed_statuses'] = dict(Counter(r['relation']['status'] for r in fixed))
        summary['runs'][side + '/CORE']['previous_assumed_accurate_statuses'] = dict(Counter(r['previous_assumed_accurate_status'] for r in fixed))
        summary['runs'][side + '/CORE']['changed_after_source_review'] = sum(r['relation']['status'] != r['previous_assumed_accurate_status'] for r in fixed)
        # Same candidate pool isolates permission/record filtering, rather than
        # confusing fewer candidates with a search mechanism change.
        old_candidates = read(prior / side / 'core/candidates.json')
        current_candidates = read(out / side / 'CORE/candidates.json')
        pool = sorted(set(old_candidates) | set(current_candidates), key=candidate_order)
        pool_run = stage(side + '/CORE/prior-common-pool.json', lambda: mine(
            [discovery_view(v) for v in all_views['CORE']], candidates=pool))
        write_new(out / side / 'CORE/prior-common-pool-candidates.json', pool)
        summary['runs'][side + '/CORE']['prior_common_pool_size'] = len(pool)
        summary['runs'][side + '/CORE']['prior_common_pool_repeated'] = sum(p['repeated'] for p in pool_run['patterns'])
    for name, rows, header in [('fixed-query-statuses.csv', fixed_csv, ['side', 'case_id', 'query_id', 'relation', 'cooccurrence', 'without_identity', 'previous_assumed_accurate']),
                               ('pattern-summary.csv', pattern_csv, ['side', 'profile', 'pattern_id', 'support', 'cooccurrence_support', 'unknown_cases', 'repeated', 'same_type_record_pair'])]:
        path = out / name
        if not path.exists():
            with path.open('x', newline='') as handle:
                writer = csv.writer(handle); writer.writerow(header); writer.writerows(rows)
    write_new(out / 'summary.json', summary)
    if not (out / 'runtime.json').exists():
        write_new(out / 'runtime.json', {'seconds': time.monotonic() - started, 'python': platform.python_version(), 'web_tasks': 0, 'paid_API_calls': 0})
    for item in file_checks:
        if digest(Path(item['path']).read_bytes()) != item['byte_hash']:
            raise AssertionError('Side audit input mutated')
    write_new(out / 'checkpoint.json', {'state': 'COMPLETE', 'config_hash': digest(config), 'summary_hash': digest(summary)})
    log_run(out, 'reviewed-development', inputs + code, [out / 'summary.json', out / 'checkpoint.json'])


if __name__ == '__main__':
    main()
