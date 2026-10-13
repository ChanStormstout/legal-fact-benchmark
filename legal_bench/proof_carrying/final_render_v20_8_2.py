"""The model selects/organizes reviewed clauses; code renders their exact text.

No generated paraphrase can introduce a new actor, event, premise or conclusion.
This is a source-reconstruction interface repair, not learned legal inference.
Whole-answer scope/coverage and source review are still required.
"""
import json
from . import final_bindings_v20_8 as bindings
from . import final_source_guard_v20_7 as guard
from .artifact_state_v20_2 import digest
from .schema_contract_v19_6 import loads, validate

VERSION = 'V20_8_REVIEWED_CLAUSE_RENDER_1'


def final_task(case, old_task, bridge, frame, frame_review):
    base = bindings.final_task(case, old_task, bridge, frame, frame_review)
    book = base['verification_task']['claim_registry']['accepted']
    clauses = {}
    for key, row in book.items():
        if row['kind'] == 'ATTRIBUTION':
            claim = row['claim']
            clauses[key] = {'text': claim['proposition'], 'status': claim['status'],
                            'stage': claim['stage'], 'refs': row['source_refs'],
                            'kind': 'ATTRIBUTION', 'actor_ids': [], 'property_ids': [], 'event_ids': []}
    for i, event in enumerate(frame['events'], 1):
        key = 'FE%02d' % i
        clauses[key] = {'text': event['description'], 'status': event['statement_status'],
                        'stage': event['stage'], 'refs': book[key]['source_refs'],
                        'kind': 'FRAME_FACT', 'actor_ids': [event['actor_id']],
                        'property_ids': [event['property_id']] if event['property_id'] != 'NONE' else [],
                        'event_ids': [event['id']]}
    actors = {a['id']: a for a in frame['actors']}
    dispositions = ['FE%02d' % i for i, e in enumerate(frame['events'], 1)
                    if e['kind'] in ('COURT_ORDER', 'COURT_REMAND')
                    and actors[e['actor_id']]['court_level'] == 'Supreme Court']
    if not dispositions:
        raise ValueError('NO_REVIEWED_FINAL_COURT_DISPOSITION')
    allowed = sorted(clauses)
    schema = guard.obj({'request_id': guard.enum(['Q1']),
                        'disposition_claim_ids': guard.array(guard.enum(dispositions), len(dispositions), len(dispositions)),
                        'reasoning_claim_ids': guard.array(guard.enum(allowed), 1, 12),
                        'ground_claim_ids': guard.array(guard.enum(allowed), 1, 24),
                        'counterargument_claim_ids': guard.array(guard.enum(allowed), 0, 16)})
    request = old_task['review_context']['request']
    prompt = '''Select and organize SOURCE-REVIEWED clauses for this historical
judgment reconstruction. Output ONLY clause IDs, no new prose or facts. Code will
render the exact checked text and its attribution/stage, concrete actors/property,
procedural events, all source-reviewed attributions in an appendix, and the
unchanged conditional execution status. You cannot paraphrase a lower court as a
higher court, a beneficiary as an issuer, retirement as an application, or an
if-clause as performed payment. Every final Supreme Court disposition is required.
Use reasoning_claim_ids for decisive adopted legal reasoning; ground_claim_ids
for the reasoning route and factual/procedural basis; counterargument_claim_ids
for decisive contrary accounts, rejected positions and dissent. Preserve status,
stage and scope; a quotation of an allegation is not proof that it is true.
The same clause cannot be both a ground and a counterargument. Include decisive
opposition and uncertainty. This is a complete source reconstruction, not a legal
certificate or predictive assessment. No source text is cut. Only the exact final
rendered candidate may pass an independent whole-answer source/coverage review.
'''
    material = {'request': request, 'reviewed_frame': frame, 'reviewed_clauses': clauses,
                'conditional_rules': bridge['conditional_rules'],
                'rules': old_task['review_context']['rules']}
    prompt += '\nREVIEWED INPUT:\n' + json.dumps(material, ensure_ascii=False, separators=(',', ':'))
    prompt += '\nCOMPLETE ALLOWED SOURCE:\n' + '\n'.join(s['id'] + '\n' + s['text'] for s in case['segments'])
    prompt += '\nOUTPUT SCHEMA:\n' + json.dumps(schema, separators=(',', ':'))
    verification = bindings.clone(base['verification_task'])
    appendix_schema = bindings.clone(verification['schema']['properties']['grounds'])
    appendix_schema['maxItems'] = max(appendix_schema.get('maxItems', 0), len(clauses))
    verification['schema']['properties']['source_attribution_appendix'] = appendix_schema
    verification['schema']['required'] = list(verification['schema']['properties'])
    verification['prompt'] = prompt
    verification['review_context']['render_policy'] = {
        'version': VERSION, 'literal_source_reviewed_clauses_only': True,
        'all_reviewed_attributions_in_separate_appendix': True,
        'no_new_legal_premises': True}
    verification['input_sha256'] = digest({k: verification[k] for k in ('prompt', 'schema', 'review_context')})
    proxy = bindings.clone(base)
    proxy['verification_task'] = verification
    proxy['schema']['properties']['source_attribution_appendix'] = bindings.clone(appendix_schema)
    proxy['schema']['required'] = list(proxy['schema']['properties'])
    proxy['prompt'] = prompt
    proxy['input_sha256'] = digest({k: v for k, v in proxy.items() if k != 'input_sha256'})
    task = {'version': VERSION, 'prompt': prompt, 'schema': schema,
            'source_sha256': digest(case['segments']), 'clauses': clauses,
            'frame': bindings.clone(frame), 'dispositions': dispositions,
            'review_proxy': proxy, 'source_input_truncated': False,
            'all_original_claims_saved_in_verification_registry': True}
    task['input_sha256'] = digest(task)
    return task


