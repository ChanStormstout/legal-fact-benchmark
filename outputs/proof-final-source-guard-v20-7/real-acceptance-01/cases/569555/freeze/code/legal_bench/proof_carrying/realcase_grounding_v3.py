"""Address checks and explicitly reviewed reconstruction assumptions, not a legal oracle."""
import re
from .contracts import content_hash


def canonical_chars(text):
    """Return comparison characters and reversible offsets into untouched input.

    Only citation wrappers and whitespace (including renderer spaces next to
    punctuation) are ignored. Words, numbers, punctuation and negation stay.
    """
    excluded = set()
    for m in re.finditer(r'cite[^†]*†([^]*)', text):
        excluded.update(range(m.start(), m.start(1)))
        excluded.update(range(m.end(1), m.end()))
    visible = [(c, i) for i, c in enumerate(text) if i not in excluded]
    out, positions = [], []
    for k, (c, i) in enumerate(visible):
        if c.isspace():
            if not out or out[-1] == ' ': continue
            nxt = next((v for v, _ in visible[k+1:] if not v.isspace()), '')
            if not nxt or nxt in ".,;:!?)]}'’" or out[-1] in "'’": continue
            c = ' '
        out.append(c); positions.append(i)
    return ''.join(out), positions


def source_match(record, sources):
    refs = record.get('refs', record.get('source_refs', []))
    if not refs or any(r not in sources for r in refs):
        return {'error': 'SOURCE_ADDRESS_MISSING'}
    quote = record.get('quote', record.get('source_quote', ''))
    joined = ' '.join(sources[r]['text'] for r in refs)
    q, _ = canonical_chars(quote); text, offsets = canonical_chars(joined)
    start = text.find(q) if q else -1
    if start < 0: return {'error': 'QUOTE_NOT_LOCATED'}
    lo, hi = offsets[start], offsets[start+len(q)-1]+1
    spans, base = [], 0
    for ref in refs:
        raw = sources[ref]['text']; a, b = max(0, lo-base), min(len(raw), hi-base)
        if a < b: spans.append({'ref':ref,'start':a,'end':b,'original':raw[a:b]})
        base += len(raw)+1
    return {'error':None,'mode':'EXACT' if quote in joined else 'RENDERER_WHITESPACE_OR_CITATION',
            'original_spans':spans,'semantic_verified':False}


def reviewed(record):
    if not record: return False
    review = record.get('review', {})
    body = {k:v for k,v in record.items() if k != 'review'}
    return (review.get('decision') == 'ACCEPT_RESEARCH' and
            review.get('subject_hash') == content_hash(body) and
            review.get('actor') == 'MODEL_ASSISTED_SOURCE_REVIEW' and
            review.get('qualified_legal_approval') is False)


def role_view(snap, step, slot, premise, rule):
    """Map roles only under a separately reviewed, slot-local permutation."""
    from .realcase_contracts import binding_map
    binding = binding_map(premise.get('bindings', []))
    key = step['id']+':'+slot
    record = snap.get('role_mappings', {}).get(key)
    if record is None: return binding, None, None
    expected = {'case_id':snap['case_id'],'stage':snap['stage'],
                'rule_ref':step['rule_ref'],'rule_hash':content_hash(rule),
                'premise_id':premise['id'],'premise_hash':content_hash(premise),'slot':slot}
    if (not reviewed(record) or any(record.get(k)!=v for k,v in expected.items()) or
            source_match(record,snap['sources'])['error']):
        return binding, 'ROLE_MAPPING_UNVERIFIED', None
    mapping = record.get('roles', {})
    if set(mapping)!=set(binding) or set(mapping.values())!=set(binding):
        return binding, 'ROLE_MAPPING_NOT_PERMUTATION', None
    return {k:binding[v] for k,v in mapping.items()}, None, record['id']


def court_assessment(snap, step, rule):
    """Authenticate an attributed assessment. Its legal merits are NOT recomputed.

    The supplied policy is a separate semantic research assumption; it cannot
    be supplied by the proposing certificate itself or inferred from TRUE.
    """
    record = snap.get('court_assessments', {}).get(step['id'])
    if record is None: return None, None
    expected = {'case_id':snap['case_id'],'stage':snap['stage'],
                'step_hash':content_hash(step),'rule_ref':step['rule_ref'],
                'rule_hash':content_hash(rule),'predicate':rule['conclusion_predicate'],
                'bindings':step['bindings'],'time_scope':step['time_scope'],
                'statement_status':'TARGET_COURT_FINDING','state':'TRUE'}
    if (not reviewed(record) or any(record.get(k)!=v for k,v in expected.items()) or
            source_match(record,snap['sources'])['error']):
        return None, 'COURT_ASSESSMENT_UNVERIFIED'
    if any(snap['sources'][r]['role']=='DISPOSITION_ONLY' or
           snap['sources'][r]['document']!=snap['case_id'] for r in record['refs']):
        return None, 'COURT_ASSESSMENT_SOURCE_ROLE'
    return record, None
