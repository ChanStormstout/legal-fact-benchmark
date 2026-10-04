import unittest
from legal_bench.rules_verdict_v1.rgcn_feasibility_v1 import *

class GraphChecks(unittest.TestCase):
    def graph(self):
        return {'nodes':[{'id':'a','kind':'object','text':'tenant'},{'id':'b','kind':'object','text':'group'}], 'edges':[{'source':'a','target':'b','relation':'member_of','certainty':'SOURCE_PROPOSED','evidence':[{'segment_id':'s1'}]}]}
    def test_unknown_not_edge(self):
        g=self.graph();g['edges'][0]['certainty']='UNKNOWN'
        with self.assertRaisesRegex(ValueError,'UNKNOWN'):validate_graph(g)
    def test_directed_normalization(self):
        a=adjacency(self.graph());self.assertEqual(a['member_of'][1][0],1);self.assertEqual(a['member_of'][0][1],0);self.assertEqual(a['member_of:inverse'][0][1],1)
    def test_no_gold_relation(self):
        g=self.graph();g['edges'][0]['relation']='correct_authority'
        with self.assertRaises(ValueError):validate_graph(g)
    def test_features_ignore_id(self):
        g=self.graph();x=features(g);g['nodes'][0]['id']='different';self.assertEqual(x,features(g))
    def test_no_alignment_no_pretend_B(self):
        with self.assertRaisesRegex(ValueError,'NOT_READY'):simple_rank(self.graph(),[])
    def test_unknowns_cannot_train(self):
        self.assertFalse(training_gate([],[],{},[],{})['ready'])
    def test_dispute_leakage(self):
        g=training_gate(['c1'],['c2'],{},[],{'c1':'same','c2':'same'});self.assertIn('DISPUTE_GROUP_LEAKAGE',g['reasons'])
    def test_mlx_shapes_and_gradient(self):
        import mlx.core as mx
        from legal_bench.rules_verdict_v1.rgcn_mlx_v1 import TinyRGCN,tensors,fit
        g=self.graph();x,a=tensors(g);mx.random.seed(20261004);m=TinyRGCN(a)
        scores=m.pair_scores(x,a,0,[1]);mx.eval(scores);self.assertEqual(scores.shape,(1,))
        with self.assertRaisesRegex(ValueError,'GATE_CLOSED'):fit(m,{},[],{'ready':False})
        # Numerical derivatives only, not a legal training/evaluation result.
        import mlx.nn as nn
        value,grad=nn.value_and_grad(m,lambda mm:mx.sum(mm.pair_scores(x,a,0,[1])))(m)
        mx.eval(value,grad);self.assertTrue(math.isfinite(value.item()))
if __name__=='__main__':unittest.main()
