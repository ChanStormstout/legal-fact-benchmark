"""Apply address-valid exact-span patches; no claim of semantic approval."""
import re,hashlib

def locate_findings(findings,draft,sources):
    out=[]
    for row in findings.get('findings',[]):
        if not isinstance(row,dict):out.append({'code':'NON_OBJECT_FINDING'});continue
        target=row.get('target','');hits=draft.count(target) if isinstance(target,str) and target else 0
        if hits!=1:out.append({'id':row.get('id'),'code':'TARGET_NOT_UNIQUE_OR_MISSING','occurrences':hits})
        for e in row.get('evidence',[]):
            if not isinstance(e,dict):out.append({'id':row.get('id'),'code':'BAD_EVIDENCE'});continue
            sid=e.get('source_id');quote=e.get('quote')
            if sid not in sources:out.append({'id':row.get('id'),'code':'UNKNOWN_SOURCE','source_id':sid})
            elif not isinstance(quote,str) or not quote or quote not in sources[sid]['text']:out.append({'id':row.get('id'),'code':'QUOTE_NOT_EXACT','source_id':sid})
    return out

def resolve_plan(plan,sources):
    resolved=[];errors=[]
    for row in plan.get('items',[]):
        if not isinstance(row,dict):errors.append({'code':'INVALID_PLAN_ITEM'});continue
        refs=[]
        for sid in row.get('source_ids',[]):
            if sid not in sources:errors.append({'item':row.get('id'),'code':'UNKNOWN_SOURCE','source_id':sid});continue
            refs.append({'source_id':sid,'locator':sources[sid].get('locator'),'text':sources[sid]['text']})
        resolved.append({'item':row,'resolved_originals':refs})
    return {'items':resolved,'open_items':plan.get('open_items',[]),'address_errors':errors,'semantic_acceptance':None}

def apply_local(draft,proposal,sources):
    operations=[];audit=[]
    for i,row in enumerate(proposal.get('edits',[])):
        aid=row.get('id',str(i)) if isinstance(row,dict) else str(i)
        if not isinstance(row,dict):audit.append({'id':aid,'status':'INVALID_EDIT_OBJECT'});continue
        old=row.get('old');new=row.get('new');op=row.get('op')
        if not isinstance(old,str) or not old or not isinstance(new,str) or not new.strip() or op not in ('REPLACE','INSERT_AFTER'):
            audit.append({'id':aid,'status':'INVALID_EDIT_FIELDS','draft_preserved':True});continue
        if draft.count(old)!=1:
            audit.append({'id':aid,'status':'TARGET_NOT_UNIQUE_OR_MISSING','occurrences':draft.count(old),'draft_preserved':True});continue
        if op=='REPLACE' and old==new:audit.append({'id':aid,'status':'NO_TEXT_CHANGE','draft_preserved':True});continue
        if old.strip()==draft.strip():audit.append({'id':aid,'status':'WHOLE_DRAFT_REPLACEMENT_REJECTED','draft_preserved':True});continue
        ids=row.get('source_ids',[])
        # Source existence is an address condition; it does not certify support.
        inline=re.findall(r'(?<![A-Za-z0-9])[SL][0-9a-f]{12}(?![A-Za-z0-9])',new)
        bad=[sid for sid in list(ids)+inline if sid not in sources]
        if bad:audit.append({'id':aid,'status':'UNKNOWN_SOURCE_IN_PATCH','source_ids':bad,'draft_preserved':True});continue
        start=draft.index(old);end=start+len(old)
        operations.append({'id':aid,'start':start,'end':end,'replacement':new if op=='REPLACE' else old+new,'op':op,'finding_ids':row.get('finding_ids',[]),'model_reason':row.get('reason')})
    conflicts=set()
    for i,left in enumerate(operations):
        for j,right in enumerate(operations[:i]):
            if left['start']<right['end'] and right['start']<left['end']:conflicts.update([i,j])
    valid=[]
    for i,row in enumerate(operations):
        if i in conflicts:audit.append({'id':row['id'],'status':'OVERLAPPING_EDIT_NOT_APPLIED','draft_preserved':True})
        else:valid.append(row)
    final=draft;chunks=[];cursor=0
    for row in sorted(valid,key=lambda x:x['start']):
        unchanged=draft[cursor:row['start']];chunks.append(unchanged);cursor=row['end']
        audit.append({k:v for k,v in row.items() if k!='replacement'}|{'status':'APPLIED','old_chars':row['end']-row['start'],'new_chars':len(row['replacement']),'semantic_correctness':None})
    chunks.append(draft[cursor:])
    for row in sorted(valid,key=lambda x:x['start'],reverse=True):final=final[:row['start']]+row['replacement']+final[row['end']:]
    return final,{'edits':audit,'applied':len(valid),'unchanged_original_characters':sum(map(len,chunks)),'unchanged_chunks_sha256':hashlib.sha256(''.join(chunks).encode()).hexdigest(),'unchanged_text_copied_byte_for_byte':True,'semantic_retention_score':None,'new_errors':None}
