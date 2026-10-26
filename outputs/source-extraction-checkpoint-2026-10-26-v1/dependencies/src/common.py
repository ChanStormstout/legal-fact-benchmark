"""Immutable artifacts and source contracts. No semantic defaults or labels."""
import copy
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
VERSION = 'RAPIDO_ONTOLOGY_SOURCE_V24'
SCOPE_FIELDS = {'entities':('actors','properties','participant_roles'),'time':('time',),
    'stage_court':('stage','court','procedure','jurisdiction'),'request':('request',),'record_attribution':('record_level',)}
SPEAKER_KINDS = ('PARTY','PERSON','ORGANIZATION','COURT')

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def read(path):
    return json.loads(Path(path).read_text())

def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if path.exists():
        if path.read_text() != text:
            raise ValueError('IMMUTABLE_ARTIFACT_COLLISION:' + str(path))
        return
    with path.open('x') as f:
        f.write(text)

def mint(rows, prefix):
    """Exact-content duplicates only. Never merge semantically different statements."""
    result = {}
    for row in rows:
        ident = prefix + digest(row)[:16]
        if ident in result and result[ident] != row:
            raise ValueError('CONTENT_ADDRESS_COLLISION')
        result[ident] = copy.deepcopy(row)
    return result


def mint_objects(rows, cap):
    """Address model-declared property members; never infer a partition or fact."""
    objects={}
    for raw in rows:
        from object_contract import validate_object_shape
        validate_object_shape(raw)
        row=copy.deepcopy(raw);components=row.pop('components',[])
        if components and (row['kind']!='PROPERTY' or row.get('extent')!='HETEROGENEOUS_COLLECTION'):
            raise ValueError('PROPERTY_COMPONENTS_REQUIRE_DECLARED_COLLECTION')
        ident=next(iter(mint([raw],'O')));objects[ident]=row
        children=mint([{**c,'kind':'PROPERTY','parent_object':ident} for c in components],'O')
        objects.update(children)
        if components:objects[ident]['member_ids']=list(children)
    if len(objects)>cap:raise ValueError('EXPANDED_OBJECT_CAP_EXCEEDED_NO_TRUNCATION')
    return objects


def complete_rule_questions(rows,snapshot,cap,selected_pairs=None):
    """Instantiate frozen rule QUESTIONS, not answers, for model-selected rules.

    The exact predicate text is public shared law. No CASE assessment, state,
    binding verdict or applicability is supplied by this function.
    """
    result=copy.deepcopy(rows);created=[];rules={r['id']:r for r in snapshot['rule_library']['rules']}
    for task in rows:
        if task['kind']!='DERIVED' or task['rule_id']=='NONE':continue
        if selected_pairs is not None and (task['rule_id'],task['scope_id']) not in selected_pairs:continue
        rule=rules[task['rule_id']]
        for pred,question in rule['predicates'].items():
            key=rule['id']+':'+pred
            if any(t.get('rule_condition')==key and t['scope_id']==task['scope_id'] and t['kind'] not in ('ATTRIBUTION','DERIVED') for t in result):continue
            refs=[i for i,src in snapshot['directory'].items() if src['domain']=='LAW' and src['original_id'] in rule['refs']]
            item={'proposition':'Assess from the permitted record: '+question,'scope_id':task['scope_id'],
                'kind':'LEGAL','rule_id':'NONE','role':'PROOF','rule_condition':key,'source_owner':'NONE',
                'effect':'DESCRIPTIVE','section':'GROUND','importance':'CONTEXT','burden_holder':'UNRESOLVED',
                'standard':question,'authority_refs':refs,'question_basis_refs':list(task['question_basis_refs']),
                'why_required':'Unassessed predicate required by model-selected frozen rule '+rule['id'],
                'question_origin':'FROZEN_RULE_CONDITION_NOT_CASE_ANSWER'}
            result.append(item);created.append(item)
    if len(result)>cap:raise ValueError('RULE_QUESTION_CAP_EXCEEDED_NO_SILENT_OMISSION')
    return result,created

