"""Contract failures, source/state fidelity and actual PyG inference without fitting."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tests.test_pipeline_diagnostic_v19_8 import pair, part
from legal_bench.proof_carrying import local_pipeline_v19_8 as legacy
from legal_bench.proof_carrying import evidence_binding_gate_v20_5 as binding
from legal_bench.historical_contrasts_v1 import adapter, graph, ranking, contrasts, pipeline
from legal_bench.historical_contrasts_v1.contracts import ContractError, TASK, digest, seal, validate, read_json, write_immutable


def reviews(raw,case,rules):
    rows=[]
    for pid,unit in raw['analyses'].items():
        for coll in ('uses','judgments'):
            for i,row in enumerate(unit[coll]):
                for role,ref in row['role_objects'].items():
                    if ref=='UNMAPPED':continue
                    path=['analyses',pid,coll,i,'role_objects',role]
                    rows.append({'path':path,'claim_sha256':digest(binding.binding_claim(raw,path)),
                        'label':'SUPPORTED','refs':['SRC:1'],'reason':'Synthetic fixture review; no real legal annotation.'})
    return {'payload_sha256':digest(raw),'source_sha256':digest(case['segments']),
            'rule_sha256':digest(rules),'verdicts':rows}


def fixture(cid='QUERY', reviewed=True, change=None, technical_status='OK'):
    c,r,raw=pair();c['case_id']=cid;c['dispute_id']=cid
    c['targets'][0]['text']='Synthetic tenancy entitlement and evidence query.'
    r[0]['jurisdiction']='urn:jurisdiction:synthetic';r[0]['stage']='trial'
    if change:change(c,r,raw)
    sc=legacy.schema(r,c);rv=reviews(raw,c,r) if reviewed else None
    return adapter.packet(c,r,part(c,r),raw,sc,rv,technical_status)


def setup():
    q=fixture();refs=[fixture('A'),fixture('B')]
    g=graph.build(refs,q);p=ranking.candidate_pool(g,refs,q);f=graph.hashed_features(g)
    req=ranking.request(g,p,f,'TEST',None);rank=ranking.baseline(req,g,p,f)
    return q,refs,g,p,f,req,rank


def review_fixture(g,p,rank):
    ids=rank['body']['selected_ids'];a,b=ids[:2]
    candidates={c['uid']:c for c in p['body']['candidates']}
    def sources(uid):
        return [n['uid'] for n in g['body']['nodes'] if n['node_type']=='SOURCE' and n['case_id']==candidates[uid]['case_id'] and n['text'].strip()][:1]
    ar,br=sources(a),sources(b)
    scope=copy.deepcopy(candidates[a]['scope']);scope.update(legal_period='urn:period:test',claim_type='urn:claim:test',route_family='urn:route:test')
    body={'task_id':TASK,'graph_sha256':g['sha256'],'pool_sha256':p['sha256'],'left':a,'right':b,
        'route_family':scope['route_family'],'checked_scope':scope,'left_outcome':'SUCCESS',
        'right_outcome':'FAILURE','left_outcome_refs':ar,'right_outcome_refs':br,
        'scope_left_refs':ar,'scope_right_refs':br,
        'distinctions':[{'text':'Synthetic source-reviewed difference only.','left_refs':ar,
                        'right_refs':br,'review':'MODEL_SOURCE_REVIEWED','status':'SUPPORTED'}],
        'review':'MODEL_SOURCE_REVIEWED','reviewer_id':'SYNTHETIC_TEST',
        'review_version':'1','label_origin':'SYNTHETIC_NOT_REAL_ANNOTATION'}
    return seal('ContrastReview',body)


class Contracts(unittest.TestCase):
    def test_full_roundtrip_preserves_every_legacy_value_and_order(self):
        q=fixture();self.assertEqual(read_json_roundtrip(q),q)
        old=q['body']['legacy'];self.assertEqual(adapter.handoff(q)['formal_answer'],old['payload'])
        self.assertFalse(q['body']['legal_approval'])

    def test_same_local_ids_in_different_cases_are_globally_distinct(self):
        a,b=fixture('A'),fixture('B')
        self.assertEqual([s['local_id'] for s in a['body']['sources']],[s['local_id'] for s in b['body']['sources']])
        self.assertFalse({s['uid'] for s in a['body']['sources']}&{s['uid'] for s in b['body']['sources']})

    def test_bad_reference_preserved_and_quarantined_not_fixed(self):
        def bad(c,r,x):x['analyses']['R1.P1']['uses'][0]['records']=['EV:999']
        q=fixture(change=bad);self.assertTrue(q['body']['errors']);self.assertEqual(q['body']['records'],[])
        self.assertEqual(q['body']['legacy']['payload']['analyses']['R1.P1']['uses'][0]['records'],['EV:999'])
        self.assertIsNone(adapter.handoff(q)['formal_answer'])

    def test_missing_role_is_pending_and_high_score_cannot_unblock(self):
        def missing(c,r,x):x['analyses']['R1.P1']['uses'][0]['role_objects']['tenant']='UNMAPPED'
        q=fixture(change=missing);self.assertNotEqual(q['body']['contract_status'],'READY_FOR_CONDITIONAL_PROCESSING')
        self.assertFalse(any(r['computational_eligible'] for r in q['body']['records']))
        self.assertIsNone(adapter.handoff(q)['formal_answer'])

    def test_technical_failure_is_null_not_unknown(self):
        q=fixture(technical_status='OUTPUT_TRUNCATED')
        self.assertEqual(q['body']['records'],[]);self.assertIsNone(adapter.handoff(q)['formal_answer'])
        self.assertEqual(adapter.handoff(q)['technical_status'],'OUTPUT_TRUNCATED')

    def test_stale_binding_review_does_not_become_accepted(self):
        q=fixture();old=copy.deepcopy(q['body']['legacy']);old['reviews']['payload_sha256']='stale'
        v=adapter.packet(old['case'],old['rules'],old['part'],old['payload'],old['original_schema'],old['reviews'])
        self.assertIsNone(adapter.handoff(v)['formal_answer'])

    def test_source_text_offset_and_origin_tampering_rejected(self):
        q=fixture()
        for change in ('text','end','original'):
            b=copy.deepcopy(q['body'])
            if change=='text':b['sources'][0]['text']='Changed'
            elif change=='end':b['sources'][0]['end']+=1
            else:b['sources'][0]['original']['text']='Changed';b['sources'][0]['text']='Changed'
            with self.subTest(change=change),self.assertRaises(ContractError):seal('CasePacket',b)

    def test_source_deletion_and_global_id_reuse_rejected(self):
        q=fixture()
        for op in ('delete','uid'):
            b=copy.deepcopy(q['body'])
            if op=='delete':b['sources'].pop()
            else:b['sources'][0]['uid']='SOURCE:wrong'
            with self.subTest(op=op),self.assertRaises(ContractError):seal('CasePacket',b)

    def test_versions_extra_fields_and_hashes_rejected(self):
        q=fixture()
        for field,value in [('schema_version','historical-contrasts/2.0'),('sha256','wrong'),('extra',1)]:
            b=copy.deepcopy(q);b[field]=value
            with self.subTest(field=field),self.assertRaises(ContractError):validate(b)

    def test_gate_and_technical_status_cannot_be_promoted_in_packet(self):
        pending=fixture(reviewed=False);b=copy.deepcopy(pending['body']);b['contract_status']='READY_FOR_CONDITIONAL_PROCESSING'
        with self.assertRaises(ContractError):seal('CasePacket',b)
        failed=fixture(technical_status='OUTPUT_TRUNCATED');b=copy.deepcopy(failed['body']);b['technical_status']='OK'
        with self.assertRaises(ContractError):seal('CasePacket',b)

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'bad.json';p.write_text('{"x":1,"x":2}')
            with self.assertRaises(ContractError):read_json(p)

    def test_immutable_outputs_refuse_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'result.json';write_immutable(p,{'x':1});write_immutable(p,{'x':1})
            with self.assertRaises(ContractError):write_immutable(p,{'x':2})

    def test_bool_not_accepted_as_integer(self):
        q,refs,g,p,f,req,r=setup();b=copy.deepcopy(req['body']);b['seed']=True
        with self.assertRaises(ContractError):seal('RankRequest',b)

    def test_node_reordering_keeps_maps_and_predictions(self):
        q,refs,g,p,f,req,r=setup();b=copy.deepcopy(g['body']);b['nodes'].reverse();b['edges'].reverse()
        reordered=seal('GraphRelease',b);f2=graph.hashed_features(reordered)
        p2=ranking.candidate_pool(reordered,refs,q);rq=ranking.request(reordered,p2,f2,'TEST',None)
        r2=ranking.baseline(rq,reordered,p2,f2)
        self.assertEqual(r['body']['scores'],r2['body']['scores'])

    def test_wrong_node_map_rejected(self):
        q,refs,g,p,f,req,r=setup();b=copy.deepcopy(g['body']);b['node_map']['SOURCE'].reverse()
        with self.assertRaises(ContractError):seal('GraphRelease',b)

    def test_graph_source_text_and_actor_join_checked_against_original_packets(self):
        q,refs,g,p,f,req,r=setup()
        for field in ('text','case_id'):
            b=copy.deepcopy(g['body']);n=next(n for n in b['nodes'] if n['node_type']=='SOURCE')
            n[field]='wrong'
            with self.subTest(field=field),self.assertRaises(ContractError):ranking.candidate_pool(seal('GraphRelease',b),refs,q)

    def test_graph_edge_loss_rejected_and_request_query_must_match(self):
        q,refs,g,p,f,req,r=setup();b=copy.deepcopy(g['body']);b['edges'].pop()
        with self.assertRaises(ContractError):ranking.candidate_pool(seal('GraphRelease',b),refs,q)
        with self.assertRaises(ContractError):ranking.request(g,p,f,'TEST',query_id='WRONG_QUERY')

    def test_query_without_rules_can_retrieve_but_cannot_make_a_legal_answer(self):
        q=fixture();old=q['body']['legacy'];part_value={**old['part'],'rule_ids':[]}
        value=adapter.packet(old['case'],[],part_value,{'analyses':{},'object_links':[],'coverage_limits':[]},
                             legacy.schema([],old['case']))
        g=graph.build([fixture('A')],value);p=ranking.candidate_pool(g,[fixture('A')],value)
        self.assertEqual(len(p['body']['candidates']),1)
        self.assertIsNone(adapter.handoff(value)['formal_answer'])

    def test_query_dispute_group_excluded_before_graph_and_pool(self):
        q=fixture();a=fixture('A')
        old=copy.deepcopy(a['body']['legacy']);old['case']['dispute_id']='QUERY'
        same=adapter.packet(old['case'],old['rules'],old['part'],old['payload'],old['original_schema'],old['reviews'])
        g=graph.build([same,q],q);p=ranking.candidate_pool(g,[same,q],q)
        self.assertEqual(p['body']['candidates'],[])
        self.assertTrue(all(n['case_id']=='QUERY' for n in g['body']['nodes']))

    def test_duplicate_reference_snapshot_rejected(self):
        q=fixture();a=fixture('A')
        with self.assertRaises(ContractError):graph.build([a,a],q)

    def test_context_direction_is_preserved_separately(self):
        def change(c,r,x):x['analyses']['R1.P1']['uses'][0]['direction']='CONTEXT'
        q=fixture(change=change);self.assertTrue(any(r['direction']=='CONTEXT' for r in q['body']['records']))
        g=graph.build([fixture('A')],q)
        self.assertTrue(any(e['relation']=='PROPOSED_CONTEXT' for e in g['body']['edges']))

    def test_not_analyzed_with_artifacts_cannot_enter_computation(self):
        def change(c,r,x):x['analyses']['R1.P1']['analysis_status']='NOT_ANALYZED'
        q=fixture(change=change)
        self.assertEqual(q['body']['contract_status'],'REJECTED_STATUS_CONSISTENCY')
        with patch.object(adapter.gate,'process_saved') as entry:
            self.assertIsNone(adapter.handoff(q)['formal_answer']);entry.assert_not_called()
        self.assertTrue(q['body']['legacy']['payload']['analyses']['R1.P1']['uses'])

    def test_multi_query_requires_explicit_selection(self):
        q=fixture();old=copy.deepcopy(q['body']['legacy']);old['case']['targets'].append({'id':'Q2','text':'Another distinct inquiry.'})
        args=[old['case'],old['rules'],old['part'],old['payload'],old['original_schema']]
        with self.assertRaises(ContractError):adapter.packet(*args)
        selected=adapter.packet(*args,query_id='Q2')
        self.assertEqual(selected['body']['query_text'],'Another distinct inquiry.')
        self.assertEqual(len(selected['body']['legacy']['case']['targets']),2)

    def test_test_or_sealed_input_rejected(self):
        q=fixture();old=copy.deepcopy(q['body']['legacy'])
        for split in ('TEST','SEALED'):
            old['case']['split']=split
            with self.subTest(split=split),self.assertRaises(ContractError):adapter.packet(old['case'],old['rules'],old['part'],old['payload'],old['original_schema'])
        old['case'].pop('split');old['case'].pop('dispute_id')
        with self.assertRaises(ContractError):adapter.packet(old['case'],old['rules'],old['part'],old['payload'],old['original_schema'])

    def test_record_projection_tampering_and_dependency_loss_rejected(self):
        q=fixture()
        for op in ('text','dependency','origin','role'):
            b=copy.deepcopy(q['body']);use=next(r for r in b['records'] if r['kind']=='USE')
            if op=='text':use['text']='Invented claim'
            elif op=='dependency':use['dependency_ids'].pop()
            elif op=='origin':use['original']['claim']='Invented claim'
            else:next(r for r in b['records'] if r['kind']=='BINDING')['text']='Wrong actor'
            with self.subTest(op=op),self.assertRaises(ContractError):seal('CasePacket',b)

    def test_unicode_original_character_and_byte_offsets_are_independent(self):
        import hashlib
        from legal_bench.historical_contrasts_v1 import provenance
        with tempfile.TemporaryDirectory() as tmp:
            text='租赁 Ω';path=Path(tmp)/'source.txt';path.write_text(text)
            def change(c,r,x):
                s=c['segments'][0];s['text']=text
                s['provenance']=[{'raw_path':'source.txt','raw_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                    'raw_char_range':[0,len(text)],'raw_byte_range':[0,len(text.encode())],'document_id':s['source_document']}]
            q=fixture(change=change);self.assertEqual(provenance.audit(q,tmp)['checked_original_spans'],1)
            path.write_text(text+' changed')
            with self.assertRaises(ContractError):provenance.audit(q,tmp)

    def test_supervision_edges_and_review_fields_not_model_inputs(self):
        q,refs,g,p,f,req,r=setup();b=copy.deepcopy(g['body']);e=copy.deepcopy(b['edges'][0]);e['relation']='UTILITY_POSITIVE'
        nodes={n['uid']:n for n in b['nodes']};b['edges'].append(e)
        b['relation_types'].append('|'.join((nodes[e['src']]['node_type'],e['relation'],nodes[e['dst']]['node_type'])))
        with self.assertRaises(ContractError):seal('GraphRelease',b)
        self.assertNotIn('review_reason',g['body']['visibility_manifest']['feature_fields'])

    def test_long_text_all_windows_and_coverage_gap_detection(self):
        q,refs,g,p,f,req,r=setup();b=copy.deepcopy(g['body']);b['nodes'][0]['text']='word '*1400
        g2=seal('GraphRelease',b);f2=graph.hashed_features(g2)
        row=next(x for x in f2['coverage'] if x['uid']==b['nodes'][0]['uid'])
        self.assertEqual(row['encoded_tokens'],1400);self.assertEqual(len(row['windows']),3)
        row['encoded_tokens']=512;f2['sha256']=digest({k:v for k,v in f2.items() if k!='sha256'})
        with self.assertRaises(ContractError):graph.check_features(g2,f2)

    def test_feature_dimension_nan_and_stale_graph_rejected(self):
        q,refs,g,p,f,req,r=setup()
        for op in ('dimension','nan','graph'):
            bad=copy.deepcopy(f);uid=next(iter(bad['vectors']))
            if op=='dimension':bad['vectors'][uid].pop()
            elif op=='nan':bad['vectors'][uid][0]=float('nan')
            else:bad['graph_sha256']='stale'
            with self.subTest(op=op),self.assertRaises((ContractError,ValueError)):
                bad['sha256']=digest({k:v for k,v in bad.items() if k!='sha256'});graph.check_features(g,bad)

    def test_scope_unknown_is_not_false_and_descriptive_difference_not_mismatch(self):
        scope={k:None for k in ('jurisdiction','stage','legal_period','claim_type','route_family')}
        a={**scope,'jurisdiction':'India; Delhi law'};b={**scope,'jurisdiction':'Delhi legislation'}
        self.assertEqual(ranking.compare_scope(a,b)[0],'PENDING')
        self.assertEqual(ranking.compare_scope({**a,'stage':'trial'},{**b,'stage':'appeal'})[0],'INCOMPATIBLE')

    def test_signed_signature_separates_opposition_and_missing_is_unavailable(self):
        from legal_bench.historical_contrasts_v1.signatures import profile
        def change(c,r,x):x['analyses']['R1.P1']['uses'][0]['direction']='OPPOSE'
        q=fixture(change=change);g=graph.build([],q)
        sig=profile(g,[r['uid'] for r in q['body']['routes']])
        self.assertGreater(sig['negative_edges'],0);self.assertGreater(sig['positive_edges'],0)
        bad=fixture(change=lambda c,r,x:x['analyses']['R1.P1']['uses'][0].update(records=['EV:999']))
        bg=graph.build([],bad)
        self.assertFalse(profile(bg,[r['uid'] for r in bad['body']['routes']])['available'])

    def test_rrf_and_lexical_use_same_complete_pool(self):
        q,refs,g,p,f,req,r=setup();rq=ranking.request(g,p,f,'TEST',None,scorer='RRF')
        rr=ranking.baseline(rq,g,p,f)
        self.assertEqual({s['uid'] for s in rr['body']['scores']},{s['uid'] for s in r['body']['scores']})
        self.assertFalse(rr['body']['semantic_approval'])

    def test_result_invention_omission_nan_and_promotion_rejected(self):
        q,refs,g,p,f,req,r=setup()
        for op in ('invent','omit','nan','promote'):
            b=copy.deepcopy(r['body'])
            if op=='invent':b['scores'][0]['uid']='invented'
            elif op=='omit':b['scores'].pop();b['selected_ids'].pop()
            elif op=='nan':b['scores'][0]['score']=float('nan')
            else:b['runtime_status']='OK'
            with self.subTest(op=op),self.assertRaises((ContractError,ValueError)):
                wrong=seal('RankResult',b);ranking.validate_result(wrong,req,g,p)

    def test_request_source_and_task_mismatches_rejected(self):
        q,refs,g,p,f,req,r=setup()
        for op in ('graph','task','source'):
            with self.subTest(op=op),self.assertRaises(ContractError):
                if op=='graph':
                    b=copy.deepcopy(req['body']);b['graph_sha256']='old';ranking.join(seal('RankRequest',b),g,p)
                elif op=='task':
                    b=copy.deepcopy(req['body']);b['task_id']='OLD_USE_CLASSIFICATION';seal('RankRequest',b)
                else:
                    b=copy.deepcopy(p['body']);b['candidates'][0]['source_ids']=['invented'];ranking.join(req,g,seal('CandidatePool',b))

    def test_sampling_stable_permutation_bounded_and_no_unsampled_edges(self):
        q,refs,g,p,f,req,r=setup();seeds=[c['route_id'] for c in p['body']['candidates']]
        a=graph.sample(g,seeds,[1,1],7);b=graph.sample(g,seeds[::-1],[1,1],7)
        self.assertEqual(a,b);self.assertTrue(all(x['sampled']<=1 for x in a['counts']))
        self.assertTrue(set(a['node_ids'])<={n['uid'] for n in g['body']['nodes']})

    def test_without_review_no_contrast_created(self):
        q,refs,g,p,f,req,r=setup();bundle=contrasts.form(r,req,g,p)
        self.assertEqual(bundle['body']['contrasts'],[]);self.assertEqual(len(bundle['body']['pending']),2)

    def test_source_bound_review_retains_conditional_not_legal_approval(self):
        q,refs,g,p,f,req,r=setup();review=review_fixture(g,p,r)
        bundle=contrasts.form(r,req,g,p,[review]);self.assertEqual(len(bundle['body']['contrasts']),1)
        self.assertFalse(bundle['body']['legal_approval']);self.assertFalse(bundle['body']['semantic_approval'])

    def test_wrong_case_stale_or_empty_distinction_review_rejected(self):
        q,refs,g,p,f,req,r=setup();review=review_fixture(g,p,r)
        for op in ('source','stale','empty','stage'):
            b=copy.deepcopy(review['body'])
            if op=='source':b['distinctions'][0]['left_refs']=b['right_outcome_refs']
            elif op=='stale':b['pool_sha256']='stale'
            elif op=='empty':b['distinctions']=[]
            else:b['checked_scope']['stage']='appeal'
            with self.subTest(op=op),self.assertRaises(ContractError):contrasts.form(r,req,g,p,[seal('ContrastReview',b)])

    def test_unknown_relevance_not_negative_and_exposed_train_rejected(self):
        q,refs,g,p,f,req,r=setup();c=p['body']['candidates'][0]
        qref=next(n['uid'] for n in g['body']['nodes'] if n['node_type']=='SOURCE' and n['case_id']=='QUERY')
        cref=next(n['uid'] for n in g['body']['nodes'] if n['node_type']=='SOURCE' and n['case_id']==c['case_id'])
        b={'task_id':TASK,'pool_sha256':p['sha256'],'candidate_id':c['uid'],'query_group_id':'QUERY',
            'candidate_group_id':c['group_id'],'split':'DEV','utility':'UNKNOWN','candidate_refs':[cref],
            'query_refs':[qref],'reason':'Unknown utility.','review':'MODEL_SOURCE_REVIEWED','label_origin':'SYNTHETIC'}
        self.assertEqual(contrasts.training_pairs(g,p,[seal('RelevanceLabel',b)])['pairs'],[])
        b.update(split='TRAIN',utility='POSITIVE')
        with self.assertRaises(ContractError):contrasts.training_pairs(g,p,[seal('RelevanceLabel',b)],['QUERY'])
        with self.assertRaises(ContractError):contrasts.training_pairs(g,p,[seal('RelevanceLabel',b)])

    def test_end_to_end_normal_and_blocked_paths_preserve_old_gate(self):
        q=fixture();refs=[fixture('A'),fixture('B')]
        with tempfile.TemporaryDirectory() as tmp:
            accepted=pipeline.run(q,refs,Path(tmp)/'normal')
            self.assertTrue(accepted['formal_answer_present']);self.assertEqual(accepted['training_calls'],0)
            unknown=fixture(reviewed=False)
            blocked=pipeline.run(unknown,refs,Path(tmp)/'blocked')
            self.assertFalse(blocked['formal_answer_present']);self.assertEqual(blocked['accepted_contrasts'],0)


def read_json_roundtrip(value):
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)/'packet.json';write_immutable(p,value);return read_json(p)


class NeuralContracts(unittest.TestCase):
    def test_actual_pinned_encoder_long_text_and_token_replay(self):
        from legal_bench.historical_contrasts_v1.encoder import encode,verify_tokenization
        from transformers import AutoTokenizer
        import torch
        torch.set_num_threads(2)
        q=fixture(change=lambda c,r,x:c['segments'][0].update(text='tenancy '*1400))
        refs=[fixture('A'),fixture('B')];g2=graph.build(refs,q)
        source=next(n for n in g2['body']['nodes'] if n['node_type']=='SOURCE' and n['case_id']=='QUERY')
        cfg=read_json(Path(__file__).resolve().parents[1]/'outputs/gnn-irac-aligned-v2/text-cache/encoder.json')
        encoded=encode(g2,cfg,batch_size=8)
        row=next(r for r in encoded['coverage'] if r['uid']==source['uid'])
        self.assertGreater(row['token_count'],512);self.assertGreater(len(row['windows']),1)
        self.assertEqual(row['encoded_tokens'],row['token_count']);self.assertEqual(len(encoded['vectors'][source['uid']]),384)
        row['token_ids'][0]+=1;row['token_ids_sha256']=digest(row['token_ids'])
        encoded['sha256']=digest({k:v for k,v in encoded.items() if k!='sha256'})
        tok=AutoTokenizer.from_pretrained(cfg['path'],local_files_only=True)
        with self.assertRaises(ContractError):verify_tokenization(g2,encoded,tok)

    def test_real_pyg_forward_mapping_empty_types_finite_and_weights_unchanged(self):
        from legal_bench.historical_contrasts_v1 import model
        q,refs,g,p,f,req,r=setup();net,ck=model.initialize_smoke(g,f)
        nr=ranking.request(g,p,f,'TEST',None,'SAGE_SMOKE',ck)
        out,data,mapping=model.rank(nr,g,p,f,net,ck)
        self.assertEqual(out['body']['runtime_status'],'UNTRAINED_SMOKE')
        self.assertEqual(ck['sha256'],model.state_hash(net))
        self.assertEqual({x['uid'] for x in out['body']['scores']},{x['uid'] for x in r['body']['scores']})
        self.assertEqual(data['LINK'].x.shape[0],0)
        for edge_type in data.edge_types:self.assertEqual(data[edge_type].edge_index.shape[0],2)

    def test_untrained_checkpoint_cannot_be_production(self):
        from legal_bench.historical_contrasts_v1 import model
        q,refs,g,p,f,req,r=setup();net,ck=model.initialize_smoke(g,f)
        with self.assertRaises(ContractError):ranking.request(g,p,f,'TEST',None,'SAGE',ck)

    def test_actual_neural_output_invariant_to_node_edge_order(self):
        from legal_bench.historical_contrasts_v1 import model
        q,refs,g,p,f,req,r=setup();net,ck=model.initialize_smoke(g,f)
        nr=ranking.request(g,p,f,'TEST',None,'SAGE_SMOKE',ck);a,_,_=model.rank(nr,g,p,f,net,ck)
        b=copy.deepcopy(g['body']);b['nodes'].reverse();b['edges'].reverse();g2=seal('GraphRelease',b)
        f2=graph.hashed_features(g2);p2=ranking.candidate_pool(g2,refs,q)
        nr2=ranking.request(g2,p2,f2,'TEST',None,'SAGE_SMOKE',ck);out,_,_=model.rank(nr2,g2,p2,f2,net,ck)
        self.assertEqual(a['body']['scores'],out['body']['scores'])

    def test_real_pyg_pipeline_tensor_roundtrip_and_idempotence(self):
        q=fixture();refs=[fixture('A'),fixture('B')]
        with tempfile.TemporaryDirectory() as tmp:
            out=pipeline.run(q,refs,tmp,neural_smoke=True)
            self.assertEqual(out['neural_runtime_status'],'UNTRAINED_SMOKE')
            self.assertEqual(pipeline.run(q,refs,tmp,neural_smoke=True),out)


if __name__=='__main__':unittest.main()
