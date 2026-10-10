"""Guide 4.0 teaching fixtures, not annotations of an Indian judgment.

The exercise supplies accepted synthetic inputs. EXERCISE_SUPPLIED is explicitly
not a human review or qualified legal approval, including the correction.
"""
import copy
from pathlib import Path

from .contracts import byte_hash, content_hash, subject_hash, write_once


SCOPE = {'jurisdiction': 'DEMO', 'issue_id': 'ENTRY_AUTHORIZATION', 'stage_id': 'TEACHING',
         'valid_from': '2026-10-01', 'valid_to': '2026-10-31'}


def review(record, reviews, role):
    rid = 'REVIEW-' + record['id']
    record['review_id'] = rid
    reviews[rid] = {'id': rid, 'subject_sha256': subject_hash(record), 'decision': 'EXERCISE_SUPPLIED',
                    'reviewer_role': role, 'basis': 'SYNTHETIC_EXERCISE', 'human_legal_approval': False,
                    'rationale': 'Stipulated teaching input; no person has been represented as approving it.'}


def source(root, snapshot, did, text, ref):
    path = Path(root) / 'documents' / (did + '.txt')
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    path.write_text(text)
    snapshot['documents'][did] = {'case_id': 'DEMO_PERMISSION', 'path': 'documents/' + path.name,
                                  'sha256': byte_hash(path), 'kind': 'SYNTHETIC_TEACHING_SOURCE'}
    snapshot['sources'][ref] = {'document_id': did, 'case_id': 'DEMO_PERMISSION', 'start': 0,
        'end': len(text.rstrip('\n')), 'line': 1, 'exact_text': text.rstrip('\n'),
        'availability': 'SYNTHETIC_ORIGINAL_AVAILABLE', 'original_legal_exhibit_available': False}


def proposition(pid, predicate, refs, assessment='TRUE', **fields):
    return dict(id=pid, case_id='DEMO_PERMISSION', stage_id='TEACHING', predicate=predicate,
                bindings={'person': 'Person_A', 'property': 'Parcel_P'},
                statement_status='EXERCISE_STIPULATION', party_stance=None, court_assessment=None,
                claim_disposition=None, assessment=assessment, source_refs=refs, **fields)


