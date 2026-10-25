"""Frozen, visibility-scoped BM25 RAG. Original text remains addressable.

Three collections, independent ranked queues, parent/neighbor expansion. Unknown
law scope is retained as unresolved, never silently filtered as inapplicable.
"""
import math
import re
import hashlib
from collections import Counter
from pathlib import Path
from common import digest, read, source_payload

def ranking_text(text):
    # Renderer link wrappers carry no judgment meaning; keep their visible label.
    text=re.sub(r'\ue200cite\ue202[^†]*†([^\ue201]*)\ue201',r'\1',text)
    lines=[]
    for line in text.splitlines():
        # Ranking only: raw passages and offsets NEVER change. Numbers alone
        # cannot improve a match. Agent signatures cannot serve as legal evidence.
        if re.fullmatch(r'\s*\d+[.)]?\s*',line):continue
        if re.fullmatch(r'\s*Agent for the (?:appellant|respondent|petitioner)s?\s*:.*',line,re.I):continue
        lines.append(line)
    return '\n'.join(lines)

def tokens(text): return re.findall(r'\w+', ranking_text(text).casefold())

def load_corpus(manifest_path, case_id):
    manifest=read(manifest_path); rows=[]
    for item in manifest['documents']:
        if case_id not in item['allowed_cases']: continue
        if item['visibility']!='ALLOWED' or item['domain'] not in ('LAW','HISTORY'):
            raise ValueError('CORPUS_VISIBILITY_OR_DOMAIN')
        if item['domain']=='HISTORY' and (not item.get('dispute_group') or item['dispute_group'] in manifest['target_dispute_groups'].get(case_id,[])):
            raise ValueError('RELATED_DISPUTE_HISTORY_LEAKAGE')
        if manifest.get('version')=='HISTORY_ORIGINAL_RENDERINGS_V1':
            if item['case_id'] in manifest['target_dispute_groups'] or item['date']>=manifest['target_decision_dates'][case_id]:
                raise ValueError('TARGET_OR_FUTURE_HISTORY')
            original=Path(__file__).resolve().parents[3]/item['original_source_file']
            if hashlib.sha256(original.read_bytes()).hexdigest()!=item['original_source_sha256']:
                raise ValueError('ORIGINAL_HISTORY_CHANGED')
        path=(Path(manifest_path).parent/item['path']).resolve()
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('CORPUS_BYTES_CHANGED')
        data=read(path)
        for src in data['sources']:
            if src.get('visibility','ALLOWED')!='ALLOWED' or src.get('role')=='HIDDEN_TARGET':raise ValueError('HIDDEN_CORPUS_SOURCE')
            rows.append({**src,'source_id':item['id']+':'+src['source_id'],'document_role':'HISTORICAL' if item['domain']=='HISTORY' else 'LAW',
                'document_id':item['id'],'source_file_sha256':item['sha256'],'dispute_group':item.get('dispute_group'),
                'retrieval_scope':item.get('retrieval_scope',{}),'corpus_manifest_hash':digest(manifest)})
    return rows,digest(manifest)

