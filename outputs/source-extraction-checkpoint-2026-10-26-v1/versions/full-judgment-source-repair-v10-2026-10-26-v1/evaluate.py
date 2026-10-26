"""Export whole-document artifacts and aggregate source-grounded annotations.

This module does not call a model or create labels. Missing labels remain null.
Anonymous files omit arm names; native output structures can still reveal a method.
"""
import argparse
import hashlib
import json
import secrets
from pathlib import Path
import environment as env
from source_v8 import save, digest
from prepare import load, sha


def exported_content(slot, arm):
    if arm=='LW':
        p=slot/'canonical.json'
        if not p.exists():return None
        canonical=load(p)
        # Canonical content is retained verbatim, without importing audit opinions.
        return {'native_extraction':canonical}
    p=slot/'source-records.json'
    if not p.exists():return None
    packet=load(p)
    # Strip wrapper/internal acceptance labels equally for source-content judging.
    # Raw hashes and internal states remain available separately to the adjudicator.
    return {'records':{k:v['record'] for k,v in packet['records'].items()}}


def export(run,dest):
    if dest.exists():raise ValueError('EVALUATION_DIRECTORY_ALREADY_EXISTS')
    cfg=load(env.HERE/'protocol.json');mapping=[]
    for cid in cfg['cases']:
        original=load(env.HERE/'private/preparation/inputs'/f'{cid}.json')
        for arm in cfg['arms']:
            slot=run/'cases'/cid/arm
            outcome=load(slot/'outcome.json') if (slot/'outcome.json').exists() else None
            completed=bool(outcome and outcome.get('technical_complete'))
            content=exported_content(slot,arm) if completed else None
            bid=secrets.token_hex(8)
            item={'blind_id':bid,'case_id':cid,'source_hash':digest(original['sources']),
                  'sources':original['sources'],'complete_artifact_delivered':completed,
                  'extraction':content,'task':'Judge only the full source extraction against the original, using the frozen whole-document rubric.'}
            item['artifact_hash']=digest(content)
            save(dest/'anonymous'/f'{bid}.json',item)
            mapping.append({'blind_id':bid,'case_id':cid,'arm':arm,'artifact_hash':item['artifact_hash'],
                'source_hash':item['source_hash'],'status':'UNRUN' if outcome is None else ('COMPLETED' if completed else 'TECHNICAL_FAILURE'),
                'raw_outcome_path':str(slot/'outcome.json'),'label_status':'PENDING'})
    save(dest/'private-method-map.json',{'entries':mapping,'do_not_send_to_annotator':True})
    save(dest/'README.json',{'status':'AWAITING_SOURCE_REFERENCE_AND_ANNOTATIONS',
        'method_blinding':'Arm names and internal review verdicts omitted; format blinding is imperfect.',
        'annotation_type':'Source-grounded model reference unless an actual human review is separately documented.',
        'partial_failed_outputs':'Retained in original run for diagnostics, not substituted for a delivered artifact.'})
    return {'exported':len(mapping),'scores':None}