def build(root):
    """Create S1 and an additive S2; never change the Monday record."""
    root = Path(root)
    policy = {'id': 'TEACHING_PREMISE_POLICY@1', 'mode': 'TEACHING',
              'accepted_statement_statuses': ['EXERCISE_STIPULATION'],
              'accepted_review_roles': {'premise': ['EXERCISE_FIXTURE'], 'rule': ['DEMO_RULE_FIXTURE']},
              'legal_approval_status': 'NOT_OBTAINED', 'default_from_missing': 'UNKNOWN',
              'source_check_scope': 'Byte/locator checks plus stipulated exercise review, not semantic entailment.'}
    registry = {'id': 'TEACHING_RULE_REGISTRY@1', 'rules': {}, 'reviews': {}, 'production_approved_rules': []}
    rule = {'id': 'COVERAGE_DEMO@1', 'version': 1, 'status': 'DEMO_ONLY', 'scope': SCOPE,
            'kind': 'PERMISSION_COVERAGE', 'conclusion': 'SPECIFIC_AUTHORIZATION_COVERS_ENTRY',
            'inputs': [{'role': 'authorization', 'predicate': 'AUTHORIZATION'}, {'role': 'entry', 'predicate': 'ENTRY'}],
            'logic': 'Same person AND same property AND event inside inclusive interval AND granted activity.',
            'burden_policy': 'NOT_APPLICABLE_NARROW_TEACHING_TEST',
            'exception_policy': 'NOT_APPLICABLE_NARROW_TEACHING_TEST',
            'authority_status': 'INSTRUCTIONAL_NOT_LEGAL_AUTHORITY', 'guide_pages': [5, 9, 10],
            'limits': ['Only this authorization/entry pair.', 'No inference of global absence or liability.']}
    review(rule, registry['reviews'], 'DEMO_RULE_FIXTURE'); registry['rules'][rule['id']] = rule
    for op in ('AND', 'OR'):
        r = {'id': op + '_GATE_DEMO@1', 'version': 1, 'status': 'DEMO_ONLY', 'scope': SCOPE,
             'kind': 'EXPRESSION', 'conclusion': 'DEMO_ISSUE_CONDITION_MET',
             'inputs': [{'role': 'left', 'predicate': 'TEST_ASSESSMENT'},
                        {'role': 'right', 'predicate': 'TEST_ASSESSMENT'},
                        {'role': 'exception', 'predicate': 'TEST_ASSESSMENT'}],
             'expression': {'op': 'AND', 'args': [{'op': op, 'args': [{'op': 'REF', 'role': 'left'}, {'op': 'REF', 'role': 'right'}]},
                                                  {'op': 'NOT', 'arg': {'op': 'REF', 'role': 'exception'}}]},
             'burden_policy': 'NOT_APPLICABLE_NARROW_TEACHING_TEST', 'exception_policy': 'EXPLICIT_INPUT',
             'authority_status': 'INSTRUCTIONAL_NOT_LEGAL_AUTHORITY', 'guide_pages': [19],
             'limits': ['Test fixture for a bounded expression, not a real possession rule.']}
        review(r, registry['reviews'], 'DEMO_RULE_FIXTURE'); registry['rules'][r['id']] = r
    snapshot = {'snapshot_id': 'S1', 'case_id': 'DEMO_PERMISSION', 'issue_id': 'ENTRY_AUTHORIZATION',
                'jurisdiction': 'DEMO', 'stage_id': 'TEACHING', 'as_of': '2026-10-13',
                'task_mode': 'SYNTHETIC_TEACHING', 'parent_snapshot_hash': None,
                'entities': {'Person_A': {'type': 'PERSON'}, 'Parcel_P': {'type': 'PROPERTY'},
                             'Parcel_Q': {'type': 'PROPERTY'}},
                'documents': {}, 'sources': {}, 'propositions': {}, 'reviews': {}}
    source(root, snapshot, 'E1', 'Synthetic message: Person_A may enter Parcel_P on Monday, 2026-10-12, for entry only.\n', 'demo_message_1')
    source(root, snapshot, 'E2', 'Synthetic entry record: Person_A entered Parcel_P on Tuesday, 2026-10-13.\n', 'demo_entry_record_2')
    p1 = proposition('P1', 'AUTHORIZATION', ['demo_message_1'], interval=['2026-10-12', '2026-10-12'], activity_scope=['entry'])
    p2 = proposition('P2', 'ENTRY', ['demo_entry_record_2'], event_time='2026-10-13', activity='entry')
    for p in (p1, p2):
        review(p, snapshot['reviews'], 'EXERCISE_FIXTURE'); snapshot['propositions'][p['id']] = p
    # Unknown query is separate from accepted premises; no source is invented.
    snapshot['unresolved_queries'] = [{'id': 'P3', 'predicate': 'AUTHORIZATION', 'assessment': 'UNKNOWN',
        'person': 'Person_A', 'property': 'Parcel_P', 'date': '2026-10-13',
        'reason': 'No accepted record supplied for this query; absence of all authorization not established.'}]
    s2 = copy.deepcopy(snapshot); s2['snapshot_id'] = 'S2'; s2['parent_snapshot_hash'] = content_hash(snapshot)
    source(root, s2, 'E3', 'Synthetic correction message: Person_A may also enter Parcel_P on Tuesday, 2026-10-13, for entry only.\n', 'demo_message_3')
    p4 = proposition('P4', 'AUTHORIZATION', ['demo_message_3'], interval=['2026-10-13', '2026-10-13'], activity_scope=['entry'])
    review(p4, s2['reviews'], 'EXERCISE_FIXTURE'); s2['propositions']['P4'] = p4
    s2['unresolved_queries'] = []
    for sid, data in (('S1', snapshot), ('S2', s2)):
        write_once(root / 'snapshots' / (sid + '.json'), data)
    write_once(root / 'rule-registry.json', registry)
    write_once(root / 'premise-policy.json', policy)
    manifest = {'snapshots': {}, 'registry': file_entry(root, 'rule-registry.json'), 'policy': file_entry(root, 'premise-policy.json')}
    for sid in ('S1', 'S2'):
        manifest['snapshots'][sid] = file_entry(root, 'snapshots/' + sid + '.json')
    write_once(root / 'trust-manifest.json', manifest)
    return snapshot, s2, registry, policy


