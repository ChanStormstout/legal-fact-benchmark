import unittest
import numpy as np
import mlx.core as mx
import mlx.nn as nn
from legal_bench.rules_verdict_v1 import rgcn_use_v1 as use
from legal_bench.rules_verdict_v1.rgcn_train_v2 import fold_data
from legal_bench.rules_verdict_v1.rgcn_development_v3 import WIDTH, EDGE_TYPES, Z_NAMES


class UseChecks(unittest.TestCase):
    def data(self, zvalue=0):
        x = np.random.default_rng(7).normal(size=(3, WIDTH)).astype(np.float32)
        adj = np.zeros((len(EDGE_TYPES), 3, 3), np.float32)
        adj[0, 1, 0] = 1
        pools = np.zeros((14, 7, 3), np.float32)
        pools[:7, :, 1] = 1
        pools[7:, :, 2] = 1
        return {k: mx.array(v) for k, v in dict(x=x, adj=adj, pools=pools, z=np.full((14, len(Z_NAMES)), zvalue, np.float32)).items()}

    def test_no_implicit_negative(self):
        labels = {'uses': [{'unit_id': 'a', 'category': 'DIRECT'}, {'unit_id': 'b', 'category': 'UNKNOWN'}],
                  'isolated': [{'unit_id': 'c', 'category': 'IRRELEVANT'}]}
        self.assertEqual(use.supervision(labels, ['a', 'b', 'c', 'd']), [(0, 0)])

    def test_case_balancing_and_held_labels_unused(self):
        model = use.UseModel('S')
        model.logits = mx.array([[2., 0., 0.]] * 14)
        data = {'a': self.data(), 'b': self.data(), 'held': self.data()}
        targets = {'a': [(0, 0)], 'b': [(i, 2) for i in range(14)]}
        expected = (nn.losses.cross_entropy(model(data['a'])[:1], mx.array([0]), reduction='mean') +
                    nn.losses.cross_entropy(model(data['b']), mx.array([2] * 14), reduction='mean')) / 2
        self.assertAlmostEqual(float(use.data_loss(model, data, targets).item()), float(expected.item()), places=6)
        model2, log = use.fit('S', data, targets, 7, steps=2)
        self.assertNotIn('held', log['trained_cases'])
        self.assertGreater(log['parameter_delta_norm'], 0)
        self.assertTrue(np.array_equal(np.array(model2(data['a'])), np.array(model2(data['held']))))

    def test_capacity_and_message_control(self):
        d = self.data(); altered = dict(d, adj=mx.zeros_like(d['adj']))
        mx.random.seed(4); c = use.UseModel('C')
        mx.random.seed(4); c0 = use.UseModel('C0')
        self.assertEqual(c(d).shape, (14, 3))
        self.assertGreater(float(np.linalg.norm(np.array(c(d)) - np.array(c(altered)))), 1e-7)
        self.assertTrue(np.array_equal(np.array(c0(d)), np.array(c0(altered))))
        probabilities, scores = use.probabilities_and_scores(c(d))
        np.testing.assert_allclose(probabilities.sum(1), 1., atol=1e-6)
        np.testing.assert_allclose(scores, 2 * probabilities[:, 0] + probabilities[:, 1])

    def test_training_fold_scaler(self):
        raw = {k: {f: np.array(v) for f, v in self.data(z).items()} for k, z in [('train', 1), ('held', 1000)]}
        _, scale = fold_data(raw, ['train'])
        self.assertEqual(scale['mean'], [1.] * len(Z_NAMES))

if __name__ == '__main__': unittest.main()
