"""Strict source, scope and snapshot contracts for the bounded pilot."""
import hashlib
from legal_bench.historical_contrasts_v1.contracts import digest, read_json, write_immutable

VALUES = {'TRUE', 'FALSE', 'UNKNOWN', 'CONFLICT'}
KINDS = {'COURT_RECORDED', 'PARTY_ALLEGATION', 'ASSUMPTION'}
PREDICATES = {'possession_established', 'settled_possession', 'interference_recorded',
              'opponent_better_title_unproved', 'plaintiff_title_established',
              'opponent_true_owner', 'plaintiff_wholly_unlawful'}


def validate(packet, rulebook, source_store):
    if packet['mode'] not in {'DEVELOPMENT_SOURCE_REVEAL', 'HYPOTHETICAL'}:
        raise ValueError('MODE')
    if packet['case_id'] != '789051' or packet['legal_approval'] is not False:
        raise ValueError('PILOT_SCOPE')
    if packet['binding'] != {'possessor': 'M. Varadappa Naidu', 'opponent': 'Rame Gowda',
                             'property': 'suit land, Arekempanahally', 'stage': 'SOURCE_REVEAL_RECONSTRUCTION'}:
        raise ValueError('ROLE_STAGE_BINDING')
    ids = [c['id'] for c in packet['clips']]
    if len(ids) != len(set(ids)):
        raise ValueError('DUPLICATE_CLIP')
    for clip in packet['clips'] + rulebook['clips']:
        original = source_store[clip['source_id']]
        a, b = clip['span']
        if not 0 <= a < b <= len(original) or original[a:b] != clip['text']:
            raise ValueError('SOURCE_QUOTE_OR_OFFSETS')
        if clip['sha256'] != hashlib.sha256(clip['text'].encode()).hexdigest():
            raise ValueError('SOURCE_HASH')
    by = {c['id']: c for c in packet['clips']}
    for fact in packet['assessments']:
        if fact['predicate'] not in PREDICATES or fact['value'] not in VALUES or fact['kind'] not in KINDS:
            raise ValueError('UNDECLARED_PREDICATE_OR_VALUE')
        if fact['binding'] != packet['binding']:
            raise ValueError('FACT_ROLE_STAGE_BINDING')
        if fact['kind'] == 'ASSUMPTION':
            if packet['mode'] != 'HYPOTHETICAL' or fact['refs']:
                raise ValueError('ASSUMPTION_PROMOTED_TO_EVIDENCE')
        elif not fact['refs'] or any(r not in by for r in fact['refs']):
            raise ValueError('MISSING_OR_INVISIBLE_EVIDENCE')
    factids = [f['id'] for f in packet['assessments']]
    if len(set(factids)) != len(factids):
        raise ValueError('DUPLICATE_ASSESSMENT')
    ruleids = [r['id'] for r in rulebook['rules']]
    if len(set(ruleids)) != len(ruleids):
        raise ValueError('DUPLICATE_RULE')
    for r in rulebook['rules']:
        if r['operator'] != 'ALL' or not r['conditions'] or any(p not in PREDICATES for p in r['conditions']):
            raise ValueError('UNSUPPORTED_RULE_OPERATOR_OR_PREDICATE')
        if not r['refs'] or any(ref not in {c['id'] for c in rulebook['clips']} for ref in r['refs']):
            raise ValueError('RULE_WITHOUT_AUTHORITY')
        if r['authority_date'] >= '2003-12-15':
            raise ValueError('POST_TARGET_AUTHORITY')
    return True


def join(values):
    values = set(values) - {'UNKNOWN'}
    if 'CONFLICT' in values or {'TRUE', 'FALSE'} <= values:
        return 'CONFLICT'
    return next(iter(values)) if values else 'UNKNOWN'
