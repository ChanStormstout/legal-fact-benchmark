"""Bounded source repair, independent criticism and local dependency recomputation.

Original generations and sources are never changed. Reviewer labels are model
judgments, not human gold or legal approval. No reference labels are input.
"""
import copy
import json
from collections import Counter
from . import local_pipeline_v19_8 as core
from . import local_checker_v19_8 as checker
from . import source_verification_v20_2 as verification
from . import evidence_binding_gate_v20_5 as binding
from . import shared_sources_v20_3 as shared
from . import declared_references_v20_4 as addresses
from .rule_contracts_v19_7 import digest
from .rule_contracts_v19_8 import validate_rules
from .schema_contract_v19_6 import validate

VERSION = 'V20_6_6_NEUTRAL_SOURCE_REPAIR_AND_LOCAL_RECOMPUTATION'


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))



def model_rules(rules):
    """Do not expose rule-condition polarity as an expected factual answer."""
    result=copy.deepcopy(rules)
    for rule in result:
        rule.pop('slot_variables',None)
        for premise in rule['premises']:
            premise.pop('expected',None)
    return result

def corrected_rules(original):
    """Explicit semantic category correction; no changed proposition or outcome."""
    rules = copy.deepcopy(original)
    changes = []
    for rule in rules:
        for premise in rule['premises']:
            if ('statutory_term' in premise['variables']
                    and premise.get('original_variable_descriptions', {}).get('statutory_term') == 'person'
                    and premise['variables']['statutory_term'] == 'PERSON'):
                premise['variables']['statutory_term'] = 'LEGAL_CONCEPT'
                premise['input_contract']['role_types']['statutory_term'] = 'LEGAL_CONCEPT'
                changes.append({'premise': premise['id'], 'role': 'statutory_term',
                    'old': 'PERSON', 'new': 'LEGAL_CONCEPT',
                    'reason': 'The supplied role identifies the statutory word, not a natural person.'})
                # The original contract remains frozen in the input fixture;
                # this version records its explicit change separately.
                rule['category_correction_version'] = VERSION
    validate_rules(rules)
    return rules, changes


def sources(case):
    return '\n'.join(f"SRC:{i} | {s['id']} | {s['text']}"
                     for i, s in enumerate(case['segments'], 1))


def metadata_schema(schema):
    result = copy.deepcopy(schema)
    def walk(node, name=None):
        if not isinstance(node, dict):
            return
        if name in ('coverage_limits', 'gaps', 'limits', 'assumptions') and node.get('type') == 'array':
            node['uniqueItems'] = True
            # Bound annotations, never original source or substantive propositions.
            node['maxItems'] = min(node.get('maxItems', 256), 8)
            if node.get('items', {}).get('type') == 'string':
                node['items']['maxLength'] = 480
        for key, value in node.get('properties', {}).items():
            walk(value, key)
        if 'items' in node:
            walk(node['items'])
        for value in node.get('$defs', {}).values():
            walk(value)
    walk(result)
    return result


REPAIR_INSTRUCTION = '''Read the entire allowed judgment and assess EVERY supplied fixed premise.
The previous proposal is untrusted material to check, not an answer or a reference.
Produce one replacement analysis, preserving important qualifications and opposition.
Ground each role in the particular source entity/event: identify parties by names and
capacities, dates by their events, sums by unit and legal meaning, documents by purpose.
An allegation, a submission, a lower-court finding and an adopted appellate finding
are different claims. A source title cannot establish detailed facts. Read beyond
previously cited passages. Answer the EXACT fixed proposition, not a nearby question.
Use ANALYZED with UNKNOWN when examination leaves a genuine source gap. NOT_ANALYZED
means no examination and must have empty records/objects/uses/judgments. Do not discuss
an omitted unit only in coverage_limits. Include evidence-backed counterarguments.
Source lists contain the actual supporting passages, not the whole document. Reuse
shared source sets, but do not reuse a broad list for unrelated roles. Local OBJ/EV/USE
positions describe only their own unit. Cross-unit identity requires sourced links.
Give concise coverage limits about specific uncompleted work or actual source ambiguity.
Do not copy format explanations, synthetic examples, disclaimers or this instruction
into the answer. Required JSON fields do not justify inventing evidence or a finding.
'''


