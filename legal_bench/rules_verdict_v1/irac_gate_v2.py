"""Explicit semantic-stage gate and inference-only binding admission.

Address validity is not semantic validation. Reviewed partitions are inputs to
this module, not inferred from a node name, court string or past event date.
"""
import copy
import hashlib
import json

ALLOWED = {'PRE_TARGET_RECORD', 'PRIOR_COURT_FINDING', 'TARGET_STAGE_PARTY_ARGUMENT'}
FORBIDDEN = {'TARGET_COURT_REASONING', 'TARGET_DISPOSITION', 'AMBIGUOUS'}
AVAILABILITY = {'DIRECT_PRE_TARGET_SOURCE', 'RETROSPECTIVELY_RECONSTRUCTED_PRE_TARGET', 'UNKNOWN'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def admit_record(record, grant, source_grants):
    """One policy for facts, objects, evidence, edges and metadata; no rewriting."""
    errors = []
    if grant.get('semantic_stage') not in ALLOWED or grant.get('input_allowed') is not True:
        errors.append('SEMANTIC_STAGE_FORBIDDEN_OR_UNGRANTED')
    if grant.get('prospective_availability') not in AVAILABILITY:
        errors.append('AVAILABILITY_NOT_DECLARED')
    refs = record.get('refs', grant.get('source_refs', []))
    if not refs:
        errors.append('NO_SOURCE_PROVENANCE')
    if not set(refs) <= set(grant.get('source_refs', [])):
        errors.append('ORIGINAL_REFS_NOT_GRANTED')
    for ref in refs:
        sg = source_grants.get(ref, {})
        if sg.get('semantic_stage') not in ALLOWED or sg.get('input_allowed') is not True:
            errors.append('SOURCE_STAGE_FORBIDDEN:' + ref)
    # A contradictory grant must not silently promote a known target finding.
    if record.get('court') == 'TARGET' and record.get('status') == 'FOUND':
        errors.append('TARGET_FOUND_NOT_INPUT')
    return (None if errors else copy.deepcopy(record)), sorted(set(errors))


def validate_condition(condition, rules):
    rule = rules.get(condition.get('rule_id'), {})
    errors = []
    if not rule.get('independent_source_verified'):
        errors.append('NO_INDEPENDENT_RULE_SOURCE')
    quote = condition.get('exact_rule_quote', '')
    if not quote or ' '.join(quote.split()) not in ' '.join(rule.get('exact_quote', '').split()):
        errors.append('RULE_QUOTE_NOT_LOCATED')
    if not condition.get('source_refs'):
        errors.append('NO_CONDITION_SOURCE')
    for dep in condition.get('dependencies', []):
        if dep.get('operator') not in {'AND', 'OR', 'QUALIFICATION'}:
            errors.append('INVALID_DEPENDENCY')
    return errors


def validate_blind_binding(binding, facts, conditions, source_grants, fact_grants):
    errors = []
    fact = facts.get(binding.get('fact_id'))
    if fact is None:
        return ['UNKNOWN_OR_NEW_FACT_FORBIDDEN']
    if binding.get('condition_id') not in conditions:
        errors.append('UNKNOWN_CONDITION')
    if binding.get('relation') not in {'SUPPORTS', 'DEFEATS', 'RELEVANT_TO'}:
        errors.append('INVALID_RELATION')
    _, record_errors = admit_record(fact, fact_grants.get(fact['id'], {}), source_grants)
    errors += record_errors
    refs = binding.get('source_refs', [])
    if not refs or not set(refs) <= set(fact.get('refs', [])):
        errors.append('BINDING_REF_NOT_IN_FACT_PROVENANCE')
    for ref in refs:
        if not source_grants.get(ref, {}).get('input_allowed'):
            errors.append('TARGET_ONLY_OR_UNKNOWN_SOURCE:' + ref)
    if binding.get('statement_status') != fact.get('status'):
        errors.append('FACT_STATUS_CHANGED')
    stage = binding.get('court_stage', {})
    if not isinstance(stage, dict) or stage.get('court') != fact.get('court') or stage.get('stage') != fact.get('stage'):
        errors.append('COURT_STAGE_CHANGED')
    return sorted(set(errors))


def inference_payload(issue, rules, conditions, facts, relations, objects, sources):
    """Targets, oracle selection notes and source reviews have no argument here."""
    input_rules = [{k: copy.deepcopy(v) for k, v in r.items()
                    if k not in {'oracle_selection_basis', 'verification_meaning'}} for r in rules]
    return {'fixed_issue': issue, 'rules': input_rules,
            'conditions': copy.deepcopy(conditions), 'facts': copy.deepcopy(facts),
            'relations': copy.deepcopy(relations), 'objects': copy.deepcopy(objects),
            'sources': copy.deepcopy(sources), 'unknown_is_not_false': True}
