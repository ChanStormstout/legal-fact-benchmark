"""Validate explicit rule metadata; never infer role identity or answers."""
import re
from .rule_contracts_v19_7 import attach as previous_attach, digest
from .object_types_v19 import DOMAINS
VERSION='V19_8_RULE_VALIDATION_1'

def validate_rules(rules):
    for r in rules:
        if set(r['slot_variables'])!={p['id'] for p in r['premises']}:raise ValueError('SLOT_DIRECTORY_COVERAGE')
        for p in r['premises']:
            c=p['input_contract'];roles=set(p['variables']);m=r['slot_variables'][p['id']]
            if set(m)!=roles or c['role_types']!=p['variables']:raise ValueError('SLOT_ROLE_COVERAGE')
            if (set(c['required_roles'])&set(c['optional_roles']) or
                set(c['required_roles'])|set(c['optional_roles'])!=roles or
                len(c['required_roles'])!=len(set(c['required_roles'])) or
                len(c['optional_roles'])!=len(set(c['optional_roles']))):raise ValueError('ROLE_POLICY_COVERAGE')
            for name in m.values():
                if not isinstance(name,str) or not re.fullmatch(re.escape(r['id'])+r'::[A-Za-z_][A-Za-z0-9_]*',name):raise ValueError('VARIABLE_ADDRESS_NOT_TYPE')
            if any(v not in {*DOMAINS,'UNMAPPED'} for v in p['variables'].values()):raise ValueError('ROLE_TYPE_NOT_CANONICAL')
            components=c['components'];ids=[a['id'] for a in components]
            if not components or len(ids)!=len(set(ids)) or any(not a['text'] or not a['id'].startswith(p['id']+'.K') for a in components):raise ValueError('COMPONENT_ADDRESS')
            allowed=c['whole_basis_statuses']
            if not isinstance(allowed,list) or any(not isinstance(v,str) or not v for v in allowed) or len(allowed)!=len(set(allowed)):raise ValueError('STATUS_POLICY')
    return {'status':'OK','version':VERSION,'rule_sha256':digest(rules),'semantic_approval':False}

def attach(rules,contract):
    result=previous_attach(rules,contract);validate_rules(result);return result
