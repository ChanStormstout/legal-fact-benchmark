"""Read-only consolidated development audit; no semantic relabeling or merges."""
import argparse
import itertools
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.annotation_v2 import validate
from legal_bench.core import digest, read, write_new, canonical
from legal_bench.reconcile import alignment


def evidence_objects(value):
    if isinstance(value, dict):
        if 'segment_id' in value and 'quote' in value:
            yield value
        for child in value.values():
            yield from evidence_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from evidence_objects(child)


def latest_path(root, case, side):
    if case == '1064407':
        return Path('outputs/benchmark-pilot-v02/downloads') / (side + '-semantic-1') / 'annotation.json'
    base = root / 'downloads' / case / side
    # Complete downloads, not submission state, establish an available version.
    for version in ['repair2', 'repair1', '']:
        candidate = base / version / 'annotation.json'
        if candidate.exists() and (candidate.parent / 'review_notes.json').exists():
            return candidate
    raise ValueError('No complete downloaded pair: %s/%s' % (case, side))


def audit(root):
    catalog = read(root / 'development-source-catalog-v1.json')
    rows, comparisons, definitions = [], [], defaultdict(list)
    for entry in catalog['cases']:
        case, source = entry['case_id'], read(entry['source_path'])
        source_valid = digest(source['segments']) == entry['source_text_sha256'] == source['text_sha256']
        versions = {}
        for side in ['A', 'B']:
            path = latest_path(root, case, side)
            annotation, notes = read(path), read(path.parent / 'review_notes.json')
            versions[side] = annotation
            checks = validate(annotation, notes, source)
            assertions = annotation['assertions']
            review_flags = []
            for a in assertions:
                if a['kind'] == 'FACT' and a['deciding_court_treatment']['value'] == 'ADOPTED':
                    if a['origin']['mode'] in ['ALLEGED', 'TESTIFIED']:
                        review_flags.append({'id': a['id'], 'type': 'VERIFY_CURRENT_ADOPTION_OF_ATTRIBUTED_FACT',
                                             'evidence': a['evidence'],
                                             'treatment_evidence': a['deciding_court_treatment']['evidence']})
            # This is only a diagnostic for identical representations; it does not
            # search different predicates, partial temporal overlap, or synonyms.
            groups = defaultdict(list)
            for a in assertions:
                if a['kind'] == 'FACT' and a['deciding_court_treatment']['value'] == 'ADOPTED':
                    key = canonical({k: a[k] for k in ['predicate', 'roles', 'attributes', 'scope', 'time']})
                    groups[key].append(a)
            for group in groups.values():
                if len({a['polarity'] for a in group}) > 1:
                    review_flags.append({'type': 'CHECK_OPPOSITE_ADOPTED_PROPOSITIONS',
                                         'ids': [a['id'] for a in group],
                                         'identity_known': all(v is not None for v in group[0]['roles'].values())})
            blockers = [e for e in checks['errors'] if e['code'] != 'conflict_scope_unestablished']
            relation_boundaries = [e for e in checks['errors'] if e['code'] == 'conflict_scope_unestablished']
            qualified = [a['id'] for a in assertions if a['kind'] in ['FACT', 'PROCEDURAL_ACT']
                         and a['deciding_court_treatment']['value'] == 'ADOPTED'
                         and (a['scope'] or a['unresolved'] or any(v is None for v in a['roles'].values()))]
            coverage_attention = [c for c in notes['coverage'] if not c['assertion_ids']
                                  and c['category'] in ['FACT', 'MIXED', 'UNRESOLVED']]
            row = {'case_id': case, 'pass': side, 'path': str(path),
                   'annotation_hash': digest(annotation), 'notes_hash': digest(notes),
                   'source_hash_valid': source_valid, 'structurally_valid': checks['valid'],
                   'assertions': len(assertions), 'source_segments': len(source['segments']),
                   'coverage_entries': len(notes['coverage']),
                   'evidence_reference_occurrences': len(list(evidence_objects(annotation))),
                   'structural_blockers': blockers, 'relation_scope_boundaries': relation_boundaries,
                   'warning_counts': dict(Counter(x['code'] for x in checks['warnings'])),
                   'source_review_flags': review_flags,
                   'qualified_adopted_assertions_requiring_use_review': qualified,
                   'empty_coverage_entries_for_omission_review': coverage_attention,
                   'eligibility_model_label': annotation['eligible'],
                   'primary_units': [u for u in annotation['units'] if u['primary']],
                   'semantic_acceptance': 'NOT_ESTABLISHED_BY_THIS_AUDIT'}
            rows.append(row)
            for d in annotation['predicate_definitions']:
                definitions[d['id']].append({'case_id': case, 'pass': side,
                                              'meaning': d['meaning'], 'roles': d['roles']})
        result = alignment(versions['A'], versions['B'])
        comparisons.append({'case_id': case, 'candidate_count': len(result['candidates']),
                            'without_overlapping_evidence': result['without_overlapping_evidence'],
                            'input_hashes': result['input_hashes'],
                            'candidates': result['candidates'],
                            'meaning': 'Candidates for review, not known disagreements or omissions'})
    role_variants = [{'predicate': name, 'definitions': ds}
                     for name, ds in sorted(definitions.items())
                     if len({canonical(d['roles']) for d in ds}) > 1]
    role_name_variants = [{'predicate': name, 'definitions': ds}
                          for name, ds in sorted(definitions.items())
                          if len({canonical(sorted(d['roles'])) for d in ds}) > 1]
    source_pairs = []
    for a, b in itertools.combinations(catalog['cases'], 2):
        source_pairs.append({'cases': [a['case_id'], b['case_id']],
                             'same_source_hash': a['source_text_sha256'] == b['source_text_sha256'],
                             'same_dispute': 'NOT_ESTABLISHED_BY_DIFFERENT_HASHES'})
    return {'audit_version': 'consolidated-dev-v2',
            'script_hash': digest(Path(__file__).read_bytes()), 'automatic_changes': 0,
            'frozen_check_set_used': False, 'rows': rows, 'a_b_alignment': comparisons,
            'role_description_or_name_variants': role_variants,
            'role_name_set_variants': role_name_variants,
            'role_variant_interpretation': 'Diagnostic only: wording variants do not establish semantic incompatibility',
            'source_pair_checks': source_pairs,
            'summary': {'case_candidates': len(catalog['cases']), 'annotation_versions': len(rows),
                        'structurally_valid': sum(r['structurally_valid'] for r in rows),
                        'structural_blockers': sum(len(r['structural_blockers']) for r in rows),
                        'relation_scope_boundaries': sum(len(r['relation_scope_boundaries']) for r in rows),
                        'source_hashes_valid': all(r['source_hash_valid'] for r in rows)},
            'limits': ['Quote location is not semantic entailment',
                       'A/B differences and warning counts are not error counts',
                       'Missing overlap is not proven omission',
                       'No claims of comprehensive gold labels, accuracy, or cross-case semantic equivalence',
                       'Qualified facts need explicit use review before execution']}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', default='outputs/benchmark-pilot-v03')
    p.add_argument('--out', required=True)
    args = p.parse_args()
    result = audit(Path(args.root))
    write_new(args.out, result)
    print(json.dumps(result['summary'], indent=2))


if __name__ == '__main__':
    main()