def verify_task(task, case):
    if task['version'] != VERSION or digest({k: v for k, v in task.items() if k != 'input_sha256'}) != task['input_sha256']:
        raise ValueError('CLAUSE_TASK_CHANGED')
    if task['source_sha256'] != digest(case['segments']):
        raise ValueError('CLAUSE_SOURCE_CHANGED')
    bindings.verify_task(task['review_proxy'], case)


def sentence(text):
    return text if text.endswith(('.', '?', '!')) else text + '.'


def render(task, plan, case):
    verify_task(task, case)
    validate(plan, task['schema'])
    if set(plan['ground_claim_ids']) & set(plan['counterargument_claim_ids']):
        raise ValueError('CLAUSE_CONTRADICTORY_SECTION_ASSIGNMENT')
    def row(key, counter=False):
        c = task['clauses'][key]
        if counter:
            return {'point': c['status'] + '; ' + c['stage'] + ' [' + key + ']',
                    'refs': c['refs'], 'treatment': c['text'], 'claim_ids': [key],
                    'actor_ids': c['actor_ids'], 'property_ids': c['property_ids'], 'event_ids': c['event_ids']}
        return {'point': c['stage'] + ' [' + key + ']',
                'statement_status_and_stage': c['status'] + '; ' + c['stage'],
                'case_refs': c['refs'], 'rule_refs': [], 'explanation': c['text'],
                'claim_ids': [key], 'actor_ids': c['actor_ids'],
                'property_ids': c['property_ids'], 'event_ids': c['event_ids']}
    summary_ids = list(dict.fromkeys(plan['disposition_claim_ids'] + plan['reasoning_claim_ids']))
    # Keep complete reviewed contrary accounts available, even if the selector
    # omitted one. Each retains its ORIGINAL status/stage; the appendix is not a
    # declaration that every entry defeats the adopted reasoning.
    ground_ids = plan['ground_claim_ids']
    appendix = [k for k in sorted(task['clauses'])
        if task['clauses'][k]['kind'] == 'ATTRIBUTION'
        and k not in set(ground_ids) | set(plan['counterargument_claim_ids'])]
    answer = {'request_id': plan['request_id'],
              'conclusion': ' '.join(sentence(task['clauses'][k]['text']) for k in summary_ids),
              'conclusion_claim_ids': summary_ids, 'result_status': 'SOURCE_RECONSTRUCTION',
              'grounds': [row(k) for k in ground_ids],
              'counterarguments': [row(k, True) for k in plan['counterargument_claim_ids']],
              'source_attribution_appendix': [row(k) for k in appendix],
              'gaps': [], 'assumptions': [], 'connection_handling': [],
              'case_frame': bindings.clone(task['frame'])}
    validate(answer, task['review_proxy']['verification_task']['schema'])
    checked = guard.inspect_candidate(task['review_proxy']['verification_task'], answer)
    if checked['status'] != 'OK':
        raise ValueError('CLAUSE_RENDER_INVALID:' + str(checked['errors']))
    return answer


def review_task(task, plan, case):
    answer = render(task, plan, case)
    writer = {k: v for k, v in answer.items() if k != 'case_frame'}
    rt = bindings.review_task(task['review_proxy'], writer, case)
    start = rt['prompt'].index('{"bindings":')
    end = rt['prompt'].index('\nOUTPUT SCHEMA:\n', start)
    payload = json.loads(rt['prompt'][start:end])
    all_claims = task['review_proxy']['verification_task']['claim_registry']['accepted']
    used = set(payload['reviewed_claims']['accepted'])
    pending = [k for row in answer['source_attribution_appendix'] for k in row['claim_ids']]
    while pending:
        key = pending.pop()
        if key not in used:
            used.add(key)
            pending.extend(all_claims[key]['dependencies'])
    payload['reviewed_claims']['accepted'] = {k: all_claims[k] for k in sorted(used)}
    payload['review_display']['selected_claims_and_all_dependencies'] = sorted(used)
    rt['prompt'] = rt['prompt'][:start] + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + rt['prompt'][end:]
    rt['review_display'] = payload['review_display']
    return rt


def accept_final(task, raw, technical_status, *, case, review=None):
    if technical_status != 'OK':
        return {'version': VERSION, 'answer': None, 'technical_status': technical_status,
                'contract_status': 'GENERATION_FAILED', 'legal_approval': False}
    try:
        plan = loads(raw)
        answer = render(task, plan, case)
        writer = {k: v for k, v in answer.items() if k != 'case_frame'}
        result = bindings.accept_final(task['review_proxy'], json.dumps(writer), 'OK', case=case, review=review)
        result.update(version=VERSION, selector_sha256=digest(plan),
                      prose_rendered_literally_from_source_reviewed_inputs=True,
                      full_attribution_appendix_preserved=True)
        return result
    except (ValueError, KeyError, TypeError) as exc:
        return {'version': VERSION, 'answer': None, 'technical_status': technical_status,
                'contract_status': 'CLAUSE_RENDER_CONTRACT_REJECTED', 'error': str(exc),
                'legal_approval': False}
