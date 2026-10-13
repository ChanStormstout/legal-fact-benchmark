"""V17 fixed local proposer, common audit and final-answer interface.

This module has no reference/supervision argument. MODEL_PROPOSED semantics
never become legal approval. Citation checks do not decide proposition truth.
"""
import copy
import json
from .semantic_interface_v13 import position, recover
from .quote_locator_v16 import source_match
from .local_evaluation_v17 import LABELS, hash_value

def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

STR = {'type': 'string', 'minLength': 1}
def arr(items=STR, minimum=0, maximum=None):
    result = {'type': 'array', 'items': items, 'minItems': minimum}
    result['maxItems'] = maximum if maximum is not None else 256
    return result
def enum(values): return {'type': 'string', 'enum': list(values)}

def validate(data, schema, path='$'):
    """V17 strict small-schema validator; unlike the legacy validator it checks
    integer/boolean types and minItems. No generated-output repair."""
    if 'enum' in schema:
        if not any(type(data) is type(v) and data == v for v in schema['enum']):
            raise ValueError(path + ': outside enum')
        return
    typ = schema['type']
    if typ == 'object':
        if not isinstance(data, dict) or set(data) != set(schema['required']):
            raise ValueError(path + ': missing or extra fields')
        for k,v in data.items(): validate(v, schema['properties'][k], path+'.'+k)
    elif typ == 'array':
        if not isinstance(data,list) or not schema.get('minItems',0) <= len(data) <= schema.get('maxItems',float('inf')):
            raise ValueError(path + ': array cardinality')
        for i,v in enumerate(data): validate(v,schema['items'],path+'[%d]'%i)
    elif typ == 'string':
        if not isinstance(data,str) or not schema.get('minLength',0)<=len(data)<=schema.get('maxLength',float('inf')):
            raise ValueError(path + ': string')
    elif typ == 'integer':
        if type(data) is not int or not schema.get('minimum',float('-inf'))<=data<=schema.get('maximum',float('inf')):
            raise ValueError(path + ': integer')
    elif typ == 'boolean':
        if type(data) is not bool: raise ValueError(path + ': boolean')
    elif typ == 'null':
        if data is not None: raise ValueError(path + ': null')
    else: raise ValueError('UNSUPPORTED_SCHEMA_TYPE:'+typ)

def proposal_schema(rules):
    addresses = [p['id'] for r in rules for p in r['premises']]
    record = obj({'text': STR, 'statement_status': enum(('PARTY_CLAIM', 'TESTIMONY', 'ADMISSION', 'RECORDED_DOCUMENT', 'COURT_FINDING', 'COURT_LEGAL_REASONING', 'COURT_PROCEDURAL_ACCOUNT', 'UNKNOWN')),
                  'stage': STR, 'refs': arr(STR, 1)})
    binding = obj({'role': STR, 'object': STR, 'type': STR, 'refs': arr(STR, 1), 'basis': STR})
    witness = obj({'refs': arr(STR, 1), 'quote': STR, 'necessity': enum(('REQUIRED', 'SUPPLEMENTARY'))})
    connection = obj({'premise_id': enum(addresses), 'records': arr({'type': 'integer', 'minimum': 1}, 1),
                      'objects': arr(binding), 'direction': enum(('SUPPORT', 'OPPOSE', 'CONTEXT')),
                      'proposed_connection': STR, 'self_assessment': enum(LABELS),
                      'whole_premise_state': enum(('TRUE', 'FALSE', 'UNKNOWN', 'CONFLICTED')),
                      'whole_premise_complete': {'type': 'boolean'}, 'stage': STR,
                      'witnesses': arr(witness, 1), 'opposition_records': arr({'type': 'integer', 'minimum': 1}),
                      'gaps': arr(), 'explanation': STR})
    return obj({'records': arr(record, 1, 12), 'connections': arr(connection, 1, 12), 'coverage_limits': arr()})

