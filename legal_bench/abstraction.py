"""Task-specific views retain their complete source event separately."""
import copy


def abstract(annotation, policy):
    if not policy.get('version') or not policy.get('task'):
        raise ValueError('Version and explicit task required')
    if policy.get('state') != 'MODEL_REVIEWED':
        raise ValueError('Only reviewed policies may create computational views')
    registry = {}
    for definition in policy['definitions']:
        if not definition.get('meaning') or not definition.get('preserve'):
            raise ValueError('Every definition requires meaning and preserved fields')
        for alias in [definition['type']] + definition.get('aliases', []):
            registry.setdefault(alias, []).append(definition)
    view = copy.deepcopy(annotation)
    view['source_events'] = copy.deepcopy(annotation['events'])
    view['abstraction_policy'] = {'version': policy['version'], 'task': policy['task']}
    mappings = []
    for e in view['events']:
        choices = registry.get(e['type'], [])
        original_type = e['type']
        if len(choices) != 1:
            state = 'UNMAPPED' if not choices else 'AMBIGUOUS'
            # Keep the raw predicate. It cannot silently enter a known normalized type.
            e['type'] = 'UNMAPPED::' + e['type']
        else:
            d = choices[0]
            e['type'] = d['type']
            state = 'MAPPED'
            # Do not delete any source fields. This version supports type alignment;
            # value binning and dropping conditions are deliberately unsupported.
            if d.get('generalize') or d.get('omit'):
                raise ValueError('Value generalization/omission requires a future explicit operator')
        mappings.append({'event_id': e['id'], 'source_type': original_type,
                         'type': e['type'], 'state': state, 'policy_version': policy['version']})
    view['abstractions'] = mappings
    return view
