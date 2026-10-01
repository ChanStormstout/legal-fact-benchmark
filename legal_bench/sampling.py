"""Outcome-blind candidate order. Candidate summaries never establish eligibility."""
import re
from .core import digest

CLAIM_PATTERN = re.compile(r'\b(?:evict\w*|eject\w*|recover\w*\s+(?:of\s+)?possession|suit\s+for\s+possession)\b', re.I)
TENANCY_PATTERN = re.compile(r'\b(?:tenant\w*|tenancy|landlord\w*|rent)\b', re.I)


def reviewed_dispute_groups(row):
    """All disputes exposed by a document, not just its chosen primary request."""
    group = row.get('dispute_group')
    if not isinstance(group, str) or not group:
        raise ValueError('Missing dispute group')
    groups = row.get('associated_dispute_groups')
    if groups is None:
        if row.get('multi_dispute_document'):
            raise ValueError('Common judgment requires all reviewed dispute groups')
        return {group}
    if (not isinstance(groups, list) or not groups or group not in groups
            or any(not isinstance(g, str) or not g for g in groups)):
        raise ValueError('Invalid associated dispute groups')
    return set(groups)


def candidate_queue(records, dev_ids, target=100, seed=20260930):
    if type(target) is not int or target < 1:
        raise ValueError('Target must be a positive integer')
    ids = [str(r['doc_id']) for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate corpus IDs')
    dev_ids = set(map(str, dev_ids))
    candidates = []
    for record in records:
        case_id = str(record['doc_id'])
        if case_id in dev_ids:
            continue
        text = str(record.get('facts', '')) + '\n' + str(record.get('issues', ''))
        claim, tenancy = CLAIM_PATTERN.search(text), TENANCY_PATTERN.search(text)
        if not claim or not tenancy:
            continue
        candidates.append({'case_id': case_id, 'title': record['title'], 'url': record['url'],
                           'record_sha256': digest(record), 'state': 'CANDIDATE_NOT_ELIGIBLE',
                           'screening_hits': [claim.group(), tenancy.group()],
                           'order_key': digest({'seed': seed, 'case_id': case_id})})
    candidates.sort(key=lambda r: (r['order_key'], r['case_id']))
    for rank, row in enumerate(candidates, 1):
        row['rank'] = rank
    return {'version': 'tenant-possession-screen-v1', 'seed': seed, 'target_check_cases': target,
            'development_case_ids': sorted(dev_ids), 'candidate_count': len(candidates),
            'order_rule': 'sha256 of canonical JSON {seed,case_id}; ascending; independent of model results',
            'selection_rule': 'First target eligible distinct dispute groups in this fixed order, after source and cross-case group review; never replace difficult annotations',
            'state': 'SOURCE_AND_GROUP_REVIEW_PENDING', 'cases': candidates}


def select_screened(queue, decisions):
    """Fail closed on unfinished earlier ranks or undocumented independence."""
    by_id = {r['case_id']: r for r in decisions}
    if len(by_id) != len(decisions):
        raise ValueError('Duplicate screening decisions')
    used = set(queue.get('development_dispute_groups', []))
    if len(used) != 5:
        raise ValueError('Five development dispute groups must be reviewed before final selection')
    used.update(queue.get('development_associated_dispute_groups', []))
    selected, excluded = [], []
    for row in queue['cases']:
        decision = by_id.get(row['case_id'])
        if not decision or decision.get('state') not in ['ELIGIBLE', 'INELIGIBLE', 'SOURCE_UNAVAILABLE', 'RELATED']:
            raise ValueError('Unfinished earlier screening rank: ' + str(row['rank']))
        if not decision.get('evidence') or not decision.get('source_review_sha256'):
            raise ValueError('Screening decision needs source review evidence and hash')
        if decision['state'] != 'ELIGIBLE':
            excluded.append(decision)
            continue
        if decision.get('source_completeness') != 'VERIFIED_FULL' or decision.get('group_review_state') != 'REVIEWED':
            raise ValueError('Eligible case requires complete source and cross-case dispute review')
        groups = reviewed_dispute_groups(decision)
        if groups & used:
            excluded.append(dict(decision, state='RELATED'))
            continue
        used.update(groups)
        selected.append(dict(row, screening=decision, split='check'))
        if len(selected) == queue['target_check_cases']:
            return {'state': 'SOURCE_SCREENED_SAMPLE', 'target_check_cases': queue['target_check_cases'],
                    'queue_sha256': digest(queue), 'cases': selected, 'excluded': excluded,
                    'next_rank': row['rank'] + 1, 'label_origin': 'MODEL_GENERATED_NOT_HUMAN_GOLD'}
    raise ValueError('Insufficient independently reviewed eligible groups')
