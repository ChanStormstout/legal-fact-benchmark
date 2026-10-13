"""Versioned input contracts, not answer labels or an inferred legal ontology."""
import copy
import hashlib
import json

VERSION = 'V19_7_RULE_CONTRACT_1'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def attach(rules, contract):
    if contract['version'] != VERSION:
        raise ValueError('RULE_CONTRACT_VERSION')
    result = copy.deepcopy(rules)
    for rule in result:
        spec = contract['rules'][rule['id']]
        if digest(rule) != spec['original_rule_sha256']:
            raise ValueError('RULE_CONTRACT_BASE_CHANGED:' + rule['id'])
        if set(spec['premises']) != {p['id'] for p in rule['premises']}:
            raise ValueError('RULE_CONTRACT_PREMISE_COVERAGE')
        rule['slot_variables'] = copy.deepcopy(spec['slot_variables'])
        rule['input_contract_version'] = VERSION
        rule['input_contract_sha256'] = digest(spec)
        for premise in rule['premises']:
            c = spec['premises'][premise['id']]
            if c['fixed_proposition'] != premise['text'] or set(c['role_types']) != set(premise['variables']):
                raise ValueError('RULE_CONTRACT_MEANING_CHANGED')
            premise['original_variable_descriptions'] = copy.deepcopy(premise['variables'])
            premise['variables'] = copy.deepcopy(c['role_types'])
            premise['input_contract'] = copy.deepcopy(c)
    return result


def specs(rules):
    return {p['id']: p['input_contract'] for r in rules for p in r['premises']}
