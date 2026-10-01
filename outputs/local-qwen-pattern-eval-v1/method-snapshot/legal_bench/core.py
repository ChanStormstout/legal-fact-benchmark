import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256((value if isinstance(value, bytes) else canonical(value).encode())).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    if path.exists():
        if path.read_text() == text:
            return
        raise ValueError('Refusing to overwrite: ' + str(path))
    with path.open('x') as f:
        f.write(text)


def normalize(text):
    return re.sub(r'\s+', ' ', text).strip()


def audit(source, dest):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    dbpath = dest / 'cases.sqlite'
    sha = hashlib.sha256()
    records = []
    with Path(source).open('rb') as f:
        for line_number, line in enumerate(f, 1):
            sha.update(line)
            if line.strip():
                r = json.loads(line)
                records.append((line_number, r))
    ids = [r['doc_id'] for _, r in records]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate doc_id; resolve before indexing')
    manifest = {'source_sha256': sha.hexdigest(), 'records': len(records), 'status': {},
                'facts_nonempty': 0, 'candidate_rule': 'possession claim keyword; NOT verified eligibility'}
    candidates = []
    for n, r in records:
        status = r.get('status', 'missing')
        manifest['status'][status] = manifest['status'].get(status, 0) + 1
        manifest['facts_nonempty'] += bool(r.get('facts', '').strip())
        hits = re.findall(r'recovery of possession|recover possession|suit for possession|restoration of possession|recover the possession',
                          r.get('facts', '') + '\n' + r.get('issues', ''), re.I)
        if hits:
            candidates.append({'doc_id': r['doc_id'], 'title': r['title'], 'url': r['url'],
                               'hits': len(hits), 'eligibility': 'UNREVIEWED'})
    candidates.sort(key=lambda x: (-x['hits'], x['doc_id']))
    if dbpath.exists():
        if read(dest / 'audit.json')['source_sha256'] != manifest['source_sha256']:
            raise ValueError('Different input; use a new destination')
    else:
        con = sqlite3.connect(str(dbpath))
        con.execute('CREATE TABLE cases (doc_id TEXT PRIMARY KEY, line_number INTEGER, title TEXT, url TEXT, record_sha256 TEXT, raw_json TEXT)')
        con.executemany('INSERT INTO cases VALUES (?,?,?,?,?,?)',
                        [(r['doc_id'], n, r['title'], r['url'], digest(r), canonical(r)) for n, r in records])
        con.commit()
        con.close()
    write_new(dest / 'audit.json', manifest)
    write_new(dest / 'candidates.json', candidates)
    return manifest


def make_source(case_id, text, url, source_file_hash, page_texts=None):
    pages = page_texts or [text]
    paragraphs = []
    for page_number, page in enumerate(pages, 1):
        for block in re.split(r'\n\s*\n', page.strip()):
            if block.strip():
                paragraphs.append({'id': 'p%04d' % (len(paragraphs) + 1),
                                   'page': page_number if page_texts else None,
                                   'text': normalize(block)})
    return {'case_id': str(case_id), 'url': url, 'source_sha256': source_file_hash,
            'paragraphs': paragraphs, 'text_sha256': digest(paragraphs),
            'source_completeness': 'REQUIRES_REVIEW'}


STATUSES = {'COURT_FOUND', 'ALLEGED', 'DISPUTED', 'REJECTED', 'UNDETERMINED'}


