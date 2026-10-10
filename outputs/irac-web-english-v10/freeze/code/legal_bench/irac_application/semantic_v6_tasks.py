"""One frozen interface revision; no case-specific hints or semantic repairs."""
import copy
import json

from .semantic_v6 import catalogue, source_catalogue, display
from .pipeline_v4_tasks import GUIDE, FINAL_GUIDE, EXAMPLES, schema as old_schema
from .hybrid_v3_tasks import obj, arr, S, enum, A, STAT

PROPOSAL_GUIDE = '''Organize the supplied record for this request, without predicting the request outcome.
records stores each distinct attributed account once: text includes its speaker and procedural stage, statement_status preserves its evidential position, refs identifies the supplied passages. These are accounts of evidence, not independently inspected originals. Program-assigned record numbers are their one-based array positions. A record has no parent arrangement. Different accounts about one event remain distinct records, not automatically different events.
arrangements describes the actual persons, premises and transaction or ongoing situation, with case refs. Number arrangements by their one-based array positions. Later testimony, a finding, an appeal, a date question or a consent question does not alone create another transaction. Shared names do not establish that separate transactions are identical. Keep uncertainty rather than inventing a connection.
conditions contains only useful local analyses. Select a condition ID from the readable CONDITION_CATALOGUE; each ID already determines its legal branch. arrangement is the array position, or 0 if the connection is unknown. evidence connects existing record numbers to this particular analysis: role SUPPORT/OPPOSE concerns relevance to the printed proposition, CONTEXT is background, IRRELEVANT explicitly excludes an inapplicable record, and UNRESOLVED leaves correspondence open. connection briefly explains that use; the same record may be connected independently to more than one arrangement. It is not a vote or a finding that the whole condition is satisfied.
assessment is your separate, reasoned judgment of the complete proposition (SUPPORTED, REFUTED, UNRESOLVED, UNSUPPORTED), not a restatement of an edge direction. explanation weighs the pertinent support, opposition, identity, statement status and legal scope; law_refs cites the rule and gaps preserves important uncertainty. Support need not be sufficient, silence is not refutation, and conflicting accounts are not decided by counting. Law can interpret a requirement; facts of another precedent cannot alone establish a fact in this case. Source roles are supplied by code.
limitations is optional in coverage. A limitation selects an arrangement and condition. EVIDENCE_USE_BLOCK targets only listed records in that local analysis. CONDITION_PENDING with records=[] expressly limits that entire proposition. NOTE preserves a caveat without blocking. UNMAPPED records uncertain scope; arrangement=0 and condition="" are available. Each limit has reason and refs; an invalid source does not release an otherwise identifiable limitation. Free-text gaps alone do not silently disable a whole case.
Use sparse arrays. Prefer 5-8 records and the decisive conditions; maxima are ceilings, not targets. No need to cover all conditions or fill unknown roles. Preserve important opposition and multiple court stages. If coverage is limited, state it in coverage_limits. Every top-level array must exist, but may be empty. Return one complete JSON within budget; no repeated long quotations or separate request answer.'''

EXAMPLE = {
    'label': 'COMPLETE FICTIONAL INTERMEDIATE EXAMPLE; NOT TARGET LAW OR FACTS',
    'input': {'case_sources': {'EX-S1': 'Orin alleges that Leda installed lamp Q without permission. The municipal panel found installation by Leda; on appeal Leda disputes that finding.',
                             'EX-S2': 'A receipt concerns Leda buying a chair, not installing lamp Q.'},
              'law': {'EX-L1': 'Fictional Lamp Code: an unauthorized personal installation meets the installation ground.'},
              'conditions': {'EX-INSTALL': 'Leda personally installed lamp Q.', 'EX-UNAUTHORIZED': 'That installation lacked permission.'}},
    'output': {
        'records': [{'text': 'Orin alleges Leda installed Q without permission.', 'statement_status': 'PARTY_CLAIM', 'refs': ['EX-S1']},
                    {'text': 'Municipal panel found Leda installed Q; Leda contests that finding on appeal.', 'statement_status': 'PRIOR_COURT_FINDING', 'refs': ['EX-S1']},
                    {'text': 'The supplied receipt records a chair purchase.', 'statement_status': 'RECORDED_DOCUMENT', 'refs': ['EX-S2']}],
        'arrangements': [{'description': 'Leda; lamp Q; alleged installation challenged on appeal', 'refs': ['EX-S1']}],
        'conditions': [{'arrangement': 1, 'condition': 'EX-INSTALL', 'assessment': 'SUPPORTED',
                        'evidence': [{'record': 1, 'role': 'SUPPORT', 'connection': 'Alleges the same installation.'},
                                     {'record': 2, 'role': 'SUPPORT', 'connection': 'Prior finding about this installation, still contested on appeal.'},
                                     {'record': 3, 'role': 'IRRELEVANT', 'connection': 'A chair purchase does not address lamp installation.'}],
                        'law_refs': ['EX-L1'], 'explanation': 'I use the specific prior finding as a stage-qualified premise; the allegation is not independent proof and appellate acceptance is undecided.',
                        'gaps': ['The appeal challenge remains open.']},
                       {'arrangement': 1, 'condition': 'EX-UNAUTHORIZED', 'assessment': 'UNRESOLVED',
                        'evidence': [{'record': 1, 'role': 'SUPPORT', 'connection': 'Alleges absence of permission.'}],
                        'law_refs': ['EX-L1'], 'explanation': 'A relevant allegation supplies an argument, but the supplied panel finding addresses installation only and does not establish lack of permission.',
                        'gaps': ['No permission instrument or finding on permission is supplied.']}],
        'limitations': [], 'coverage_limits': ['This proposal does not decide the pending appeal.']}}

