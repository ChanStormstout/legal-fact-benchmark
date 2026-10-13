"""V19_7 unified proposal-to-final interface. No reference or approval input."""
import copy
import json
from . import local_pipeline_v19_6 as previous
from . import local_pipeline_v19_refs as semantic
from .local_pipeline_v17 import obj, enum, STR
from .object_types_v19 import DOMAINS
from .rule_contracts_v19_7 import specs, digest
from .schema_contract_v19_6 import loads, validate

VERSION = 'V19_8'
source_directory = previous.source_directory
source_text = previous.source_text
coverage = previous.coverage
merge_parts = previous.merge_parts
FINAL_SCHEMA = previous.FINAL_SCHEMA


def schema(rules, case):
    sc = previous.schema(rules, case)
    for pid in sc['properties']['analyses']['properties']:
        # V19_6 reused common nested schema objects across work units. Break
        # aliases before installing premise-specific finite component enums.
        unit = copy.deepcopy(sc['properties']['analyses']['properties'][pid])
        sc['properties']['analyses']['properties'][pid] = unit
        c = specs(rules)[pid]
        unit['properties']['objects']['items']['properties']['type'] = enum([*DOMAINS, 'UNMAPPED'])
        jp = unit['properties']['judgments']['items']
        jp['properties']['basis_mode'] = enum(('ASSESS_FIXED_PROPOSITION', 'REPORT_STATEMENT_ONLY', 'PARTIAL_FACT_ONLY', 'UNMAPPED'))
        jp['required'].append('basis_mode')
        comp = jp['properties']['components']['items']
        comp['properties']['component_id'] = enum(x['id'] for x in c['components'])
        del comp['properties']['description']
        comp['required'] = ['component_id', 'alternatives']
    return sc


CONTRACT_INSTRUCTION = '''
V19_7 FIXED-PROPOSITION CONTRACT:
Each judgment assesses the exact supplied proposition, not a nearby event, statement or the fact that an objection was raised. basis_mode=ASSESS_FIXED_PROPOSITION means you assess that exact proposition. REPORT_STATEMENT_ONLY and PARTIAL_FACT_ONLY preserve useful information but do not establish a legal-effect proposition. A proposition expressly asking whether an argument was made is itself an attributed-report target and may use REPORT_STATEMENT_ONLY.
Components select the supplied component_id and retain its meaning. Code restores component text. Do not invent component IDs or change the legal question. A complete TRUE judgment needs every listed component; a FALSE judgment must identify at least one necessary component actually refuted, with its source and explanation. UNKNOWN/CONFLICTED remain available. This does not mechanically prove your semantic judgment.
Use the finite object type vocabulary; UNMAPPED is permitted. Types never establish identity. Only the declared shared variables connect different premise slots. Explicit source-grounded object_links are needed when separate local objects denote the same shared variable. Do not make different actors equal merely because they have the same role name. Optional roles may be UNMAPPED; this does not prove a missing document never existed.
Permitted whole_basis_statuses constrain which attributed records can alone bear the whole legal proposition. Other records still serve claims, background, opposition and partial evidence. Keep important rejected arguments and appellate evaluation separately. Do not upgrade an assertion to an adopted judgment. All proposed semantics and identities remain MODEL_PROPOSED; no legal approval is conferred.
'''


def proposal_prompt(case, rules, part):
    # Replace only the previous synthetic example/contract presentation. No old
    # target answer, corrected source hint or review information is consulted.
    prompt = previous.proposal_prompt(case, rules, part)
    prompt = prompt.replace('components are ALL;', 'components preserve the fixed contract;')
    example = previous.synthetic_example()
    example['analyses']['SYN.P1']['objects'][0]['type'] = 'PERSON'
    j = example['analyses']['SYN.P1']['judgments'][0]
    j['basis_mode'] = 'REPORT_STATEMENT_ONLY'
    j['components'][0]['component_id'] = 'SYN.P1.K1'
    del j['components'][0]['description']
    old_example = semantic.compact_json(previous.synthetic_example())
    prompt = prompt.replace(old_example, semantic.compact_json(example))
    return (CONTRACT_INSTRUCTION + prompt + '\nRULE INPUT CONTRACTS (not answers):\n' +
            semantic.compact_json([{'rule_id': r['id'], 'shared_variables': r['slot_variables'],
                'premises': [{'id': p['id'], **p['input_contract']} for p in r['premises']]}
                for r in rules if r['id'] in part['rule_ids']]))


