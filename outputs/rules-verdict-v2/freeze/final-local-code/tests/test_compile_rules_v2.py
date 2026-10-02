import unittest
from legal_bench.rules_verdict_v1.compile_rules_v2 import compile_card,apply_fragments

class PartialRule(unittest.TestCase):
    def setUp(self):
        self.card={'id':'r','proposition':'Five conditions are required.','source_kind':'COURT_ADOPTED','conditions':[{'id':'c'+str(i),'text':'condition '+str(i),'kind':'NECESSARY'} for i in range(5)],'scope':{},'evidence':[{'quote':'fixture'}],'effect':'Legal effect','exceptions':['exception E']}
        self.mapping={c['id']:{'unsupported_reason':'Not implemented'} for c in self.card['conditions']}
    def test_five_conditions_and_exception_cannot_be_silently_dropped(self):
        self.mapping.pop('c4')
        with self.assertRaises(ValueError):compile_card(self.card,self.mapping)
    def test_partial_match_never_emits_legal_effect(self):
        self.mapping['c0']={'query':{'op':'atom','id':'a','predicate':'LEASE','roles':{'tenant':'$t'},'polarity':'POSITIVE'},'translation_note':'Only a factual fragment.'}
        compiled=compile_card(self.card,self.mapping)
        out=apply_fragments(compiled,{'records':[],'relations':[],'coverage_limited':False})
        self.assertEqual(len(out['conditions']),5)
        self.assertIsNone(out['legal_effect'])
        self.assertIsNone(out['answer_status'])
        self.assertEqual(out['run_status'],'UNSUPPORTED')
        self.assertEqual(compiled['exceptions_retained'],['exception E'])
