import copy
import unittest
from legal_bench.fast_development import import_case,candidates,execute,run,parse_local,CONFIG,audit_items


class FastDevelopmentTests(unittest.TestCase):
    def setUp(self):
        self.quote={'segment_id':'p1','quote':'L leased A to T. T occupied A. T occupied B.'}
        self.source={'case_id':'c1','url':'https://example.org/c1','text_sha256':'x','segments':[{'id':'p1','text':self.quote['quote'],'page':1}]}
        def obj(oid):return {'id':oid,'label':oid,'identity_resolved':True,'evidence':[self.quote]}
        def event(eid,typ,roles):return {'id':eid,'unit_id':'u1','kind':'FACT','type':typ,'roles':roles,'role_evidence':{r:[self.quote] for r,v in roles.items() if v},'polarity':'POSITIVE','status':'NARRATED','origin':{},'time':None,'attributes':{},'scope':{},'scope_parsed':True,'unresolved':[],'evidence':[self.quote]}
        self.annotation={'case_id':'c1','objects':[obj(x) for x in ['L','T','A','B']],'units':[{'id':'u1','primary':True,'evidence':[self.quote]}],
                         'events':[event('a1','LEASE_PROPERTY',{'landlord':'L','tenant':'T','property':'A'}),event('a2','OCCUPY_PROPERTY',{'occupant':'T','property':'B'})]}
        self.query={'atoms':[{'var':'a','type':'LEASE_PROPERTY','status':'NARRATED'},{'var':'b','type':'OCCUPY_PROPERTY','status':'NARRATED'}],
                    'constraints':[{'op':'different','left':'a.id','right':'b.id'},{'op':'same','left':'a.roles.property','right':'b.roles.property'}]}
    def view(self):return import_case(self.annotation,self.source)
    def test_wrong_property_rejected_but_common_types_present(self):
        view=self.view();r=execute(view,self.query)
        self.assertEqual(r['status'],'NOT_FOUND');self.assertEqual(r['rejected_bindings'][0]['failed_conditions'][0]['left'],'A')
        q=copy.deepcopy(self.query);q['constraints']=q['constraints'][:1]
        self.assertEqual(execute(view,q)['status'],'MATCH')
    def test_one_failed_binding_does_not_deny_another_unknown(self):
        e=copy.deepcopy(self.annotation['events'][1]);e['id']='a3';e['roles']['property']=None;self.annotation['events'].append(e)
        self.assertEqual(execute(self.view(),self.query)['status'],'UNKNOWN')
    def test_one_failed_binding_does_not_block_a_valid_match(self):
        e=copy.deepcopy(self.annotation['events'][1]);e['id']='a3';e['roles']['property']='A';self.annotation['events'].append(e)
        r=execute(self.view(),self.query);self.assertEqual(r['status'],'MATCH');self.assertEqual(len(r['witnesses']),1)
    def test_unlocated_binding_is_isolated_not_repaired_semantically(self):
        self.annotation['events'][1]['role_evidence']['property']=[{'segment_id':'p1','quote':'fabrication'}]
        view=self.view();self.assertEqual(len(view['events']),2);self.assertEqual(execute(view,self.query)['status'],'UNKNOWN')
    def test_dangling_object_cannot_seed_a_join(self):
        self.annotation['events'][1]['roles']['property']='missing'
        view=self.view();self.assertEqual(execute(view,self.query)['status'],'UNKNOWN')
        _,qs=candidates([view]);self.assertFalse(any('roles.property' in s for s in qs))
    def test_bad_event_quote_quarantines_only_that_record(self):
        self.annotation['events'][1]['evidence']=[{'segment_id':'p1','quote':'fabrication'}]
        view=self.view();self.assertEqual(len(view['events']),1);self.assertEqual(view['excluded'][0]['reason'],'UNLOCATED_EVENT_QUOTE')
    def test_missing_date_does_not_block_identity(self):
        self.annotation['events'][1]['roles']['property']='A';self.annotation['events'][1]['unresolved']=[{'field':'time','reason':'missing'}]
        self.assertEqual(execute(self.view(),self.query)['status'],'MATCH')
    def test_unparsed_qualifier_blocks_record_use(self):
        self.annotation['events'][1]['scope']={'qualification':'unknown portion'};self.annotation['events'][1]['scope_parsed']=False
        self.assertEqual(execute(self.view(),self.query)['status'],'UNKNOWN')
    def test_same_roles_not_same_people(self):
        self.annotation['objects'][1]['identity_resolved']=False
        q=copy.deepcopy(self.query);q['constraints'][1]={'op':'same','left':'a.roles.tenant','right':'b.roles.occupant'}
        self.assertEqual(execute(self.view(),q)['status'],'UNKNOWN')
    def test_support_counts_cases_not_binding_multiplicity(self):
        self.annotation['events'].append(dict(copy.deepcopy(self.annotation['events'][1]),id='a3'))
        v1=self.view();v2=copy.deepcopy(v1);v2['case_id']='c2'
        r=run([v1,v2]);self.assertTrue(all(p['support']<=2 for m in r['methods'].values() for p in m['patterns']))
        with self.assertRaises(ValueError):run([v1,v1])
    def test_no_semantic_rewrite_in_local_parser(self):
        obj,repairs=parse_local(b'```json\n{"cases":[]}\n```');self.assertEqual(obj,{'cases':[]});self.assertTrue(repairs)
        with self.assertRaises(ValueError):parse_local(b'{"cases": [}')
    def test_exact_duplicate_record_cannot_make_false_pair(self):
        self.annotation['events']=[self.annotation['events'][0],dict(copy.deepcopy(self.annotation['events'][0]),id='a3')]
        self.assertEqual(len(self.view()['events']),1)
        self.assertEqual(candidates([self.view()]),([],[]))
    def test_seed_state_preserved_and_negation_not_mined_as_positive(self):
        self.annotation['events'][1]['polarity']='NEGATIVE'
        self.assertEqual(candidates([self.view()]),([],[]))
    def test_deterministic_budget_frontier_and_small_audit(self):
        v=self.view();conf=dict(CONFIG,budget=1)
        a=run([v],conf);b=run([v],conf);self.assertEqual(a,b)
        self.assertEqual(a['methods']['relation']['executed'],1)
        self.assertEqual(audit_items(a),audit_items(b))


if __name__=='__main__':unittest.main()