def convert(raw, case, version, rules):
    if version not in ('V19_7', VERSION):
        return previous.convert(raw, case, version)
    transport = copy.deepcopy(raw)
    contracts = specs(rules)
    for pid, unit in transport['analyses'].items():
        fixed = {x['id']: x['text'] for x in contracts[pid]['components']}
        for j in unit['judgments']:
            for c in j['components']:
                c['description'] = fixed.get(c['component_id'], 'UNMAPPED_COMPONENT')
    result, ledger = previous.convert(transport, case, previous.VERSION)
    return result, [{'version': VERSION, 'conversion': 'RESTORE_FIXED_COMPONENT_TEXT', 'approval': False}] + ledger


def correspondence_errors(judgment, rule_premise, checks, p):
    """Check declared correspondence, never infer meaning from free text."""
    c = rule_premise['input_contract']; errors = []
    mode = judgment.get('basis_mode')
    if mode != 'ASSESS_FIXED_PROPOSITION' and not (mode == 'REPORT_STATEMENT_ONLY' and c['target_kind'] == 'ATTRIBUTED_REPORT'):
        errors.append('FIXED_PROPOSITION_ASSESSMENT_NOT_DECLARED')
    required = {x['id'] for x in c['components']}
    declared = [x.get('component_id') for x in judgment['components']]
    if len(declared) != len(set(declared)) or any(x not in required for x in declared):
        errors.append('FIXED_COMPONENT_ADDRESS_INVALID')
    if judgment['state'] == 'TRUE' and set(declared) != required:
        errors.append('FIXED_COMPONENT_COVERAGE_INCOMPLETE')
    if not declared:
        errors.append('NO_FIXED_COMPONENT_ASSESSMENT')
    return errors


def learner_inputs(case, rules, p):
    data = semantic.learner_inputs(case, rules, p)
    data['interface_version'] = VERSION
    data['rule_contract_sha256'] = digest(rules)
    data['encoding_status'] = 'PREPARED_NOT_YET_ENCODED'
    data['common_material_manifest']['version']=VERSION
    return data


def prediction_decisions(rows, manifest, expected, input_sha256):
    if manifest.get('version') != VERSION or manifest.get('input_sha256') != input_sha256:
        raise ValueError('STALE_VERSION_OR_INPUT_PREDICTIONS')
    legacy_manifest = {**manifest, 'version': 'V19_4'}
    return semantic.validate_predictions(rows, expected, legacy_manifest, input_sha256)


