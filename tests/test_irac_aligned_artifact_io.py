import unittest,tempfile,json
from pathlib import Path
from legal_bench.irac_application.aligned_artifact_io import save_completed_fit
class ArtifactIOTest(unittest.TestCase):
    def test_failure_keeps_fit_record_and_creates_directory(self):
        with tempfile.TemporaryDirectory() as d:
            def fail(path):
                self.assertTrue(Path(path).parent.is_dir());raise OSError('synthetic export failure')
            result=save_completed_fit(d,'fixture',{'history':[{'loss':1.2}]},fail)
            self.assertEqual(result['status'],'WEIGHT_EXPORT_FAILURE')
            self.assertEqual(json.loads(Path(result['fit_record']).read_text())['history'][0]['loss'],1.2)
