import copy
import tempfile
import unittest
from pathlib import Path
from legal_bench.rules_verdict_v1.contracts import extraction_schema, validate
from legal_bench.rules_verdict_v1.source_views import build_view, windows, write_new
from legal_bench.rules_verdict_v1.extract import demonstration, import_records, field_value
from legal_bench.rules_verdict_v1.apply_rules import execute


def record(identifier, predicate, roles, unknown=None):
    return {'id': identifier, 'predicate': predicate, 'roles': roles,
            'status': 'COURT_FOUND', 'polarity': 'POSITIVE', 'context': 'MAIN_CASE',
            'stage': 'prior trial', 'time': None, 'attributes': [],
            'known': ['predicate', 'status', 'polarity', 'context', 'stage'] + ['roles.' + k for k in roles],
            'unknown': unknown or [], 'evidence': [{'segment_id': identifier, 'quote': 'fixture'}]}


def atom(identifier, predicate, roles):
    return {'op': 'atom', 'id': identifier, 'predicate': predicate, 'roles': roles, 'polarity': 'POSITIVE'}


class ContractsAndSources(unittest.TestCase):
    def test_example_is_complete_and_importable(self):
        source, output = demonstration()
        validate(output, extraction_schema(source))
        view = import_records(output, source, 'w1')
        self.assertFalse(view['quarantine'])
        self.assertEqual(view['records'][0]['roles']['payer'], 'w1:o1')

    def test_control_characters_and_quotes_preserved(self):
        source, output = demonstration()
        source['segments'][0]['text'] = 'A\n"quote"\x02 and café'
        view = import_records(output, source, 'w1')
        self.assertEqual(view['records'][0]['evidence'][0]['quote'], source['segments'][0]['text'])

    def test_local_error_isolated_and_raw_unchanged(self):
        source, output = demonstration()
        invalid = copy.deepcopy(output['records'][0])
        invalid['id'] = 'f2'
        invalid['roles'][0]['object'] = 'absent'
        output['records'].append(invalid)
        before = copy.deepcopy(output)
        view = import_records(output, source, 'w1')
        self.assertEqual(len(view['records']), 1)
        self.assertEqual(len(view['quarantine']), 1)
        self.assertTrue(view['coverage_limited'])
        self.assertEqual(output, before)

    def test_source_support_not_restored_by_whole_scope(self):
        source, output = demonstration()
        output['records'][0]['unknown'][0]['affects'] = ['*']
        record_ = import_records(output, source, 'w1')['records'][0]
        self.assertEqual(field_value(record_, 'predicate'), ('PAY_RENT', []))
        self.assertIsNone(field_value(record_, 'polarity')[0])
        self.assertIsNone(field_value(record_, 'roles.payer')[0])

    def test_unknown_time_does_not_block_known_type(self):
        source, output = demonstration()
        record_ = import_records(output, source, 'w1')['records'][0]
        self.assertEqual(field_value(record_, 'predicate')[0], 'PAY_RENT')
        self.assertIsNone(field_value(record_, 'time')[0])

    def test_view_does_not_expose_protected_outcome(self):
        source = {'case_id': 'x', 'segments': [{'id': 'p1', 'text': 'Fact. Verdict hidden.'}, {'id': 'p2', 'text': 'DISMISSED'}]}
        view = build_view(source, [{'segment_id': 'p1', 'start': 0, 'end': 5}], 'PRE_DECISION')
        self.assertEqual(view['segments'][0]['text'], 'Fact.')
        self.assertEqual(view['excluded_segment_ids'], ['p2'])
        self.assertNotIn('Verdict', str(view))

    def test_windows_cover_every_segment_without_text_loss(self):
        view = build_view({'case_id': 'x', 'segments': [{'id': str(i), 'text': 'abcd'} for i in range(5)]},
                          [{'segment_id': str(i)} for i in range(5)], 'TEST')
        result = windows(view, len, 8, 4)
        self.assertEqual({s['id'] for w in result for s in w['segments']}, set(map(str, range(5))))
        self.assertTrue(all(s['text'] == 'abcd' for w in result for s in w['segments']))
        with self.assertRaisesRegex(ValueError, 'INPUT_TOO_LONG'):
            windows(view, len, 3, 1)

    def test_immutable_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'x.json'
            write_new(p, {'a': 1})
            write_new(p, {'a': 1})
            with self.assertRaises(FileExistsError):
                write_new(p, {'a': 2})