def prepare_sources(packet, library, namespace='ACTUAL', parent=None):
    if namespace not in ('ACTUAL', 'HYPOTHETICAL'):
        raise ValueError('INVALID_NAMESPACE')
    if not packet.get('case_id') or not packet.get('question') or not packet.get('sources'):
        raise ValueError('EMPTY_SOURCE_PACKET')
    directory, original = {}, set()
    entries = [('HISTORY' if s.get('document_role') in ('ANALOG','HISTORICAL') else 'LAW' if s.get('document_role')=='LAW' else 'CASE', s['source_id'], s) for s in packet['sources']]
    entries += [('LAW', s['id'], s) for s in library['authority_clips']]
    for domain, old, s in entries:
        if old in original or not s.get('text', '').strip():
            raise ValueError('DUPLICATE_OR_EMPTY_SOURCE:' + old)
        if s.get('visibility', 'ALLOWED') != 'ALLOWED' or s.get('role') == 'HIDDEN_TARGET':
            raise ValueError('INVISIBLE_SOURCE_IN_PACKET:' + old)
        original.add(old)
        ident = ({'CASE':'S','LAW':'L','HISTORY':'H'}[domain]) + digest({'domain': domain, 'id': old})[:12]
        directory[ident] = {'id': ident, 'original_id': old, 'domain': domain,
            'text': s['text'], 'text_hash': digest(s['text']),
            'document_hash': s.get('source_file_sha256', digest(packet['sources']) if domain == 'CASE' else s.get('text_sha256', digest(s['text']))),
            'locator': s.get('locator', old), 'offset_basis': 'SUPPLIED_SPAN_UNICODE_CHARACTERS',
            'span': [0, len(s['text'])], 'file_offset_available': 'span' in s,
            'original_span': s.get('span'), 'visibility': 'ALLOWED',
            'origin_group': s.get('origin_group', packet['case_id'] if domain == 'CASE' else s.get('url', old)),
            'attribution': s.get('attribution', 'UNASSESSED'),
            'metadata': {k: v for k, v in s.items() if k != 'text'}}
    # Lossless chunks retain parent and surrounding document context. No OCR correction.
    expanded={}
    for ident,src in directory.items():
        src['document_id']=src['metadata'].get('document_id', re.sub(r':L[0-9].*$', '', src['original_id']))
        text=src['text']; offsets=[0]
        if src['domain']=='HISTORY':
            # Preserve EVERY raw character. Use complete renderer paragraphs or
            # sentence boundaries, never cut at a token budget or remove negation.
            boundaries=[m.end() for m in re.finditer(r'\n|(?<=[.!?])\s+(?=[A-Z“"(])',text)]+[len(text)]
            while len(text)-offsets[-1]>1800:
                eligible=[b for b in boundaries if offsets[-1]+600<=b<=offsets[-1]+1800]
                end=max(eligible) if eligible else next((b for b in boundaries if b>offsets[-1]+1800),len(text))
                offsets.append(end)
            if offsets[-1]!=len(text):offsets.append(len(text))
        else:
            while len(text)-offsets[-1]>12000:
                end=text.rfind('\n',offsets[-1]+6000,offsets[-1]+12000)
                offsets.append(end+1 if end>=0 else offsets[-1]+12000)
            offsets.append(len(text))
        for pos,(start,end) in enumerate(zip(offsets,offsets[1:])):
            key=ident if len(offsets)==2 else ident+'c'+str(pos)
            expanded[key]={**src,'id':key,'parent_id':ident,'parent_text_hash':src['text_hash'],
                'text':text[start:end],'text_hash':digest(text[start:end]),'span':[start,end]}
    directory=expanded
    snapshot = {'version': VERSION, 'case_id': str(packet['case_id']), 'question': packet['question'],
        'scope': packet.get('scope', ''), 'namespace': namespace, 'parent': parent,
        'directory': directory, 'rules_hash': digest(library), 'source_view_hash': digest(packet),
        'rule_library': library, 'original_sources':copy.deepcopy(packet['sources']), 'corpus_manifest_hash':packet.get('corpus_manifest_hash'), 'legal_approval': False}
    snapshot['snapshot_id'] = digest(snapshot)
    return snapshot

def source_refs(snapshot, domain=None):
    return [k for k, v in snapshot['directory'].items() if domain is None or v['domain'] == domain]

def refs_valid(refs, snapshot, domain=None):
    return bool(refs) and len(set(refs)) == len(refs) and all(r in snapshot['directory'] and (domain is None or snapshot['directory'][r]['domain'] == domain) for r in refs)

def execution_authorities(refs,snapshot):
    """Admissibility, never a legal correctness judgment. Reading-only law stays out of execution."""
    return refs_valid(refs,snapshot,'LAW') and all(
        snapshot['directory'][r].get('metadata',{}).get('execution_scope') not in
        ('READING_ONLY','EXCLUDED','HISTORICAL_VERSION_UNVERIFIED') for r in refs)