def repair_task(case, rules, part, original):
    selected = [r for r in rules if r['id'] in part['rule_ids']]
    view = {**case, 'segments': [s for s in case['segments'] if s['id'] in part['source_ids']]}
    original_schema = core.schema(selected, view)
    schema = metadata_schema(binding.generation_schema(original_schema, view, selected))
    # Restore the legacy material exactly through its shared source representation;
    # no source-reviewed labels, reference answers or corrected bindings are supplied.
    previous = shared.pack(verification.hide_self(original))
    prompt = (REPAIR_INSTRUCTION + core.CONTRACT_INSTRUCTION + shared.INSTRUCTION + addresses.INSTRUCTION
        + '\nFIXED REQUEST:\n' + compact(next(q for q in case['targets'] if q['id'] == 'Q1'))
        + '\nFIXED RULES AND ROLE CONTRACTS:\n' + compact(model_rules(selected))
        + '\nUNTRUSTED PREVIOUS PROPOSAL:\n' + compact(previous)
        + '\nCOMPLETE ALLOWED SOURCE:\n' + sources(view)
        + '\nOUTPUT SCHEMA:\n' + compact(schema))
    return {'version': VERSION, 'prompt': prompt, 'schema': schema,
        'original_schema': original_schema, 'case': view, 'rules': selected, 'part': part,
        'source_sha256': digest(view['segments']), 'previous_sha256': digest(original),
        'reference_used': False, 'source_input_truncated': False}


def empty_supplement(raw):
    return {'analyses': {pid: {'analysis_status': 'NOT_ANALYZED', 'records': [],
            'objects': [], 'uses': [], 'judgments': [], 'limits': []} for pid in raw['analyses']},
        'object_links': [], 'coverage_limits': []}


def critique_task(case, rules, raw):
    declarations = verification.declarations(raw, 'P', rules)
    groups = {}
    for declaration in declarations:
        claim = copy.deepcopy(declaration['claim'])
        # Address/collection differences do not make the same semantic binding a
        # different question. Preserve exact aliases for expanding the verdict.
        if declaration['kind'] == 'OBJECT_BINDING':
            claim.pop('proposed_local_address', None)
        key = digest({'kind': declaration['kind'], 'claim': claim, 'refs': declaration['refs']})
        if key not in groups:
            groups[key] = {'kind': declaration['kind'], 'claim': claim,
                'refs': declaration['refs'], 'aliases': []}
        groups[key]['aliases'].append(declaration['id'])
    claims = {'D'+str(i): row for i, row in enumerate(groups.values(), 1)}
    source_enum = binding.citation_choices(case)
    verdict = {'type': 'object', 'properties': {
        'label': {'type': 'string', 'enum': list(verification.LABELS)},
        'refs': {'type': 'array', 'items': {'$ref': '#/$defs/source_choice'},
            'minItems': 0, 'maxItems': len(source_enum), 'uniqueItems': True},
        'reason': {'type': 'string', 'minLength': 1, 'maxLength': 240}},
        'required': ['label', 'refs', 'reason'], 'additionalProperties': False}
    schema = {'type': 'object', '$defs': {
        'source_choice': {'type': 'string', 'enum': source_enum}, 'verdict': verdict},
        'properties': {
        'verdicts': {'type': 'object', 'properties': {k: {'$ref': '#/$defs/verdict'} for k in claims},
            'required': list(claims), 'additionalProperties': False},
        'coverage_limits': {'type': 'array', 'items': {'type': 'string', 'minLength': 1,
            'maxLength': 480}, 'minItems': 0, 'maxItems': 8, 'uniqueItems': True}},
        'required': ['verdicts', 'coverage_limits'], 'additionalProperties': False}
    prompt = ('''Independently check each exact supplied claim against the COMPLETE allowed source.
Do not inherit the candidate's confidence, labels or conclusions. A rule's required condition is not an observed factual answer. SUPPORTED means the
particular identity, event, attribution, stage, direction and full claimed scope are
supported. A legal source address or compatible type alone is not support. UNSUPPORTED
requires a clear semantic error with source evidence; otherwise use UNRESOLVED.
Check each date against its event and each quantity against its unit and meaning.
For ATTRIBUTION verify who stated/found what and whether the court adopted it.
For EVIDENCE_USE verify the proposed direction and role bindings, not just relevance.
For PREMISE_BASIS assess the exact fixed proposition and every necessary component;
partial/background evidence and the mere existence of a party argument cannot establish
the whole premise. A correct opposition use can be SUPPORTED without making the opposed
proposition TRUE. Preserve conflicting source accounts rather than choosing silently.
Conditionals, legal prerequisites and reported precedent principles are not observations that their antecedents occurred.
A claim of first actual knowledge remains unresolved when expressly contested and not separately found.
Do not bind generic legal placeholders or unknown dates as identified case facts.
Give relevant supporting/counterevidence refs; SUPPORTED/UNSUPPORTED require refs.
Read beyond candidate refs. Output concise verdicts only; do not propose new facts.
This review is a model judgment, not legal approval.\n'''
        + '\nCLAIMS (ref_set:Cn resolves to the exact source_sets[n-1]; output uses SRC refs):\n'
        + compact(shared.pack({k: {f: v for f, v in row.items() if f != 'aliases'}
                                    for k, row in claims.items()}))
        + '\nFIXED LEGAL CONTRACTS:\n' + compact(model_rules(rules))
        + '\nCOMPLETE ALLOWED SOURCE:\n' + sources(case)
        + '\nOUTPUT SCHEMA:\n' + compact(schema))
    return {'version': VERSION, 'prompt': prompt, 'schema': schema, 'claims': claims,
        'raw_sha256': digest(raw), 'source_sha256': digest(case['segments']),
        'rule_sha256': digest(rules), 'reference_used': False,
        'source_input_truncated': False}


