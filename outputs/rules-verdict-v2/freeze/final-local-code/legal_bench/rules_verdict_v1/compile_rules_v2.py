"""Source-linked partial compilation: never upgrades a fragment to a legal rule."""
import copy
from .apply_rules import validate_query, execute


def compile_card(card, condition_mappings):
    """Every natural-language condition remains represented, even if unsupported.

    Mappings are versioned developer translations of model-reviewed RuleCards.
    They cannot assert that a quoted statute is a complete consolidated statute.
    Each mapping is either one existing factual query or an explicit unsupported
    reason. Whole-rule consequence execution is intentionally unavailable until
    connective/scope/exception semantics are independently implemented.
    """
    required=['id','proposition','source_kind','conditions','scope','evidence','effect']
    if any(k not in card for k in required):
        raise ValueError('Missing normalized RuleCard fields')
    ids=[c['id'] for c in card['conditions']]
    if len(set(ids)) != len(ids) or set(condition_mappings) != set(ids):
        raise ValueError('All and only source conditions must be mapped')
    clauses=[]
    for c in card['conditions']:
        m=copy.deepcopy(condition_mappings[c['id']])
        if set(m)=={'query','translation_note'}:
            validate_query(m['query'])
            clauses.append({'condition':c,'execution_kind':'FACT_QUERY_FRAGMENT',**m})
        elif set(m)=={'unsupported_reason'} and m['unsupported_reason']:
            clauses.append({'condition':c,'execution_kind':'UNSUPPORTED',**m})
        else:raise ValueError('Explicit query or unsupported reason required')
    return {'rule_id':card['id'],'source_card':copy.deepcopy(card),'conditions':clauses,
            'whole_rule_execution_status':'UNSUPPORTED',
            'reason':'CONDITION_FRAGMENTS_DO_NOT_IMPLEMENT_FULL_LOGICAL_SCOPE_OR_LEGAL_EFFECT',
            'exceptions_retained':copy.deepcopy(card.get('exceptions',[])),
            'legal_effect_may_be_emitted':False}


def apply_fragments(compiled, facts):
    rows=[]
    for c in compiled['conditions']:
        if c['execution_kind']=='UNSUPPORTED':
            result={'run_status':'UNSUPPORTED','answer_status':None,'reason':c['unsupported_reason']}
        else:
            result=execute(facts,c['query'])
        rows.append({'condition_id':c['condition']['id'],'condition_text':c['condition']['text'],
                     'kind':c['condition']['kind'],'result':result})
    return {'rule_id':compiled['rule_id'],'conditions':rows,'run_status':'UNSUPPORTED',
            'answer_status':None,'legal_effect':None,
            'reason':compiled['reason'],
            'warning':'No independent-condition vote, no cross-binding legal conclusion; NOT_FOUND is not legal defeat.'}
