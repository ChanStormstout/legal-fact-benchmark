"""Finite declared type vocabulary, not entity resolution or semantic matching.

Unknown descriptions stay unknown even when their text is identical. Compatible
domains only remove a mechanical type objection; they do not establish identity,
role qualification, truth, or legal applicability. No reference data is read.
"""
VERSION = 'V19_OBJECT_TYPES_1'
DOMAINS = {
    'PERSON': ('human',),
    'PERSON_GROUP': ('human_group',),
    'PARTY': ('human', 'organization'),
    'ORGANIZATION': ('organization',),
    'PROPERTY': ('property',),
    'TIME': ('time',),
    'QUANTITY': ('quantity',),
    'DOCUMENT': ('document',),
    'LEGAL_CONCEPT': ('legal_concept',),
    'EVENT': ('event',),
    'BOOLEAN': ('boolean',),
}
# Explicit generic aliases only. No case IDs, proper names, substring rules,
# edit distance, embeddings, or inferred identity from a role name.
ALIASES = {
    'person': 'PERSON', 'natural person': 'PERSON',
    'persons': 'PERSON_GROUP', 'group of persons': 'PERSON_GROUP',
    'party': 'PARTY', 'tenant': 'PARTY', 'landlord': 'PARTY',
    'lessee': 'PARTY', 'lessor': 'PARTY', 'occupant': 'PARTY',
    'association': 'ORGANIZATION', 'organization': 'ORGANIZATION',
    'organisation': 'ORGANIZATION', 'company': 'ORGANIZATION',
    'court': 'ORGANIZATION', 'judicial_forum': 'ORGANIZATION',
    'property': 'PROPERTY', 'premises': 'PROPERTY', 'land': 'PROPERTY',
    'immovable_property': 'PROPERTY', 'leased_premises': 'PROPERTY',
    'date': 'TIME', 'time': 'TIME', 'time_period': 'TIME',
    'money': 'QUANTITY', 'amount': 'QUANTITY',
    'document': 'DOCUMENT', 'instrument': 'DOCUMENT', 'lease': 'DOCUMENT',
    'identified lease': 'DOCUMENT', 'deed': 'DOCUMENT', 'statute': 'DOCUMENT',
    'ejectment decree': 'DOCUMENT', 'ejectment_decree': 'DOCUMENT',
    'court_decree': 'DOCUMENT', 'court_compromise': 'DOCUMENT',
    'judicial decision': 'DOCUMENT',
    'legal_requirement': 'LEGAL_CONCEPT',
    'event': 'EVENT', 'overt_act': 'EVENT', 'boolean': 'BOOLEAN',
}


def normalize(value):
    key = ' '.join(value.split()).casefold() if isinstance(value, str) else None
    canonical = ALIASES.get(key)
    if canonical is None and isinstance(value, str) and value in DOMAINS:
        canonical = value
    return {'raw': value, 'canonical': canonical,
            'domain': list(DOMAINS[canonical]) if canonical else [],
            'status': 'MAPPED' if canonical else 'UNMAPPED_DESCRIPTION',
            'policy_version': VERSION}


def compare(actual, expected):
    a, b = normalize(actual), normalize(expected)
    if not a['domain'] or not b['domain']:
        status = 'UNMAPPED_DESCRIPTION'
    elif set(a['domain']) & set(b['domain']):
        status = 'COMPATIBLE_TYPE_DOMAIN'
    else:
        status = 'EXPLICIT_TYPE_CONFLICT'
    return {'actual': a, 'expected': b, 'status': status,
            'identity_established': False, 'semantic_approval': False}


def contract():
    return {'version': VERSION, 'domains': DOMAINS, 'aliases': ALIASES,
            'normalization': 'Whitespace and letter case only; finite exact alias lookup.',
            'unmapped_use': 'Retain connection and explicit object-ID binding. Conditional derivation records unverified model role/type compatibility; no verified type compatibility is claimed. Unmapped type alone is not a premise blocker.',
            'unmapped_identity_link': 'Retain proposed link without merging object IDs.',
            'compatible_domain': 'Type non-conflict only; identity and specific role remain model assumptions requiring explicit binding and sources.',
            'forbidden': ['fuzzy matching', 'case-specific aliases', 'reference-derived objects', 'null-as-wildcard']}