class Index:
    def __init__(self,snapshot):
        self.snapshot=snapshot; self.docs=snapshot['directory']
        self.terms={k:Counter(tokens(v['text'])) for k,v in self.docs.items()}
        self.sizes={k:sum(v.values()) for k,v in self.terms.items()}
        self.stats={}
        for domain in ('CASE','LAW','HISTORY'):
            ids=[i for i,s in self.docs.items() if s['domain']==domain]
            self.stats[domain]={'n':len(ids),'avg':sum(self.sizes[i] for i in ids)/max(1,len(ids)),
                'df':Counter(t for i in ids for t in self.terms[i])}
    def law_scope(self,src,scope):
        if src['domain']!='LAW':return 'NOT_LAW'
        meta=src['metadata'].get('retrieval_scope',{})
        for field in ('jurisdiction','procedure'):
            allowed=meta.get(field,[]); wanted=scope.get(field)
            if allowed and wanted and wanted not in allowed:return 'EXPLICIT_SCOPE_MISMATCH'
        # Temporal exceptions/savings require legal assessment. No nearest-date guess.
        return 'REQUIRES_TEMPORAL_VERSION_REVIEW' if meta else 'SCOPE_METADATA_UNRESOLVED'
    def search(self,query,domain,scope=None,top_k=8):
        q=set(tokens(query)); hits=[]; skipped=[];stats=self.stats[domain]
        for ident,ts in self.terms.items():
            src=self.docs[ident]
            if src['domain']!=domain:continue
            status=self.law_scope(src,scope or {})
            if status=='EXPLICIT_SCOPE_MISMATCH':skipped.append(ident);continue
            score=sum(math.log(1+(stats['n']-stats['df'][t]+.5)/(stats['df'][t]+.5))*ts[t]*2.2/(ts[t]+1.2*(.25+.75*self.sizes[ident]/max(stats['avg'],1))) for t in q if ts[t])
            if score>0:hits.append({'id':ident,'score':score,'scope_status':status})
        hits.sort(key=lambda x:(-x['score'],x['id']))
        return {'hits':hits[:top_k],'not_returned':len(hits[top_k:]),'explicit_scope_exclusions':skipped}
    def expand(self,ids):
        selected=set(ids)
        # Parent IDs include long paragraphs split at transport-safe boundaries;
        # neighbors preserve negation/quotation context within the same document.
        ordered=list(self.docs)
        for ident in list(selected):
            src=self.docs[ident];parent=src.get('parent_id',ident);doc=src.get('document_id',src['original_id'])
            if src['domain']!='HISTORY':selected.update(i for i,s in self.docs.items() if s.get('parent_id',i)==parent)
            pos=ordered.index(ident)
            for j in (pos-1,pos+1):
                if 0<=j<len(ordered):
                    other=self.docs[ordered[j]]
                    if other.get('document_id',other['original_id'])==doc:selected.add(ordered[j])
        return [i for i in ordered if i in selected]

    def document_context(self,ident,cap):
        src=self.docs[ident];doc=src['document_id'];parent=src.get('parent_id',ident)
        document=[i for i,r in self.docs.items() if r['document_id']==doc and r['domain']==src['domain']]
        parent_ids=[i for i in document if self.docs[i].get('parent_id',i)==parent]
        if sum(len(self.docs[i]['text']) for i in document)<=cap:ids=document
        elif sum(len(self.docs[i]['text']) for i in parent_ids)<=cap:ids=parent_ids
        else:ids=self.expand([ident])
        if sum(len(self.docs[i]['text']) for i in ids)>cap:return None
        return {'selected_ids':ids,'document_id':doc,'whole_registered_document_selected':set(ids)==set(document),
            'whole_parent_selected':set(parent_ids)<=set(ids),'stored_document_integrity':
            src.get('metadata',{}).get('text_integrity','UNVERIFIED_ORIGINAL_COMPLETENESS'),
            'reading_adequacy':'REQUIRES_MODEL_ASSESSMENT','selected_span_hash':digest({i:self.docs[i]['text_hash'] for i in ids}),
            'not_selected_ids':[i for i in document if i not in ids]}

    def more_context(self,ids,cap):
        doc=self.docs[ids[0]]['document_id'];selected=set(ids)
        ordered=[i for i,r in self.docs.items() if r['domain']=='HISTORY' and r['document_id']==doc]
        # Add a complete neighboring unit on both sides if it fits; never slice.
        lo=min(ordered.index(i) for i in ids);hi=max(ordered.index(i) for i in ids)
        for i in ([ordered[lo-1]] if lo else [])+([ordered[hi+1]] if hi+1<len(ordered) else []):
            if sum(len(self.docs[r]['text']) for r in selected|{i})<=cap:selected.add(i)
        return [i for i in ordered if i in selected]


