"""Conservative, reversible typography location. No fuzzy semantic matching.

A spaced hyphen is joinable only when the joined word is independently present
unbroken in the SAME permitted document and neither half is independently a
word there. This deliberately leaves many possible layout breaks unresolved.
"""
import re
from .grounding_v9 import source_match as exact_match
from .realcase_grounding_v3 import canonical_chars

VERSION = 'V16-TYPOGRAPHY-1'


def normalize(text, document_text):
    split_pattern = r'\b([A-Za-z]+)(-\s+)([A-Za-z]+)\b'
    # Fragments of the very layout breaks being checked are not independent
    # occurrences of complete words.
    independent = re.sub(split_pattern, ' ', document_text)
    words = set(re.findall(r'\b[A-Za-z]+\b', independent))
    removed, edits = set(), []
    for m in re.finditer(split_pattern, text):
        left, right = m.group(1), m.group(3)
        joined = left + right
        if joined in words and left not in words and right not in words:
            removed.update(range(m.start(2), m.end(2)))
            edits.append({'start': m.start(), 'end': m.end(), 'original': m.group(),
                          'normalized': joined, 'basis': 'INDEPENDENT_UNBROKEN_WORD_IN_SAME_ALLOWED_DOCUMENT'})
    visible = ''.join(c for i, c in enumerate(text) if i not in removed)
    raw_map = [i for i in range(len(text)) if i not in removed]
    canon, offset = canonical_chars(visible)
    return {'original': text, 'normalized': canon,
            'original_offsets': [raw_map[i] for i in offset], 'edits': edits,
            'version': VERSION}


def source_match(record, sources):
    quote = record.get('quote', record.get('source_quote'))
    if not isinstance(quote, str):
        return {'error': 'QUOTE_NOT_A_STRING', 'semantic_verified': False}
    ordinary = exact_match(record, sources)
    if ordinary.get('error') not in {None, 'QUOTE_NOT_LOCATED'}:
        return ordinary
    refs = list(dict.fromkeys(record.get('refs', record.get('source_refs', []))))
    # exact_match has already checked addresses and document identity.
    doc = sources[refs[0]]['document']
    corpus = '\n'.join(s['text'] for s in sources.values() if s['document'] == doc)
    refs.sort(key=lambda r: (sources[r].get('original_line', 10**12), r))
    groups = []
    for ref in refs:
        line = sources[ref].get('original_line')
        if groups and line is not None and sources[groups[-1][-1]].get('original_line') is not None and line == sources[groups[-1][-1]]['original_line'] + 1:
            groups[-1].append(ref)
        else:
            groups.append([ref])
    q = normalize(quote, corpus)
    matches = []
    for group in groups:
        raw = ' '.join(sources[r]['text'] for r in group)
        normalized = normalize(raw, corpus)
        if not normalized['edits'] and not q['edits']:
            continue
        needle = q['normalized']; hay = normalized['normalized']
        pos = hay.find(needle) if needle else -1
        while pos >= 0:
            lo = normalized['original_offsets'][pos]
            hi = normalized['original_offsets'][pos + len(needle) - 1] + 1
            spans, base = [], 0
            for ref in group:
                text = sources[ref]['text']; a, b = max(0, lo-base), min(len(text), hi-base)
                if a < b:
                    spans.append({'ref': ref, 'start': a, 'end': b, 'original': text[a:b]})
                base += len(text) + 1
            matches.append({'spans': spans, 'source_normalization': normalized,
                            'quote_normalization': q})
            pos = hay.find(needle, pos+1)
    if len(matches) != 1:
        if not matches and ordinary.get('error') is None:
            return ordinary
        return {'error': 'QUOTE_AMBIGUOUS' if matches else 'QUOTE_NOT_LOCATED',
                'semantic_verified': False, 'typography_policy': VERSION}
    if ordinary.get('error') is None:
        return ordinary
    return {'error': None, 'mode': 'REVERSIBLE_DOCUMENT_ATTESTED_LAYOUT_JOIN',
            'original_spans': matches[0]['spans'], 'normalization': matches[0],
            'semantic_verified': False}
