import copy, json, tempfile, unittest
from pathlib import Path
from legal_bench.proof_carrying.source_alignment_v16 import prepare, supplement, schemas
from legal_bench.proof_carrying.semantic_checker_v16 import check
from legal_bench.proof_carrying.semantic_search_v12 import complete_search
from scripts.proof_source_alignment_v16 import run


def fixture(operator='ALL'):
    text = 'Trial court found Mira controlled Room A. Owner alleged Len controlled Room A.'
    case = {'case_id': 'SYN', 'split': 'DEV', 'segments': [{'id': 'SYN:L1', 'source_document': 'SYN', 'original_line': 1, 'text': text}], 'targets': [{'id': 'Q1', 'question': 'Reconstruct the narrow trial premise'}]}
    f = {'id': 'F1', 'text': 'Attributed trial finding', 'statement_status': 'LOWER_COURT_FINDING', 'bindings': {'person': 'Mira', 'room': 'Room A'}, 'quote': None, 'refs': ['SYN:L1']}
    p = {'facts': [f], 'rules': [{'id': 'R1', 'version': 1, 'description': 'Fictional teaching composition', 'source_refs': ['SYN:L1'], 'source_quote': 'Trial court found Mira controlled Room A.', 'operator': operator, 'conclusion': 'Narrow teaching result', 'stage': 'trial reconstruction', 'premises': [{'id': 'R1.P1', 'text': 'Trial finding about Mira in Room A', 'variables': {'holder': 'person', 'room': 'property'}, 'allowed_statuses': ['LOWER_COURT_FINDING']}, {'id': 'R1.P2', 'text': 'Second independently attributed trial premise', 'variables': {'holder': 'person', 'room': 'property'}, 'allowed_statuses': ['LOWER_COURT_FINDING']}], 'exceptions': [], 'limits': ['Fictional, not target law']}], 'uses': [{'id': 'U1', 'request_id': 'Q1', 'rule_premise': 'R1.P1', 'evidence_ids': ['F1'], 'bindings': {'tenant': 'Mira', 'premises': 'Room A'}, 'use_judgment': 'USABLE', 'premise_state': 'TRUE', 'basis': 'Raw proposal'}, {'id': 'U2', 'request_id': 'Q1', 'rule_premise': 'R1.P2', 'evidence_ids': ['F1'], 'bindings': {'tenant': 'Mira', 'premises': 'Room A'}, 'use_judgment': 'USABLE', 'premise_state': 'TRUE', 'basis': 'Raw proposal'}], 'targets': [{'id': 'Q1', 'rule_ids': ['R1']}], 'relations': [{'from': 'F1', 'to': 'F1', 'sign': 'OPPOSE'}], 'coverage_limits': []}
    return prepare(case, p, 'Q1::R1')


def proposed(bundle):
    w = {'refs': ['SYN:L1'], 'quote': 'Trial court found Mira controlled Room A.', 'reason': 'Trial-stage source, no appeal endorsement'}
    rows = []
    for d in bundle['directory']:
        rows.append({'address': d['address'], 'bindings': [
            {'role': 'holder', 'variable': 'tenant', 'value': 'Mira', 'status': 'BOUND', 'witnesses': [w], 'basis': 'Explicitly named holder'},
            {'role': 'room', 'variable': 'premises', 'value': 'Room A', 'status': 'BOUND', 'witnesses': [w], 'basis': 'Explicit room'}],
            'uses': [{'purpose': 'RECONSTRUCT_COURT_PREMISE', 'direction': 'SUPPORT', 'witnesses': [w], 'explanation': 'Attributed trial finding'}],
            'whole_premise': {'state': 'TRUE', 'complete': True, 'basis': 'Full narrow reporting premise', 'components': [{'component': 'holder and room at trial', 'covered': True, 'witnesses': [w], 'basis': 'Entire reporting proposition'}], 'missing_components': [], 'use_indices': [1]},
            'statement_status': 'LOWER_COURT_FINDING', 'court_level': 'trial court', 'source_stage': 'trial judgment', 'rule_stage': 'trial reconstruction', 'counterevidence': [{'refs': ['SYN:L1'], 'quote': 'Owner alleged Len controlled Room A.', 'reason': 'Contrary allegation is not a finding'}], 'limitations': ['Appeal acceptance absent']})
    return {'alignments': copy.deepcopy(rows), 'coverage_limits': []}