def apply_critique(case, rules, raw, task, criticism):
    if (task['raw_sha256'] != digest(raw) or task['source_sha256'] != digest(case['segments'])
            or task['rule_sha256'] != digest(rules)):
        raise ValueError('STALE_SOURCE_CRITIQUE')
    validate(criticism, task['schema'])
    verdicts = []
    for key, value in criticism['verdicts'].items():
        for alias in task['claims'][key]['aliases']:
            verdicts.append({'declaration': alias, 'kind': task['claims'][key]['kind'],
                'label': value['label'], 'refs': value['refs'], 'counter_refs': [],
                'reason': value['reason']})
    q = {'supplement': empty_supplement(raw), 'verdicts': verdicts,
        'coverage_limits': criticism['coverage_limits']}
    result = verification.apply(case, rules, raw, q)
    result.update(version=VERSION, original_replacement_sha256=digest(raw),
        original_material_preserved=True, policy='LOCAL_DECLARATION_REFUSAL_NOT_WHOLE_PART_REJECTION',
        reviewer='SAME_PINNED_LLM_SEPARATE_SOURCE_REVIEW_NOT_STATISTICALLY_INDEPENDENT',
        criticism_sha256=digest(criticism))
    result['decision_counts'] = dict(Counter(v['label'] for v in verdicts))
    return result


def merge_applied(case, rules, parts):
    # merge_parts consumes imported unit records, not its own flattened result.
    # Reimport the actually applied immutable replacement, not the unreviewed P.
    imported = []
    for name, row in parts:
        raw = row['applied_proposals']['P']
        converted, _ = core.convert(raw, case, 'V19_8', rules)
        import_check = checker.check_import(raw, converted, case, 'V19_8', rules)
        if import_check['status'] != 'OK':
            raise ValueError('REPAIRED_PART_IMPORT_REJECTED')
        imported.append((name, converted))
    canonical, ledger = core.merge_parts(imported)
    merged = checker.check_merge(imported, canonical)
    if merged['status'] != 'OK':
        raise ValueError('REPAIRED_PART_MERGE_REJECTED')
    audit = core.apply_connection_decisions(case, rules, canonical)
    independent = checker.check(case, rules, canonical, None, audit)
    if independent['status'] != 'OK':
        raise ValueError('REPAIRED_DEPENDENCY_RECOMPUTATION_REJECTED')
    for route in audit['conditional_rules']:
        rule = next(r for r in rules if r['id'] == route['rule_id'])
        if rule.get('unmapped_shared_variable_contract'):
            route['conditional_result'] = 'UNKNOWN'
            route['contract_limit'] = 'SHARED_VARIABLE_MAPPING_NOT_DECLARED'
    return {'version': VERSION, 'canonical': canonical, 'audit': audit,
        'independent': independent, 'merge_check': merged, 'merge_ledger': ledger,
        'legal_approval': False, 'semantic_approval': False}


