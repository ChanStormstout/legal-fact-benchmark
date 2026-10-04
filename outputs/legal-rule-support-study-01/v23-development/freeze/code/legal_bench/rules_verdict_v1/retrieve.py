"""Deterministic ranking fusion and explicit authority dependency expansion."""


def fuse(rankings, k=60, limit=40):
    if k <= 0 or limit < 1:
        raise ValueError('Invalid fusion budget')
    scores, contributions = {}, {}
    for name, ranking in sorted(rankings.items()):
        seen = set()
        for position, record in enumerate(ranking, 1):
            key = record['id']
            if key in seen:
                raise ValueError('Duplicate ranking item')
            seen.add(key)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + position)
            contributions.setdefault(key, []).append({'route': name, 'rank': position})
    return [{'id': key, 'rrf_score': scores[key], 'contributions': contributions[key]}
            for key in sorted(scores, key=lambda key: (-scores[key], key))[:limit]]


def expand(ranking, units, initial=8, max_units=24, rounds=2):
    if not 0 < initial <= max_units or rounds < 0:
        raise ValueError('Invalid expansion budget')
    registry = {u['id']: u for u in units}
    if len(registry) != len(units):
        raise ValueError('Duplicate authority IDs')
    selected, missing, truncated = [], [], []
    for item in ranking[:initial]:
        key = item['id']
        if key not in registry:
            raise ValueError('Unknown ranked authority: ' + key)
        if key not in selected:
            selected.append(key)
    frontier = list(selected)
    for _ in range(rounds):
        next_frontier = []
        for key in frontier:
            for dependency in sorted(registry[key].get('dependencies', [])):
                if dependency not in registry:
                    missing.append({'parent': key, 'dependency': dependency})
                elif dependency not in selected:
                    if len(selected) >= max_units:
                        truncated.append({'parent': key, 'dependency': dependency})
                    else:
                        selected.append(dependency)
                        next_frontier.append(dependency)
        frontier = next_frontier
    outstanding = [{'parent': key, 'dependency': dep} for key in selected
                   for dep in registry[key].get('dependencies', []) if dep not in selected]
    return {'selected_ids': selected, 'units': [registry[k] for k in selected],
            'missing_dependencies': missing, 'budget_truncated_dependencies': truncated,
            'outstanding_dependencies': outstanding, 'dependency_complete': not outstanding,
            'note': 'Relevance, scope and condition satisfaction remain separate; no condition-based pruning.'}
