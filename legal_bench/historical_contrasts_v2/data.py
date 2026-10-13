"""Reviewed source views and labels. Unknown never becomes a negative."""
from collections import Counter
from pathlib import Path
import json
from legal_bench.historical_contrasts_v1.contracts import ContractError, digest, read_json, write_immutable

SPLITS={'TRAIN','VALIDATION','DEVELOPMENT_HOLDOUT'}
UTILITIES={'POSITIVE','NEGATIVE','UNKNOWN','DISPUTED'}

def parse_raw_review(raw):
    """Audit original exported text before a normal parser can discard duplicate keys."""
    def pairs(values):
        d={}
        for k,v in values:
            if k in d:raise ContractError('DUPLICATE_RAW_JSON_KEY',detail=k)
            d[k]=v
        return d
    def constant(value):raise ContractError('NONFINITE_RAW_JSON',detail=value)
    start,end=raw.find('{'),raw.rfind('}')
    if start<0 or end<start:raise ContractError('NO_RAW_JSON_OBJECT')
    return json.loads(raw[start:end+1],object_pairs_hook=pairs,parse_constant=constant)

def audit_task_coverage(path,review):
    """Bind an export to its own task, not just the union of all case IDs."""
    task=path.parent.parent/'tasks'/(path.stem+'.txt')
    if not task.exists():raise ContractError('REVIEW_TASK_REQUIRED',detail=str(task))
    text=task.read_text()
    if '\nPUBLIC SOURCE MATERIAL\n' not in text:raise ContractError('TASK_SOURCE_MARKER')
    material=parse_raw_review(text.split('\nPUBLIC SOURCE MATERIAL\n',1)[1].split('\nEND_OF_INPUT',1)[0])
    kind='queries' if path.stem.startswith('LABELS-') else 'references'
    if set(review)!={kind}:raise ContractError('REVIEW_TOP_LEVEL_FIELDS')
    if Counter(r['case_id'] for r in review[kind])!=Counter(r['case_id'] for r in material[kind]):
        raise ContractError('REVIEW_TASK_CASE_COVERAGE',detail=path.stem)
    if kind=='queries':
        expected=Counter(r['case_id'] for r in material['references'])
        for r in review[kind]:
            if Counter(x['candidate_case_id'] for x in r['labels'])!=expected:
                raise ContractError('REVIEW_TASK_CANDIDATE_COVERAGE',detail=r['case_id'])

def audit_export(path,review):
    path=Path(path)
    receipt=path.with_name(path.stem+'-merge-receipt.json')
    if receipt.exists():
        merge=read_json(receipt)
        if merge.get('operation')!='CONCATENATE_UNCHANGED_QUERIES':raise ContractError('MERGE_OPERATION')
        names=merge.get('parts',[])
        if not names or len(set(names))!=len(names):raise ContractError('MERGE_PARTS')
        rows=[]
        for name in names:
            if Path(name).name!=name or not name.startswith(path.stem) or name==path.name:
                raise ContractError('MERGE_PART_PATH')
            part=path.with_name(name);value=read_json(part);audit_export(part,value)
            if digest(value)!=merge['part_sha256'][name]:raise ContractError('MERGE_PART_CHANGED')
            rows.extend(value['queries'])
        if review!={'queries':rows}:raise ContractError('REVIEW_CHANGED_DURING_MERGE')
        audit_task_coverage(path,review)
        return
    # Reference format recovery is preserved separately from its malformed first reply.
    raw=path.with_name(path.stem+'-format-recovery.txt')
    if not raw.exists():raw=path.with_name(path.stem+'-raw.txt')
    if not raw.exists():raise ContractError('ORIGINAL_REVIEW_EXPORT_REQUIRED',detail=str(path))
    if parse_raw_review(raw.read_text())!=review:raise ContractError('REVIEW_CHANGED_DURING_EXPORT',detail=str(path))
    audit_task_coverage(path,review)

def check_quotes(refs, sources, excluded=(), required=True):
    if not isinstance(refs,list) or (required and not refs): raise ContractError('MISSING_SOURCE_QUOTE')
    checked=[]
    for r in refs:
        if set(r)!={'source_id','quote'}:raise ContractError('QUOTE_FIELDS')
        sid,quote=r['source_id'],r['quote']
        if sid not in sources or sid in excluded or not isinstance(quote,str) or not quote.strip():
            raise ContractError('UNAVAILABLE_QUOTE_SOURCE',detail=str(sid))
        if quote not in sources[sid]:raise ContractError('QUOTE_NOT_EXACT',detail=sid)
        a=sources[sid].index(quote)
        checked.append({'source_id':sid,'quote':quote,'char_span':[a,a+len(quote)],'source_sha256':digest(sources[sid])})
    return checked

