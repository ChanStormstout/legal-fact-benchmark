"""Check web grouping proposals without treating matching names as identity proof."""


def validate_grouping_reply(reply, task, sources):
    errors = []
    if not isinstance(reply, dict) or not isinstance(reply.get('cases'), list):
        return {'valid': False, 'errors': ['Expected an object with cases']}
    rows = reply['cases']
    if any(not isinstance(row, dict) for row in rows):
        return {'valid': False, 'errors': ['Invalid case entry']}
    ids = [row.get('case_id') for row in rows]
    if any(not isinstance(cid, str) for cid in ids):
        return {'valid': False, 'errors': ['Case IDs must be strings']}
    if len(ids) != len(set(ids)) or set(ids) != set(task['case_ids']):
        errors.append('Missing, additional or duplicate case IDs')
    if reply.get('batch_id') != task['batch_id']:
        errors.append('Wrong batch')
    if reply.get('end_marker') != 'END_COMPLETE_GROUP_REVIEW ' + task['batch_id']:
        errors.append('Missing response end marker')
    source_map = {source['case_id']: {s['id']: s['text'] for s in source['segments']} for source in sources}
    for row in rows:
        cid = row['case_id']
        if cid not in source_map:
            errors.append(cid + ': missing source'); continue
        if row.get('review_state') not in ['IDENTIFIER_REVIEW_COMPLETE', 'FULL_SOURCE_REVIEW_REQUIRED']:
            errors.append(cid + ': invalid review state')
        groups = row.get('associated_disputes')
        if not isinstance(groups, list) or not groups:
            errors.append(cid + ': missing associated disputes'); continue
        if any(not isinstance(group, dict) for group in groups):
            errors.append(cid + ': invalid dispute'); continue
        keys = [group.get('key') for group in groups]
        if any(not isinstance(key, str) or not key for key in keys):
            errors.append(cid + ': invalid dispute keys'); continue
        if len(keys) != len(set(keys)) or row.get('primary_dispute_key') not in keys:
            errors.append(cid + ': primary dispute or duplicate key invalid')
        for group in groups:
            evidence = group.get('evidence')
            if not isinstance(evidence, list) or not evidence:
                errors.append(cid + ': dispute needs evidence'); continue
            for ev in evidence:
                if (not isinstance(ev, dict) or ev.get('segment_id') not in source_map[cid]
                    or not isinstance(ev.get('quote'), str) or not ev['quote']
                    or ev['quote'] not in source_map[cid][ev['segment_id']]):
                    errors.append(cid + ': unlocated dispute quote')
        if not isinstance(row.get('links'), list):
            errors.append(cid + ': missing links')
        else:
            for link in row['links']:
                if not isinstance(link, dict) or link.get('other_case_id') not in task['case_ids'] or link.get('other_case_id') == cid:
                    errors.append(cid + ': invalid linked document')
    return {'valid': not errors, 'errors': errors,
            'interpretation': 'Coverage and exact dispute evidence only; not a proof of identity or sample independence'}