def retrieve(snapshot,tasks,top_k=8,queries=None,scopes=None,history_limit=20000,needs=None,cfg=None):
    cfg=cfg or {};idx=Index(snapshot);ledger={};ids=set();needs=needs or {}
    for tid,t in tasks.items():
        angles=(queries or {}).get(tid) or {a:t['proposition']+' '+t['standard'] for a in ('SUPPORT','OPPOSITION','EXCEPTION')}
        ledger[tid]={}
        for angle,q in angles.items():
            ledger[tid][angle]={}
            for domain in ('CASE','LAW'):
                result=idx.search(q,domain,(scopes or {}).get(t['scope_id'],{}),top_k)
                result['expanded_ids']=idx.expand([x['id'] for x in result['hits']]);ids.update(result['expanded_ids'])
                ledger[tid][angle][domain]=result
    queues=[];need_ledger={};enabled=cfg.get('history_enabled',True)
    for nid,need in sorted(needs.items(),key=lambda kv:(kv[1]['priority'],kv[0])):
        routes={'ORIGINAL_QUESTION':need['open_question'],**need['queries']};ranked={};hits={};traces={}
        query_scope={} if need.get('origin')=='ORIGINAL_USER_QUESTION_SEARCH_NOT_SEMANTIC_NEED' else (scopes or {}).get(need['scope_id'],{})
        for angle,q in routes.items():
            result=idx.search(q,'HISTORY',query_scope,top_k) if enabled else {'hits':[],'not_returned':0,'explicit_scope_exclusions':[]}
            traces[angle]={'query':q,**result}
            for rank,row in enumerate(result['hits'],1):
                doc=idx.docs[row['id']]['document_id'];ranked[doc]=ranked.get(doc,0)+1/(60+rank)
                hits.setdefault(doc,[]).append({'angle':angle,'rank':rank,**row})
        docs=sorted(ranked,key=lambda d:(-ranked[d],d))
        queues.append([(nid,doc,sorted(hits[doc],key=lambda h:(h['rank'],h['id']))[0]['id']) for doc in docs])
        need_ledger[nid]={'queries':traces,'document_ranking':[{'document_id':doc,'rrf_score':ranked[doc],'hits':hits[doc]} for doc in docs],
            'status':'HISTORY_DISABLED' if not enabled else 'RANKED' if docs else 'NO_LEXICAL_CANDIDATE_NOT_PROOF_OF_ABSENCE'}
    # Round-robin issues, then prefer distinct documents. Fixed resource policy,
    # never influenced by labels or by whether a comparison is favorable.
    candidates=[q[n] for n in range(max((len(q) for q in queues),default=0)) for q in queues if n<len(q)]
    selected=[];pairs={};skipped=[];seen_docs=set();considered=set();cap=cfg.get('history_per_document_cap_chars',7000)
    for distinct in (True,False):
        for nid,doc,ident in candidates:
            if (nid,doc) in considered or (distinct and doc in seen_docs):continue
            considered.add((nid,doc));reason=None
            if len(pairs)>=cfg.get('history_max_pairs',3):reason='PAIR_BUDGET_NOT_ASSESSED'
            elif doc not in seen_docs and len(seen_docs)>=cfg.get('history_max_documents',3):reason='DOCUMENT_BUDGET_NOT_ASSESSED'
            context=idx.document_context(ident,cap)
            if context is None:reason=reason or 'COMPLETE_CONTEXT_UNIT_EXCEEDS_CAP'
            unit=context['selected_ids'] if context else []
            candidate=list(dict.fromkeys(selected+unit))
            if sum(len(idx.docs[i]['text']) for i in candidate)>history_limit:reason=reason or 'HISTORY_CONTEXT_BUDGET_NOT_ASSESSED'
            if reason:
                skipped.append({'need_id':nid,'document_id':doc,'id':ident,'reason':reason,'context_ids':unit});continue
            pid='HP'+digest({'need':nid,'doc':doc,'context':unit})[:12]
            pairs[pid]={'need_id':nid,'document_id':doc,'history_refs':unit,'context':context}
            selected=candidate;seen_docs.add(doc)
    for nid in need_ledger:
        need_ledger[nid]['selected_pair_ids']=[i for i,p in pairs.items() if p['need_id']==nid]
        if need_ledger[nid]['status']=='RANKED' and not need_ledger[nid]['selected_pair_ids']:need_ledger[nid]['status']='BUDGET_NOT_ASSESSED'
    nonhistory=[i for i in idx.expand(ids) if idx.docs[i]['domain']!='HISTORY']
    return {'method':'DOMAIN_SCOPED_BM25_ISSUE_DOCUMENT_RRF','tasks':ledger,'needs':needs,'need_ledger':need_ledger,
        'history_pairs':pairs,'selected_ids':nonhistory+selected,'history_selected_ids':selected,
        'history_context_budget_chars':history_limit,'history_per_document_cap_chars':cap,
        'context_policy':'FULL_PARENT_OR_EXPLICIT_PARTIAL_CONTEXT_COMPLETE_UNITS',
        'history_budget_exclusions':skipped,'history_enabled':enabled,'all_history_scanned_by_model':False,
        'collections':{d:sum(s['domain']==d for s in idx.docs.values()) for d in ('CASE','LAW','HISTORY')},
        'rank_is_not_semantic_acceptance':True,'snapshot_id':snapshot['snapshot_id'],
        'corpus_manifest_hash':snapshot.get('corpus_manifest_hash'),'queries':queries or {},
        'external_network':False,'coverage_complete':False,'source_view_hash':snapshot['source_view_hash']}

def batches(snapshot,limit,ids=None):
    batch=[];n=0
    for ident in ids if ids is not None else snapshot['directory']:
        size=len(snapshot['directory'][ident]['text'])
        if size>limit:raise ValueError('SOURCE_CHUNK_EXCEEDS_WINDOW')
        if batch and n+size>limit:yield batch;batch=[];n=0
        batch.append(ident);n+=size
    if batch:yield batch

def source_window(snapshot,selected,limit):
    ids=list(dict.fromkeys(selected))
    if sum(len(snapshot['directory'][i]['text']) for i in ids)>limit:
        raise ValueError('RETRIEVAL_WINDOW_CAP_NO_SILENT_TRUNCATION')
    payload=source_payload(snapshot)
    return {i:payload[i] for i in ids}