def mask_view(case, review, reference=False):
    segments=case['allowed_input'] if reference else case['segments']
    by_id={s['id']:s['text'] for s in segments}
    if len(by_id)!=len(segments):raise ContractError('DUPLICATE_SOURCE_ID')
    if review['case_id']!=case['case_id']:raise ContractError('VISIBILITY_CASE_ID')
    excluded=review['excluded_input_ids']
    if not isinstance(excluded,list) or len(set(excluded))!=len(excluded) or set(excluded)-set(by_id):
        raise ContractError('VISIBILITY_SOURCE_ID')
    if not isinstance(review['visibility_reason'],str) or not review['visibility_reason'].strip():
        raise ContractError('MISSING_VISIBILITY_REVIEW')
    kept=[s for s in segments if s['id'] not in set(excluded)]
    if not kept:raise ContractError('EMPTY_MASKED_VIEW')
    # No outcomes, labels, reasons, ID strings, or learned ontology in encoded text.
    body={'case_id':case['case_id'],'group_id':case['group_id'],'segments':kept,
          'source_view_review_hash':digest(review),'original_view_sha256':digest(segments),
          'model_text_sha256':digest([s['text'] for s in kept]),'excluded_ids':excluded,
          'input_scope':case['input_scope'],'reference_only':reference,
          'split':None if reference else case['split']}
    body['sha256']=digest(body);return body

def check_groups(views):
    groups={};ids=set();texts={}
    for v in views:
        if v['case_id'] in ids:raise ContractError('DUPLICATE_CASE')
        ids.add(v['case_id']);role='REFERENCE_ONLY' if v['reference_only'] else v['split']
        if not v['reference_only'] and role not in SPLITS:raise ContractError('SPLIT_NOT_AUTHORIZED')
        if v['group_id'] in groups and groups[v['group_id']]!=role:raise ContractError('GROUP_LEAKAGE')
        groups[v['group_id']]=role
        if v['model_text_sha256'] in texts:raise ContractError('DUPLICATE_SOURCE_TEXT')
        texts[v['model_text_sha256']]=v['case_id']

def prepare_labels(query, references, review):
    if review['case_id']!=query['case_id']:raise ContractError('LABEL_QUERY_ID')
    candidates={r['case_id']:r for r in references};by_query={s['id']:s['text'] for s in query['segments']}
    rows=review['labels']
    if Counter(r['candidate_case_id'] for r in rows)!=Counter({c:1 for c in candidates}):
        raise ContractError('LABEL_CANDIDATE_COVERAGE')
    valid=[];rejected=[]
    for r in rows:
        cid=r['candidate_case_id'];c=candidates[cid]
        try:
            if set(r)!={'candidate_case_id','utility','query_refs','candidate_refs','reason'}:raise ContractError('LABEL_FIELDS')
            if r['utility'] not in UTILITIES:raise ContractError('LABEL_UTILITY')
            if query['group_id']==c['group_id']:raise ContractError('SELF_GROUP_LABEL')
            if not isinstance(r['reason'],str) or not r['reason'].strip():raise ContractError('MISSING_LABEL_REASON')
            known=r['utility'] in ('POSITIVE','NEGATIVE')
            qrefs=check_quotes(r['query_refs'],by_query,required=known)
            crefs=check_quotes(r['candidate_refs'],{s['id']:s['text'] for s in c['segments']},required=known)
            body={**r,'query_case_id':query['case_id'],'query_group_id':query['group_id'],
                  'candidate_group_id':c['group_id'],'split':query['split'],
                  'query_view_sha256':query['sha256'],'candidate_view_sha256':c['sha256'],
                  'checked_query_quotes':qrefs,'checked_candidate_quotes':crefs,
                  'review':'GPT6_HIGH_SOURCE_REVIEWED_NOT_HUMAN_GOLD','original_row_sha256':digest(r)}
            valid.append({**body,'sha256':digest(body)})
        except ContractError as e:
            rejected.append({'query_case_id':query['case_id'],'candidate_case_id':cid,
                'reason':str(e),'original_row_sha256':digest(r),'utility':None})
    return valid,rejected

def supervision(labels, allowed_split):
    if allowed_split not in SPLITS:raise ContractError('TRAIN_SPLIT')
    if any(x['split']!=allowed_split for x in labels):raise ContractError('CROSS_SPLIT_LABEL_ACCESS')
    return {x['candidate_case_id']:1 if x['utility']=='POSITIVE' else 0
            for x in labels if x['utility'] in ('POSITIVE','NEGATIVE')}

