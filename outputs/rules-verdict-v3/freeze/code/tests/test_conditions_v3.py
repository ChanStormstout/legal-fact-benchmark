import copy
import unittest
from legal_bench.rules_verdict_v1.conditions_v3 import execute, import_facts


class ConditionTests(unittest.TestCase):
    def view(self):
        return {'case_id':'C', 'objects':{'d':{'id':'d','kind':'DOCUMENT','primary':True},
            'e':{'id':'e','kind':'TRANSFER','primary':True}}, 'atoms':[], 'quarantine':[]}

    def atom(self, subject, prop, value, **kw):
        a={'id':subject+':'+prop+':'+value,'subject':subject,'property':prop,'value':value,
           'status':'NARRATED','context':'MAIN_CASE','uncertainty':'NONE','stage':'background','evidence':[]}
        a.update(kw); return a

    def test_registered_is_refutation_not_no_lease(self):
        v=self.view();v['atoms']=[self.atom('d','registration','REGISTERED')]
        self.assertEqual(execute(v,'Q1')['answer_status'],'REFUTED')
        self.assertIsNone(execute(v,'Q1')['legal_effect'])
        self.assertEqual(execute(v,'Q3')['answer_status'],'UNKNOWN')

    def test_source_scope_state_and_unknown_are_local(self):
        v=self.view(); v['atoms']=[self.atom('d','registration','UNREGISTERED'),
            self.atom('e','parted_possession','YES',status='PARTY_CLAIMED',uncertainty='VALUE')]
        self.assertEqual(execute(v,'Q1')['answer_status'],'SUPPORTED')
        self.assertEqual(execute(v,'Q3')['answer_status'],'UNKNOWN')
        v['atoms'][0]['context']='PRECEDENT'
        self.assertEqual(execute(v,'Q1')['answer_status'],'UNKNOWN')
        self.assertIsNone(execute(v,'Q1',expected_case='OTHER')['answer_status'])

    def test_consent_requires_same_permission_and_event(self):
        v=self.view()
        for id,kind in [('p','PERMISSION'),('q','PERMISSION'),('l','ACTOR'),('other','TRANSFER')]:
            v['objects'][id]={'id':id,'kind':kind,'primary':False}
        v['atoms']=[self.atom('p','form','WRITTEN'),self.atom('q','specificity','SPECIFIC'),
            self.atom('p','target','e'),self.atom('p','grantor','l'),self.atom('l','role','LANDLORD')]
        self.assertEqual(execute(v,'Q2')['answer_status'],'UNKNOWN')
        v['atoms'].append(self.atom('p','specificity','SPECIFIC'))
        self.assertEqual(execute(v,'Q2')['answer_status'],'SUPPORTED')
        v['atoms'][2]['value']='other'
        self.assertEqual(execute(v,'Q2')['answer_status'],'UNKNOWN')

    def test_tenant_permission_and_general_clause_not_global_denial(self):
        v=self.view();v['objects'].update({'p':{'id':'p','kind':'PERMISSION','primary':False},
            'l':{'id':'l','kind':'ACTOR','primary':False}})
        v['atoms']=[self.atom('p','form','WRITTEN'),self.atom('p','specificity','GENERAL'),
            self.atom('p','target','e'),self.atom('p','grantor','l'),self.atom('l','role','TENANT')]
        self.assertEqual(execute(v,'Q2')['answer_status'],'UNKNOWN')
        v['atoms'].append(self.atom('e','specific_written_landlord_consent_absent','YES',status='COURT_FOUND'))
        self.assertEqual(execute(v,'Q2')['answer_status'],'REFUTED')

    def test_conflict_and_explicit_court_finding(self):
        v=self.view();v['atoms']=[self.atom('d','registration','REGISTERED'),self.atom('d','registration','UNREGISTERED')]
        self.assertEqual(execute(v,'Q1')['answer_status'],'CONFLICT')
        v['atoms'].append(self.atom('e','parted_possession','YES',status='COURT_FOUND'))
        self.assertEqual(execute(v,'Q3')['answer_status'],'SUPPORTED')

    def test_invalid_quote_isolated_without_rewriting(self):
        source={'case_id':'C','segments':[{'id':'s1','text':'A registered deed.'}]}
        ev=[{'segment_id':'s1','quote':'registered deed'}]
        data={'case_id':'C','objects':[{'id':'o1','kind':'DOCUMENT','label':'deed','primary':True,'evidence':ev}],
              'atoms':[], 'limitations':[]}
        a=self.atom('o1','registration','REGISTERED',speaker='narrator',uncertainty_reason='',evidence=ev)
        b=copy.deepcopy(a);b['id']='bad';b['evidence']=[{'segment_id':'s1','quote':'unregistered deed'}]
        data['atoms']=[a,b];view=import_facts(data,source)
        self.assertEqual(len(view['atoms']),1);self.assertEqual(len(view['quarantine']),1)
        self.assertEqual(execute(view,'Q1')['answer_status'],'REFUTED')


if __name__=='__main__':unittest.main()