def review_ok(record, snapshot, required_domain=None):
    return bool(record) and record.get('decision') == 'ACCEPT' and bool(record.get('reason', '').strip()) and refs_valid(record.get('refs', []), snapshot) and (required_domain is None or any(snapshot['directory'][r]['domain'] == required_domain for r in record['refs']))

def source_payload(snapshot, domain=None):
    result={}
    for k,v in snapshot['directory'].items():
        if domain is not None and v['domain']!=domain:continue
        row={name:v[name] for name in ('text','original_id','domain','locator','origin_group','span')}
        row.update(parent_id=v.get('parent_id',k),document_id=v.get('document_id'))
        if v['domain']=='LAW':
            # These qualifications used to be saved in metadata but absent from
            # model inputs because frozen_law omits the duplicated authority_clips.
            row['authority_provenance']={name:v['metadata'][name] for name in (
                'url','source_grade','version_status','temporal_status','effective_from','effective_to',
                'execution_scope','metadata_warning','source_file_sha256','text_sha256','legal_approval') if name in v['metadata']}
        result[k]=row
    return result

def render_text(report):
    parts=[]
    for i,x in report['items'].items():
        links=x.get('also_covered_by',[])
        if not x['include'] and not links:continue
        body=x['text'] if x['include'] else ''
        if links:body+=('\n' if body else '')+'Shared material for this question: '+', '.join('['+j+']' for j in links)+'.'
        parts.append(f"{x['section']} [{i}]\n{body}\nSources: {', '.join(x['refs'])}")
    parts += [f"HISTORICAL COMPARISON [{i}] for report item {x.get('report_item_id','UNRESOLVED')}\n{x['text']}\nSources: {', '.join(x['refs'])}" for i,x in report.get('comparisons',{}).items() if x['include']]
    return '\n\n'.join(parts)


@lru_cache(maxsize=4096)
def source_spans(ref, text):
    """Lossless source addresses, not semantic evidence annotations."""
    boundaries = sorted(set([m.end() for m in re.finditer(r'\n|(?<=[.!?])\s+(?=[A-Z“"(])', text)] + [len(text)]))
    start = 0; result = []
    while start < len(text):
        candidates = [b for b in boundaries if start < b <= start + 1000]
        end = max(candidates) if candidates else next(b for b in boundaries if b > start)
        quote = text[start:end]
        sid = 'W' + digest({'ref': ref, 'start': start, 'end': end, 'text': quote})[:12]
        result.append((sid, start, end, quote)); start = end
    if ''.join(row[3] for row in result) != text: raise ValueError('LOSSLESS_WITNESS_INDEX_FAILED')
    return tuple(result)


def witness_registry(snapshot, domain=None):
    return {sid: {'ref': ref, 'quote': quote, 'start': start, 'end': end}
        for ref, source in snapshot['directory'].items() if domain is None or source['domain'] == domain
        for sid, start, end, quote in source_spans(ref, source['text'])}


def witness_payload(sources):
    # Each original character appears exactly once, with machine-generated addresses.
    return {ref: {**{k:v for k,v in source.items() if k!='text'},
        'passages': [{'span_id': sid, 'start': start, 'end': end, 'text': quote}
                     for sid,start,end,quote in source_spans(ref,source['text'])]}
        for ref,source in sources.items()}


def resolve_witnesses(witnesses, snapshot):
    registry = witness_registry(snapshot)
    return [registry.get(w.get('span_id')) for w in witnesses]


def witness_quotes_valid(witnesses,snapshot,domain=None,refs=None):
    """Fixed-source traceability only; the model must still judge semantic support."""
    if not witnesses:return False
    for w in resolve_witnesses(witnesses,snapshot):
        if not w:return False
        source=snapshot['directory'].get(w['ref'])
        if not source or (domain and source['domain']!=domain):return False
        if refs is not None and w['ref'] not in refs:return False
        if not w['quote'].strip() or source['text'][w['start']:w['end']]!=w['quote']:return False
    return True


def unsupported_time_years(time_value, witnesses, snapshot):
    """Necessary lexical support, never confirmation that a date belongs to an event."""
    years=set(re.findall(r'(?<![0-9])(?:1[0-9]{3}|20[0-9]{2})(?![0-9])',time_value))
    quotes=' '.join(w['quote'] for w in resolve_witnesses(witnesses,snapshot) if w)
    supported=set(re.findall(r'(?<![0-9])(?:1[0-9]{3}|20[0-9]{2})(?![0-9])',quotes))
    return sorted(years-supported)