def final_task(case, rules, entry, method, prediction=None, full_rules=None):
    if method not in ('A', 'B', 'C', 'D', 'E', 'F', 'G'):
        raise ValueError('FINAL_METHOD')
    intermediate = {}
    if method == 'B':
        if not isinstance(prediction, dict) or 'prior_answer' not in prediction:
            raise ValueError('B_REQUIRES_SAME_CASE_A')
        validate(prediction['prior_answer'], FINAL_SCHEMA)
        intermediate = {'self_review': prediction['prior_answer']}
    elif method in ('C', 'D', 'E', 'F', 'G'):
        if entry.get('formal_answer') is None or entry.get('contract_status') != 'CONTRACT_VALID':
            raise ValueError('NO_ACCEPTED_PROPOSAL')
        intermediate = {'raw_P': entry['formal_answer'], 'P_scope': entry['coverage'], 'unapproved': True}
        if method != 'C':
            canonical = entry['canonical_P']
            decisions = None
            if method in ('E', 'F', 'G'):
                if prediction is None: raise ValueError('PREDICTIONS_MISSING_NO_FALLBACK')
                keys = ['K%03d' % (i+1) for i in range(len(canonical['uses']))]
                decisions = prediction_decisions(prediction['rows'], prediction['manifest'], keys, digest(entry['learner_inputs']))
            audit = apply_connection_decisions(case, rules, canonical, decisions)
            from .local_checker_v19_8 import check
            verified = check(case, rules, canonical, decisions, audit)
            if verified['status'] != 'OK': raise ValueError('FINAL_AUDIT_REJECTED')
            intermediate['checks'] = audit
            intermediate['independent_check'] = verified
    legal_pack = rules if full_rules is None else full_rules
    from .presentation_v19_8 import pack, audit as presentation_audit
    presented=pack(intermediate)
    prompt = ('V19_8 unified final entry. No legal approval is implied.\n'
        'An object {"$exact_text":"TXT:n"} means the exact unchanged string in exact_text_pool. '
        'Resolve it as that string; it does not omit, summarize or approve content.\n'
        + semantic.final_prompt(case, legal_pack, presented))
    return {'version': VERSION, 'method': method, 'prompt': prompt, 'schema': FINAL_SCHEMA,
            'input_sha256': digest({'prompt': prompt, 'schema': FINAL_SCHEMA}), 'source_ids': [s['id'] for s in case['segments']],
            'rule_addresses': sorted({v for r in legal_pack for v in [r['id'], *r.get('source_refs',[]), *[p['id'] for p in r['premises']]]}),
            'material_state': 'ASSEMBLED_NOT_GENERATED', 'semantic_success': False,
            'presentation_audit':presentation_audit(intermediate,presented)}


def accept_final(task, raw_text, technical_status):
    result = {'version': VERSION, 'method': task['method'], 'answer': None, 'technical_status': technical_status,
              'input_sha256': task['input_sha256'], 'legal_approval': False, 'semantic_evaluation': 'NOT_DONE'}
    if technical_status != 'OK': return result
    try:
        answer = loads(raw_text); validate(answer, task['schema'])
        if answer['request_id'] != 'Q1': raise ValueError('REQUEST_COVERAGE')
        for ground in answer['grounds']:
            if any(ref not in task['source_ids'] for ref in ground['case_refs']): raise ValueError('FINAL_CASE_SOURCE_OUTSIDE_ALLOWLIST')
            if any(ref not in task['rule_addresses'] for ref in ground['rule_refs']): raise ValueError('FINAL_RULE_OUTSIDE_ALLOWLIST')
        for row in answer['counterarguments'] + answer['connection_handling']:
            if any(ref not in task['source_ids'] + task['rule_addresses'] for ref in row['refs']): raise ValueError('FINAL_REFERENCE_OUTSIDE_ALLOWLIST')
        result['answer'] = answer; result['contract_status'] = 'VALID_FINAL_NOT_LEGAL_SUCCESS'
    except (ValueError, TypeError, KeyError) as e:
        result['contract_status'] = 'FINAL_CONTRACT_REJECTED'; result['error'] = str(e)
    return result