class BindingExecution(unittest.TestCase):
    def setUp(self):
        self.query = {'op': 'all', 'children': [atom('lease', 'LEASE', {'tenant': '$t', 'premises': '$p'}),
                                             atom('possession', 'POSSESSION', {'holder': '$t', 'premises': '$p'})]}
        self.view = {'records': [record('l', 'LEASE', {'tenant': 'T', 'premises': 'P1'}),
                                 record('p', 'POSSESSION', {'holder': 'T', 'premises': 'P2'})],
                     'relations': [], 'objects': [], 'coverage_limited': False}

    def test_different_property_fails_only_pair(self):
        self.assertEqual(execute(self.view, self.query)['answer_status'], 'NOT_FOUND')
        self.view['records'].append(record('p2', 'POSSESSION', {'holder': 'T', 'premises': 'P1'}))
        result = execute(self.view, self.query)
        self.assertEqual(result['answer_status'], 'MATCH')
        self.assertEqual(result['witnesses'][0]['binding'], {'$t': 'T', '$p': 'P1'})

    def test_failed_pair_with_other_uncertain_candidate(self):
        uncertain = record('p2', 'POSSESSION', {'holder': 'T'}, [{'affects': ['roles.premises'], 'reason': 'unknown property'}])
        self.view['records'].append(uncertain)
        self.assertEqual(execute(self.view, self.query)['answer_status'], 'UNKNOWN')

    def test_wrong_known_type_excluded_even_if_whole_scope_unknown(self):
        self.view['records'] = [record('rent', 'PAY_RENT', {}, [{'affects': ['*'], 'reason': 'scope unresolved'}])]
        result = execute(self.view, atom('s', 'SUBLET', {'tenant': '$t'}))
        self.assertEqual(result['answer_status'], 'NOT_FOUND')
        self.assertEqual(result['candidate_decisions'][0]['decision'], 'EXCLUDE')

    def test_undetermined_type_remains_unknown_candidate(self):
        self.view['records'] = [record('x', 'UNKNOWN', {})]
        self.view['records'][0]['known'].remove('predicate')
        self.assertEqual(execute(self.view, atom('s', 'SUBLET', {'tenant': '$t'}))['answer_status'], 'UNKNOWN')

    def test_or_preserves_branches_no_cross_branch_join(self):
        self.view['records'] = [record('l', 'LEASE', {'tenant': 'T', 'premises': 'P1'})]
        query = {'op': 'any', 'children': [self.query, atom('s', 'SUBLET', {'tenant': '$t'})]}
        self.assertEqual(execute(self.view, query)['answer_status'], 'NOT_FOUND')

    def test_budget_failure_not_unknown_or_absence(self):
        result = execute(self.view, self.query, budget=1)
        self.assertIsNone(result['answer_status'])
        self.assertEqual(result['run_status'], 'UNSUPPORTED')

    def test_missing_membership_is_unknown_not_false(self):
        self.view['records'] = [record('l', 'LEASE', {'tenant': 'T'}), record('f', 'FILE_PROCEEDING', {'respondent': 'G'})]
        q = {'op': 'all', 'children': [atom('a', 'LEASE', {'tenant': '$t'}), atom('b', 'FILE_PROCEEDING', {'respondent': '$g'}),
                                      {'op': 'relation', 'id': 'c', 'relation': 'member_of', 'left': '$t', 'right': '$g'}]}
        self.assertEqual(execute(self.view, q)['answer_status'], 'UNKNOWN')

    def test_quoted_precedent_not_current_case_fact(self):
        self.view['records'][1]['roles']['premises'] = 'P1'
        self.view['records'][1]['context'] = 'QUOTED_PRECEDENT'
        self.assertEqual(execute(self.view, self.query)['answer_status'], 'NOT_FOUND')


if __name__ == '__main__':
    unittest.main()
