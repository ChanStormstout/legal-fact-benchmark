"""Guide 4.0 pp. 15-18: separate nonnegative channels, component-wise solve.

This is not ANCO-HITS. NumPy is used only in this optional numeric teaching view.
"""
def solve(P, N):
    import numpy as np
    P, N = np.asarray(P, dtype=float), np.asarray(N, dtype=float)
    if P.ndim != 2 or P.shape[0] != P.shape[1] or N.shape != P.shape:
        raise ValueError('CHANNEL_SHAPE')
    for M in (P, N):
        if not np.isfinite(M).all() or (M < 0).any() or not np.allclose(M, M.T) or np.any(np.diag(M)):
            raise ValueError('FINITE_NONNEGATIVE_SYMMETRIC_ZERO_DIAGONAL_REQUIRED')
    adjacency = P + N
    unseen = set(range(len(P))); components = []; isolated = []
    while unseen:
        seed = min(unseen); todo = [seed]; ids = []; unseen.remove(seed)
        while todo:
            i = todo.pop(); ids.append(i)
            for j in np.flatnonzero(adjacency[i] > 0):
                if int(j) in unseen:
                    unseen.remove(int(j)); todo.append(int(j))
        ids.sort()
        if len(ids) == 1:
            isolated.extend(ids); continue
        pp, nn = P[np.ix_(ids, ids)], N[np.ix_(ids, ids)]
        d = (pp + nn).sum(axis=1); q = 1 / np.sqrt(d)
        L = np.diag(d) - (pp - nn); norm = q[:, None] * L * q[None, :]
        ev, U = np.linalg.eigh(norm); u = U[:, 0]; x = q * u
        # First nonzero node positive: deterministic presentation, not truth.
        anchor = next(k for k, v in enumerate(x) if abs(v) > 1e-10)
        if x[anchor] < 0:
            x = -x
        x /= np.max(np.abs(x))
        components.append({'nodes': ids, 'scores': x.tolist(), 'eigenvalues': ev[:2].tolist(),
            'residual': float(np.linalg.norm(norm @ u - ev[0] * u)), 'degree': d.tolist(),
            'nonunique_axis': bool(ev[1] - ev[0] < 1e-8),
            'interpretation': 'Alignment coordinate only; no comparison across components, no truth or probability.'})
    return {'components': components, 'isolates': isolated, 'P': P.tolist(), 'N': N.tolist(),
            'degrees_use': 'P+N', 'conflicting_pairs': [[i, j] for i in range(len(P)) for j in range(i+1, len(P)) if P[i,j] and N[i,j]]}


def examples():
    import numpy as np
    B = np.array([[3, 2, -3], [2, -1, -2], [-3, -2, 3]])
    CL = np.array([[0, 1, -2], [1, 0, -1], [-2, -1, 0]])
    CR = np.array([[0, -1, -2], [-1, 0, -1], [-2, -1, 0]])
    out = {}
    for name, left, right in [('bipartite', np.zeros((3,3)), np.zeros((3,3))), ('internal', CL, CR)]:
        W = np.block([[left, B], [B.T, right]])
        out[name] = solve(np.maximum(W, 0), np.maximum(-W, 0))
    out['parallel_conflict'] = solve([[0,3,0],[3,0,0],[0,0,0]], [[0,3,0],[3,0,0],[0,0,0]])
    out['parallel_conflict']['edge_records'] = [
        {'id':'NUMERIC_PLUS','source':0,'target':1,'sign':'SUPPORT','weight':3},
        {'id':'NUMERIC_MINUS','source':0,'target':1,'sign':'OPPOSE','weight':3}]
    out['scope'] = 'SYNTHETIC_NUMERIC_EXERCISES_NOT_LEGAL_RELATIONS'
    out['numpy_version'] = np.__version__
    return out