class TestV16(unittest.TestCase):
    def result(self, b, p, review=None, view='P'):
        rt = complete_search(b['candidates'], b['snapshot']['rules'], b['requests'], b['snapshot']['contracts'])
        return check(b, rt, supplement(b, p), review, view)

    def test_real_subprocess_entry_and_null_original_quote(self):
        b = fixture();p = proposed(b)
        with tempfile.TemporaryDirectory() as tmp:
            result = run(b, supplement(b, p), None, 'P', Path(tmp) / 'run')
            self.assertEqual(result['requests'][0]['answer'], 'TRUE')
            self.assertEqual(result['original_null_quotes_retained'], ['F1'])
            self.assertFalse(result['formal_legal_approval'])
            self.assertTrue((Path(tmp) / 'run/checker.stdout.txt').exists())

    def test_self_approval_has_no_effect(self):
        b = fixture();p = proposed(b);p['alignments'][0]['review_decision'] = 'ACCEPT'
        result = self.result(b, p, view='R')
        self.assertEqual(result['requests'][0]['answer'], 'UNKNOWN')
        self.assertEqual(result['structure_checks']['A01']['review']['decision'], 'NOT_REVIEWED')
        from legal_bench.rules_verdict_v1.irac_contract_v1 import validate
        self.assertTrue(validate(p, schemas(['A01', 'A02'])[0]))

    def test_partial_use_is_not_full_truth(self):
        b = fixture();p = proposed(b)
        for row in p['alignments']: row['uses'][0]['purpose'] = 'PARTIAL_SUPPORT'
        self.assertEqual(self.result(b, p)['requests'][0]['answer'], 'UNKNOWN')

    def test_type_and_null_are_not_identity(self):
        b = fixture();p = proposed(b);p['alignments'][0]['bindings'][0]['variable'] = 'person'
        self.assertEqual(self.result(b, p)['structure_checks']['A01']['conditional_state'], 'UNKNOWN')
        p = proposed(b);p['alignments'][0]['bindings'][0]['value'] = None
        self.assertEqual(self.result(b, p)['structure_checks']['A01']['conditional_state'], 'UNKNOWN')

    def test_wrong_object_and_bad_quote_preserve_or_branch(self):
        b = fixture('ANY');p = proposed(b)
        p['alignments'][0]['bindings'][0]['value'] = 'Len'
        p['alignments'][0]['whole_premise']['components'][0]['witnesses'][0] = {'refs': ['SYN:L1'], 'quote': 'Trial court did not find Mira controlled Room A.', 'reason': 'Altered negation'}
        result = self.result(b, p)
        self.assertEqual(result['requests'][0]['answer'], 'TRUE')
        self.assertEqual(result['structure_checks']['A01']['conditional_state'], 'UNKNOWN')
        self.assertEqual(len(result['structure_checks']['A02']['counterevidence_checks']), 1)

    def test_stage_and_attribution(self):
        b = fixture();p = proposed(b);p['alignments'][0]['rule_stage'] = 'appeal'
        self.assertEqual(self.result(b, p)['requests'][0]['answer'], 'UNKNOWN')
        p = proposed(b);p['alignments'][0]['statement_status'] = 'PARTY_CLAIM'
        self.assertEqual(self.result(b, p)['requests'][0]['answer'], 'UNKNOWN')

    def test_review_acceptance_and_rejection_are_separate(self):
        b = fixture();p = proposed(b);sup = supplement(b, p)
        rev = {'proposal_sha256': sup['proposal_sha256'], 'raw': {'reviews': [{'address': a['address'], 'decision': 'ACCEPT', 'reason': 'Limited attributed premise supported', 'witnesses': a['uses'][0]['witnesses'], 'counterevidence': a['counterevidence'], 'limitations': []} for a in p['alignments']]}}
        self.assertEqual(self.result(b, p, rev, 'R')['requests'][0]['answer'], 'TRUE')
        rev['raw']['reviews'][0]['decision'] = 'REJECT'
        self.assertEqual(self.result(b, p, rev, 'R')['requests'][0]['answer'], 'UNKNOWN')
        self.assertEqual(self.result(b, p)['requests'][0]['answer'], 'TRUE')

    def test_open_text_not_converted(self):
        b = fixture('OPEN_TEXT');p = proposed(b)
        self.assertEqual(self.result(b, p)['requests'][0]['answer'], 'UNKNOWN')

    def test_presentation_repair_never_fills_null(self):
        b = fixture();self.assertIsNone(b['snapshot']['premises']['F1']['quote'])
        self.assertEqual(b['original_P']['facts'][0]['quote'], None)

    def test_schema_example_complete_and_technical_failure_null(self):
        from legal_bench.rules_verdict_v1.irac_contract_v1 import validate
        from legal_bench.proof_carrying.source_alignment_v16 import synthetic_example
        ex = synthetic_example();self.assertFalse(validate(ex['output'], schemas(['EX01'])[0]));self.assertFalse(validate(ex['independent_review_example'], schemas(['EX01'])[1]))
        b = fixture();bad = copy.deepcopy(b);bad['snapshot']['rules'] = None
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'failure'
            with self.assertRaises(Exception): run(bad, None, None, 'D', dest)
            self.assertIsNone(json.loads((dest / 'failure.json').read_text())['answer'])