def file_entry(root, path):
    return {'path': path, 'sha256': byte_hash(Path(root) / path)}


def validate_revision(parent, child, patch):
    """Bounded additive patch contract: cannot rewrite existing evidence/reviews."""
    if patch['parent'] != content_hash(parent) or patch['new_snapshot'] != content_hash(child):
        raise ValueError('PATCH_HASH_MISMATCH')
    if child['parent_snapshot_hash'] != content_hash(parent) or child['snapshot_id'] == parent['snapshot_id']:
        raise ValueError('PATCH_PARENT_OR_VERSION')
    if patch['review_status'] != 'EXERCISE_SUPPLIED' or patch['human_legal_approval'] is not False:
        raise ValueError('PATCH_DEMO_REVIEW_REQUIRED')
    for collection in ('documents', 'sources', 'propositions', 'reviews', 'entities'):
        if any(child[collection].get(k) != v for k, v in parent[collection].items()):
            raise ValueError('PATCH_REWRITES_EXISTING_' + collection.upper())
    for field in ('case_id', 'stage_id', 'issue_id', 'jurisdiction', 'as_of', 'task_mode'):
        if child[field] != parent[field]:
            raise ValueError('PATCH_SCOPE_CHANGE')
    added = set(child['propositions']) - set(parent['propositions'])
    if added != {patch['new_value']['id']} or child['propositions'][patch['new_value']['id']] != patch['new_value']:
        raise ValueError('PATCH_UNDECLARED_PROPOSITION_CHANGE')
    return {'status':'VALID_ADDITIVE_TEACHING_PATCH', 'preserved_premises':sorted(parent['propositions']),
            'added_premises':sorted(added), 'human_legal_approval':False}


def patch_record(s1, s2):
    return {'patch_id': 'PATCH-S1-S2', 'kind': 'ADD_SYNTHETIC_PREMISE', 'parent': content_hash(s1),
            'new_snapshot': content_hash(s2), 'old_value': None, 'new_value': s2['propositions']['P4'],
            'rationale': 'Add a separate Tuesday authorization; do not rewrite Monday.',
            'review_status': 'EXERCISE_SUPPLIED', 'human_legal_approval': False,
            'approval_missing_for_real_cases': True,
            'preserved_ids': ['P1', 'P2', 'demo_message_1', 'demo_entry_record_2'],
            'recompute': ['coverage(P4,P2)', 'Tuesday_authorization_query'],
            'historical_certificate_policy': 'C1 stays valid for S1; stale if presented as the current S2 result.'}


def graph(snapshot):
    nodes, edges = [], []
    for pid, p in snapshot['propositions'].items():
        nodes.append({'id': pid, 'type': 'PROPOSITION', 'assessment': p['assessment'], 'review_id': p['review_id']})
        for sid in p['source_refs']:
            nodes.append({'id': sid, 'type': 'SYNTHETIC_EVIDENCE'})
            edges.append({'id': sid + '--' + pid, 'source': sid, 'target': pid, 'type': 'SUPPORTS',
                          'sign': 'SUPPORT', 'weight': 1, 'source_refs': [sid],
                          'review_status': 'EXERCISE_SUPPLIED', 'legal_approved': False})
        pred = p['predicate']
        if not any(n['id'] == pred for n in nodes):
            nodes.append({'id': pred, 'type': 'CANONICAL_PREDICATE'})
        edges.append({'id': pid + '--' + pred, 'source': pid, 'target': pred, 'type': 'INSTANTIATES',
                      'source_refs': p['source_refs'], 'sign': None})
    nodes.append({'id': 'COVERAGE_DEMO@1', 'type': 'TEST_RULE'})
    for pred in ('AUTHORIZATION', 'ENTRY'):
        edges.append({'id': 'requires-' + pred, 'source': 'COVERAGE_DEMO@1', 'target': pred,
                      'type': 'REQUIRES', 'sign': None, 'source_refs': [], 'guide_page': 9,
                      'provenance_kind': 'INSTRUCTIONAL_RULE_DEPENDENCY'})
    return {'snapshot_id': snapshot['snapshot_id'], 'nodes': nodes, 'edges': edges,
            'note': 'No opposing party invented. Separate numeric fixtures illustrate conflict, not case evidence.'}