def validate(annotation, source):
    errors = []
    warnings = []
    def err(code, item):
        errors.append({'code': code, 'item': item})
    if not isinstance(annotation, dict):
        return {'valid': False, 'errors': [{'code': 'invalid_annotation_object', 'item': None}], 'warnings': []}
    required = ['case_id', 'units', 'entities', 'events', 'coverage', 'unresolved']
    for k in required:
        if k not in annotation:
            err('missing_field', k)
    if errors:
        return {'valid': False, 'errors': errors, 'warnings': warnings}
    if annotation['case_id'] != source['case_id']:
        err('case_mismatch', annotation['case_id'])
    pmap = {p['id']: p['text'] for p in source['paragraphs']}
    entities = annotation['entities']
    events = annotation['events']
    units = annotation['units']
    for collection, name in [(entities, 'entity'), (events, 'event'), (units, 'unit')]:
        if not isinstance(collection, list) or any(not isinstance(x, dict) or 'id' not in x for x in collection):
            err('invalid_collection', name)
            continue
        ids = [x['id'] for x in collection]
        if len(ids) != len(set(ids)):
            err('duplicate_id', name)
    if errors:
        return {'valid': False, 'errors': errors, 'warnings': warnings}
    entity_ids = {x['id'] for x in entities}
    unit_ids = {x['id'] for x in units}
    event_ids = {x['id'] for x in events}
    cited = set()
    for e in events:
        for k in ['type', 'unit_id', 'roles', 'status', 'polarity', 'speaker', 'time', 'attributes', 'evidence', 'unresolved']:
            if k not in e:
                err('missing_event_field', [e['id'], k])
        if not isinstance(e.get('roles'), dict) or not isinstance(e.get('attributes'), dict) or not isinstance(e.get('evidence'), list) or not isinstance(e.get('unresolved'), list):
            err('invalid_event_field_type', e['id'])
            continue
        if e.get('unit_id') not in unit_ids:
            err('unknown_unit', e['id'])
        if e.get('status') not in STATUSES:
            err('unknown_status', e['id'])
        if e.get('polarity') not in ['POSITIVE', 'NEGATIVE']:
            err('unknown_polarity', e['id'])
        for role, entity in e.get('roles', {}).items():
            if entity is not None and entity not in entity_ids:
                err('dangling_entity', [e['id'], role, entity])
        for other in e.get('conflicts_with', []):
            if other not in event_ids or other == e['id']:
                err('invalid_conflict_reference', [e['id'], other])
        for ev in e.get('evidence', []):
            if not isinstance(ev, dict):
                err('invalid_evidence', e['id'])
                continue
            pid, quote = ev.get('paragraph_id'), ev.get('quote', '')
            if not quote or pid not in pmap or normalize(quote) not in normalize(pmap.get(pid, '')):
                err('unlocated_quote', [e['id'], pid, quote])
            else:
                cited.add(pid)
        if not e.get('evidence'):
            err('missing_evidence', e['id'])
        t = e.get('time')
        if t is not None:
            try:
                datetime.strptime(t, '%Y-%m-%d')
            except (ValueError, TypeError):
                err('invalid_date', e['id'])
        if e.get('unresolved'):
            warnings.append({'code': 'unresolved_event', 'item': e['id']})
    coverage = annotation.get('coverage', [])
    if not isinstance(coverage, list):
        err('invalid_coverage', None)
        coverage = []
    covered = {x.get('paragraph_id') for x in coverage if isinstance(x, dict)}
    if set(pmap) - covered:
        err('unreviewed_paragraphs', sorted(set(pmap) - covered))
    if covered - set(pmap):
        err('invalid_coverage_paragraphs', sorted(covered - set(pmap)))
    return {'valid': not errors, 'errors': errors, 'warnings': warnings,
            'event_count': len(events), 'located_paragraphs': len(cited),
            'semantic_correctness': 'NOT_ESTABLISHED_BY_VALIDATOR'}


def compare(a, b):
    # IDs are local to a conversation. Align by source span, never by generated IDs.
    def signatures(ann):
        result = {}
        names = {x['id']: normalize(x.get('label', '')).lower() for x in ann['entities']}
        for e in ann['events']:
            key = canonical(sorted((x['paragraph_id'], normalize(x['quote'])) for x in e['evidence']))
            sig = {'type': e['type'], 'roles': {r: names.get(v) for r, v in e['roles'].items()},
                   'status': e['status'], 'polarity': e['polarity'], 'time': e['time'],
                   'attributes': e['attributes'], 'unresolved': e['unresolved']}
            result.setdefault(key, []).append(sig)
        return result
    aa, bb = signatures(a), signatures(b)
    return {'only_a_spans': sorted(set(aa) - set(bb)), 'only_b_spans': sorted(set(bb) - set(aa)),
            'differences': [{'span': k, 'a': aa[k], 'b': bb[k]} for k in sorted(set(aa) & set(bb))
                            if canonical(aa[k]) != canonical(bb[k])],
            'note': 'Span boundaries/name variants require model review; agreement is not accuracy.'}


def log_run(root, command, inputs, outputs):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    record = {'at': datetime.now(timezone.utc).isoformat(), 'command': command,
              'inputs': {str(p): digest(Path(p).read_bytes()) for p in inputs},
              'outputs': list(map(str, outputs))}
    with (root / 'runs.jsonl').open('a') as f:
        f.write(canonical(record) + '\n')
