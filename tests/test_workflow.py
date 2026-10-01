import json
import tempfile
import unittest
from pathlib import Path
from legal_bench.core import write_new, digest, make_source, audit
from legal_bench.tasks import prepare, import_reply
from legal_bench.experiment import select_split, check_manifest, freeze, score
from legal_bench.abstraction import abstract


class WorkflowTests(unittest.TestCase):
    def test_abstraction_retains_source_and_ambiguous_mapping(self):
        a = {'events': [{'id': 'e', 'type': 'REMOVED', 'roles': {'actor': 'x'}, 'attributes': {'consent': 'unknown'}}]}
        p = {'version': 'v1', 'task': 'possession', 'state': 'MODEL_REVIEWED', 'definitions': [
            {'type': 'DISPOSSESSED', 'aliases': ['REMOVED'], 'meaning': 'deprived of possession', 'preserve': ['roles', 'attributes']}]}
        v = abstract(a, p)
        self.assertEqual(v['events'][0]['type'], 'DISPOSSESSED')
        self.assertEqual(v['source_events'], a['events'])
        self.assertEqual(a['events'][0]['type'], 'REMOVED')
        p['definitions'].append(dict(p['definitions'][0], type='OTHER'))
        self.assertEqual(abstract(a, p)['abstractions'][0]['state'], 'AMBIGUOUS')

    def test_abstraction_rejects_implicit_loss(self):
        p = {'version': 'v1', 'task': 't', 'state': 'MODEL_REVIEWED', 'definitions': [
            {'type': 'T', 'meaning': 'm', 'preserve': ['roles'], 'omit': ['amount']}]}
        with self.assertRaises(ValueError): abstract({'events': [{'id': 'e', 'type': 'T'}]}, p)

    def test_immutable_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'x.json'; write_new(p, {'a': 1}); write_new(p, {'a': 1})
            with self.assertRaises(ValueError): write_new(p, {'a': 2})

    def test_prepare_requires_full_source(self):
        s = make_source('c', 'Text', 'url', 'hash')
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): prepare(s, d)
            s['source_completeness'] = 'VERIFIED_FULL'
            a = prepare(s, d, 'A'); b = prepare(s, d, 'B')
            self.assertEqual(a['prompt'], b['prompt'])
            self.assertNotEqual(a['id'], b['id'])
            self.assertEqual(a, prepare(s, d, 'A'))

    def test_split_and_freeze(self):
        eligible = [{'case_id': str(i), 'dispute_group': str(i), 'eligibility_evidence': 'source', 'group_review': 'checked'} for i in range(30)]
        m = select_split(eligible, list(map(str, range(5))))
        self.assertEqual(m, select_split(list(reversed(eligible)), list(map(str, range(5)))))
        check_manifest(m, True)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'manifest.json'; write_new(p, m)
            q = Path(d) / 'queries.json'; write_new(q, [])
            f = freeze(p, [q], Path(d) / 'f.json')
            self.assertEqual(f['files']['queries.json']['sha256'], digest(q.read_bytes()))
        m['cases'][10]['dispute_group'] = m['cases'][0]['dispute_group']
        with self.assertRaises(ValueError): check_manifest(m)

    def test_reference_disagreement_not_hidden(self):
        refs = [{'case_id': 'a', 'unit_id': 'u', 'query_id': 'q', 'status': 'MATCH', 'review_state': 'RESOLVED'},
                {'case_id': 'a', 'unit_id': 'u', 'query_id': 'q2', 'status': 'UNKNOWN', 'review_state': 'DISPUTED'}]
        p = [{'case_id': 'a', 'unit_id': 'u', 'query_id': 'q', 'status': 'NOT_FOUND'}]
        r = score(p, refs)
        self.assertEqual(r['case_macro_status_agreement'], 0)
        self.assertEqual(len(r['excluded_unresolved']), 1)
        self.assertEqual(score([], refs)['case_macro_status_agreement'], None)

    def test_hundred_case_split_excludes_related_development_and_duplicates(self):
        eligible = [{'case_id': str(i), 'dispute_group': str(i), 'eligibility_evidence': 'source',
                     'group_review': 'checked'} for i in range(115)]
        eligible.append(dict(eligible[0], case_id='related-dev'))
        eligible.append(dict(eligible[10], case_id='related-check'))
        m = select_split(eligible, list(map(str, range(5))), check_count=100)
        self.assertEqual(m, select_split(list(reversed(eligible)), list(map(str, range(5))), check_count=100))
        check_manifest(m, True)
        checks = [r for r in m['cases'] if r['split'] == 'check']
        self.assertEqual(len(checks), 100)
        self.assertEqual(len({r['dispute_group'] for r in checks}), 100)
        self.assertTrue({r['dispute_group'] for r in checks}.isdisjoint(map(str, range(5))))
        self.assertNotIn('related-dev', [r['case_id'] for r in checks])
        # A partial hundred-case sample cannot be frozen by silently reverting to twenty.
        m['cases'] = m['cases'][:25]
        with self.assertRaises(ValueError): check_manifest(m, True)

    def test_hundred_case_split_requires_hundred_independent_groups(self):
        eligible = [{'case_id': str(i), 'dispute_group': str(i % 40),
                     'eligibility_evidence': 'source', 'group_review': 'checked'} for i in range(150)]
        with self.assertRaises(ValueError):
            select_split(eligible, list(map(str, range(5))), check_count=100)
        for count in [True, 0, -1, 100.0]:
            with self.assertRaises(ValueError): select_split(eligible, list(map(str, range(5))), check_count=count)

    def test_audit_resumes_and_rejects_changed_input(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'raw.jsonl'
            p.write_text(json.dumps({'doc_id': '1', 'title': 'case', 'url': 'url', 'facts': 'suit for possession', 'status': 'ok'}) + '\n')
            r = audit(p, Path(d) / 'data')
            self.assertEqual(r, audit(p, Path(d) / 'data'))
            p.write_text(p.read_text() + '\n')
            with self.assertRaises(ValueError): audit(p, Path(d) / 'data')

    def test_import_records_format_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = make_source('c', 'Text', 'url', 'hash'); source['source_completeness'] = 'VERIFIED_FULL'
            write_new(root / 'source.json', source)
            task = prepare(source, root)
            metadata = {'conversation_url': 'https://chatgpt.com/c/example', 'model_display': '6', 'effort_display': 'High',
                        'submitted_at': '2026-09-30', 'retrieved_at': '2026-09-30', 'prompt_sha256': task['prompt_sha256']}
            write_new(root / 'metadata.json', metadata)
            (root / 'reply.txt').write_text('not JSON')
            r = import_reply(root / (task['id'] + '.json'), root / 'source.json', root / 'reply.txt', root / 'metadata.json', root / 'imports')
            self.assertEqual(r['state'], 'FORMAT_ERROR')
            self.assertEqual(r['raw_reply'], 'not JSON')


if __name__ == '__main__': unittest.main()
