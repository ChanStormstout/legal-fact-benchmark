import copy
import unittest
from legal_bench.fast_development import import_case
from legal_bench.typed_relations import import_edges, execute, generate, summarize_patterns, relation_value, validate_query


class TypedRelationTests(unittest.TestCase):
    def setUp(self):
        self.ev={'segment_id':'s1','quote':'T leased building A. T occupies room B in A. T belongs to group G.'}
        self.source={'case_id':'c','url':'https://example.org/c','text_sha256':'x','segments':[dict(id='s1',text=self.ev['quote'],page=1)]}
        def obj(oid,kind):return {'id':oid,'kind':kind,'label':oid,'identity_resolved':True,'evidence':[self.ev]}
        def event(eid,typ,roles):return {'id':eid,'unit_id':'u','kind':'FACT','type':typ,'roles':roles,
              'role_evidence':{k:[self.ev] for k in roles},'status':'NARRATED','polarity':'POSITIVE','evidence':[self.ev],
              'status_evidence':[],'time':None,'origin':{},'scope':{},'scope_parsed':True,'attributes':{},'unresolved':[]}
        self.ann={'case_id':'c','objects':[obj('T','PERSON'),obj('A','PROPERTY'),obj('B','PROPERTY'),obj('G','GROUP'),obj('C','PROPERTY')],
          'units':[{'id':'u','primary':True,'evidence':[self.ev]}],
          'events':[event('a','LEASE_PROPERTY',{'tenant':'T','property':'A'}),event('b','OCCUPY_PROPERTY',{'occupant':'T','property':'B'})]}
        self.q={'atoms':[{'var':'a','type':'LEASE_PROPERTY','status':'NARRATED'},{'var':'b','type':'OCCUPY_PROPERTY','status':'NARRATED'}],
          'constraints':[{'op':'different','left':'a.id','right':'b.id'},{'op':'part_of','left':'b.roles.property','right':'a.roles.property'}]}
        self.target={'parent_pairs':[{'left':'B','right':'A'}],'group_ids':['G']}
        self.reply={'edges':[{'op':'part_of','left':'B','right':'A','decision':'SUPPORTED','evidence':[self.ev],
                             'explanation':'explicit room in building','stage_scope':'source background'}],'group_reviews':[{'group_id':'G'}]}
    def data(self):
        v=import_case(self.ann,self.source);return v,import_edges(v,self.source,self.reply,self.target)
    def test_part_does_not_turn_into_identity(self):
        v,r=self.data();self.assertEqual(execute(v,r,self.q)['status'],'MATCH')
        q=copy.deepcopy(self.q);q['constraints'][1]['op']='same'
        self.assertEqual(execute(v,r,q)['status'],'NOT_FOUND')
    def test_reverse_direction_is_not_inferred(self):
        v,r=self.data();q=copy.deepcopy(self.q);c=q['constraints'][1];c['left'],c['right']=c['right'],c['left']
        self.assertEqual(execute(v,r,q)['status'],'UNKNOWN')
    def test_missing_edge_is_unknown_not_false(self):
        v,r=self.data();r['edges']=[]
        self.assertEqual(execute(v,r,self.q)['status'],'UNKNOWN')
    def test_explicit_denial_is_distinct_from_missing(self):
        self.reply['edges'][0]['decision']='DENIED';v,r=self.data()
        self.assertEqual(execute(v,r,self.q)['status'],'NOT_FOUND')
    def test_conflicting_edge_evidence_retained_as_unknown(self):
        denied=copy.deepcopy(self.reply['edges'][0]);denied['decision']='DENIED';self.reply['edges'].append(denied)
        v,r=self.data();self.assertEqual(execute(v,r,self.q)['status'],'UNKNOWN')
    def test_source_silent_parent_proposal_cannot_compute(self):
        self.reply['edges'][0]['evidence']=[{'segment_id':'s1','quote':'fabricated'}]
        v,r=self.data();self.assertEqual(len(r['edges']),0);self.assertEqual(r['rejected'][0]['reason'],'UNLOCATED_EDGE_EVIDENCE')
        self.assertEqual(execute(v,r,self.q)['status'],'UNKNOWN')
    def test_transitive_property_relation_not_inferred(self):
        v,r=self.data();r['edges'].append({'id':'x','op':'part_of','left':'A','right':'C','decision':'SUPPORTED'})
        self.assertEqual(relation_value(r,{o['id']:o for o in v['objects']},'part_of','B','C')[0],'UNKNOWN')
    def test_membership_does_not_assign_group_event_to_person(self):
        self.ann['events'][1]['roles']['occupant']='G'
        self.reply['edges'].append({'op':'member_of','left':'T','right':'G','decision':'SUPPORTED','evidence':[self.ev]})
        v,r=self.data();q=copy.deepcopy(self.q);q['constraints'][1]={'op':'member_of','left':'a.roles.tenant','right':'b.roles.occupant'}
        x=execute(v,r,q);self.assertEqual(x['status'],'MATCH');self.assertEqual(v['events'][1]['roles']['occupant'],'G')
        q['constraints'][1]['op']='same';self.assertEqual(execute(v,r,q)['status'],'NOT_FOUND')
    def test_blocked_identity_not_overridden_by_new_edge(self):
        self.ann['objects'][2]['identity_resolved']=False
        v,r=self.data();self.assertEqual(execute(v,r,self.q)['status'],'UNKNOWN');self.assertEqual(generate([v],{'c':r})['typed'],[])
    def test_unknown_time_does_not_block_nontemporal_relation(self):
        self.ann['events'][1]['unresolved']=[{'field':'time','reason':'unknown date'}]
        v,r=self.data();self.assertEqual(execute(v,r,self.q)['status'],'MATCH')
    def test_unparsed_qualifier_is_not_circumvented(self):
        self.ann['events'][1]['scope']={'qualifier':'unclear'};self.ann['events'][1]['scope_parsed']=False
        v,r=self.data();self.assertEqual(execute(v,r,self.q)['status'],'UNKNOWN')
    def test_self_part_and_wrong_kinds_do_not_match(self):
        v,r=self.data();objs={o['id']:o for o in v['objects']}
        self.assertEqual(relation_value(r,objs,'part_of','A','A')[0],'MISMATCH')
        self.assertEqual(relation_value(r,objs,'part_of','T','A')[0],'MISMATCH')
    def test_display_family_preserves_different_role_queries(self):
        q=copy.deepcopy(self.q);q['constraints'][1]['left']='b.roles.occupant'
        ps=[{'id':'one','query':self.q,'repeated':True},{'id':'two','query':q,'repeated':False}]
        fs=summarize_patterns(ps);self.assertEqual(len(fs),1);self.assertEqual(fs[0]['query_ids'],['one','two']);self.assertEqual(fs[0]['repeated_variants'],1)
    def test_compact_trace_keeps_resolvable_assertions_and_edge_ids(self):
        v,r=self.data();w=execute(v,r,self.q)['witnesses'][0]
        self.assertEqual(w['binding'],{'a':'a','b':'b'});self.assertEqual({x['event_id'] for x in w['evidence_refs']},{'a','b'})
        self.assertEqual(w['relation_edge_refs'],[r['edges'][0]['id']]);self.assertNotIn('evidence',w)
    def test_generated_queries_are_deterministic_and_supported_language(self):
        v,r=self.data();a=generate([v],{'c':r});b=generate([v],{'c':r});self.assertEqual(a,b);self.assertEqual(len(a['typed']),1)
        for qs in a.values():
            for text in qs:
                import json
                self.assertIsNone(validate_query(json.loads(text)))
    def test_arbitrary_operator_and_nonrole_relation_rejected(self):
        q=copy.deepcopy(self.q);q['constraints'][1]['op']='execute_code';self.assertTrue(validate_query(q))
        q=copy.deepcopy(self.q);q['constraints'][1]['left']='a.time';self.assertTrue(validate_query(q))


if __name__=='__main__':unittest.main()