FINAL_SCHEMA = obj({'request_id': enum(('Q1',)), 'conclusion': STR,
    'grounds': arr(obj({'point': STR, 'statement_status_and_stage': STR,
                        'case_refs': arr(), 'rule_refs': arr(), 'explanation': STR}), 1, 8),
    'counterarguments': arr(obj({'point': STR, 'refs': arr(), 'treatment': STR}), 0, 5),
    'gaps': arr(), 'assumptions': arr(),
    'connection_handling': arr(obj({'connection_id': STR, 'decision': enum(('ADOPT', 'REJECT', 'REINTERPRET', 'NOT_USED')),
                                  'refs': arr(), 'reason': STR}))})

PROPOSAL_INSTRUCTION = '''Reconstruct the specified judgment reasoning in English using only the provided allowed text and given rule drafts. Propose source-supported connections to the frozen premise directory; do not rewrite rules. One connection is one specific claim about how an attributed record and explicitly bound object at a specified court stage bear on the whole premise. self_assessment evaluates this proposed connection, NOT whether the legal premise is true. A correct opposition connection may be SUPPORTED. Whole-premise state and complete coverage are separate: partial support and background cannot by themselves prove TRUE. Preserve decisive opposition and unknown links.
Records use 1-based array positions; do not generate internal IDs or hashes. Each record is saved once, and may support multiple distinct uses. Object type (person/property/etc.), rule role, and concrete object are distinct; names/types/null do not establish identity. State the source basis for each proposed role binding. Two speakers or court stages discussing one transaction do not make two transactions. Prior final orders cannot prove themselves circularly. A court's recorded legal evaluation may be reconstructed as external semantic reasoning with its court and stage; do not claim a program independently proves it. A party assertion directly establishes that the assertion was made, not necessarily its truth.
Use exact premise IDs from the readable directory. Required witnesses are necessary for the proposed scope; supplementary witnesses failing location do not invalidate independent required witnesses. Provide short verbatim quotes with exact source IDs. Keep necessary scope/negation/exceptions. At most 12 records and 12 connections; these are maxima, not quotas. Usually use one or two sentences for each explanation; do not repeat the complete case in every connection. Explicitly record decisive omissions in coverage_limits. Do not force every premise to have a connection. Return the complete JSON contract once; no external information.
SYNTHETIC TEACHING EXAMPLE (not target facts or law): A fictional record SYN:L1 states “Tenant Mira said the key was returned on Friday.” SYN:L2 states “The trial court found the key remained with Mira on Saturday.” Fictional premise SYN.P1 asks whether the trial court found retained control on Saturday. A record of Mira's claim is PARTY_CLAIM, stage pleading; the court finding is COURT_FINDING, trial. The connection using SYN:L2 to report that finding is SUPPORTED, direction SUPPORT, and whole_premise_state TRUE only within that trial-finding scope. Using SYN:L1 to assert an independently established return is UNSUPPORTED; it can instead establish that Mira made that claim. If a separate appellate adoption is required, the trial record alone leaves that different premise UNKNOWN. Do not invent a new event merely because two stages discuss the key.'''

FINAL_INSTRUCTION = '''Answer the fixed reconstruction request in English from the allowed judgment and given rule drafts. Reconstruct the court's adopted reasoning with actors/property/event, attributed statements, stage, applicable rule/scope, decisive counterargument and limited conclusion. Do not merely repeat the disposition or use the final order as proof of itself. The source may contain final reasoning because this is historical reconstruction, not prediction.
Intermediate material is fallible. You may correct, reject or reinterpret it directly from the original text and must record this in connection_handling. A model review is not independent approval. The program checks only the explicitly stated structural or logical properties; source address validity is not semantic proof. OPEN_TEXT means the program has not executed that legal interpretation, not that the judgment contains no reasoning: explain the sourced interpretation while noting it depends on semantic reading. A connection classified SUPPORTED does not imply the proposition TRUE; opposition and background retain their distinct functions.
Give one Q1 answer with nonempty grounds. A point is one short proposition, followed by a compact explanation normally one to three sentences. Preserve important counterarguments and real limitations without repeating the entire account. Distinguish what the judgment establishes, what is only attributed, and what remains open; state any assumption that actually affects the conclusion. Do not invent burden rules or scope. Cite only supplied source IDs and rule IDs. Return the complete JSON contract, no external searches or sources.
COMPLETE SYNTHETIC EXAMPLE (fictional teaching rule, not target law):
Input: SYN:L1 “Mira alleged a return of the key on Friday.” SYN:L2 “At trial the court found that Mira retained the key on Saturday.” Fictional rule SYN.R1: retained physical control may be reported as the court's trial finding, but does not by itself decide legal title. Request Q1: reconstruct that distinction.
Output: {"request_id":"Q1","conclusion":"The trial reasoning treated Mira as retaining physical control on Saturday, without deciding legal title on that fact alone.","grounds":[{"point":"The trial court found retained control on Saturday.","statement_status_and_stage":"COURT_FINDING; trial","case_refs":["SYN:L2"],"rule_refs":["SYN.R1"],"explanation":"The finding is attributed to the trial court and concerns the key on Saturday. It does not establish legal title."}],"counterarguments":[{"point":"Mira alleged an earlier return.","refs":["SYN:L1"],"treatment":"This is a party allegation, not a contrary court finding."}],"gaps":["No title ruling is supplied."],"assumptions":[],"connection_handling":[]}
No example content is evidence about the actual case.'''

