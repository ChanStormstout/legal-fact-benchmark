"""Versioned task abstraction of source-reviewed records; no field promotion.

Mappings are weaker task types, not claims of exact synonymy, shared events or
legal sufficiency. Raw definitions, object roles, source claims and permissions
are retained. Unknown fields stay in query pools but cannot generate candidates.
"""
import copy
from .core import digest
from .scoped_engine import projection_view


CARDS = {
    'OCCUPATION_RECORD': ('CORE', 'Recorded possession/occupation of an identified object, within its original scope.',
                          'Not current occupation, equal extent, simultaneous possession or entitlement.'),
    'LEASE_RECORD': ('CORE', 'Recorded granting, letting or execution of a lease for property.',
                     'Not exact synonyms or the same event; agreement and granting distinctions remain in source records.'),
    'RENT_PAYMENT_RECORD': ('CORE', 'Recorded actual rent payment, not merely agreed rent or a receipt.',
                            'No exact amount, cumulative payment or debt discharge inference.'),
    'SUIT_FILING_RECORD': ('CORE', 'Recorded filing of a civil suit; property may be unspecified.',
                           'Not filing an appeal or administrative representation; no unique relief or exhaustive parties inferred.'),
    'DISPOSSESSION_RECORD': ('CORE', 'Recorded taking possession from another party within stated scope.',
                            'No full-parcel or collective-to-individual binding inferred.'),
    'SURRENDER_RECORD': ('CORE', 'Recorded voluntary surrender of possession.', 'No exact time or present state inferred.'),
    'TITLE_OR_OWNERSHIP_RECORD': ('LEGAL_STATE', 'Scoped source-attributed title/ownership state.',
                                 'Not a physical event; excluded from observable-event discovery; not unrestricted ownership.'),
    'BUSINESS_OPERATION_RECORD': ('EXTENDED', 'Recorded carrying on a business at premises when specified.',
                                  'Not intention, business experience, bona fide need or permission to operate.'),
    'APPEAL_FILING_RECORD': ('PROCEDURAL', 'Recorded filing/preference of an appeal.',
                             'The receiving court is distinct from the prior court; no same appeal assumed.'),
    'APPEAL_ALLOWANCE_RECORD': ('PROCEDURAL', 'Recorded allowance of an appeal.',
                               'Not substantive correctness or the same appeal as another event.'),
    'APPEAL_DISMISSAL_RECORD': ('PROCEDURAL', 'Recorded dismissal of an appeal.', 'Not dismissal of its underlying suit.'),
    'SUIT_DISMISSAL_RECORD': ('PROCEDURAL', 'Recorded dismissal of a suit.', 'Not dismissal of an appeal.'),
    'ADJUDICATION_REVERSAL_RECORD': ('PROCEDURAL', 'Recorded setting aside/reversal of a judgment or decree.',
                                    'Participant means associated party only, not uniformly beneficiary; no common adjudication inferred.'),
    'ADJUDICATION_RESTORATION_RECORD': ('PROCEDURAL', 'Recorded restoration of an earlier judgment or decree.',
                                       'Does not erase the earlier reversal; participant has no stronger benefit meaning.'),
}