from .local_pipeline_v19_refs import (sources, object_aliases, role_directory, packet, bind, binding_type_audit, limit_effects, source_match, type_contract, LABELS, hash_value)
def apply_connection_decisions(case,rules,p,decisions=None):
    expected={'K%03d'%(i+1) for i in range(len(p['uses']))}
    if decisions is not None and set(decisions)!=expected:raise ValueError('PREDICTION_ID_COVERAGE_NO_P_FALLBACK')
    src=sources(case);aliases,linkchecks=object_aliases(p,src);roles={r['address']:r for r in role_directory(rules)}
    prem={x['id']:(x,r) for r in rules for x in r['premises']};checks=[]
    for i,u in enumerate(p['uses']):
        k='K%03d'%(i+1);pkg=packet(case,rules,p,i);errors=list(pkg['structural_input_limits']);warnings=[];b,ee=bind(u['bindings'],p['objects'],roles,u['premise'],aliases);errors+=ee
        spec,rule=prem.get(u['premise'],({},{}))
        type_rows=binding_type_audit(u['bindings'],p['objects'],roles,u['premise'])
        if not spec:errors.append('PREMISE_UNKNOWN')
        for o in pkg['objects']:
            if any(ref not in src for ref in o['refs']):errors.append('OBJECT_SOURCE_INVALID')
        scopechecks=[];full_eligible=True
        if any(x['status']=='UNMAPPED_DESCRIPTION' for x in type_rows):warnings.append('OBJECT_TYPE_UNMAPPED_UNVERIFIED_MODEL_BINDING_ASSUMPTION')
        for rec in pkg['records']:
            if any(ref not in src for ref in rec['refs']):errors.append('RECORD_SOURCE_INVALID')
            allowed=spec['input_contract']['whole_basis_statuses']
            if rec['status'] not in allowed:full_eligible=False;warnings.append('STATUS_NOT_FULL_PREMISE_BASIS')
            if rec['status'] in ('LEGAL_RULE','TARGET_DISPOSITION'):full_eligible=False;warnings.append('NOT_INDEPENDENT_CASE_FACT')
            # Rule stage is scope of legal use; do not assert every evidence item occurred there.
            scopechecks.append({'rule_stage':rule.get('stage'),'record_stage':rec.get('stage'),'record_court':rec.get('court_level'),
                                'status':'EXPLICIT_PREMISE_SCOPE_CHECK' if spec.get('stage') or spec.get('court_level') else 'RULE_SCOPE_RECORDED_SEMANTIC_COMPATIBILITY_UNVERIFIED'})
            for field in ('stage','court_level'):
                if spec.get(field):
                    if rec.get(field) in (None,'UNMAPPED'):full_eligible=False;warnings.append('SCOPE_UNMAPPED:'+field)
                    elif spec[field]!=rec[field]:errors.append('EXPLICIT_SCOPE_MISMATCH:'+field)
        locations=[]
        for w in u['witnesses']:
            loc=source_match(w,src)
            if loc.get('complete_quote_verified') is False:full_eligible=False;warnings.append('DISCONTINUOUS_QUOTE_NOT_COMPLETE_PREMISE_BASIS')
            locations.append({'witness':w,'location':loc})
            if loc.get('error'):(errors if w['necessity']=='REQUIRED' else warnings).append('WITNESS_'+loc['error'])
        if not any(w['necessity']=='REQUIRED' for w in u['witnesses']):errors.append('NO_REQUIRED_WITNESS')
        value=u['self_assessment'] if decisions is None else decisions[k]
        if value not in LABELS:raise ValueError('LABEL_INVALID')
        disposition='STRUCTURAL_INVALID' if errors else 'MODEL_REJECTED_USE' if value=='UNSUPPORTED' else 'MODEL_PENDING_USE' if value=='UNRESOLVED' else 'CONDITIONALLY_AVAILABLE_USE'
        checks.append({'connection_id':k,'premise':u['premise'],'binding':b,'direction':u['direction'],'P_label':u['self_assessment'],'applied_label':value,
                       'disposition':disposition,'errors':errors,'warnings':warnings,'locations':locations,'scope_checks':scopechecks,
                       'type_compatibility':type_rows,'type_coverage':'PENDING' if any(x['status']=='UNMAPPED_DESCRIPTION' for x in type_rows) else 'MAPPED',
                       'full_basis_eligible':full_eligible,'model_semantics_verified':False,'source_retained':True,'packet_hash':hash_value(pkg)})
    judgments=[]
    for i,j in enumerate(p['premises']):
        b,errors=bind(j['bindings'],p['objects'],roles,j['premise'],aliases);need={x['variable'] for x in roles.values() if x['premise_id']==j['premise'] and x['role'] in prem[j['premise']][0]['input_contract']['required_roles']}
        type_rows=binding_type_audit(j['bindings'],p['objects'],roles,j['premise'])
        if not need.issubset(b):errors.append('MISSING_OR_EXTRA_ROLE')
        def valid_use(k,basis=False):
            if not 1<=k<=len(checks):return False
            z=checks[k-1]
            return z['premise']==j['premise'] and all(b.get(var)==val for var,val in z['binding'].items()) and z['disposition']=='CONDITIONALLY_AVAILABLE_USE' and (not basis or (z['direction']!='CONTEXT' and z['full_basis_eligible']))
        ids=list(dict.fromkeys(j['uses']+j['opposition_uses']));available=[];blocked=[];pending=[]
        for k in ids:
            if not 1<=k<=len(checks):blocked.append({'index':k,'reason':'USE_INDEX_INVALID'});continue
            z=checks[k-1]
            if valid_use(k):available.append(z['connection_id'])
            elif z['disposition']=='MODEL_PENDING_USE':pending.append(z['connection_id'])
            else:blocked.append({'connection_id':z['connection_id'],'reason':'UNAVAILABLE_OR_BINDING_MISMATCH'})
        components=[]
        for component in j.get('components',[]):
            alternatives=[]
            for bundle in component['alternatives']:
                usable=bool(bundle) and all(k in j['uses'] and valid_use(k,True) for k in bundle)
                alternatives.append({'uses':bundle,'available':usable,
                    'supports':usable and any(checks[k-1]['direction']=='SUPPORT' for k in bundle),
                    'refutes':usable and any(checks[k-1]['direction']=='OPPOSE' for k in bundle)})
            components.append({'component_id':component.get('component_id'), 'description':component['description'],
                'alternatives':alternatives,'covered':any(a['available'] for a in alternatives),
                'support_basis':any(a['supports'] for a in alternatives),
                'refuting_basis':any(a['refutes'] for a in alternatives)})
        if not j['complete'] or not j['basis'] or not components:errors.append('WHOLE_PREMISE_DEPENDENCIES_UNESTABLISHED')
        if j['state']=='FALSE':
            if not any(c['refuting_basis'] for c in components):errors.append('NO_REFUTING_NECESSARY_COMPONENT_BASIS')
        elif j['state']=='TRUE':
            if any(not c['support_basis'] for c in components):errors.append('NECESSARY_COMPONENT_WITHOUT_SUPPORTING_BASIS')
        elif any(not c['covered'] for c in components):errors.append('NECESSARY_COMPONENT_WITHOUT_AVAILABLE_BASIS')
        if j.get('analysis_status')=='NOT_ANALYZED':errors.append('NOT_ANALYZED')
        errors += correspondence_errors(j, prem[j['premise']][0], checks, p)
        limit_audit=limit_effects(j,src)
        state='UNKNOWN' if errors or limit_audit['blocked'] or limit_audit['scope_pending'] else j['state']
        judgments.append({'id':'J%03d'%(i+1),'premise':j['premise'],'binding':b,'stage':j['stage'],'model_state':j['state'],'conditional_state':state,
                          'errors':errors,'type_compatibility':type_rows,'unverified_type_assumptions':[x for x in type_rows if x['status']=='UNMAPPED_DESCRIPTION'],'necessary_limits':j['necessary_limits'],'limit_scope_audit':limit_audit,'available_uses':available,'blocked_uses':blocked,'pending_uses':pending,
                          'basis':j['basis'],'gaps':j['gaps'],'components':components,'opposition_uses':[{'index':k,'retained':True,'available':valid_use(k)} for k in j['opposition_uses']],
                          'direction_check':'EXACT_PROPOSITION_MODEL_BASIS_RETAINED; NO_SUPPORT_TO_TRUE_SHORTCUT; SEMANTICS_NOT_PROVED',
                          'assumption':'UNVERIFIED_MODEL_WHOLE_PREMISE_JUDGMENT_NOT_USE_VOTE'})
    audit = {'interface':VERSION,'object_type_policy':type_contract(),'checks':checks,'premise_judgments':judgments,'conditional_rules':compose(rules,judgments,p['objects']),
            'object_links':linkchecks,'analysis_units':p.get('analysis_units',[]),'raw_records_retained':len(p['records']),
            'raw_opposition_retained':[c for c in checks if c['direction']=='OPPOSE'],'limitations_retained':p['coverage_limits'],
            'approval':'NOT_GRANTED','reference_used':False,'rule_scope_policy':'Rule-level stage/court recorded in actual checks; only explicit premise restrictions are mechanically enforceable. No source-document stage inheritance.'}
    audit['rule_coverage'] = route_coverage(rules, judgments, p['objects'])
    return audit

