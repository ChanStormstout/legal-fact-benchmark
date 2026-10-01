"""Apply explicit, source-reviewed type-only projections to copied views.

Quote and hash checks establish provenance, not semantic correctness. Semantic
support is an explicit local model judgement saved by the two-case study, never
inferred from the presence of a type label or a matching word. No default grants
are created for other records, and wildcard limits on other fields survive.
"""
import copy
from .core import digest


REVIEW_KIND = 'LOCAL_MODEL_SOURCE_REVIEW_NOT_HUMAN_GOLD'
SCOPE = 'COARSE_SIGNED_ASSERTION_TYPE_ONLY_NOT_OCCURRENCE_OR_SCOPE'


def apply_type_projections(view, source, reviews):
    out = copy.deepcopy(view)
    events = {e['id']: e for e in out['events']}
    segments = {s['id']: s['text'] for s in source['segments']}
    seen = set()
    for review in reviews:
        if review['case_id'] != view['case_id'] or source['case_id'] != view['case_id']:
            raise ValueError('Projection case mismatch')
        if review['view_hash'] != digest(view) or review['source_hash'] != digest(source):
            raise ValueError('Stale projection evidence')
        event = events[review['event_id']]
        if event['id'] in seen:
            raise ValueError('Duplicate type projection')
        seen.add(event['id'])
        if (review.get('review_kind') != REVIEW_KIND or review.get('scope') != SCOPE
                or review.get('field') != 'type' or review.get('value') != event['type']
                or review.get('source_support') is not True or not review.get('rationale')):
            raise ValueError('Explicit source-reviewed type-only judgement required')
        evidence = review.get('evidence', [])
        if not evidence or any(not e.get('quote') or
                               e['quote'] not in segments.get(e.get('segment_id'), '') for e in evidence):
            raise ValueError('Unlocated projection quote')
        if any('type' in b['affected_fields'] for b in event['field_contract']['blocked']):
            raise ValueError('Explicit predicate uncertainty is outside this minimal repair')
        event['field_contract']['source_reviewed_type_projection'] = copy.deepcopy(review)
        event['field_contract']['type_unresolved'] = False
    return out