def extended_rule(definition):
    """Explicit predicate allowlist; roles selected using reviewed definitions."""
    name, roles = definition['id'], definition['roles']
    options = {
        'OPERATE_BUSINESS': ('BUSINESS_OPERATION_RECORD', {'operator': ['subject'], 'property': ['property']}),
        'CARRY_ON_BUSINESS': ('BUSINESS_OPERATION_RECORD', {'operator': ['subject', 'actor'], 'property': ['property']}),
        'CARRY_ON_BUSINESS_AT_PROPERTY': ('BUSINESS_OPERATION_RECORD', {'operator': ['subject'], 'property': ['property']}),
        'FILE_APPEAL': ('APPEAL_FILING_RECORD', {'appellant': ['appellant', 'filer', 'party'], 'court': ['court'],
                                               'prior_court': ['prior_court'], 'property': ['property']}),
        'ALLOW_APPEAL': ('APPEAL_ALLOWANCE_RECORD', {'appellant': ['appellant', 'party'], 'court': ['court'], 'property': ['property']}),
        'ALLOW_CURRENT_APPEAL': ('APPEAL_ALLOWANCE_RECORD', {'appellant': ['appellant'], 'court': ['court']}),
        'DISMISS_APPEAL': ('APPEAL_DISMISSAL_RECORD', {'appellant': ['appellant', 'party'], 'court': ['court'], 'property': ['property']}),
        'DISMISS_SUIT': ('SUIT_DISMISSAL_RECORD', {'claimant': ['plaintiff', 'party'], 'court': ['court'], 'property': ['property']}),
        'REVERSE_DECREE': ('ADJUDICATION_REVERSAL_RECORD', {'court': ['court'], 'participant': ['party'], 'property': ['property']}),
        'SET_ASIDE_DECREE': ('ADJUDICATION_REVERSAL_RECORD', {'court': ['court'], 'participant': ['party'], 'property': ['property']}),
        'SET_ASIDE_JUDGMENT': ('ADJUDICATION_REVERSAL_RECORD', {'court': ['court'], 'participant': ['party'], 'prior_court': ['prior_court']}),
        'RESTORE_DECREE': ('ADJUDICATION_RESTORATION_RECORD', {'court': ['court'], 'participant': ['party'], 'property': ['property']}),
        'RESTORE_JUDGMENT': ('ADJUDICATION_RESTORATION_RECORD', {'court': ['court'], 'participant': ['party']}),
    }
    if name not in options:
        return None
    typ, alternatives = options[name]
    mapping = {}
    for target, sources in alternatives.items():
        found = [src for src in sources if src in roles]
        if len(found) > 1:
            raise ValueError('Ambiguous role mapping; inspect definition: ' + name + '/' + target)
        if found:
            mapping[target] = found[0]
    return {'type': typ, 'roles': mapping, 'basis': 'Explicit task abstraction from source predicate and role definitions'}


def registry(annotation, core_rules, side):
    definitions = {d['id']: d for d in annotation['predicate_definitions']}
    rules = {}
    for name, supplied in core_rules.items():
        rule = copy.deepcopy(supplied)
        # Classification of this overloaded predicate is assertion-specific,
        # from source-reviewed records, not an executable attribute equality.
        if name == 'FILE_PROCEEDING' and annotation['case_id'] == '184866874' and side == 'B':
            rule.pop('attribute_guard', None)
            rule['assertion_ids'] = ['a3', 'a31']
            rule['basis'] = '184866874 B source-backed O.S. 178/1967 and O.S. 115/1996 filings only; A.S. 1931/2002 is an appeal.'
        rule['source_definition_hash'] = digest(definitions[name])
        rule['source_definition'] = definitions[name]
        rule['card'] = CARDS[rule['type']]
        rules[name] = rule
    for name, definition in definitions.items():
        rule = extended_rule(definition)
        if rule:
            rule.update(source_definition=definition, source_definition_hash=digest(definition), card=CARDS[rule['type']])
            rules[name] = rule
    if annotation['case_id'] == '184866874' and side == 'B':
        definition = definitions['FILE_PROCEEDING']
        rules['FILE_PROCEEDING::appeal'] = {'source_predicate': 'FILE_PROCEEDING', 'assertion_ids': ['a35'],
            'type': 'APPEAL_FILING_RECORD', 'roles': {'appellant': 'filer', 'court': 'court', 'property': 'property'},
            'source_definition': definition, 'source_definition_hash': digest(definition),
            'basis': 'a35 refers explicitly to A.S. No.1931/2002, an appeal; not suit filing.', 'card': CARDS['APPEAL_FILING_RECORD']}
    return {'version': 'source-reviewed-task-types-v1', 'case_id': annotation['case_id'], 'side': side,
            'annotation_hash': digest(annotation), 'rules': rules,
            'boundary': 'Task-specific weaker abstraction; not exact fact equivalence or automatic role/coreference discovery'}


