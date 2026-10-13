import copy, json, tempfile, unittest
from pathlib import Path
from legal_bench.historical_contrasts_v1.contracts import ContractError,digest
from legal_bench.historical_contrasts_v1.graph import hashed_features
from legal_bench.historical_contrasts_v1.model import Ranker,state_hash
from legal_bench.historical_contrasts_v2 import data,graph,metrics,train
import torch

def view(cid,split='TRAIN',reference=False):
    source={'case_id':cid,'group_id':cid,'segments':[{'id':cid+':L1','text':'The tenant claims retained control.'},
        {'id':cid+':L2','text':'Target court decided eviction.'}],'input_scope':'fixture','split':split}
    review={'case_id':cid,'excluded_input_ids':[cid+':L2'],'visibility_reason':'Remove target disposition.'}
    if reference:source['allowed_input']=source.pop('segments')
    return data.mask_view(source,review,reference)

class Contracts(unittest.TestCase):
    def export_fixture(self,root,stem,cid):
        review={'queries':[{'case_id':cid,'labels':[{'candidate_case_id':'r'}]}]}
        tasks=root/'tasks';reviews=root/'reviews';tasks.mkdir(exist_ok=True);reviews.mkdir(exist_ok=True)
        material={'queries':[{'case_id':cid}],'references':[{'case_id':'r'}]}
        (tasks/(stem+'.txt')).write_text('Task\nPUBLIC SOURCE MATERIAL\n'+json.dumps(material)+'\nEND_OF_INPUT')
        path=reviews/(stem+'.json');path.write_text(json.dumps(review))
        path.with_name(stem+'-raw.txt').write_text(json.dumps(review));return path,review
    def test_stale_clipboard_export_rejected_per_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            path,review=self.export_fixture(Path(tmp),'LABELS-1','a')
            wrong={'queries':[{'case_id':'b','labels':[{'candidate_case_id':'r'}]}]}
            path.with_name('LABELS-1-raw.txt').write_text(json.dumps(wrong))
            with self.assertRaisesRegex(ContractError,'REVIEW_TASK_CASE_COVERAGE'):data.audit_export(path,wrong)
    def test_protocol_split_cannot_drift_after_annotation(self):
        bundle={'queries':[{'case_id':'q','split':'TRAIN'}],'references':[{'case_id':'r'}],'labels':[],'trainable_queries':[]}
        protocol={'query_cases':1,'reference_cases':1,'split_manifest':{'q':'VALIDATION'}}
        with self.assertRaisesRegex(ContractError,'PROTOCOL_SPLIT_MISMATCH'):train.validate_protocol(bundle,protocol)
    def test_protocol_label_join_cannot_use_holdout_for_train(self):
        bundle={'queries':[{'case_id':'q','split':'TRAIN'}],'references':[{'case_id':'r'}],
            'labels':[{'query_case_id':'q','candidate_case_id':'r','split':'DEVELOPMENT_HOLDOUT'}],'trainable_queries':[]}
        protocol={'query_cases':1,'reference_cases':1,'split_manifest':{'q':'TRAIN'}}
        with self.assertRaisesRegex(ContractError,'PROTOCOL_LABEL_JOIN'):train.validate_protocol(bundle,protocol)
    def test_multipart_merge_audits_original_parts_and_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);parts=[self.export_fixture(root,'LABELS-5A','a'),self.export_fixture(root,'LABELS-5B','b')]
            path,review=self.export_fixture(root,'LABELS-5','a');review={'queries':sum([v['queries'] for _,v in parts],[])}
            (root/'tasks/LABELS-5.txt').write_text('Task\nPUBLIC SOURCE MATERIAL\n'+json.dumps({'queries':[{'case_id':'a'},{'case_id':'b'}],'references':[{'case_id':'r'}]})+'\nEND_OF_INPUT')
            receipt={'operation':'CONCATENATE_UNCHANGED_QUERIES','parts':[p.name for p,_ in parts],'part_sha256':{p.name:digest(v) for p,v in parts}}
            path.with_name('LABELS-5-merge-receipt.json').write_text(json.dumps(receipt));data.audit_export(path,review)
            review['queries'][0]['case_id']='tampered'
            with self.assertRaisesRegex(ContractError,'REVIEW_CHANGED_DURING_MERGE'):data.audit_export(path,review)
    def test_duplicate_raw_label_key_rejected(self):
        with self.assertRaises(ContractError):data.parse_raw_review('{"utility":"NEGATIVE","utility":"POSITIVE"}')
    def test_nonfinite_raw_review_rejected(self):
        with self.assertRaises(ContractError):data.parse_raw_review('{"score":NaN}')
    def test_visibility_source_unknown_rejected(self):
        with self.assertRaises(ContractError):data.mask_view({'case_id':'a','group_id':'a','segments':[{'id':'a:1','text':'x'}],
            'input_scope':'f','split':'TRAIN'},{'case_id':'a','excluded_input_ids':['absent'],'visibility_reason':'x'})
    def test_exact_quote_not_normalized(self):
        with self.assertRaises(ContractError):data.check_quotes([{'source_id':'s','quote':'not control'}],{'s':'control'})
    def test_unknown_not_negative(self):
        x=[{'candidate_case_id':'a','utility':'UNKNOWN','split':'TRAIN'},{'candidate_case_id':'b','utility':'NEGATIVE','split':'TRAIN'}]
        self.assertEqual(data.supervision(x,'TRAIN'),{'b':0})
    def test_holdout_labels_cannot_train(self):
        with self.assertRaises(ContractError):data.supervision([{'split':'DEVELOPMENT_HOLDOUT'}],'TRAIN')
    def test_groups_cannot_cross_roles(self):
        a=view('a');b=view('b','VALIDATION');b['group_id']='a'
        with self.assertRaises(ContractError):data.check_groups([a,b])
    def test_query_group_not_reference(self):
        with self.assertRaises(ContractError):graph.build([view('a',reference=True)],view('a'))
    def test_only_one_query_and_masked_outcome_absent(self):
        refs=[view('r',reference=True)];q=view('q');g=graph.build(refs,q)
        self.assertEqual({n['case_id'] for n in g['body']['nodes']},{'r','q'})
        self.assertTrue(all('Target court decided' not in n['text'] for n in g['body']['nodes']))
        self.assertTrue(graph.check_view(g,refs,q))
    def test_changed_node_cannot_replay(self):
        refs=[view('r',reference=True)];q=view('q');g=graph.build(refs,q);g['body']['nodes'][0]['text']='forged'
        with self.assertRaises(ContractError):graph.check_view(g,refs,q)
    def test_annotation_reason_is_not_text(self):
        a=view('a');b=copy.deepcopy(a);b['source_view_review_hash']='changed-reason'
        self.assertEqual(graph.text(a),graph.text(b))
    def test_unknown_does_not_depress_judged_metric(self):
        m=metrics.evaluate({'unknown':3,'p':2,'n':1},{'p':1,'n':0})
        self.assertEqual(m['NDCG@3'],1);self.assertEqual(m['unknown_in_original_top3'],1)
    def test_no_positive_unevaluable(self):
        self.assertFalse(metrics.evaluate({'n':1},{'n':0})['evaluable'])
    def test_same_outcome_not_contrast(self):
        m=metrics.evaluate({'a':2,'b':1},{'a':1,'b':1},{'a':'SUPPORT_GROUND','b':'SUPPORT_GROUND'})
        self.assertIsNone(m['contrast_pair_coverage@3'])
    def test_opposite_outcome_pair_uses_actual_top3(self):
        m=metrics.evaluate({'u1':5,'u2':4,'a':3,'b':2},{'a':1,'b':1},{'a':'SUPPORT_GROUND','b':'OPPOSE_GROUND'})
        self.assertEqual(m['contrast_pair_coverage@3'],0)
    def test_actual_gradient_changes_weights(self):
        refs=[view('r',reference=True),view('s',reference=True)];q=view('q')
        g=graph.build(refs,q);f=hashed_features(g);d,qi,ci,_,_=graph.tensors(g,f,refs,q)
        torch.manual_seed(13);m=Ranker(g['body']['node_types'],g['body']['relation_types'],64)
        before=state_hash(m);opt=torch.optim.AdamW(m.parameters(),lr=.001)
        frame={'data':d,'qi':qi,'ci':ci};s=train.score(m,frame,'GRAPH_SAGE')
        loss=torch.nn.functional.softplus(s[1]-s[0]);loss.backward();opt.step()
        self.assertNotEqual(before,state_hash(m))
    def test_edge_ablation_preserves_original_edges(self):
        refs=[view('r',reference=True)];q=view('q');g=graph.build(refs,q);f=hashed_features(g)
        d,qi,ci,_,_=graph.tensors(g,f,refs,q);m=Ranker(g['body']['node_types'],g['body']['relation_types'],64)
        edges={k:d[k].edge_index.clone() for k in d.edge_types}
        train.score(m,{'data':d,'qi':qi,'ci':ci},'GRAPH_SAGE_NO_EDGES')
        self.assertTrue(all(torch.equal(v,d[k].edge_index) for k,v in edges.items()))

if __name__=='__main__':unittest.main()
