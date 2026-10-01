import json
import tempfile
import unittest
from pathlib import Path
from scripts.repository_bridge import publication_paths, scan, prepare, verify, export


class RepositoryBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'docs').mkdir()
        for name in ['README.md', 'AGENTS.md', '.gitignore', '.gitattributes', 'Makefile']:
            (self.root/name).write_text('fixture\n')
        self.policy = dict(repository='example/repo', branch='main', latest_run='outputs/run',
                           max_artifact_bytes=100000, artifact_roots=['outputs/run'],
                           exclude_globs=['*/web-tasks/*'], artifact_suffixes=['.json','.txt'],
                           extra_artifacts=[], code_review_files=[])
        self.write('docs/repository-artifacts.json', self.policy)
        self.write('docs/EXPERIMENTS.json', {'experiments': []})
        self.write('outputs/run/scoring/results-v1.json', {'actual_cases': 0, 'question_count': 0,
                                                         'summary': {}, 'rows': []})
        self.write('outputs/run/evaluation-sample.json', {'cases': []})
        self.write('outputs/run/freeze.json', {'method_hashes': {}})

    def write(self, name, obj):
        path = self.root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj))

    def test_excludes_unregistered_data_and_ui(self):
        self.write('work/private.json', {'private': 1})
        self.write('outputs/run/web-tasks/state.json', {'ui': 1})
        self.write('outputs/run/data.json', {'data': 1})
        paths, excluded = publication_paths(self.root, self.policy)
        self.assertIn('outputs/run/data.json', paths)
        self.assertNotIn('work/private.json', paths)
        self.assertNotIn('outputs/run/web-tasks/state.json', paths)
        self.assertTrue(any(e['path'].endswith('state.json') for e in excluded))

    def test_prepare_is_idempotent_and_stale_changes_fail(self):
        first = prepare(self.root)
        manifest = (self.root/'review/MANIFEST.json').read_bytes()
        self.assertEqual(first, prepare(self.root))
        self.assertEqual(manifest, (self.root/'review/MANIFEST.json').read_bytes())
        (self.root/'README.md').write_text('changed\n')
        with self.assertRaisesRegex(ValueError, 'stale'):
            verify(self.root)

    def test_export_exact_selected_files_with_reproducible_bytes(self):
        import zipfile
        self.write('work/private.json', {'private': 1})
        prepare(self.root)
        first = export(self.root)
        self.assertEqual(first, export(self.root))
        with zipfile.ZipFile(first['path']) as z:
            self.assertIn('review/MANIFEST.json', z.namelist())
            self.assertNotIn('work/private.json', z.namelist())
            self.assertEqual(z.read('README.md'), (self.root/'README.md').read_bytes())

    def test_secret_scan_never_echoes_credential(self):
        value = 'ghp_' + 'a'*30
        (self.root/'README.md').write_text(value)
        with self.assertRaises(ValueError) as caught:
            scan(self.root, ['README.md'])
        self.assertNotIn(value, str(caught.exception))

    def test_symlink_is_not_published(self):
        (self.root/'outputs/run/link.json').symlink_to(self.root/'README.md')
        paths, _ = publication_paths(self.root, self.policy)
        self.assertNotIn('outputs/run/link.json', paths)


if __name__ == '__main__':
    unittest.main()