def source_text(case):
    rows = sorted(case['segments'], key=lambda s: (s['source_document'], position(s), s['id']))
    return '\n\n'.join(s['id'] + '\n' + s['text'] for s in rows)

def directory(rules):
    return [{'rule_id': r['id'], 'operator': r['operator'], 'conclusion': r['conclusion'],
             'premises': [{'id': p['id'], 'proposition': p['text'],
                           'role_types_not_identity': p.get('variables', {}),
                           'allowed_statuses': p.get('allowed_statuses', [])} for p in r['premises']],
             'exceptions': r.get('exceptions', []), 'scope': r.get('stage'),
             'source_refs': r.get('source_refs', []), 'source_quote': r.get('source_quote'),
             'status': 'GIVEN_MODEL_DRAFT_RULE_NOT_LEGAL_APPROVAL'} for r in rules]

def common_prompt(case, rules):
    request = next(q for q in case['targets'] if q['id'] == 'Q1')
    return '\nGIVEN RULE DRAFTS AND PREMISE DIRECTORY:\n' + json.dumps(directory(rules), ensure_ascii=False) + '\nCOMPLETE ALLOWED JUDGMENT TEXT (source IDs retained):\n' + source_text(case) + '\nFIXED REQUEST:\n' + json.dumps(request, ensure_ascii=False)

def proposal_prompt(case, rules):
    return PROPOSAL_INSTRUCTION + common_prompt(case, rules) + '\nOUTPUT SCHEMA:\n' + json.dumps(proposal_schema(rules))

def final_prompt(case, rules, intermediate):
    # Every condition uses exactly this ordering and final instruction.
    return 'INTERMEDIATE MATERIAL (not approved):\n' + json.dumps(intermediate, ensure_ascii=False) + common_prompt(case, rules) + '\nFINAL TASK:\n' + FINAL_INSTRUCTION + '\nOUTPUT SCHEMA:\n' + json.dumps(FINAL_SCHEMA)