FINAL_ADDITION = '''Completion contract: answer each listed substantive request exactly once; never return an empty answers array or duplicate a claim. Keep at least one decisive condition analysis. reason must distinguish what this record establishes at its stated stage, what legal application is unresolved, and which assumptions sustain the binary prediction. Use gaps for concrete unresolved matters. A required binary choice does not convert every unknown into a negative condition or create a burden-of-proof or appellate-effect rule.
For method B, the intermediate proposal is raw model output, not a verified fact table. No program audit is supplied. Read the complete case and law to correct it when necessary; identify consequential corrections using intermediate_correction. For method A, intermediate material is empty; apply the same final contract. Final answers, source IDs and condition labels being syntactically valid do not establish legal correctness.'''


def schema(stage, material, template, law):
    if stage != 'proposal':
        sc = copy.deepcopy(old_schema('final', material, template, law))
        count = len([c for c in template['claims'] if c['expression']['op'] != 'UNSUPPORTED'])
        sc['properties']['answers']['minItems'] = count
        sc['properties']['answers']['maxItems'] = count
        sc['properties']['answers']['items']['properties']['conditions']['minItems'] = 1
        return sc
    allrefs = arr(enum(list(source_catalogue(material, law))), 6)
    lawrefs = arr(enum([s['source_id'] for s in law]), 6)
    case_refs = arr(enum(list(material['sources'])), 6)
    condition = enum(list(catalogue(template)))
    # The inherited enum helper is string-only; numeric array addresses must
    # declare integer type. The fixed constraint runtime itself is unchanged.
    recno = {'type': 'integer', 'enum': list(range(1, 13))}
    ano = {'type': 'integer', 'enum': list(range(0, 5))}
    return obj({
        'records': arr(obj({'text': S, 'statement_status': STAT, 'refs': allrefs}), 12),
        'arrangements': arr(obj({'description': S, 'refs': case_refs}), 4),
        'conditions': arr(obj({'arrangement': ano, 'condition': condition, 'assessment': A,
                              'evidence': arr(obj({'record': recno, 'role': enum(['SUPPORT', 'OPPOSE', 'CONTEXT', 'UNRESOLVED', 'IRRELEVANT']), 'connection': S}), 8),
                              'law_refs': lawrefs, 'explanation': S, 'gaps': arr(S, 3)}), 12),
        'limitations': arr(obj({'arrangement': ano, 'condition': enum([''] + list(catalogue(template))),
                                'records': arr(recno, 8), 'effect': enum(['EVIDENCE_USE_BLOCK', 'CONDITION_PENDING', 'NOTE', 'UNMAPPED']),
                                'reason': S, 'refs': allrefs}), 6),
        'coverage_limits': arr(S, 4)})


def prompt(stage, material, template, law, source_map, intermediate=None):
    view, _, _ = display(material, source_map)
    parts = [GUIDE]
    if stage == 'proposal':
        parts += [PROPOSAL_GUIDE, json.dumps(EXAMPLE, ensure_ascii=False)]
    else:
        parts += ['TWO COMPLETE FICTIONAL EXAMPLES:', json.dumps(EXAMPLES, ensure_ascii=False), FINAL_GUIDE, FINAL_ADDITION]
    roles = {k: v['role'] for k, v in source_catalogue(material, law).items()}
    parts += ['SOURCE_ROLES (addresses classified by frozen input provenance):', json.dumps(roles),
              'CONDITION_CATALOGUE (ID, complete proposition and exact parent/branch mapping):', json.dumps(catalogue(template), ensure_ascii=False),
              'COMMON GIVEN LAW:', json.dumps(law, ensure_ascii=False),
              'COMMON LEGAL STRUCTURE:', json.dumps(template, ensure_ascii=False),
              'INTERMEDIATE MATERIAL:', json.dumps(intermediate or {}, ensure_ascii=False),
              'COMPLETE ALLOWED CASE MATERIAL:', json.dumps(view, ensure_ascii=False),
              'TASK: ' + ('Organize decisive records, actual arrangements and reasoned condition judgments. Do not write a final request prediction.' if stage == 'proposal' else
                         'Under the supplied facts, law and procedural stage, should each specified substantive request be supported? Answer each request once; make an explicit prediction and state its evidence, legal gaps and assumptions.')]
    return '\n\n'.join(parts)
