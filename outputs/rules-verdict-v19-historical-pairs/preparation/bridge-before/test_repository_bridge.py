import json
import tempfile
import unittest
from pathlib import Path
from scripts.repository_bridge import publication_paths, scan, prepare, verify, export, git, git_names, sync


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

    def test_slash_branch_targets_all_review_links_without_changing_results(self):
        branch = 'research/rules-and-verdict'
        self.policy['branch'] = branch
        self.write('docs/repository-artifacts.json', self.policy)
        result_path = self.root/'outputs/run/scoring/results-v1.json'
        original = result_path.read_bytes()
        first = prepare(self.root)
        manifest = json.loads((self.root/'review/MANIFEST.json').read_text())
        self.assertEqual(manifest['branch'], branch)
        prefix = 'https://raw.githubusercontent.com/example/repo/' + branch + '/'
        for entry in manifest['source_files'] + manifest['derived_files']:
            self.assertTrue(entry['raw_url'].startswith(prefix))
        for name in ['review/START_HERE.md', 'review/REVIEW_REQUEST.md']:
            content = (self.root/name).read_text()
            self.assertIn('https://github.com/example/repo/tree/' + branch, content)
            self.assertIn(prefix + 'review/START_HERE.md', content)
            self.assertNotIn('example/repo/main/', content)
        state = json.loads((self.root/'docs/PROJECT_STATE.json').read_text())
        self.assertEqual(state['publication_target']['branch'], branch)
        self.assertEqual(result_path.read_bytes(), original)
        self.assertEqual(prepare(self.root), first)

    def test_live_fix_preserves_exact_explicit_frozen_snapshot(self):
        import hashlib
        self.write('scripts/method.py', {'version': 'old'})
        old=(self.root/'scripts/method.py').read_bytes()
        snapshot='outputs/run/method.txt'
        (self.root/snapshot).write_bytes(old)
        self.write('outputs/run/freeze.json', {'method_hashes': {
            'scripts/method.py': hashlib.sha256(old).hexdigest()}})
        self.write('scripts/method.py', {'version': 'fixed'})
        self.policy['frozen_method_snapshots']={'outputs/run': {'scripts/method.py':snapshot}}
        self.write('docs/repository-artifacts.json', self.policy)
        self.assertEqual(prepare(self.root)['status'],'VERIFIED')
        self.assertEqual((self.root/snapshot).read_bytes(),old)

    def test_incorrect_frozen_snapshot_cannot_hide_live_change(self):
        import hashlib
        self.write('scripts/method.py', {'version':'old'})
        old=(self.root/'scripts/method.py').read_bytes()
        self.write('outputs/run/freeze.json', {'method_hashes': {
            'scripts/method.py':hashlib.sha256(old).hexdigest()}})
        self.write('scripts/method.py', {'version':'fixed'})
        self.write('outputs/run/method.txt', {'version':'not_original'})
        self.policy['frozen_method_snapshots']={'outputs/run': {
            'scripts/method.py':'outputs/run/method.txt'}}
        self.write('docs/repository-artifacts.json', self.policy)
        with self.assertRaisesRegex(ValueError,'without matching published snapshot'):
            prepare(self.root)

    def test_wrong_branch_refuses_sync_before_generating_or_staging(self):
        from unittest.mock import patch
        self.policy['branch'] = 'research/rules-and-verdict'
        self.write('docs/repository-artifacts.json', self.policy)
        def git_read(root, *args, **kwargs):
            if args == ('remote', 'get-url', 'origin'):
                return 'https://github.com/example/repo.git'
            if args == ('branch', '--show-current'):
                return 'main'
            self.fail('Unexpected Git mutation or query: ' + repr(args))
        with patch('scripts.repository_bridge.git', side_effect=git_read), patch('scripts.repository_bridge.prepare') as generator:
            with self.assertRaisesRegex(ValueError, 'Not on registered branch'):
                sync(self.root, message='Must not publish')
            generator.assert_not_called()

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

    def test_literal_unicode_filename_is_not_a_glob_or_quoted_guard_entry(self):
        git(self.root, 'init', '-q')
        name='docs/记录[1].md'
        (self.root/name).write_text('selected')
        (self.root/'docs/记录1.md').write_text('unselected')
        pathspec=self.root/'paths.txt';pathspec.write_text(name+'\n')
        git(self.root,'--literal-pathspecs','add','--pathspec-from-file='+str(pathspec),capture=False)
        self.assertEqual(git_names(self.root,'diff','--cached','--name-only'),{name})
        self.assertEqual(git_names(self.root,'ls-files'),{name})


if __name__ == '__main__':
    unittest.main()
