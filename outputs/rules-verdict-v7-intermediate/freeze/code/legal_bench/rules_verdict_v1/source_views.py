"""Explicit source slices and token windows; no semantic filtering by keywords."""
import hashlib
import json
from pathlib import Path


def digest(value):
    raw = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    if path.exists():
        if path.read_text() != raw:
            raise FileExistsError('Refusing to overwrite: ' + str(path))
        return
    with path.open('x') as handle:
        handle.write(raw)


def build_view(source, slices, purpose):
    original = {s['id']: s for s in source['segments']}
    if len(original) != len(source['segments']):
        raise ValueError('Duplicate source segment ID')
    seen = set()
    segments = []
    for selection in slices:
        sid = selection['segment_id']
        if sid in seen or sid not in original:
            raise ValueError('Duplicate/unknown selection ' + sid)
        seen.add(sid)
        text = original[sid]['text']
        start, end = selection.get('start', 0), selection.get('end', len(text))
        if not (type(start) is int and type(end) is int and 0 <= start < end <= len(text)):
            raise ValueError('Invalid source offsets')
        view_id = sid if start == 0 and end == len(text) else '%s@%d:%d' % (sid, start, end)
        segments.append({'id': view_id, 'text': text[start:end], 'source_segment_id': sid,
                         'start': start, 'end': end, 'page': original[sid].get('page')})
    if not segments:
        raise ValueError('Empty allowed source')
    return {'case_id': source['case_id'], 'purpose': purpose, 'source_hash': digest(source),
            'slices_hash': digest(slices), 'segments': segments,
            'excluded_segment_ids': [s['id'] for s in source['segments'] if s['id'] not in seen],
            'input_view_hash': digest(segments), 'metadata_exposed': ['case_id']}


def windows(view, count_tokens, max_tokens=4000, overlap_tokens=400):
    """Preserve exact supplied segments. Oversize segments fail instead of truncating."""
    segments = view['segments']
    sizes = [count_tokens(s['text']) for s in segments]
    if any(n > max_tokens for n in sizes):
        raise ValueError('INPUT_TOO_LONG: single source segment exceeds extraction window')
    result, start = [], 0
    while start < len(segments):
        end, total = start, 0
        while end < len(segments) and total + sizes[end] <= max_tokens:
            total += sizes[end]
            end += 1
        result.append({'case_id': view['case_id'], 'window_id': 'w%03d' % (len(result) + 1),
                       'segments': segments[start:end], 'source_token_count': total,
                       'input_view_hash': view['input_view_hash']})
        if end == len(segments):
            break
        next_start, overlap = end, 0
        while next_start > start + 1 and overlap + sizes[next_start - 1] <= overlap_tokens:
            next_start -= 1
            overlap += sizes[next_start]
        start = next_start
    covered = {s['id'] for w in result for s in w['segments']}
    if covered != {s['id'] for s in segments}:
        raise AssertionError('Source coverage lost')
    return result
