import unittest
from legal_bench.rules_verdict_v1.translation_gate_v2 import compile_reviewed_fragments

class ScopeNegation(unittest.TestCase):
    def test_unregistered_lease_not_compiled_as_no_lease(self):
        card={'id':'r','proposition':'An unregistered document may be inadmissible.','source_kind':'COURT_ADOPTED','scope':{},'evidence':[{'quote':'fixture'}],'effect':'inadmissible term','conditions':[{'id':'c','text':'Lease deed is not registered.','kind':'NECESSARY','factual_predicate':'LEASE','polarity':'NEGATIVE'}]}
        compiled=compile_reviewed_fragments(card)
        self.assertEqual(compiled['conditions'][0]['execution_kind'],'UNSUPPORTED')
        self.assertNotIn('query',compiled['conditions'][0])
        self.assertFalse(compiled['legal_effect_may_be_emitted'])
