"""Optional absence, required absence, and wrong nonempty identities are distinct."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tests.test_pipeline_diagnostic_v19_8 import pair, part
from tests.test_evidence_binding_v20_5 import reviews
from legal_bench.proof_carrying import evidence_binding_gate_v20_5 as previous
from legal_bench.proof_carrying import evidence_binding_gate_v20_5_1 as gate
from legal_bench.proof_carrying import local_pipeline_v19_8 as core
from legal_bench.proof_carrying import shared_sources_v20_3 as shared
from legal_bench.proof_carrying.rule_contracts_v19_7 import digest


def optional_fixture(nonempty=False):
    case, rules, raw = pair()
    for premise in rules[0]['premises']:
        pid = premise['id']
        premise['variables']['optional_document'] = 'DOCUMENT'
        premise['input_contract']['role_types']['optional_document'] = 'DOCUMENT'
        premise['input_contract']['optional_roles'] = ['optional_document']
        rules[0]['slot_variables'][pid]['optional_document'] = 'R1::optional_document'
        unit = raw['analyses'][pid]
        if nonempty:
            unit['objects'].append({'label': 'Synthetic optional document', 'type': 'DOCUMENT',
                'refs': ['SRC:1'], 'identity_basis': 'Synthetic only.'})
        for collection in ('uses', 'judgments'):
            for row in unit[collection]:
                row['role_objects']['optional_document'] = 'OBJ:2' if nonempty else 'UNMAPPED'
    return case, rules, raw, core.schema(rules, case), shared.pack(raw)


class OptionalBindings(unittest.TestCase):
    def test_optional_absence_does_not_establish_an_identity_or_change_payload(self):
        c, r, raw, schema, compact = optional_fixture()
        before = copy.deepcopy(compact)
        rv = reviews(raw, c, r)
        self.assertEqual(previous.audit(compact, schema, c, r, rv)['pending_bindings'], 4)
        checked = gate.audit(compact, schema, c, r, rv)
        self.assertEqual(checked['status'], 'READY_FOR_CONDITIONAL_PROCESSING')
        self.assertEqual(checked['binding_state_counts']['OPTIONAL_UNMAPPED_PRESERVED'], 4)
        self.assertFalse(checked['optional_absence_is_source_review'])
        self.assertEqual(compact, before)

    def test_optional_absence_reaches_original_conversion_merge_and_checker(self):
        c, r, raw, schema, compact = optional_fixture()
        result = gate.process_saved(c, r, part(c, r), compact, schema, reviews=reviews(raw, c, r))
        entry = result['original_entry']
        self.assertEqual(result['formal_answer'], raw)
        for key in ('independent_import', 'independent_merge', 'independent_check'):
            self.assertEqual(entry[key]['status'], 'OK')
        self.assertFalse(result['semantic_approval'])

    def test_required_unknown_is_still_blocked(self):
        c, r, raw, schema, compact = optional_fixture()
        for unit in raw['analyses'].values():
            for collection in ('uses', 'judgments'):
                for row in unit[collection]: row['role_objects']['tenant'] = 'UNMAPPED'
        compact = shared.pack(raw)
        with patch('scripts.proof_pipeline_contract_v19_8.process_saved') as original:
            result = gate.process_saved(c, r, part(c, r), compact, schema, reviews=reviews(raw, c, r))
        self.assertEqual(result['contract_status'], 'BINDING_REVIEW_PENDING')
        self.assertIsNone(result['formal_answer'])
        original.assert_not_called()

    def test_wrong_nonempty_optional_identity_is_still_rejected(self):
        c, r, raw, schema, compact = optional_fixture(nonempty=True)
        rv = reviews(raw, c, r)
        for row in rv['verdicts']:
            if row['path'][-1] == 'optional_document': row['label'] = 'UNSUPPORTED'
        checked = gate.audit(compact, schema, c, r, rv)
        self.assertEqual(checked['status'], 'BINDING_REVIEW_REJECTED')
        self.assertEqual(checked['rejected_bindings'], 4)

    def test_unreviewed_nonempty_optional_identity_is_still_pending(self):
        c, r, raw, schema, compact = optional_fixture(nonempty=True)
        rv = reviews(raw, c, r)
        rv['verdicts'] = [row for row in rv['verdicts'] if row['path'][-1] != 'optional_document']
        checked = gate.audit(compact, schema, c, r, rv)
        self.assertEqual(checked['status'], 'BINDING_REVIEW_PENDING')
        self.assertEqual(checked['pending_bindings'], 4)

    def test_overlapping_required_optional_role_does_not_weaken_requiredness(self):
        c, r, raw, schema, compact = optional_fixture()
        for p in r[0]['premises']:
            p['input_contract']['required_roles'].append('optional_document')
        checked = gate.audit(compact, schema, c, r, reviews(raw, c, r))
        self.assertEqual(checked['status'], 'BINDING_REVIEW_PENDING')
        self.assertNotIn('OPTIONAL_UNMAPPED_PRESERVED', checked['binding_state_counts'])

    def test_bad_reference_is_not_excused_by_optionalness(self):
        c, r, raw, schema, compact = optional_fixture(nonempty=True)
        raw['analyses']['R1.P1']['uses'][0]['role_objects']['optional_document'] = 'OBJ:999'
        checked = gate.audit(shared.pack(raw), schema, c, r)
        self.assertEqual(checked['status'], 'REJECTED_EVIDENCE_OR_BINDING')
        self.assertTrue(any(row['kind'] == 'INVALID_LOCAL_REFERENCE' for row in checked['errors']))

    def test_failed_saved_generation_remains_null_and_raw_bytes_preserved(self):
        c, r, raw, schema, compact = optional_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); source = folder/'generation'; source.mkdir()
            (source/'run.json').write_text(json.dumps({'run_status': 'OUTPUT_TRUNCATED'}))
            (source/'raw-response.txt').write_text('incomplete saved output')
            result = gate.accept_saved(source, folder/'acceptance', c, r, part(c, r), schema)
            self.assertIsNone(result['formal_answer'])
            self.assertEqual(result['contract_status'], 'GENERATION_FAILED')
            self.assertEqual((source/'raw-response.txt').read_text(), 'incomplete saved output')


if __name__ == '__main__': unittest.main()
