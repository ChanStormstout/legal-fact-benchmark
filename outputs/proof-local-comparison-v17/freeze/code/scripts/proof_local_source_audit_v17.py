#!/usr/bin/env python3
"""Offline address/visibility audit; never changes proposals or inference.

This implements the frozen evaluation contract's citation-address check. It
also records whether offline annotation witnesses were in the cached learner
source view. An address existing or being encoded is not semantic acceptance.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.proof_local_comparison_v17 import OUT, DEV, CONDITIONS, fixture, read, save, assert_frozen


def main():
    protocol = assert_frozen()
    citation_rows, visibility = [], []
    for cid in protocol['TRAIN'] + list(DEV):
        f = fixture(cid)
        sources = {s['id'] for s in f['case']['segments']}
        rules = {r['id'] for r in f['rules']}
        material_file = OUT / 'inputs' / cid / 'learner-inputs.json'
        label_file = OUT / 'web' / 'labels' / cid / 'parsed.json'
        if material_file.exists():
            data = read(material_file)
            common = {s['id'] for m in data['materials'].values() for s in m['segments']}
            pp = read(OUT / 'local' / cid / 'P' / 'parsed.json')
            labels = read(label_file)['connections'] if label_file.exists() else []
            for i, conn in enumerate(pp['connections'], 1):
                key = 'K%02d' % i
                direct = {s['id'] for s in data['materials'][key]['segments']}
                object_refs = {ref for obj in conn['objects'] for ref in obj['refs']}
                annotation = [v for v in labels if v['connection_id'] == key]
                label_refs = set(annotation[0].get('refs', [])) if len(annotation) == 1 else set()
                visibility.append({
                    'case_id': cid, 'connection_id': key,
                    'object_source_refs_not_in_common_restored_view': sorted(object_refs - common),
                    'annotation_refs_not_in_direct_restored_view': sorted(label_refs - direct),
                    'annotation_refs_not_in_common_restored_view': sorted(label_refs - common),
                    'saved_source_scope': 'CITED_RECORDS_AND_WITNESSES_PLUS_FIXED_NEIGHBOURS',
                    'shared_case_view_identical_for_three_learners': True,
                    'source_address_validity_not_semantic_approval': True,
                    'no_reference_content_added_to_features': True,
                })
        if cid not in DEV:
            continue
        for condition in CONDITIONS:
            path = OUT / 'local' / cid / condition / 'formal-answer.json'
            if not path.exists():
                continue
            wrapper = read(path)
            answer = wrapper['answer']
            if answer is None:
                citation_rows.append({'case_id': cid, 'condition': condition,
                                      'technical_status': wrapper['status'], 'citation_audit': None})
                continue
            for i, g in enumerate(answer['grounds'], 1):
                citation_rows.append({'case_id': cid, 'condition': condition, 'address': 'grounds[%d]' % i,
                    'unknown_case_refs': sorted(set(g['case_refs']) - sources),
                    'unknown_rule_or_source_refs': sorted(set(g['rule_refs']) - rules - sources),
                    'rule_refs_address_kind': {ref: 'GIVEN_RULE' if ref in rules else 'SOURCE_LOCATION' if ref in sources else 'UNKNOWN' for ref in g['rule_refs']},
                    'source_role': 'CASE_SOURCE_OR_GIVEN_RULE_ID_ONLY', 'semantic_support_checked': False})
            for name in ('counterarguments', 'connection_handling'):
                for i, g in enumerate(answer[name], 1):
                    citation_rows.append({'case_id': cid, 'condition': condition,
                        'address': '%s[%d]' % (name, i),
                        'unknown_refs': sorted(set(g['refs']) - sources - rules),
                        'semantic_support_checked': False})
    save(OUT / 'final-citation-address-audit.json', citation_rows)
    save(OUT / 'learner-source-visibility-audit.json', visibility)
    print(json.dumps({'final_address_records': len(citation_rows), 'connection_visibility_records': len(visibility),
                      'answers_or_labels_modified': False}))


if __name__ == '__main__':
    main()
