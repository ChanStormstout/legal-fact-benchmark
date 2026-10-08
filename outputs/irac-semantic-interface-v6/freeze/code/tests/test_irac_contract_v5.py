import copy
import json
import tempfile
import unittest
from pathlib import Path

from tests.test_irac_hybrid_v3 import fixture
from legal_bench.irac_application.contract_v5 import (
    address_directory, encode_address, decode_address, display, compact, expand_compact)
from legal_bench.irac_application.contract_v5_tasks import schema, prompt
from legal_bench.rules_verdict_v1.contracts import validate
from scripts import irac_contract_v5 as entry


class ContractV5Tests(unittest.TestCase):
    def accept(self, p, t, sources, cid='c'):
        """All semantic-state tests traverse the actual file completion entry."""
        m = {'case_id': cid, 'sources': sources}
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            raw = json.dumps(p, ensure_ascii=False)
            (out / 'raw-response.txt').write_text(raw)
            result = entry.finish_attempt({'run_status': 'OK', 'offline_replay': True}, out, 'P', m, t, [], allow_legacy=True)
            self.assertEqual(result['run_status'], 'OK')
            self.assertEqual((out / 'raw-response.txt').read_text(), raw)
            return entry.read(out / 'import.json'), entry.read(out / 'checks-full.json'), entry.read(out / 'checks-compact.json')

    def single(self):
        p, t, s = fixture()
        p['evidence'] = p['evidence'][:1]
        return p, t, s

    def test_optional_summary_absent_does_not_hide_evidence(self):
        p, t, s = self.single()
        p['limitations'] = []
        i, c, v = self.accept(p, t, s)
        row = c['conditions'][0]
        self.assertEqual(row['model_assessments'], [])
        self.assertEqual(row['program_assessment']['status'], 'SUPPORTED')
        self.assertEqual(row['evidence_use_summary']['support'], ['e1'])
        self.assertFalse(i['condition_summary_required'])
        self.assertEqual(i['status'], 'OK')
        self.assertNotIn('MISSING_DECLARED_USABLE_EVIDENCE', json.dumps(v))

    def test_summary_without_evidence_not_promoted_to_support(self):
        p, t, s = self.single()
        p['evidence'] = []
        p['limitations'] = []
        p['conditions'] = [{'binding_id': 'b', 'test_id': 'T', 'branch_id': '', 'assessment': 'SUPPORTED', 'evidence_ids': [], 'gap': ''}]
        i, c, v = self.accept(p, t, s)
        row = c['conditions'][0]
        self.assertEqual(row['model_assessments'][0]['assessment'], 'SUPPORTED')
        self.assertEqual(row['program_assessment']['status'], 'UNRESOLVED')
        self.assertEqual(row['evidence_use_summary']['condition_connections'], 0)
        self.assertIn('current proposal', row['connection_coverage_note'])

    def test_real_553_all_representation_layers(self):
        m, t, law, sm = entry.inputs('55384096')
        sources = dict(m['sources'], **{x['source_id']: x for x in law})
        p = json.loads((entry.V4 / 'runs/55384096/P/raw-response.txt').read_text())
        i, c, v = self.accept(p, t, sources, '55384096')
        row = next(x for x in c['conditions'] if x['binding_id'] == 'b2' and x['test_id'] == 'DRC_SUBLETTING_C06')
        self.assertEqual(row['program_assessment']['supports'], ['e3', 'e4', 'e5'])
        self.assertEqual(row['program_assessment']['status'], 'SUPPORTED')
        self.assertEqual(row['model_output_status'], 'NOT_PRODUCED_OPTIONAL')
        text, _, intermediate = entry.final_task('55384096', 'C', p, i, c)
        self.assertIn(json.dumps(intermediate, ensure_ascii=False), text)
        self.assertNotIn('MISSING_DECLARED_USABLE_EVIDENCE', text)
        restored = expand_compact(v)
        self.assertEqual(restored['conditions'], c['conditions'])
        self.assertEqual(p, intermediate['proposal'])

    def test_specific_limit_does_not_block_independent_witness(self):
        p, t, s = fixture()
        p['evidence'][1]['uses'][0]['direction'] = 'SUPPORT'
        p['limitations'][0]['refs'] = ['bad-source']
        i, c, _ = self.accept(p, t, s)
        self.assertEqual(c['conditions'][0]['program_assessment']['supports'], ['e2'])
        self.assertEqual(c['conditions'][0]['program_assessment']['pending_uses'], ['e1'])
        self.assertEqual(c['conditions'][0]['program_assessment']['status'], 'SUPPORTED')

    def test_whole_proposition_empty_ids_valid_and_invalid_source(self):
        for refs in (['s1'], ['MISSING']):
            with self.subTest(refs=refs):
                p, t, s = self.single()
                p['limitations'][0].update(evidence_ids=[], effect='PROPOSITION_BLOCK', refs=refs)
                i, c, _ = self.accept(p, t, s)
                self.assertEqual(c['conditions'][0]['program_assessment']['status'], 'UNRESOLVED')
                self.assertEqual(c['conditions'][0]['program_assessment']['pending_uses'], ['e1'])
                if refs == ['MISSING']:
                    self.assertEqual(c['evidence_use_checks'][0]['use_status'], 'UNRESOLVED_MAPPING')
                    self.assertEqual(i['safeguards'][0]['scope'], 'WHOLE_PROPOSITION')
                    self.assertEqual(i['safeguards'][0]['evidence_ids'], [])

    def test_whole_proposition_bad_structure_keeps_known_scope(self):
        p, t, s = self.single()
        p['limitations'][0].update(evidence_ids=[], effect='PROPOSITION_BLOCK', reason=None)
        i, c, _ = self.accept(p, t, s)
        self.assertEqual(c['conditions'][0]['program_assessment']['status'], 'UNRESOLVED')
        self.assertEqual(c['evidence_use_checks'][0]['mapping_questions'], ['IMPORT-PENDING-0'])

    def test_limit_on_other_binding_does_not_propagate(self):
        p, t, s = fixture()
        p['bindings'].append(dict(p['bindings'][0], id='b2', event='another arrangement'))
        p['evidence'][1].update(binding_id='b2')
        p['evidence'][1]['uses'][0]['direction'] = 'SUPPORT'
        p['limitations'][0].update(evidence_ids=[], effect='PROPOSITION_BLOCK', refs=['bad'])
        i, c, _ = self.accept(p, t, s)
        states = {x['binding_id']: x['program_assessment']['status'] for x in c['conditions']}
        self.assertEqual(states, {'b': 'UNRESOLVED', 'b2': 'SUPPORTED'})

    def test_purpose_local_limit_does_not_block_inference(self):
        p, t, s = self.single()
        p['limitations'][0].update(evidence_ids=[], effect='PROPOSITION_BLOCK', refs=['bad'], use='TARGET_ACCEPTANCE')
        i, c, _ = self.accept(p, t, s)
        self.assertEqual(c['conditions'][0]['program_assessment']['status'], 'SUPPORTED')
        self.assertEqual(c['check_coverage'], 'INCOMPLETE_RESTRICTION_VALIDATION')
        self.assertEqual(len(c['unapplied_limits']), 1)

    def test_or_independent_branch_still_establishes_test(self):
        p, t, s = self.single()
        refs = [{'source_id': 'law', 'quote': 'A'}]
        t['tests'][0].update(branches=[{'id': 'T/A'}, {'id': 'T/B'}],
            branch_expression={'op': 'OR', 'args': [{'op': 'REF', 'id': b, 'source_refs': refs} for b in ('T/A', 'T/B')], 'source_refs': refs})
        p['evidence'][0]['uses'][0]['branch_id'] = 'T/A'
        other = copy.deepcopy(p['evidence'][0]); other['id'] = 'e2'; other['uses'][0]['branch_id'] = 'T/B'
        p['evidence'].append(other)
        p['limitations'][0].update(branch_id='T/A', effect='PROPOSITION_BLOCK', evidence_ids=[], refs=['bad'])
        i, c, _ = self.accept(p, t, s)
        self.assertEqual(c['conditions'][0]['branches']['T/A']['status'], 'UNRESOLVED')
        self.assertEqual(c['conditions'][0]['branches']['T/B']['status'], 'SUPPORTED')
        self.assertEqual(c['conditions'][0]['program_assessment']['status'], 'SUPPORTED')

    def test_unmapped_limit_preserved_without_arbitrary_global_block(self):
        p, t, s = self.single()
        p['limitations'][0].update(test_id='UNKNOWN', refs=['bad'])
        i, c, v = self.accept(p, t, s)
        self.assertEqual(c['conditions'][0]['program_assessment']['status'], 'SUPPORTED')
        self.assertEqual(c['restriction_coverage'][0]['status'], 'UNMAPPED_RESTRICTION')
        self.assertEqual(expand_compact(v)['check_coverage'], 'INCOMPLETE_RESTRICTION_VALIDATION')
        self.assertEqual(i['safeguards'], [])

    def test_invalid_evidence_scope_does_not_expand_to_all(self):
        p, t, s = self.single()
        p['limitations'][0].update(evidence_ids=None, refs=['bad'])
        i, c, v = self.accept(p, t, s)
        self.assertEqual(c['conditions'][0]['program_assessment']['status'], 'SUPPORTED')
        self.assertEqual(c['restriction_coverage'][0]['scope'], 'UNDETERMINED')
        self.assertEqual(expand_compact(v)['restriction_coverage'], c['restriction_coverage'])

    def test_support_opposition_pending_all_survive_no_vote(self):
        p, t, s = fixture()
        p['limitations'][0]['refs'] = ['bad']
        for n in range(3, 6):
            p['evidence'].append(dict(copy.deepcopy(p['evidence'][0]), id='e%d' % n))
        i, c, v = self.accept(p, t, s)
        row = c['conditions'][0]['program_assessment']
        self.assertEqual(row['status'], 'UNRESOLVED')
        self.assertTrue(row['conflict'])
        self.assertEqual(row['supports'], ['e3', 'e4', 'e5'])
        self.assertEqual(row['opposes'], ['e2'])
        self.assertEqual(row['pending_uses'], ['e1'])
        self.assertEqual(expand_compact(v)['conditions'], c['conditions'])

    def test_all_addresses_roundtrip_schema_import_execution_display(self):
        for cid in ('112400', '188721101'):
            m, t, law, sm = entry.inputs(cid)
            d = address_directory(t)
            sc = schema('proposal', m, t, law)
            choices = sc['properties']['evidence']['items']['properties']['uses']['items']['properties']
            self.assertEqual(set(choices), {'condition_address', 'direction', 'use'})
            self.assertEqual(choices['condition_address']['enum'], list(d))
            self.assertIn(json.dumps(d, ensure_ascii=False), prompt('proposal', m, t, law, sm))
            for key, pair in d.items():
                self.assertEqual(encode_address(pair['test_id'], pair['branch_id'], d), key)
                p, _, _ = self.single()
                sid = next(iter(m['sources']))
                p['bindings'][0].update(refs=[sid], claim_ids=[t['claims'][0]['id']])
                p['evidence'][0]['refs'] = [sid]
                p['evidence'][0]['uses'] = [{'condition_address': key, 'direction': 'SUPPORT', 'use': 'CONDITION_INFERENCE'}]
                p['limitations'] = []
                validate(p, sc)
                i, c, _ = self.accept(p, t, m['sources'], cid)
                self.assertEqual(c['evidence_use_checks'][0]['condition_address'], key)
                self.assertEqual(c['evidence_use_checks'][0]['test_id'], pair['test_id'])
                self.assertEqual(c['evidence_use_checks'][0]['branch_id'], pair['branch_id'])

    def test_illegal_old_pair_and_element_not_guessed(self):
        m, t, law, sm = entry.inputs('112400')
        d = address_directory(t)
        self.assertIsNone(decode_address({'test_id': 'DRC_BONA_FIDE-C04', 'branch_id': 'DRC_BONA_FIDE-C03/SELF'}, d))
        for element in t['elements']:
            self.assertIsNone(decode_address({'condition_address': element['id']}, d))
        old = json.loads((Path('outputs/irac-hybrid-decision-v3') / 'runs/188721101/proposal/raw-response.txt').read_text())
        m, t, law, sm = entry.inputs('188721101')
        i, c, _ = self.accept(old, t, m['sources'], '188721101')
        self.assertEqual(len(i['projection']['evidence']), 4)
        self.assertEqual(sum(len(x['uses']) for x in i['projection']['evidence']), 0)
        self.assertEqual(sum(x['kind'] == 'use' for x in i['quarantine']), 10)

    def test_sources_sorted_by_original_position_and_reversible(self):
        for cid in entry.AUDIT_CASES:
            m, t, law, sm = entry.inputs(cid)
            before = copy.deepcopy(m)
            view, aliases, order = display(m, sm)
            self.assertEqual(m, before)
            by = {x['source_id']: x for x in view['records']}
            positions = {x['source_id']: x['raw_char_range'][0] for x in order['rows']}
            sequence = [positions[x['source_id']] for x in view['records']]
            self.assertEqual(sequence, sorted(sequence))
            for sid, a in aliases.items():
                self.assertEqual(by[a['display_id']]['text'][slice(*a['char_range'])], m['sources'][sid]['text'])
            self.assertEqual(len(aliases), len(m['sources']))
            for stage in ('proposal', 'final'):
                text = prompt(stage, m, t, law, sm)
                self.assertEqual([text.index(json.dumps(row['text'], ensure_ascii=False)) for row in view['records']],
                                 sorted(text.index(json.dumps(row['text'], ensure_ascii=False)) for row in view['records']))

    def test_truncation_and_format_failure_null_raw_unchanged(self):
        m, t, law, sm = entry.inputs('112400')
        for status in ('OUTPUT_TRUNCATED', 'REPETITION_ABORT', 'FORMAT_ERROR'):
            with tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp); (p / 'raw-response.txt').write_text('{bad')
                result = entry.finish_attempt({'run_status': status}, p, 'P', m, t, law)
                self.assertIsNone(result['prediction'])
                self.assertEqual(result['run_status'], status)
                self.assertEqual((p / 'raw-response.txt').read_text(), '{bad')


if __name__ == '__main__':
    unittest.main()