def assemble(out):
    out=Path(out);src=read_json(out/('private/source-cases-expanded.json' if (out/'private/source-cases-expanded.json').exists() else 'private/source-cases.json'))
    refreviews={};qreviews={}
    for p in sorted((out/'private/reviews').glob('REFERENCES-[0-9].json')):
        exported=read_json(p);audit_export(p,exported)
        for r in exported['references']:
            if r['case_id'] in refreviews:raise ContractError('DUPLICATE_REFERENCE_REVIEW')
            refreviews[r['case_id']]=r
    for p in sorted((out/'private/reviews').glob('LABELS-[0-9].json')):
        exported=read_json(p);audit_export(p,exported)
        for r in exported['queries']:
            if r['case_id'] in qreviews:raise ContractError('DUPLICATE_QUERY_REVIEW')
            qreviews[r['case_id']]=r
    if set(refreviews)!={r['case_id'] for r in src['references']} or set(qreviews)!={q['case_id'] for q in src['queries']}:
        raise ContractError('INCOMPLETE_REVIEW_COVERAGE')
    refs=[mask_view(r,refreviews[r['case_id']],True) for r in src['references']]
    queries=[mask_view(q,qreviews[q['case_id']]) for q in src['queries']];check_groups(refs+queries)
    outcomes=[];outcome_rejected=[]
    for r in src['references']:
        review=refreviews[r['case_id']]
        try:
            if review['route_outcome'] not in ('SUPPORT_GROUND','OPPOSE_GROUND','UNDETERMINED'):raise ContractError('OUTCOME_ENUM')
            quotes=check_quotes(review['outcome_refs'],{s['id']:s['text'] for s in r['full_judgment']},required=review['route_outcome']!='UNDETERMINED')
            outcomes.append({'case_id':r['case_id'],'outcome':review['route_outcome'],'quotes':quotes,
                'reason':review['outcome_reason'],'review_hash':digest(review),'encoded_as_feature':False})
        except ContractError as e:outcome_rejected.append({'case_id':r['case_id'],'reason':str(e)})
    labels=[];rejected=[]
    for q in queries:
        rows,errors=prepare_labels(q,refs,qreviews[q['case_id']]);labels.extend(rows);rejected.extend(errors)
    counts={s:dict(Counter(x['utility'] for x in labels if x['split']==s)) for s in sorted(SPLITS)}
    trainable=[]
    for q in queries:
        y=supervision([x for x in labels if x['query_case_id']==q['case_id']],q['split'])
        if q['split']=='TRAIN' and 0 in y.values() and 1 in y.values():trainable.append(q['case_id'])
    if len(trainable)<3:raise ContractError('INSUFFICIENT_SOURCE_REVIEWED_TRAINING_QUERIES',detail=str(trainable))
    b={'references':refs,'queries':queries,'labels':labels,'outcomes':outcomes,
       'rejected_labels':rejected,'rejected_outcomes':outcome_rejected,
       'reference_type':'GPT6_SOURCE_REVIEWED_NOT_HUMAN_GOLD','task':'SOURCE_BOUND_CASE_ROUTE_RETRIEVAL',
       'trainable_queries':trainable,'label_counts_by_split':counts,'old_labels_reused':False}
    b['sha256']=digest(b);write_immutable(out/'private/dataset.json',b)
    composition=[]
    for q in queries:
        y=supervision([x for x in labels if x['query_case_id']==q['case_id']],q['split'])
        composition.append({'case_id':q['case_id'],'split':q['split'],'positives':sum(y.values()),
            'negatives':sum(v==0 for v in y.values()),'unknown_or_rejected':len(refs)-len(y),
            'pair_count':sum(y.values())*sum(v==0 for v in y.values()),
            'contributes_pairwise_loss':q['split']=='TRAIN' and 0 in y.values() and 1 in y.values()})
    summary={'dataset_sha256':b['sha256'],'references':len(refs),'queries':len(queries),
        'labels':len(labels),'rejected_labels':len(rejected),'counts':counts,'trainable_queries':len(trainable),
        'masked_source_segments':sum(len(v['excluded_ids']) for v in refs+queries),
        'historical_outcomes':dict(Counter(x['outcome'] for x in outcomes)),
        'rejected_outcomes':outcome_rejected,'unknown_used_as_negative':False,'independent_human_validation':False,
        'query_composition':composition,'supervised_pairs':sum(x['pair_count'] for x in composition if x['split']=='TRAIN'),
        'pairs_are_not_independent_cases':True,'target_related_group_identity_beyond_known_duplicates_unconfirmed':True}
    write_immutable(out/'data-readiness.json',summary);return b,summary