def final_task(case, rules, merged, applied_parts):
    # All detailed audits/raw material remain saved. Only this documented analysis
    # projection enters generation, together with ALL original allowed source.
    material = {'parts': {}, 'conditional_rules': merged['audit']['conditional_rules'],
        'model_review_is_not_legal_approval': True}
    for part, result in applied_parts:
        raw = result['applied_proposals']['P']
        declarations = {d['id']: d for d in result['pool']['candidates']}
        view = {}
        for pid, unit in raw['analyses'].items():
            judgments = []
            bindings = []
            for declaration in declarations.values():
                if (declaration['id'].startswith('P/'+pid+'/')
                        and declaration['kind'] == 'OBJECT_BINDING'
                        and declaration['proposed_label'] == 'SUPPORTED'):
                    claim = declaration['claim']
                    row = {'role': claim['role'], 'object': claim['object'],
                        'stage': claim['scope']}
                    if row not in bindings:
                        bindings.append(row)
            for i, judgment in enumerate(unit['judgments'], 1):
                key = 'P/'+pid+'/J:'+str(i)
                if declarations[key]['proposed_label'] == 'SUPPORTED':
                    judgments.append({'state': next((a['conditional_state'] for a in result['audit']['premise_judgments'] if a['premise']==pid), 'UNKNOWN'), 'model_claimed_state': judgment['state'], 'complete': judgment['complete'],
                        'basis': judgment['basis'], 'stage': judgment['stage'],
                        'gaps': judgment['gaps'], 'necessary_limits': judgment['necessary_limits'],
                        'basis_refs': declarations[key]['verification_refs'],
                        'reviewed_bindings': bindings})
            records = [r for i, r in enumerate(unit['records'], 1)
                       if declarations['P/'+pid+'/EV:'+str(i)]['proposed_label'] == 'SUPPORTED']
            # This projection contains resolved identities, never reindexed local
            # addresses. Rejected original text remains in the saved full audit.
            view[pid] = {'analysis_status': unit['analysis_status'],
                'source_reviewed_records': records, 'source_reviewed_bindings': bindings,
                'reviewed_judgments': judgments,
                'pending_or_rejected_declarations': [
                    {'id': d['id'], 'label': d['proposed_label'], 'reason': d['verifier_reason']}
                    for d in declarations.values() if d['id'].startswith('P/'+pid+'/')
                    and d['proposed_label'] != 'SUPPORTED']}
        material['parts'][part] = view
    schema = metadata_schema(copy.deepcopy(core.FINAL_SCHEMA))
    rule_addresses = sorted({v for r in rules for v in [r['id'], *r.get('source_refs', []),
        *[p['id'] for p in r['premises']]]})
    source_addresses = [s['id'] for s in case['segments']]
    ground = schema['properties']['grounds']['items']['properties']
    ground['case_refs']['items'] = {'type': 'string', 'enum': source_addresses}
    ground['rule_refs']['items'] = {'type': 'string', 'enum': rule_addresses}
    for key in ('counterarguments', 'connection_handling'):
        schema['properties'][key]['items']['properties']['refs']['items'] = {
            'type': 'string', 'enum': source_addresses + rule_addresses}
    for key in ('grounds', 'counterarguments', 'connection_handling'):
        props = schema['properties'][key]['items']['properties']
        for name in ('refs', 'case_refs', 'rule_refs'):
            if name in props:
                props[name]['uniqueItems'] = True
    prompt = ('''Answer the fixed request using the entire allowed judgment and supplied legal rules.
The intermediate analysis has undergone source criticism and local recomputation.
Rejected/pending claims are displayed for audit only; never adopt them as established
facts. If you independently recover a missing fact from the original source, state
its source and attribution; do not say the checker approved it. Follow the exact
names, events, dates, quantity units and court stages. Preserve material opposition,
uncertainty and distinctions. OPEN_TEXT/identity-pending routes are not executed proofs.
Explain reported court reasoning as reported reasoning, not independent proof or a
prediction of a future judgment. Answer in English, using the supplied JSON schema.
Use original IK source addresses for citations. Do not repeat commentary or disclaimers.
\nFIXED REQUEST:\n''' + compact(next(q for q in case['targets'] if q['id'] == 'Q1'))
        + '\nFIXED LEGAL RULES:\n' + compact(model_rules(rules))
        + '\nREVIEWED ANALYSIS AND EXPLICIT PENDING CLAIMS:\n' + compact(material)
        + '\nCOMPLETE ALLOWED SOURCE:\n' + sources(case)
        + '\nOUTPUT SCHEMA:\n' + compact(schema))
    return {'version': VERSION, 'method': 'D', 'prompt': prompt, 'schema': schema,
        'input_sha256': digest({'prompt': prompt, 'schema': schema}),
        'source_ids': source_addresses, 'rule_addresses': rule_addresses,
        'source_input_truncated': False, 'projection': material,
        'full_audit_saved_separately': True, 'semantic_success': False}
