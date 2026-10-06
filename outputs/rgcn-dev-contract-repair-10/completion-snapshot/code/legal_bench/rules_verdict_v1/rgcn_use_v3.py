"""V09: explicit pool size and CORE alias; V08 architecture/loss unchanged."""
import numpy as np
import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from mlx.utils import tree_flatten
from .rgcn_development_v4 import WIDTH, EDGE_TYPES, Z_NAMES

CLASSES = ['CORE', 'BACKGROUND', 'IRRELEVANT']
from .authority_use_v10 import ALIASES, normalize, targets
MAPPING = {k: CLASSES.index(v) for k,v in ALIASES.items() if v!='UNKNOWN'}


def supervision(labels, unit_ids):
    """Only accepted, explicitly known uses enter the loss."""
    return targets(labels['uses'],unit_ids)


class UseModel(nn.Module):
    def __init__(self, kind, units=14):
        super().__init__()
        self.kind = kind
        if kind == 'S':
            self.logits = mx.zeros((units, 3))
        elif kind == 'B':
            self.linear = nn.Linear(len(Z_NAMES), 3, bias=False)
        elif kind in ['C', 'C0']:
            self.project = nn.Linear(WIDTH, 16)
            self.self_layers = [nn.Linear(16, 16) for _ in range(2)]
            self.bases = mx.random.normal((2, 2, 16, 16)) * .05
            self.coefficients = mx.random.normal((2, len(EDGE_TYPES), 2)) * .05
            self.hidden = nn.Linear(7 * 16 + len(Z_NAMES), 16)
            self.output = nn.Linear(16, 3)
        else:
            raise ValueError('UNKNOWN_METHOD')

    def __call__(self, data):
        if self.kind == 'S':
            return self.logits
        if self.kind == 'B':
            return self.linear(data['z'])
        h = nn.relu(self.project(data['x']))
        for i in range(2):
            y = self.self_layers[i](h)
            if self.kind == 'C':
                w = mx.einsum('rb,bij->rij', self.coefficients[i], self.bases[i])
                transformed = mx.einsum('ni,rij->rnj', h, w)
                y = y + mx.einsum('rtn,rnj->tj', data['adj'], transformed)
            h = nn.relu(y)
        pooled = mx.einsum('ltn,nw->ltw', data['pools'], h).reshape(data['pools'].shape[0], -1)
        return self.output(nn.relu(self.hidden(mx.concatenate([pooled, data['z']], axis=1))))


def data_loss(model, data, targets):
    losses = []
    for cid, pairs in targets.items():
        if pairs:
            p = mx.array(pairs, dtype=mx.int32)
            losses.append(nn.losses.cross_entropy(model(data[cid])[p[:, 0]], p[:, 1], reduction='mean'))
    if not losses:
        raise ValueError('NO_ACCEPTED_USE_SUPERVISION')
    return mx.mean(mx.stack(losses))


def fit(kind, data, targets, seed, steps=200, lr=.003, l2=.001, units=30):
    if not targets or not any(targets.values()):
        raise ValueError('NO_ACCEPTED_USE_SUPERVISION')
    mx.random.seed(seed)
    model = UseModel(kind, units=units)
    mx.eval(model.parameters())
    before = {k: np.array(v) for k, v in tree_flatten(model.parameters())}
    optimizer = optim.Adam(lr)
    def loss(m):
        return data_loss(m, data, targets) + l2 * sum(mx.sum(v * v) for _, v in tree_flatten(m.trainable_parameters()))
    grad = nn.value_and_grad(model, loss)
    history = []
    first_grad = None
    for _ in range(steps):
        value, grads = grad(model)
        optimizer.update(model, grads)
        mx.eval(model.parameters(), optimizer.state, value, grads)
        if first_grad is None:
            first_grad = float(sum(mx.sum(v * v).item() for _, v in tree_flatten(grads))) ** .5
        history.append(float(value.item()))
    delta = float(sum(np.sum((np.array(v) - before[k]) ** 2) for k, v in tree_flatten(model.parameters()))) ** .5
    if not np.isfinite(history).all() or not np.isfinite(delta):
        raise ValueError('NONFINITE_TRAINING')
    data_final=float(data_loss(model,data,targets).item())
    regularizer_final=float((l2*sum(mx.sum(v*v) for _,v in tree_flatten(model.trainable_parameters()))).item())
    return model, dict(data_loss_final=data_final,regularizer_final=regularizer_final,loss=history, gradient_norm_first=first_grad, parameter_delta_norm=delta,
                      parameters=sum(v.size for _, v in tree_flatten(model.trainable_parameters())),
                      updates=steps, trained_cases=list(targets), accepted_uses=sum(map(len, targets.values())),
                      kind=kind, seed=seed, loss_weighting='mean within case, then mean across training cases',
                      initialization='zero shared logits' if kind == 'S' else 'seeded original-width encoder')


def probabilities_and_scores(logits):
    probabilities = np.array(mx.softmax(logits, axis=-1)).astype(float)
    return probabilities, 2 * probabilities[:, 0] + probabilities[:, 1]