def audit(case, rules, proposal):
    sources = {s['id']: {'document': s['source_document'], 'original_line': s.get('original_line'), 'text': s['text']} for s in case['segments']}
    premises = {p['id']: (p, r) for r in rules for p in r['premises']}
    records = proposal['records']; checks = []
    for i, conn in enumerate(proposal['connections'], 1):
        errors, warnings = [], []
        address = conn['premise_id']; pid = 'K%02d' % i
        if address not in premises: errors.append('PREMISE_ADDRESS_UNKNOWN')
        if any(not 1 <= j <= len(records) for j in conn['records'] + conn['opposition_records']): errors.append('RECORD_ADDRESS_INVALID')
        witnesses = []
        for w in conn['witnesses']:
            loc = source_match(w, sources)
            witnesses.append({'necessity': w['necessity'], 'location': loc, 'raw_witness': w})
            if loc.get('error'):
                (errors if w['necessity'] == 'REQUIRED' else warnings).append('WITNESS_' + loc['error'])
        if not any(w['necessity'] == 'REQUIRED' for w in conn['witnesses']): errors.append('NO_REQUIRED_WITNESS')
        mapping = {}; role_types = premises.get(address, ({}, {}))[0].get('variables', {})
        for b in conn['objects']:
            if b['role'] not in role_types: errors.append('UNDECLARED_RULE_ROLE:' + b['role'])
            if not b['object'].strip(): errors.append('EMPTY_OBJECT_NOT_IDENTITY')
            if any(ref not in sources for ref in b['refs']): errors.append('OBJECT_SOURCE_ADDRESS_INVALID')
            if not b['basis'].strip(): errors.append('OBJECT_LINK_WITHOUT_PROPOSED_BASIS')
            if b['role'] in mapping and mapping[b['role']] != b['object']: errors.append('CONFLICTING_OBJECT_BINDING')
            mapping[b['role']] = b['object']
        missing = sorted(set(role_types) - set(mapping))
        if missing: warnings.append('INCOMPLETE_OBJECT_ROLES:' + ','.join(missing))
        for j in conn['records']:
            if not 1 <= j <= len(records): continue
            rec = records[j-1]
            if any(ref not in sources for ref in rec['refs']): errors.append('RECORD_SOURCE_ADDRESS_INVALID')
        state = conn['whole_premise_state']
        if errors or missing or not conn['whole_premise_complete'] or conn['direction'] == 'CONTEXT': state = 'UNKNOWN'
        checks.append({'connection_id': pid, 'premise_id': address, 'structural_status': 'BLOCKED_LOCAL_USE' if errors else 'STRUCTURALLY_AVAILABLE',
                       'errors': sorted(set(errors)), 'warnings': sorted(set(warnings)), 'witnesses': witnesses,
                       'objects_model_proposed': mapping, 'identity_semantically_verified': False,
                       'evidence_direction': conn['direction'], 'model_connection_assessment': conn['self_assessment'],
                       'model_whole_premise_state': conn['whole_premise_state'], 'conditional_premise_state': state,
                       'semantic_approval': 'NOT_GRANTED', 'coverage': 'COMPLETE_MODEL_CLAIM' if conn['whole_premise_complete'] else 'PARTIAL_MODEL_CLAIM'})
    rule_results = []
    for rule in rules:
        # Only combine a declared, complete state of every slot under the SAME
        # explicitly proposed concrete binding, never mere support-edge counts.
        grouped = {}
        for check in checks:
            if check['premise_id'] not in {p['id'] for p in rule['premises']}: continue
            binding = tuple(sorted(check['objects_model_proposed'].items()))
            grouped.setdefault(binding, {}).setdefault(check['premise_id'], []).append(check['conditional_premise_state'])
        for binding, slots in grouped.items():
            states = []
            for p in rule['premises']:
                values = set(slots.get(p['id'], []))
                states.append(next(iter(values)) if len(values) == 1 else 'CONFLICTED' if values else 'UNKNOWN')
            operator = rule['operator']; outcome = 'UNKNOWN'
            if operator == 'ALL': outcome = 'FALSE' if 'FALSE' in states else 'TRUE' if states and all(x == 'TRUE' for x in states) else 'UNKNOWN'
            elif operator == 'ANY': outcome = 'TRUE' if 'TRUE' in states else 'FALSE' if states and all(x == 'FALSE' for x in states) else 'UNKNOWN'
            # Exception material is never silently thrown away or guessed away.
            if rule.get('exceptions') and outcome == 'TRUE': outcome = 'UNKNOWN'
            rule_results.append({'rule_id': rule['id'], 'operator': operator, 'objects': dict(binding), 'slot_states': states,
                                 'conditional_result': outcome, 'not_executed': operator not in ('ALL', 'ANY'),
                                 'exception_records': rule.get('exceptions', []), 'model_semantics_independently_verified': False})
    return {'interface': 'V17', 'checks': checks, 'conditional_rules': rule_results,
            'scope': 'STRUCTURE_AND_EXPLICIT_CONDITIONAL_LOGIC_ONLY; OPEN_TEXT_REQUIRES_EXTERNAL_SEMANTIC_INTERPRETATION',
            'approval': 'NOT_GRANTED', 'proposal_hash': hash_value(proposal), 'raw_records_retained': len(records)}