def substantive_report_text(text):
    """Reject blank/placeholder/letter output; passing is not semantic correctness."""
    value=text.strip()
    if value in ('OMITTED','UNKNOWN','UNRESOLVED'):return False
    letters=re.findall(r'[A-Za-z]',value);words=re.findall(r"[A-Za-z]+(?:['-][A-Za-z]+)*",value)
    return (len(letters)>=16 and len(words)>=3) or len(re.findall(r'[\u3400-\u9fff]',value))>=10


def derive_allowed_coverage(review,snapshot):
    value=copy.deepcopy(review);coverage=value['whole_source_coverage']
    coverage['complete']=not bool(actionable_omissions(coverage,snapshot)) and coverage.get('inventory_check',{}).get('complete',False)
    coverage['aggregation']='PROGRAM_FROM_MODEL_CLASSIFICATIONS_UNDER_ALLOWED_VIEW'
    return value


def actionable_omissions(coverage, snapshot):
    """Route model classifications; not an independent semantic correctness claim."""
    return [o for o in coverage.get('omissions',[]) if o.get('importance')=='IMPORTANT'
        and o.get('classification') in ('ALLOWED_SOURCE_OMISSION','CORRECTABLE_ERROR')
        and o.get('information_target')=='ALLOWED_RECORD'
        and refs_valid(o.get('refs',[]),snapshot)]

def coverage_consistent(coverage, snapshot):
    # Invalid classifications/references are check failures, never repair permissions.
    actionable=actionable_omissions(coverage,snapshot)
    malformed=any(o.get('classification') in ('ALLOWED_SOURCE_OMISSION','CORRECTABLE_ERROR')
        and (o.get('information_target')!='ALLOWED_RECORD' or not refs_valid(o.get('refs',[]),snapshot))
        for o in coverage.get('omissions',[]))
    return not malformed and coverage.get('complete') == (not bool(actionable) and coverage.get('inventory_check',{}).get('complete',False))


def task_review_ok(record,snapshot,task,execution=True):
    if not review_ok(record.get('question',{}),snapshot,'CASE'):return False
    assumptions=record.get('assumptions',{})
    if not review_ok(assumptions,snapshot,'CASE') or not witness_quotes_valid(assumptions.get('witnesses',[]),snapshot,'CASE',assumptions.get('refs',[])):return False
    needs_law=task['kind'] in ('LEGAL','PROCEDURE','DERIVED') or task['effect']!='DESCRIPTIVE' or task['rule_id']!='NONE' or bool(task['authority_refs'])
    if not execution or not needs_law:return True
    legal=record.get('law',{})
    return review_ok(legal,snapshot,'LAW') and execution_authorities(task['authority_refs'],snapshot) and set(task['authority_refs'])<=set(legal.get('refs',[]))


def time_registry(snapshot):
    """Literal calendar mentions, not inferred event dates or semantic bindings."""
    months=r'(?:January|February|March|April|May|June|July|August|September|October|November|December)'
    full=r'\b(?:\d{4}-\d{2}-\d{2}|'+months+r'\s+\d{1,2}(?:st|nd|rd|th)?[,]?\s+\d{4}|\d{1,2}(?:st|nd|rd|th)?\s+'+months+r'[,]?\s+\d{4})\b'
    patterns=[('EXACT_DATE',full),('MONTH',r'\b'+months+r'[,]?\s+\d{4}\b'),('YEAR',r'\b(?:1[0-9]{3}|20[0-9]{2})\b')]
    rows={}
    for sid,w in witness_registry(snapshot,'CASE').items():
        occupied=[]
        for precision,pattern in patterns:
            for match in re.finditer(pattern,w['quote'],re.IGNORECASE):
                if any(lo<=match.start()<hi for lo,hi in occupied):continue
                occupied.append(match.span());value=match.group()
                ident='D'+digest({'span_id':sid,'offset':match.start(),'value':value})[:12]
                rows[ident]={'time':value,'time_precision':precision,'time_witnesses':[{'span_id':sid}],
                    'ref':w['ref'],'source_start':w['start']+match.start(),'source_end':w['start']+match.end(),
                    'not_event_acceptance':True}
    return rows
