import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import proof_together_diagnostic as run
from scripts.proof_together_diagnostic_audit import unique_errors


class TogetherTransportTests(unittest.TestCase):
    def test_exact_user_input_original_schema_and_thinking_disabled(self):
        body = run.request_body('same source\nno new instructions', {'type':'object'})
        self.assertEqual(body['messages'], [{'role':'user','content':'same source\nno new instructions'}])
        self.assertEqual(body['response_format']['json_schema']['schema'], {'type':'object'})
        self.assertEqual(body['reasoning'], {'enabled':False})
        self.assertEqual(body['max_tokens'], 16384)

    def test_sse_preserves_content_and_actual_usage_without_repair(self):
        content, reasoning, receipt = io.StringIO(), io.StringIO(), {}
        run.stream_event(json.dumps({'id':'fixed','model':run.MODEL,
            'choices':[{'index':0,'delta':{'content':'{"x":'},'finish_reason':None}]}),content,reasoning,receipt)
        run.stream_event(json.dumps({'choices':[{'index':0,'delta':{'content':'1}'},'finish_reason':'stop'}],
                                    'usage':{'prompt_tokens':4,'completion_tokens':3}}),content,reasoning,receipt)
        run.stream_event('[DONE]',content,reasoning,receipt)
        self.assertEqual(content.getvalue(), '{"x":1}')
        self.assertTrue(receipt['done_received'])
        self.assertEqual(receipt['usage']['completion_tokens'],3)

    def test_interrupted_attempt_not_resubmitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run.save(out/'freeze/protocol.json', {'runner_sha256':run.sha(Path(run.__file__))})
            run.save(out/'runs/c/P01/start.json', {'dispatch_count':1})
            with patch.object(run,'OUT',out), patch.object(run.urllib.request,'urlopen') as network:
                with self.assertRaisesRegex(ValueError,'NO_RESEND'):
                    run.run_one({'case_id':'c','part':'P01'}, 'never-used')
                network.assert_not_called()

    def test_unique_items_independent_of_provider_claim(self):
        self.assertEqual(unique_errors(['SRC:1','SRC:1'], {'type':'array','items':{'type':'string'},'uniqueItems':True}), ['$'])


if __name__ == '__main__':
    unittest.main()
