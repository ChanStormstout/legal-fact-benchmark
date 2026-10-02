import tempfile
import unittest
from pathlib import Path
from legal_bench.rules_verdict_v1.authority_index import build, search
from legal_bench.rules_verdict_v1.retrieve import fuse, expand


class RetrievalTests(unittest.TestCase):
    def test_exact_sources_and_idempotent_readonly_index(self):
        units = [{'id': 's14', 'text': 'Consent in writing. Exception follows.', 'source': 'fixture',
                  'version_status': 'HISTORICAL_REVIEW_PENDING'}]
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'index.sqlite'
            first = build(units, p)
            self.assertEqual(build(units, p), first)
            self.assertEqual(search(p, 'consent " OR *')[0]['id'], 's14')
            self.assertEqual(search(p, ''), [])
            units[0]['text'] += ' altered'
            with self.assertRaises(FileExistsError):
                build(units, p)

    def test_rrf_ties_and_duplicate_route_items(self):
        result = fuse({'b': [{'id': 'z'}], 'a': [{'id': 'a'}]})
        self.assertEqual([x['id'] for x in result], ['a', 'z'])
        with self.assertRaises(ValueError):
            fuse({'a': [{'id': 'x'}, {'id': 'x'}]})

    def test_exception_dependency_not_pruned_by_failed_condition(self):
        units = [{'id': 'law', 'text': 'rule', 'condition_satisfied': False, 'dependencies': ['exception']},
                 {'id': 'exception', 'text': 'except', 'dependencies': ['definition']},
                 {'id': 'definition', 'text': 'defined', 'dependencies': []}]
        result = expand([{'id': 'law'}], units, initial=1)
        self.assertEqual(result['selected_ids'], ['law', 'exception', 'definition'])
        self.assertTrue(result['dependency_complete'])
        bounded = expand([{'id': 'law'}], units, initial=1, max_units=1)
        self.assertFalse(bounded['dependency_complete'])
        self.assertTrue(bounded['budget_truncated_dependencies'])


if __name__ == '__main__':
    unittest.main()