def score(evaluation,references,labels,dest):
    """Each reference enumerates important relationships, not isolated trigger words.

    Required label fields: blind_id, artifact_hash, source_hash, reference_hash,
    matches [{reference_id, complete_correct, rationale, source_ids}], serious_errors
    [{type, description, source_ids}], minor_errors, omissions, adjudication_status,
    annotation_provenance, and preserved_disagreements. Exactly one match per unit.
    """
    mapping=load(evaluation/'private-method-map.json')['entries'];label_rows=load(labels)['annotations']
    if len({r['blind_id'] for r in label_rows})!=len(label_rows):raise ValueError('DUPLICATE_LABEL')
    by_id={r['blind_id']:r for r in label_rows};results=[]
    for item in mapping:
        cid=item['case_id'];ref=load(references/f'{cid}.json')
        if ref['source_hash']!=item['source_hash']:raise ValueError('REFERENCE_SOURCE_MISMATCH')
        important=[r['id'] for r in ref['relationships'] if r['important']]
        if not important or len(important)!=len(set(important)):raise ValueError('INVALID_IMPORTANT_REFERENCE_SET')
        base={**item,'important_reference_count':len(important),'recovery_rate':None,
              'whole_document_success':None,'serious_errors':None,'reference_hash':digest(ref)}
        if item['status']=='TECHNICAL_FAILURE':
            base.update(recovery_rate=0.0,whole_document_success=0,semantic_quality=None)
        elif item['status']=='COMPLETED' and item['blind_id'] in by_id:
            row=by_id[item['blind_id']]
            for k in ['artifact_hash','source_hash','reference_hash']:
                if row[k]!=base[k]:raise ValueError('STALE_OR_MISBOUND_LABEL:'+k)
            if row['adjudication_status']!='SOURCE_ADJUDICATED':
                base['label_status']='DISAGREEMENT_OR_REVIEW_PENDING';results.append(base);continue
            for field in ['annotation_provenance','preserved_disagreements','minor_errors','omissions']:
                if field not in row:raise ValueError('INCOMPLETE_ANNOTATION:'+field)
            matches=row['matches'];ids=[m['reference_id'] for m in matches]
            if len(ids)!=len(set(ids)) or set(ids)!=set(important):raise ValueError('MISSING_OR_DUPLICATE_IMPORTANT_RELATIONSHIP')
            allowed=set(load(evaluation/'anonymous'/f"{item['blind_id']}.json")['sources'])
            for m in matches+row['serious_errors']:
                if not m['source_ids'] or not set(m['source_ids'])<=allowed:raise ValueError('ANNOTATION_SOURCE_NOT_ALLOWED')
            if any(type(m['complete_correct']) is not bool or not m['rationale'].strip() for m in matches):
                raise ValueError('INVALID_MATCH_ASSESSMENT')
            recovered=sum(m['complete_correct'] for m in matches);errors=len(row['serious_errors'])
            base.update(recovery_rate=recovered/len(important),whole_document_success=int(recovered==len(important) and errors==0),
                serious_errors=errors,label_status='ADJUDICATED_MODEL_REFERENCE',
                preserved_disagreements=row['preserved_disagreements'])
        results.append(base)
    groups={}
    for arm in ['V9','LW','V10']:
        rows=[r for r in results if r['arm']==arm];complete=all(r['recovery_rate'] is not None for r in rows)
        groups[arm]={'denominator':len(rows),'complete_evaluation':complete,
            'mean_recovery_rate':sum(r['recovery_rate'] for r in rows)/len(rows) if complete else None,
            'whole_document_successes':sum(r['whole_document_success'] for r in rows) if complete else None,
            'technical_failures':sum(r['status']=='TECHNICAL_FAILURE' for r in rows),
            'unrun':sum(r['status']=='UNRUN' for r in rows)}
    pairs=[]
    for cid in dict.fromkeys(r['case_id'] for r in results):
        rows={r['arm']:r for r in results if r['case_id']==cid}
        for other in ['V9','LW']:
            a,b=rows['V10'],rows[other]
            pairs.append({'case_id':cid,'comparison':'V10-'+other,
                'recovery_difference':None if a['recovery_rate'] is None or b['recovery_rate'] is None else a['recovery_rate']-b['recovery_rate'],
                'serious_error_difference':None if a['serious_errors'] is None or b['serious_errors'] is None else a['serious_errors']-b['serious_errors']})
    save(dest,{'cases':results,'groups':groups,'pairs':pairs,'independent_test':False,
        'human_gold':False,'full_C_or_baseline_conclusion':None})
    return groups


def main():
    ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest='command',required=True)
    p=sp.add_parser('export');p.add_argument('run',type=Path);p.add_argument('destination',type=Path)
    p=sp.add_parser('score');p.add_argument('evaluation',type=Path);p.add_argument('references',type=Path)
    p.add_argument('labels',type=Path);p.add_argument('destination',type=Path)
    a=ap.parse_args()
    result=export(a.run,a.destination) if a.command=='export' else score(a.evaluation,a.references,a.labels,a.destination)
    print(json.dumps(result))


if __name__=='__main__':main()