class TestV16Repairs(unittest.TestCase):
    def test_typography_reversible_and_substantive_rejected(self):
        from legal_bench.proof_carrying.quote_locator_v16 import source_match
        sources={'S:L1':{'document':'S','original_line':1,'text':'The right was established earlier. The right so estab- lished remains.'}}
        found=source_match({'refs':['S:L1'],'quote':'The right so established remains.'},sources)
        self.assertIsNone(found['error'])
        span=found['original_spans'][0]
        self.assertEqual(sources[span['ref']]['text'][span['start']:span['end']],span['original'])
        self.assertIn('estab- lished',span['original'])
        for quote in ['The right so established does not remain.','The right so created remains.']:
            self.assertIsNotNone(source_match({'refs':['S:L1'],'quote':quote},sources)['error'])
        self.assertIsNotNone(source_match({'refs':['BAD:L1'],'quote':'The right so established remains.'},sources)['error'])
        self.assertEqual(source_match({'refs':['S:L1'],'quote':None},sources)['error'],'QUOTE_NOT_A_STRING')

    def test_uncertain_hyphen_and_multiple_locations_pending(self):
        from legal_bench.proof_carrying.quote_locator_v16 import source_match
        sources={'S:L1':{'document':'S','original_line':1,'text':'An owner and a co-owner. A co- owner.'}}
        self.assertIsNotNone(source_match({'refs':['S:L1'],'quote':'A coowner.'},sources)['error'])
        sources['S:L1']['text']='Established established. estab- lished estab- lished.'
        self.assertEqual(source_match({'refs':['S:L1'],'quote':'established'},sources)['error'],'QUOTE_AMBIGUOUS')

    def test_binding_failure_keeps_judgment_but_blocks_rule(self):
        b=fixture();p=proposed(b);p['alignments'][0]['bindings'][0]['value']='Len'
        rt=complete_search(b['candidates'],b['snapshot']['rules'],b['requests'],b['snapshot']['contracts'])
        result=check(b,rt,supplement(b,p),None,'P');a=result['structure_checks']['A01']
        self.assertEqual(a['independent_conditional_judgment'],'TRUE')
        self.assertEqual(a['conditional_state'],'UNKNOWN')
        self.assertEqual(result['requests'][0]['answer'],'UNKNOWN')
        self.assertEqual(len(a['counterevidence_checks']),1)

    def test_local_review_does_not_negate_independent_false_or_bypass_dependency(self):
        b=fixture();p=proposed(b);p['alignments'][0]['whole_premise']['state']='FALSE'
        sup=supplement(b,p);rows=[]
        for a in p['alignments']:
            for scope,role,idx,decision in [('WHOLE_PREMISE','',None,'ACCEPT'),('BINDING','holder',None,'REJECT' if a['address']=='A01' else 'ACCEPT'),('BINDING','room',None,'ACCEPT'),('USE','',1,'ACCEPT')]:
                rows.append({'address':a['address'],'scope':scope,'role':role,'use_index':idx,'decision':decision,'reason':'Synthetic scoped source review','witnesses':a['uses'][0]['witnesses'],'counterevidence':a['counterevidence'],'limitations':[]})
        rev={'proposal_sha256':sup['proposal_sha256'],'raw':{'reviews':rows}}
        rt=complete_search(b['candidates'],b['snapshot']['rules'],b['requests'],b['snapshot']['contracts'])
        r=check(b,rt,sup,rev,'R');a=r['structure_checks']['A01']
        self.assertEqual(a['accepted_independent_judgment'],'FALSE')
        self.assertEqual(a['accepted_state'],'UNKNOWN')
        self.assertEqual(r['requests'][0]['answer'],'UNKNOWN')
        self.assertFalse(r['formal_legal_approval'])

    def test_legacy_whole_reject_cannot_manufacture_acceptance(self):
        b=fixture();p=proposed(b);sup=supplement(b,p)
        rev={'proposal_sha256':sup['proposal_sha256'],'raw':{'reviews':[{'address':'A01','decision':'REJECT','reason':'Bad binding','witnesses':p['alignments'][0]['uses'][0]['witnesses']}]}}
        rt=complete_search(b['candidates'],b['snapshot']['rules'],b['requests'],b['snapshot']['contracts'])
        a=check(b,rt,sup,rev,'R')['structure_checks']['A01']
        self.assertEqual(a['accepted_independent_judgment'],'UNKNOWN')
        self.assertTrue(a['review']['legacy_whole_rejection_preserved'])

if __name__ == '__main__': unittest.main()
