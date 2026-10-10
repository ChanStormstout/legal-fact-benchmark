"""Versioned response-boundary import. Identity is response metadata, not citations.

Never imports a multi-response cache under a caller-supplied document identity.
Incomplete windows are useful for screening only; freeze requires explicit coverage.
"""
import hashlib
import re
from pathlib import Path

HEADER = re.compile(r'^([^\n]+) \((https://indiankanoon\.org/doc/(\d+)/?)\)\r?\n([^\n]*Content type:[^\n]*Source: [^\n]*Total lines: (\d+)[^\n]*)$', re.M)
LINE = re.compile(r'(?:^|(?<= ))L(\d+): ?', re.M)


def parse_responses(raw, raw_path):
    heads = list(HEADER.finditer(raw))
    if not heads:
        raise ValueError('IDENTITY_UNCONFIRMED: no supported response envelope')
    responses = []
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(raw)
        content = raw[h.end():end]
        rows = []
        marks = list(LINE.finditer(content))
        for j, m in enumerate(marks):
            start = h.end() + m.end()
            line_end = content.find('\n',m.end())
            line_end = len(content) if line_end < 0 else line_end
            if j+1 < len(marks): line_end = min(line_end, marks[j+1].start())
            stop = h.end() + line_end
            # Exactly one renderer separator space precedes an inline address.
            if j+1 < len(marks) and line_end == marks[j+1].start() and raw[stop-1:stop]==' ': stop-=1
            rows.append({'line': int(m[1]), 'text': raw[start:stop], 'raw_char_range': [start, stop],
                         'raw_byte_range': [len(raw[:start].encode()), len(raw[:stop].encode())],
                         'raw_physical_line': raw.count('\n', 0, start) + 1})
        unparsed = [x for x in content.splitlines() if x.strip() and not re.match(r'^L\d+:',x)
                    and not re.fullmatch(r'-{3,}', x.strip())]
        responses.append({'document_id': h[3], 'url': h[2], 'title': h[1],
                          'response_index': i, 'raw_path': str(raw_path),
                          'raw_sha256': hashlib.sha256(raw.encode()).hexdigest(),
                          'response_char_range': [h.start(), end], 'total_lines': int(h[5]),
                          'lines': rows, 'unparsed_body_lines': unparsed})
    return responses


def merge_windows(responses):
    result = {}
    for r in responses:
        doc = result.setdefault(r['document_id'], {'document_id': r['document_id'],
            'url': r['url'], 'titles': [], 'segments': [], 'conflicts': [], 'unparsed': [], 'totals': []})
        if r['title'] not in doc['titles']: doc['titles'].append(r['title'])
        if r['total_lines'] not in doc['totals']: doc['totals'].append(r['total_lines'])
        doc['unparsed'].extend(r['unparsed_body_lines'])
        for line in r['lines']:
            provenance = {k: r[k] for k in ('document_id','url','response_index','raw_path','raw_sha256')}
            provenance.update({k: line[k] for k in ('raw_char_range','raw_byte_range','raw_physical_line')})
            provenance['original_line'] = line['line']
            old = next((s for s in doc['segments'] if s['original_line'] == line['line']), None)
            if old is None:
                doc['segments'].append({'id': 'IK-%s:L%d' % (r['document_id'], line['line']),
                    'source_document': r['document_id'], 'original_line': line['line'],
                    'text': line['text'], 'provenance': [provenance]})
            elif old['text'] == line['text']:
                old['provenance'].append(provenance)
            else:
                doc['conflicts'].append({'line': line['line'], 'existing': old['text'],
                                        'alternative': line['text'], 'provenance': provenance})
    for d in result.values():
        d['segments'].sort(key=lambda s:s['original_line'])
        got = {s['original_line'] for s in d['segments']}
        d['missing_lines'] = sorted(set(range(max(d['totals']))) - got)
        d['status'] = ('CONFLICT' if d['conflicts'] or len(d['totals']) != 1 or d['unparsed']
                       else 'INCOMPLETE' if d['missing_lines'] else 'COMPLETE_RENDERING')
    return result


def validate_view(view, document, require_complete=True):
    if str(view['case_id']) != document['document_id']:
        raise ValueError('SOURCE_IDENTITY_CONFLICT')
    if document['status'] == 'CONFLICT': raise ValueError('SOURCE_CONFLICT')
    if require_complete and document['status'] not in ('COMPLETE_RENDERING','COMPLETE_DECLARED_BODY'):
        raise ValueError('SOURCE_INCOMPLETE')
    originals = {s['id']:s for s in document['segments']}
    mapping = []
    for s in view['segments']:
        if str(s.get('source_document')) != document['document_id']:
            raise ValueError('SOURCE_IDENTITY_CONFLICT: ' + s['id'])
        original = originals.get(s.get('source_segment_id', s['id']))
        if original is None: raise ValueError('SOURCE_ADDRESS_MISSING: ' + s['id'])
        start, end = s.get('start',0), s.get('end',len(original['text']))
        if s['text'] != original['text'][start:end]:
            raise ValueError('SOURCE_TEXT_MISMATCH: ' + s['id'])
        for p in original['provenance']:
            raw = Path(p['raw_path']).read_text()
            a,b = p['raw_char_range']
            if hashlib.sha256(raw.encode()).hexdigest() != p['raw_sha256'] or raw[a:b] != original['text']:
                raise ValueError('RAW_PROVENANCE_MISMATCH')
            if p['document_id'] != document['document_id']: raise ValueError('SOURCE_IDENTITY_CONFLICT')
        mapping.append({'submitted_segment_id':s['id'], 'source_segment_id':original['id'],
                        'range':[start,end], 'provenance':original['provenance']})
    if not mapping: raise ValueError('SOURCE_EMPTY')
    return mapping


def validate_submission(text, view, document):
    mapping = validate_view(view, document)
    for s in view['segments']:
        if s['text'] not in text or s['id'] not in text:
            raise ValueError('SUBMISSION_SOURCE_OMISSION: ' + s['id'])
    return {'sha256':hashlib.sha256(text.encode()).hexdigest(), 'mapping':mapping,
            'scope':'Exact approved source delivery and document provenance; not legal correctness or external identity proof.'}


def declare_body(document, first, last, basis):
    """Explicit source review of body bounds; cannot forgive an interior missing line."""
    import copy
    d=copy.deepcopy(document)
    if d['status']=='CONFLICT':raise ValueError('SOURCE_CONFLICT')
    if not basis or first>last:raise ValueError('BODY_RANGE_UNCONFIRMED')
    missing=sorted(set(range(first,last+1))-{s['original_line'] for s in d['segments']})
    d['body_coverage']={'first_line':first,'last_line':last,'basis':basis,'missing':missing}
    if missing:raise ValueError('BODY_INCOMPLETE: '+str(missing))
    d['status']='COMPLETE_DECLARED_BODY'
    return d