def learner_inputs(case, rules, proposal):
    """Same raw proposal/rules, actual restored text and relation content.

    Mentions are scoped by connection+role: a string does not merge identities.
    No referenced or evaluated label enters nodes, topology, or source recovery.
    """
    from .semantic_features_v12 import REL
    nodes, edges, idx = [], [], {}
    def add(key, body, kind):
        idx[key] = len(nodes); nodes.append({'id': key, 'text': json.dumps(body, ensure_ascii=False, sort_keys=True), 'kind': kind})
    q = next(q for q in case['targets'] if q['id'] == 'Q1'); add('Q:Q1', q, 3)
    for i, rec in enumerate(proposal['records'], 1): add('F:%d' % i, rec, 0)
    pindex = {}
    for rule in rules:
        for p in rule['premises']:
            pindex[p['id']] = p; add('R:' + p['id'], {'premise': p, 'rule': rule}, 1)
    pairs, materials, ids = [], {}, []
    for i, c in enumerate(proposal['connections'], 1):
        cid = 'K%02d' % i
        refs = [ref for j in c['records']+c['opposition_records'] if 1 <= j <= len(proposal['records']) for ref in proposal['records'][j-1]['refs']]
        refs += [ref for witness in c['witnesses'] for ref in witness['refs']]
        material = recover(case, list(dict.fromkeys(refs))); materials[cid] = material
        body = {'model_proposal': c, 'actual_restored_source': material}
        add('C:' + cid, body, 2); ids.append(cid)
        edges.append((idx['C:' + cid], idx['Q:Q1'], 3))
        if c['premise_id'] in pindex: edges.append((idx['R:'+c['premise_id']], idx['C:'+cid], 1))
        for j in c['records']:
            if 'F:%d' % j in idx:
                f = idx['F:%d' % j]; u = idx['C:'+cid]
                edges += [(f,u,0), (f,u, {'SUPPORT':5,'OPPOSE':6,'CONTEXT':7}[c['direction']])]
        for j in c['opposition_records']:
            if 'F:%d' % j in idx: edges.append((idx['F:%d' % j],idx['C:'+cid],6))
        for j, b in enumerate(c['objects']):
            mention = 'E:%s:%d' % (cid, j); add(mention, {'proposal': b, 'identity': 'PROPOSED_SCOPED_MENTION'}, 4)
            edges.append((idx[mention],idx['C:'+cid],4))
        pairs.append({'id': cid, 'left': json.dumps({'request': q, 'premise': pindex.get(c['premise_id']), 'proposed_connection': c['proposed_connection']}, ensure_ascii=False),
                      'right': json.dumps(body, ensure_ascii=False)})
    edges += [(b,a,r+len(REL)) for a,b,r in list(edges)]
    union = {s['id']: {'id': s['id'], 'text': s['text'], 'document': s['source_document'], 'position': s['original_position']} for m in materials.values() for s in m['segments']}
    shared = {'request': q, 'raw_proposal': proposal, 'given_rules': rules,
              'restored_source': sorted(union.values(), key=lambda s:(s['document'],s['position'],s['id'])),
              'relations': [{'from':nodes[a]['id'],'to':nodes[b]['id'],'type':REL[r] if r<len(REL) else REL[r-len(REL)]+'_REVERSE'} for a,b,r in edges]}
    # Same full common information is encoded in a shared node and CE context.
    # This adds text to the existing request node, not a new model architecture.
    nodes[idx['Q:Q1']]['text'] = json.dumps(shared, sort_keys=True, ensure_ascii=False)
    for pair in pairs: pair['shared_case_context'] = shared
    return {'graph': {'nodes': nodes, 'edges': edges, 'ids': ids, 'candidate_indices': [idx['C:'+k] for k in ids], 'request_indices': {'Q1':idx['Q:Q1']}},
            'ce_pairs': pairs, 'materials': materials, 'reference_used': False,
            'coverage': 'REFERENCED_TEXT_PLUS_FIXED_ONE_NEIGHBOUR; NOT_FULL_JUDGMENT_OMISSION_DETECTION'}

def reviewer_material(proposal):
    value = copy.deepcopy(proposal)
    for c in value['connections']:
        c.pop('self_assessment', None)
        c.pop('explanation', None)  # hide self-justification, preserve proposed claim
    return value