import itertools

def compose(rules, judgments, objects, cap=1000):
    """Preserve pending joins; distinct local declarations are not inequality.

    ANY branches have their own bindings. A valid independent alternative is
    evaluated without requiring equality with a branch it does not depend on.
    No names/types/null values are used to establish identity.
    """
    traces=[]
    for rule in rules:
        choices=[[j for j in judgments if j['premise']==slot['id']] or
                 [{'id':None,'binding':{},'conditional_state':'UNKNOWN'}] for slot in rule['premises']]
        total=1
        for group in choices: total*=len(group)
        for route in itertools.islice(itertools.product(*choices),cap):
            candidates={}
            for row in route:
                for var,value in row['binding'].items():
                    candidates.setdefault(var,[])
                    if value not in candidates[var]:candidates[var].append(value)
            pending=[];conflicts=[]
            for var,values in candidates.items():
                if len(values)>1:
                    domains=[set(type_contract_domain(objects[v-1].get('type'))) for v in values]
                    if all(domains) and not set.intersection(*domains):conflicts.append(var)
                    else:pending.append(var)
            vals=[]
            for slot,row in zip(rule['premises'],route):
                state=row['conditional_state']
                if slot.get('expected')=='FALSE':state={'TRUE':'FALSE','FALSE':'TRUE'}.get(state,state)
                vals.append(state)
            op=rule['operator'];state='UNKNOWN';winning=[]
            if op=='ALL' and not pending and not conflicts:
                state='FALSE' if 'FALSE' in vals else 'CONFLICTED' if 'CONFLICTED' in vals else 'TRUE' if vals and all(v=='TRUE' for v in vals) else 'UNKNOWN'
            elif op=='ANY':
                winning=[i for i,v in enumerate(vals) if v=='TRUE']
                state='TRUE' if winning else 'CONFLICTED' if 'CONFLICTED' in vals else 'FALSE' if vals and all(v=='FALSE' for v in vals) else 'UNKNOWN'
            if rule.get('exceptions') and state=='TRUE':state='UNKNOWN'
            binding={v:ids[0] for v,ids in candidates.items() if len(ids)==1}
            traces.append({'rule_id':rule['id'],'operator':op,'binding':binding,
                'binding_candidates':candidates,'branch_bindings':[r['binding'] for r in route],
                'identity_pending':pending,'explicit_type_conflicts':conflicts,
                'join_status':'INDEPENDENT_ALTERNATIVES' if op=='ANY' else 'EXPLICIT_TYPE_CONFLICT' if conflicts else 'IDENTITY_PENDING' if pending else 'CONNECTED',
                'winning_branch_inputs':[route[i]['id'] for i in winning],
                'inputs':[r['id'] for r in route],'slot_states':vals,'conditional_result':state,
                'not_executed':op not in ('ALL','ANY'),'exceptions':rule.get('exceptions',[]),
                'limits':rule.get('limits',[]),'enumeration_complete':total<=cap,'stage':rule.get('stage'),
                'status':'CONDITIONAL_UNVERIFIED_MODEL_SEMANTICS'})
    return traces

def type_contract_domain(typ):
    from .object_types_v19 import normalize
    return normalize(typ)['domain']

def route_coverage(rules, judgments, objects):
    traces=compose(rules,judgments,objects)
    result=[]
    for r in rules:
        groups=[[j for j in judgments if j['premise']==p['id']] or [None] for p in r['premises']]
        total=1
        for g in groups:total*=len(g)
        rows=[t for t in traces if t['rule_id']==r['id']]
        result.append({'rule_id':r['id'],'cartesian_routes':total,'routes_examined':len(rows),
            'identity_pending_routes':sum(bool(t['identity_pending']) for t in rows),
            'explicit_type_conflict_routes':sum(bool(t['explicit_type_conflicts']) for t in rows),
            'retained_routes':len(rows),'enumeration_complete':total<=1000})
    return result