def normalize_view(annotation, review, registry_data, profile='CORE'):
    if profile not in ['CORE', 'ATLAS', 'NATIVE']:
        raise ValueError('Unknown normalization profile')
    if registry_data['annotation_hash'] != digest(annotation):
        raise ValueError('Stale abstraction registry')
    original = projection_view(annotation, review)
    view = copy.deepcopy(original)
    view['events'], view['excluded_by_profile'] = [], []
    raw = {a['id']: a for a in annotation['assertions']}
    definitions = {d['id']: d for d in annotation['predicate_definitions']}
    for event in original['events']:
        matches = []
        if profile == 'NATIVE':
            matches = [{'type': 'NATIVE::' + event['type'] + '::' + digest(sorted(event['roles']))[:12],
                        'roles': {key: key for key in event['roles']}, 'card': ('NATIVE', definitions[event['type']]['meaning'],
                        'Syntactic comparability only; no established cross-case equivalence.'),
                        'source_definition': definitions[event['type']]}]
        else:
            for key, rule in registry_data['rules'].items():
                if rule.get('source_predicate', key) != event['type']:
                    continue
                if 'assertion_ids' in rule and event['id'] not in rule['assertion_ids']:
                    continue
                if profile == 'CORE' and rule['card'][0] not in ['CORE', 'LEGAL_STATE']:
                    continue
                matches.append(rule)
        if not matches:
            view['excluded_by_profile'].append({'assertion_id': event['id'], 'predicate': event['type'], 'reason': 'OUTSIDE_DECLARED_TASK_PROFILE'})
            continue
        if len(matches) != 1:
            raise ValueError('Overlapping task abstraction rules')
        rule = matches[0]
        if not set(rule['roles'].values()) <= set(definitions[event['type']]['roles']):
            raise ValueError('Role absent from source definition')
        mapped = copy.deepcopy(event)
        mapped['original_type'], mapped['original_roles'] = event['type'], copy.deepcopy(event['roles'])
        mapped['original_approved_fields'] = list(event['approved_fields'])
        mapped['type'], mapped['roles'] = rule['type'], {dst: event['roles'].get(src) for dst, src in rule['roles'].items()}
        # Permissions follow an approved source cell; a rename never grants it.
        mapped['approved_fields'] = [f for f in event['approved_fields'] if not f.startswith('roles.')]
        mapped['approved_fields'] += ['roles.' + dst for dst, src in rule['roles'].items()
                                      if 'roles.' + src in event['approved_fields']]
        inverse = {src: dst for dst, src in rule['roles'].items()}
        for uncertainty in mapped['unresolved']:
            if uncertainty['field'].startswith('roles.'):
                src = uncertainty['field'].split('.', 1)[1]
                uncertainty['field'] = 'roles.' + inverse.get(src, src)
        mapped.update(source_assertion=copy.deepcopy(raw[event['id']]), source_definition=copy.deepcopy(definitions[event['type']]),
                      abstraction=copy.deepcopy(rule), task_stratum=rule['card'][0])
        view['events'].append(mapped)
    view.update(profile=profile, registry_hash=digest(registry_data), source_review_provenance=copy.deepcopy(review['provenance']),
                abstraction_state='EXPLICIT_LOCAL_TASK_ABSTRACTION_WITH_SOURCE_REVIEW_GATES')
    return view


def oracle_view(view):
    """Independent permission translation, without the tested field projector.

    The exhaustive oracle reads this contract. Manual integration controls also
    test renames, withheld roles, typed bools and unapproved dates directly.
    """
    events = []
    for event in view['events']:
        record = copy.deepcopy(event)
        fields = ['id', 'type', 'status', 'polarity', 'time'] + ['roles.' + key for key in event['roles']] + [
            'attributes.' + key for key in event['attributes']]
        blocks = [{'affected_fields': [f], 'reason': 'Not approved'} for f in fields if f not in event['approved_fields']]
        for u in event['unresolved']:
            key = u['field']
            recognized = key in ['time', 'origin', 'scope'] or key.startswith(('roles.', 'attributes.', 'scope.', 'origin.'))
            blocks.append({'affected_fields': [key if recognized else '*'], 'reason': u['reason']})
        record['field_contract'] = {'blocked': blocks, 'type_unresolved': False}
        record['unit_id'] = view['unit_id']
        events.append(record)
    return {'case_id': view['case_id'], 'units': [{'id': view['unit_id']}], 'events': events}
