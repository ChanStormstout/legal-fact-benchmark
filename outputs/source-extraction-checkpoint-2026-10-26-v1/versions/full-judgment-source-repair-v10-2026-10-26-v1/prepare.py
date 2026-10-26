"""Prepare a fixed whole-document cohort and request previews; no model client."""
import hashlib
import json
from pathlib import Path
import environment as env
import source_v10 as method
import source_v9
from source_v8 import save, digest
from communication import request_wire

SEED='source-v10-cohort-20261026:'
ANCHORS=['1251841','1252014']
SOURCE_ROOT=env.REPO/'outputs/rapido-source-screen-v1/private/sources-02'
IDENTITY=env.REPO/'outputs/rapido-source-screen-v1/identity-groups.json'
PRIOR=env.REPO/'outputs/rapido-source-record-repair-v17-2026-10-23-v1/protocol.json'


def load(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def document_sources(raw):
    segments=raw['segments']
    start=next(s['line'] for s in segments if s['text'].startswith('### Supreme Court'))
    stop=next(s['line'] for s in segments if s['line']>start and s['text'].startswith('### Related AI tags'))
    sources={s['id']:s['text'] for s in segments if start<=s['line']<stop and s['text'].strip()}
    return sources,[start,stop-1]


def wire(req,cfg):
    return request_wire({'policy':req['policy'],'task':req['task'],'schema':req['schema'],
        'material':{k:v for k,v in req.items() if k not in ['policy','task','schema']},
        'output_token_cap':cfg['parameters']['max_tokens']},cfg)


def main():
    dest=env.HERE/'private/preparation'
    if dest.exists():raise ValueError('PREPARATION_ALREADY_EXISTS')
    old=load(PRIOR)['cases']; identities=load(IDENTITY)
    membership={cid:g['cluster_id'] for g in identities['groups'] for cid in g['members']} if 'groups' in identities else {}
    if not membership:
        for value in identities.values():
            if isinstance(value,list):
                for g in value:
                    if isinstance(g,dict) and 'cluster_id' in g:
                        membership.update({cid:g['cluster_id'] for cid in g['members']})
    inventory=[];eligible=[]
    for p in sorted(SOURCE_ROOT.glob('*.json')):
        raw=load(p)
        if not isinstance(raw,dict) or 'segments' not in raw:continue
        reasons=[]
        if raw.get('status')!='COMPLETE_RENDERED_TEXT' or raw.get('missing_lines') or raw.get('conflicts'):reasons.append('INCOMPLETE_OR_CONFLICTED_RENDERING')
        if p.stem in old:reasons.append('PREVIOUS_TWELVE_CASE_COHORT')
        if p.stem not in membership:reasons.append('NO_LOCAL_DISPUTE_GROUP_RECORD')
        try:document_sources(raw)
        except (StopIteration,KeyError):reasons.append('DOCUMENT_BOUNDARY_NOT_IDENTIFIED')
        row={'case_id':p.stem,'source_path':str(p),'source_sha256':sha(p),
             'rank':hashlib.sha256((SEED+p.stem).encode()).hexdigest(),'exclusion_reasons':reasons}
        inventory.append(row)
        if not reasons:eligible.append(row)
    selected=list(ANCHORS);groups={membership[c] for c in selected}
    for row in sorted(eligible,key=lambda r:r['rank']):
        cid=row['case_id']
        if membership[cid] in groups:row['exclusion_reasons'].append('SAME_SELECTED_DISPUTE_GROUP');continue
        selected.append(cid);groups.add(membership[cid])
        if len(selected)==6:break
    if len(selected)!=6:raise ValueError('SIX_SOURCE_DOCUMENTS_NOT_AVAILABLE')
    cfg=load(env.V9/'protocol.json')
    for k in ['capacity_diagnostic','billing_authorization_mode','diagnostic_case_limit','diagnostic_arm_limit',
              'maximum_new_usd','planned_calls','comparison_reference','arm_labels','diagnostic_output_tokens']:
        cfg.pop(k,None)
    cfg.update(version=method.VERSION,cases=selected,arms=['V9','LW','V10'],execution_enabled=False,
        paid_api_enabled=False,capacity_diagnostic=False,diagnostic_output_tokens=65536,
        scope='Whole-document source extraction only; no A0, full C, training, retrieval or prediction.',
        cohort_role='EXPOSED_DEVELOPMENT_WITH_FOUR_ADDITIONAL_LOCAL_DISPUTE_GROUPS',
        unknown_usage_policy='RESERVE_AND_ISOLATE_FAILED_CASE',allow_unknown_usage_reserve_continuation=False,
        comparison_scope='V9, full-document local LatentWeaver adaptation with the arbitrary word refusal removed, and V10; not native upstream performance.',
        prior_conservative_usd=None,maximum_new_usd=None,
        annotation_status='SOURCE_ONLY_PACKETS_PREPARED_REFERENCE_ANNOTATION_PENDING',
        no_semantic_reruns=True,publication_language='ENGLISH',
        old_accounting_is_not_new_authorization=True,baseline_run_enabled=False,full_pipeline_run_enabled=False)
    rows=[]
    for cid in selected:
        p=SOURCE_ROOT/(cid+'.json');raw=load(p);sources,bounds=document_sources(raw)
        if cid in ANCHORS:
            original=load(env.PREP/'private/inputs'/(cid+'.json'))['sources']
            if sources!=original:raise ValueError('ANCHOR_SOURCE_CHANGED:'+cid)
        catalog=method.prepare_units(sources);v9_groups=source_v9.plan(sources)
        rendered='\n\n'.join('['+k+']\n'+v for k,v in sources.items())
        row={'case_id':cid,'title':raw.get('title'),'original_url':raw.get('original_url'),
             'source_path':str(p),'source_sha256':sha(p),'source_map_hash':digest(sources),
             'document_line_bounds':bounds,'source_entries':len(sources),
             'words':sum(len(v.split()) for v in sources.values()),'rendered_words':len(rendered.split()),
             'source_chars':sum(len(v) for v in sources.values()),'dispute_group':membership[cid],
             'independence_status':'PROVISIONAL_LOCAL_COHORT_GROUPING_NOT_EXHAUSTIVE_REGISTRY_SEARCH',
             'prior_exposure':'KNOWN_ANCHOR' if cid in ANCHORS else 'PREVIOUS_SOURCE_SCREEN_AND_DESIGN_MATERIAL_NOT_SEALED_TEST',
             'prompt_revision_exposure_verified_absent':False,
             'v10_batches':len(catalog['groups']),'v10_review_groups':len(method.review_groups(catalog)),
             'v10_planned_calls':2*len(catalog['groups'])+2*len(method.review_groups(catalog)),
             'v9_planned_calls':2*len(v9_groups),'lw_planned_calls':4,
             'lw_scope_status':'FULL_DOCUMENT_ADAPTATION_HOSTED_CONTEXT_LIMIT_APPLIES',
             'court_certified':False,'scope':'Complete cached rendered document region, including headnote, reasoning and outcome; not all underlying litigation materials.'}
        rows.append(row)
        save(dest/'inputs'/(cid+'.json'),{'case_id':cid,'sources':sources,'manifest':row})
        save(dest/'catalogs'/(cid+'.json'),catalog)
        for i,focus in enumerate(catalog['groups']):
            for role,independent in [('primary',False),('independent',True)]:
                req=method.reading_request(sources,catalog,focus,independent)
                save(dest/'requests'/cid/(f'{i:03d}-{role}.json'),wire(req,cfg))
        annotation={'case_id':cid,'source_hash':digest(sources),'sources':sources,
            'task':'Prepare a whole-document material-relationship reference from the original only. Record speaker, participants, polarity, case/procedure, conditions and exact source IDs. Distinguish unknown from false. Do not see method outputs. Preserve disagreements.',
            'reference_status':'NOT_ANNOTATED','model_reference_not_human_gold':True}
        save(dest/'annotation-source-only'/(cid+'.json'),annotation)
    max_calls=max(max(r['v10_planned_calls'],r['v9_planned_calls'],4) for r in rows)
    cfg.pop('planning_cost_usd_range',None)
    cfg.update(arm_order_reason='Rotate the three arms by case position before outcomes are observed; no arm receives prior outputs.',
        arm_order_by_case={c:cfg['arms'][i%3:]+cfg['arms'][:i%3] for i,c in enumerate(selected)},
        comparator_adapter='latentweaver_v10.py',comparator_native_chunk_schedule=False,
        max_calls_per_arm=max_calls*2,max_input_tokens_per_arm=max_calls*2*262144,
        max_output_tokens_per_arm=max_calls*2*65536,local_total_seconds=max_calls*2*2400,
        max_logical_calls_per_arm=max_calls,
        resource_policy='Common ceiling based on the largest complete frozen plan plus at most one identical technical retry per logical call; no source truncation.')
    save(env.HERE/'protocol.json',cfg)
    save(dest/'cohort.json',{'selection_seed':SEED,'prior_cohort_path':str(PRIOR),'identity_path':str(IDENTITY),
        'identity_sha256':sha(IDENTITY),'selection':'Two fixed anchors plus four hash-ranked complete sources outside the old twelve, one per local dispute group; no outcome filtering.',
        'inventory':inventory,'selected':rows,'sealed_test':False,'reference_annotation_complete':False})
    print(json.dumps({'cases':selected,'planned_calls':{a:sum(r[a.lower()+'_planned_calls'] for r in rows) for a in cfg['arms']},
                      'unsupported_lw':[r['case_id'] for r in rows if not r['lw_planned_calls']],'new_model_calls':0}))


if __name__=='__main__':main()
