import unittest
from legal_bench.irac_application.aligned_anco import anco,project
from legal_bench.irac_application.aligned_logic import evaluate,combine_bound
R=[{'source_id':'S','quote':'fictional'}]
def ref(i):return dict(op='REF',id=i,source_refs=R)
class AlignedTests(unittest.TestCase):
    def test_anco_degenerate(self):
        self.assertEqual(anco([[1,1],[1,1]])['x'],[1.,1.]);self.assertTrue(anco([[1,-1],[-1,1]])['all_zero'])
    def test_anco_camps(self):self.assertEqual(anco([[1,1],[-1,-1]])['x'],[1.,-1.])
    def test_isolated_nonfinite(self):
        self.assertEqual(anco([[0]])['isolated_tests'],[0]);self.assertEqual(anco([[float('nan')]])['status'],'NON_FINITE_INPUT')
    def test_conflict_not_absence(self):
        p=project(['t'],['f'],[dict(test_id='t',instance_id='f',direction=d) for d in ['SUPPORT','OPPOSE','UNKNOWN']])
        self.assertEqual(p['matrix'],[[0.]]);self.assertEqual(len(p['conflicts']),1);self.assertEqual(len(p['non_numeric_links']),1)
    def test_polarity_exception(self):
        e=dict(op='EXCEPT',base=ref('transfer'),exception=ref('consent'),source_refs=R)
        self.assertEqual(evaluate(e,{'transfer':{'status':'SUPPORTED'},'consent':{'status':'SUPPORTED'}})['status'],'REFUTED')
    def test_unknown_not_negative(self):self.assertEqual(evaluate(ref('missing'),{})['status'],'UNRESOLVED')
    def test_missing_source(self):self.assertEqual(evaluate(dict(op='REF',id='x'),{})['status'],'UNSUPPORTED')
    def test_no_cross_binding_stitch(self):
        e=dict(op='AND',args=[ref('a'),ref('b')],source_refs=R)
        rows=[dict(binding_id=str(i),binding_source_refs=R,identity_checks_complete=True,tests={key:{'status':'SUPPORTED'}}) for i,key in enumerate(['a','b'])]
        self.assertEqual(combine_bound(e,rows)['status'],'UNRESOLVED')
    def test_another_binding_succeeds(self):
        r=combine_bound(ref('a'),[dict(binding_id='1'),dict(binding_id='2',binding_source_refs=R,identity_checks_complete=True,tests={'a':{'status':'SUPPORTED'}})])
        self.assertEqual(r['status'],'SUPPORTED');self.assertFalse(r['burden_failure_inferred'])
if __name__=='__main__':unittest.main()

class InputBoundaryTests(unittest.TestCase):
    def test_supervision_rejected(self):
        from legal_bench.irac_application.graph_builder import reject_supervision
        with self.assertRaises(ValueError):reject_supervision({'links':[{'supervision_mask':True}]})
    def test_source_address_not_semantics(self):
        from legal_bench.irac_application.aligned_graph import check_refs
        self.assertEqual(check_refs([{'source_id':'a','quote':'said'}],{'a':{'text':'Tenant said X'}}),[])
        self.assertTrue(check_refs([{'source_id':'b','quote':'said'}],{'a':{'text':'Tenant said X'}}))
    def test_claimed_not_found(self):
        from legal_bench.irac_application.aligned_logic import evaluate
        # No conversion of assertion existence to the supported proposition.
        self.assertEqual(evaluate(ref('t'),{'t':{'status':'UNRESOLVED','reason':'only disputed allegation'}})['status'],'UNRESOLVED')
    def test_unknown_identity_not_wildcard(self):
        self.assertEqual(combine_bound(ref('a'),[dict(binding_id='b',binding_source_refs=[],identity_checks_complete=False,tests={'a':{'status':'SUPPORTED'}})])['status'],'UNRESOLVED')

class DependencyTests(unittest.TestCase):
    def test_local_unknown(self):
        from legal_bench.irac_application.aligned_dependencies import usable_fields
        r={'type':'PAY_RENT','unknowns':[{'fields':['date'],'reason':'interval unclear'}]}
        self.assertTrue(usable_fields(r,['type'])['usable']);self.assertFalse(usable_fields(r,['date'])['usable'])
        r['unknowns']=[{'fields':['*'],'reason':'proposition scope unknown'}];self.assertFalse(usable_fields(r,['type'])['usable'])
    def test_identity_and_dates(self):
        from legal_bench.irac_application.aligned_dependencies import identity,time_order
        self.assertEqual(identity('tenant','tenant',[])['status'],'UNRESOLVED')
        self.assertEqual(identity(None,None,[])['status'],'UNRESOLVED')
        self.assertEqual(time_order({'date':'2020-01-03','source_refs':R},{'date':'2020-01-01','source_refs':R})['status'],'REFUTED')
    def test_failed_combination_not_global_absence(self):
        rows=[dict(binding_id='x',binding_source_refs=R,identity_checks_complete=True,tests={'a':{'status':'REFUTED'}})]
        self.assertEqual(combine_bound(ref('a'),rows)['status'],'UNRESOLVED')
