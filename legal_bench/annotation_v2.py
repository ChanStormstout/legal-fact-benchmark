"""Versioned annotation workflow. Deliberately independent of the v0.1 executor."""
import argparse
import copy
import json
import re
from pathlib import Path
from datetime import datetime, timezone
from .core import digest, read, write_new, normalize

VERSION = 'pilot-0.2-dev'
TREATMENTS = {'ADOPTED', 'REJECTED', 'NOT_ESTABLISHED', 'NOT_ASSESSED', 'UNCLEAR'}
MODES = {'NARRATED', 'ALLEGED', 'TESTIFIED', 'FOUND', 'ARGUED'}
KINDS = {'FACT', 'PROCEDURAL_ACT', 'LEGAL_ARGUMENT', 'JUDICIAL_REASONING'}
RELATIONS = {'DIRECT_CONTRADICTION', 'REVERSES', 'JUDICIAL_DISAGREEMENT', 'PART_OF'}


def segment_source(source, target=700, allow_pending=False):
    if source.get('source_completeness') != 'VERIFIED_FULL' and not allow_pending:
        raise ValueError('Verified complete source required')
    if type(target) is not int or target < 1:
        raise ValueError('Positive integer segment size required')
    result = {k: copy.deepcopy(v) for k, v in source.items() if k != 'paragraphs'}
    result['parent_text_sha256'] = source['text_sha256']
    result['segmentation_version'] = 'exact-slices-700-v1'
    result['segments'] = []
    for p in source['paragraphs']:
        text, start, seq = p['text'], 0, 1
        while start < len(text):
            limit = min(start + target, len(text))
            if limit < len(text):
                # Preserve every character; prefer sentence/word boundaries, never repair OCR.
                candidates = [m.end() for m in re.finditer(r'[.!?][\"\']?\s+', text[start:limit])]
                candidates = [c for c in candidates if c >= target // 2]
                cut = start + candidates[-1] if candidates else text.rfind(' ', start, limit) + 1
                if cut <= start: cut = limit
            else: cut = len(text)
            result['segments'].append({'id': p['id'] + '.s%03d' % seq, 'page': p['page'],
                                       'parent_paragraph_id': p['id'], 'start': start, 'end': cut,
                                       'text': text[start:cut]})
            start, seq = cut, seq + 1
    result['text_sha256'] = digest(result['segments'])
    return result


def check_segmentation(source, parent):
    errors = []
    for p in parent['paragraphs']:
        segs = [s for s in source['segments'] if s['parent_paragraph_id'] == p['id']]
        cursor = 0
        for s in segs:
            if s['start'] != cursor or s['text'] != p['text'][s['start']:s['end']] or s['page'] != p['page']:
                errors.append(s['id'])
            cursor = s['end']
        if cursor != len(p['text']) or ''.join(s['text'] for s in segs) != p['text']:
            errors.append(p['id'])
    if source['parent_text_sha256'] != parent['text_sha256']: errors.append('parent hash')
    return {'valid': not errors, 'errors': errors, 'segments': len(source['segments'])}


def validate(annotation, notes, source):
    errors, warnings = [], []
    def error(code, item): errors.append({'code': code, 'item': item})
    def warning(code, item): warnings.append({'code': code, 'item': item})
    if not isinstance(annotation, dict) or not isinstance(notes, dict):
        return {'valid': False, 'errors': [{'code': 'expected_objects', 'item': None}], 'warnings': []}
    for doc, name in [(annotation, 'annotation'), (notes, 'notes')]:
        if doc.get('schema_version') != VERSION: error('wrong_schema', name)
        if doc.get('case_id') != source['case_id']: error('case_mismatch', name)
    pmap = {s['id']: s['text'] for s in source['segments']}
    def evidence(value, item, required=True):
        if not isinstance(value, list) or (required and not value):
            error('missing_or_invalid_evidence', item); return
        for ev in value:
            if not isinstance(ev, dict): error('invalid_evidence', item); continue
            seg, quote = ev.get('segment_id'), ev.get('quote')
            if not isinstance(quote, str) or not quote or seg not in pmap or normalize(quote) not in normalize(pmap.get(seg, '')):
                error('unlocated_quote', [item, seg, quote])
    collections = {}
    for name in ['objects', 'stages', 'units', 'assertions', 'relations', 'predicate_definitions']:
        seq = annotation.get(name)
        if not isinstance(seq, list) or any(not isinstance(x, dict) or not isinstance(x.get('id'), str) for x in seq):
            error('invalid_collection', name); collections[name] = []; continue
        ids = [x['id'] for x in seq]
        if len(ids) != len(set(ids)): error('duplicate_id', name)
        collections[name] = seq
    if errors: return {'valid': False, 'errors': errors, 'warnings': warnings}
    maps = {n: {x['id']: x for x in xs} for n, xs in collections.items()}
    if not isinstance(annotation.get('eligible'), bool) or not isinstance(annotation.get('eligibility_reason'), str): error('eligibility_missing', None)
    primary = [u for u in collections['units'] if u.get('primary') is True]
    if annotation.get('eligible') and len(primary) != 1: error('primary_count', len(primary))
    for o in collections['objects']:
        for k in ['label', 'kind', 'evidence']:
            if k not in o: error('missing_object_field', [o['id'], k])
        if o.get('kind') not in ['PERSON', 'PROPERTY', 'ORGANIZATION', 'AGREEMENT']: error('object_kind', o['id'])
        evidence(o.get('evidence'), o['id'])
    for st in collections['stages']:
        if not isinstance(st.get('label'), str) or not isinstance(st.get('current'), bool): error('stage_fields', st['id'])
        evidence(st.get('evidence'), st['id'])
    # A single judgment may jointly dispose an appeal and a contempt petition.
    # Preserve both current proceedings; eligible cases still need one primary unit.
    if not any(s.get('current', False) for s in collections['stages']): error('current_stage_count', None)
    for u in collections['units']:
        if u.get('kind') not in ['CLAIM', 'DEFENSE']: error('unit_kind', u['id'])
        if u.get('stage_id') not in maps['stages']: error('unknown_unit_stage', u['id'])
        if u.get('party') is not None and u.get('party') not in maps['objects']: error('unknown_party', u['id'])
        if not isinstance(u.get('relief'), str) or not isinstance(u.get('grounds'), list): error('unit_fields', u['id'])
        if u.get('primary') and not maps['stages'].get(u.get('stage_id'), {}).get('current'): error('primary_not_current', u['id'])
        evidence(u.get('evidence'), u['id'])
        for g in u.get('grounds', []):
            if not isinstance(g, dict): error('ground_fields', u['id']); continue
            evidence(g.get('evidence'), [u['id'], 'ground'])
    for d in collections['predicate_definitions']:
        if not re.fullmatch(r'[A-Z][A-Z0-9_]*', d['id']) or re.search(r'(^|_)(NO|NOT|ABSENT|WITHOUT|FAIL|FAILED|REJECT)(_|$)', d['id']):
            error('negative_or_invalid_predicate_name', d['id'])
        if not isinstance(d.get('meaning'), str) or not isinstance(d.get('roles'), dict): error('predicate_definition_fields', d['id'])
    for a in collections['assertions']:
        aid = a['id']
        for k in ['kind','predicate','polarity','roles','attributes','scope','time','origin','deciding_court_treatment','relevance','evidence','unresolved']:
            if k not in a: error('missing_assertion_field', [aid,k])
        if a.get('kind') not in KINDS: error('assertion_kind', aid)
        if a.get('predicate') not in maps['predicate_definitions']: error('undefined_predicate', aid)
        if a.get('polarity') not in ['POSITIVE','NEGATIVE']: error('polarity', aid)
        roles = a.get('roles')
        if not isinstance(roles, dict): error('roles_type', aid); roles = {}
        defined_roles = maps['predicate_definitions'].get(a.get('predicate'), {}).get('roles', {})
        if set(roles) - set(defined_roles): error('undefined_roles', [aid,sorted(set(roles)-set(defined_roles))])
        for role, obj in roles.items():
            if obj is not None and obj not in maps['objects']: error('dangling_object', [aid,role,obj])
        for k in ['attributes','scope']:
            if not isinstance(a.get(k), dict): error('attribute_scope_type', [aid,k])
        # Treatment describes handling of the proposition; it never changes its polarity.
        tr = a.get('deciding_court_treatment')
        if not isinstance(tr, dict) or tr.get('value') not in TREATMENTS: error('treatment_fields', aid)
        else:
            evidence(tr.get('evidence'), [aid,'treatment'], tr['value'] != 'NOT_ASSESSED')
            if tr['value'] in ['REJECTED','NOT_ESTABLISHED'] and a.get('polarity') == 'NEGATIVE':
                warning('check_failure_of_proof_not_opposite_fact', aid)
        orig = a.get('origin')
        if not isinstance(orig, dict) or orig.get('mode') not in MODES or not isinstance(orig.get('speaker_label'), str): error('origin_fields', aid)
        else:
            if orig.get('speaker_entity') is not None and orig.get('speaker_entity') not in maps['objects']: error('origin_speaker', aid)
            if orig.get('stage_id') is not None and orig.get('stage_id') not in maps['stages']: error('origin_stage', aid)
        t = a.get('time')
        if t is not None:
            try:
                if not isinstance(t, dict) or not isinstance(t.get('date'), str): raise ValueError()
                dt = datetime.strptime(t['date'],'%Y-%m-%d')
                if dt.strftime('%Y-%m-%d') != t['date']: raise ValueError()
                evidence(t.get('evidence'), [aid,'date'])
            except (ValueError,TypeError): error('invalid_exact_date', aid)
        relevance = a.get('relevance')
        if not isinstance(relevance, list): error('relevance_type', aid); relevance = []
        seen = set()
        for rel in relevance:
            if not isinstance(rel, dict): error('relevance_fields', aid); continue
            if rel.get('unit_id') not in maps['units']: error('relevance_unit', aid)
            if rel.get('unit_id') in seen: error('duplicate_relevance', aid)
            seen.add(rel.get('unit_id'))
            if rel.get('basis') not in ['EXPLICIT','DIRECT_BACKGROUND','UNCERTAIN'] or not isinstance(rel.get('explanation'),str): error('relevance_fields', aid)
            evidence(rel.get('evidence'), [aid,'relevance'])
        evidence(a.get('evidence'), aid)
        unresolved = a.get('unresolved')
        if not isinstance(unresolved,list): error('unresolved_type', aid)
        else:
            for u in unresolved:
                if not isinstance(u,dict) or not isinstance(u.get('field'),str) or not isinstance(u.get('reason'),str): error('unresolved_fields', aid)
            if unresolved: warning('unresolved_assertion', aid)
    all_ids = set(maps['objects']) | set(maps['assertions'])
    for rel in collections['relations']:
        rid = rel['id']; typ = rel.get('type'); left,right = rel.get('from_id'),rel.get('to_id')
        if typ not in RELATIONS or left not in all_ids or right not in all_ids or left == right: error('relation_fields',rid)
        evidence(rel.get('evidence'),rid)
        if typ == 'DIRECT_CONTRADICTION':
            x,y = maps['assertions'].get(left), maps['assertions'].get(right)
            if not x or not y or x['predicate'] != y['predicate'] or x['roles'] != y['roles'] or x['polarity'] == y['polarity']:
                error('conflict_not_same_proposition',rid)
            elif x['scope'] != y['scope'] or x['time'] != y['time'] or not rel.get('same_scope_basis'):
                error('conflict_scope_unestablished',rid)
            else: warning('conflict_semantics_require_review',rid)
        if typ == 'PART_OF' and (left not in maps['objects'] or right not in maps['objects']): error('part_of_objects',rid)
    coverage = notes.get('coverage')
    if not isinstance(coverage,list): error('coverage_type',None); coverage=[]
    seen = []
    for c in coverage:
        if not isinstance(c,dict): error('coverage_fields',None); continue
        seen.append(c.get('segment_id'))
        if c.get('category') not in ['METADATA','HEADNOTE','FACT','PROCEDURE','ARGUMENT','REASONING','AUTHORITY','OUTCOME','MIXED','UNRESOLVED']: error('coverage_category',c.get('segment_id'))
        if not isinstance(c.get('assertion_ids'),list) or any(i not in maps['assertions'] for i in c.get('assertion_ids',[])): error('coverage_assertions',c.get('segment_id'))
        if not isinstance(c.get('reason'),str): error('coverage_reason',c.get('segment_id'))
    if set(seen) != set(pmap) or len(seen) != len(set(seen)): error('coverage_not_exact',None)
    category_map = {c['segment_id']:c.get('category') for c in coverage if isinstance(c,dict) and 'segment_id' in c}
    for a in collections['assertions']:
        spans=a.get('evidence',[])
        if spans and all(category_map.get(ev.get('segment_id')) in ['HEADNOTE','METADATA','AUTHORITY'] for ev in spans if isinstance(ev,dict)):
            error('editorial_or_precedent_only_assertion',a['id'])
    for k in ['source_issues','unresolved','unsupported_phenomena','self_checks']:
        if k not in notes: error('missing_notes_field',k)
    return {'valid':not errors,'errors':errors,'warnings':warnings,'assertion_count':len(collections['assertions']),
            'semantic_correctness':'NOT_ESTABLISHED_BY_VALIDATOR','source_coverage':len(set(seen))}


def execution_view(annotation, unit_id, reviewed_assertion_ids):
    """Explicit opt-in bridge: relevance selects uses; origin and originals remain untouched.

    Caller must supply identifiers accepted in a saved semantic review. This function
    does not establish correctness of that review and never promotes model output itself.
    """
    unit = next((u for u in annotation['units'] if u['id'] == unit_id), None)
    if unit is None: raise ValueError('Unknown analysis unit')
    approved = set(reviewed_assertion_ids)
    events, excluded = [], []
    for a in annotation['assertions']:
        links = [r for r in a['relevance'] if r['unit_id'] == unit_id and r['basis'] in ['EXPLICIT','DIRECT_BACKGROUND']]
        if not links: continue
        if a['id'] not in approved:
            excluded.append({'id':a['id'],'reason':'SEMANTIC_REVIEW_REQUIRED'}); continue
        if a['kind'] not in ['FACT','PROCEDURAL_ACT'] or a['deciding_court_treatment']['value'] != 'ADOPTED':
            excluded.append({'id':a['id'],'reason':'NOT_ADOPTED_FACT_OR_ACT'}); continue
        # Scope stays visible and blocks automatic execution until a query language
        # explicitly supports it. Do not silently project a qualified proposition.
        unresolved = copy.deepcopy(a['unresolved'])
        if a['scope']: unresolved.append({'field':'scope','reason':'Scope-aware query support required'})
        events.append({'id':a['id'],'unit_id':unit_id,'type':a['predicate'],
                       'roles':copy.deepcopy(a['roles']),'status':'COURT_FOUND','polarity':a['polarity'],
                       'speaker':a['origin']['speaker_label'],
                       'time':a['time']['date'] if a['time'] else None,
                       'attributes':copy.deepcopy(a['attributes']),'scope':copy.deepcopy(a['scope']),
                       'evidence':copy.deepcopy(a['evidence']),'unresolved':unresolved,
                       'origin':copy.deepcopy(a['origin']),'relevance':copy.deepcopy(links)})
    return {'case_id':annotation['case_id'],'entities':copy.deepcopy(annotation['objects']),
            'units':[dict(copy.deepcopy(unit),primary=True)],'events':events,'excluded':excluded,
            'note':'Only explicitly reviewed, currently adopted assertions. Qualified scope is retained and blocks execution.'}


def prepare(parent, protocol_dir, out, pass_name):
    source = segment_source(parent)
    if not check_segmentation(source,parent)['valid']: raise ValueError('Broken segmentation')
    pdir=Path(protocol_dir); out=Path(out)
    context=(pdir/'instructions.txt').read_text()+'\n\nSCHEMA AND SYNTHETIC EXAMPLE:\n'+(pdir/'schema-example.json').read_text()
    context+='\n\nCase ID: '+source['case_id']+'\nComplete supplied source text; use it as evidence only.\nSource: '+source['url']+'\n'
    context+='\n'.join('[%s; page=%s; parent=%s; offsets=%s:%s]\n%s\n' % (s['id'],s['page'],s['parent_paragraph_id'],s['start'],s['end'],s['text']) for s in source['segments'])
    key=digest({'version':VERSION,'prompt':context,'pass':pass_name})[:24]
    task={'id':key,'case_id':source['case_id'],'pass':pass_name,'protocol_version':VERSION,
          'prompt_sha256':digest(context.encode()),'source_hash':source['text_sha256'],
          'parent_source_hash':parent['text_sha256'],'prompt':context,'state':'PREPARED',
          'required_model':'GPT-6 non-Pro High','outputs':['annotation.json','review_notes.json']}
    write_new(out/(key+'.json'),task)
    p=out/(key+'.txt');p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists() and p.read_text()!=context: raise ValueError('Refusing changed prompt')
    if not p.exists():p.write_text(context)
    write_new(out.parent/'sources'/ (source['case_id']+'.segmented.json'),source)
    return {k:v for k,v in task.items() if k!='prompt'}


def import_files(task, source, annotation_path, notes_path, metadata, out):
    for k in ['conversation_url','model_display','effort_display','submitted_at','retrieved_at','prompt_sha256']:
        if not metadata.get(k):raise ValueError('Missing observed metadata: '+k)
    if 'pro' in metadata['effort_display'].lower():raise ValueError('Non-Pro required')
    if task['prompt_sha256']!=metadata['prompt_sha256'] or task['source_hash']!=source['text_sha256']:raise ValueError('Input hash mismatch')
    if source['case_id'] != task['case_id']:
        raise ValueError('Source case mismatch')
    if digest(source['segments']) != task['source_hash']:
        raise ValueError('Source content hash mismatch')
    if digest(task['prompt'].encode()) != task['prompt_sha256']:
        raise ValueError('Task prompt content hash mismatch')
    raw_a,raw_n=Path(annotation_path).read_bytes(),Path(notes_path).read_bytes()
    rid=digest(raw_a+raw_n)[:12]
    root=Path(out)/(task['id']+'-'+rid);root.mkdir(parents=True,exist_ok=True)
    for name,data in [('annotation.json',raw_a),('review_notes.json',raw_n)]:
        p=root/name
        if p.exists() and p.read_bytes()!=data:raise ValueError('Immutable artifact changed')
        if not p.exists():p.write_bytes(data)
    record={'task_id':task['id'],'metadata':metadata,'input_hash':task['source_hash'],
            'output_hashes':{'annotation':digest(raw_a),'review_notes':digest(raw_n)},
            'label_origin':'MODEL_GENERATED_NOT_HUMAN_GOLD'}
    try:
        ann,notes=json.loads(raw_a),json.loads(raw_n);v=validate(ann,notes,source)
        record.update(state='STRUCTURALLY_VALID_SEMANTIC_REVIEW_PENDING' if v['valid'] else 'NEEDS_REPAIR',validation=v)
    except (ValueError,TypeError,KeyError) as e: record.update(state='FORMAT_ERROR',error=str(e))
    write_new(root/'import.json',record)
    return record


def main():
    p=argparse.ArgumentParser(description='v0.2 independent annotation workflow; does not silently migrate v0.1')
    sub=p.add_subparsers(dest='command',required=True)
    s=sub.add_parser('prepare')
    for k in ['source','protocol','out']:s.add_argument('--'+k,required=True)
    s.add_argument('--pass-name',default='A')
    s=sub.add_parser('validate')
    for k in ['annotation','notes','source','out']:s.add_argument('--'+k,required=True)
    s=sub.add_parser('import')
    for k in ['task','annotation','notes','source','metadata','out']:s.add_argument('--'+k,required=True)
    a=p.parse_args()
    if a.command=='prepare':r=prepare(read(a.source),a.protocol,a.out,a.pass_name)
    elif a.command=='validate':r=validate(read(a.annotation),read(a.notes),read(a.source));write_new(a.out,r)
    else:r=import_files(read(a.task),read(a.source),a.annotation,a.notes,read(a.metadata),a.out)
    print(json.dumps(r,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
