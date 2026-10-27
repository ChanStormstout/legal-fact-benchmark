"""Offline arithmetic for RAPIDO-EVAL-2.0 model-reference labels. No model calls.

Does not assess entailment, annotation completeness, legal correctness or cohort
superiority. Missing annotations remain bounded rather than being scored as errors.
"""
import argparse
import hashlib
import json
from pathlib import Path

COVERAGE = {'CORRECT', 'NOT_SATISFIED', 'ANNOTATION_UNRESOLVED'}
ASSERTION = {'SUPPORTED', 'CONTRADICTED', 'UNSUPPORTED', 'ANNOTATION_UNRESOLVED'}
ANSWER = {'SUPPORTED_ANSWER', 'PARTIAL', 'WRONG_OR_OVERREACH',
          'NO_SUBSTANTIVE_ANSWER', 'ANNOTATION_UNRESOLVED'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique(rows, key):
    ids = [r[key] for r in rows]
    require(len(ids) == len(set(ids)), 'Duplicate ' + key)
    return set(ids)


def evidence(rows, sources):
    for r in rows:
        sid, quote = r['source_id'], r['quote']
        require(sid in sources, 'Unknown source: ' + sid)
        require(bool(quote) and quote in sources[sid]['text'],
                'Non-verbatim source quote: ' + sid)


def interval(c, u, n):
    return [c / n, (c + u) / n] if n else None


def harmonic(r, p):
    return 100 * 2 * r * p / (r + p) if r + p else 0.0


def score_one(report, labels, reference, sources, reference_hash):
    text = report['text']
    require(sha(text.encode('utf-8')) == report['report_sha256'], 'Report hash mismatch')
    status = report['delivery_status']
    require(status in {'SUBSTANTIVE_REPORT', 'EMPTY_REPORT', 'TECHNICAL_FAILURE', 'NOT_RUN'},
            'Invalid delivery status')
    result = {'blind_id': report['blind_id'], 'report_sha256': report['report_sha256'],
              'delivery_status': status, 'reference_sha256': reference_hash}
    if status != 'SUBSTANTIVE_REPORT':
        require(labels is None, 'Do not silently ignore labels for a non-report slot')
        return dict(result, annotation_status='NO_OUTPUT_SLOT', R=[0, 0], P=None,
                    H=[0, 0], strict_success=[0, 0],
                    serious_error_observed=None, no_answer_is_safe=False)
    if labels is None:
        return dict(result, annotation_status='NOT_ANNOTATED', R=[0, 1], P=[0, 1],
                    H=[0, 100], strict_success=[0, 1], serious_error_observed=None)
    for key, expected in [('case_id', reference['case_id']),
                          ('reference_sha256', reference_hash),
                          ('source_view_sha256', reference['source_view_sha256']),
                          ('report_sha256', report['report_sha256'])]:
        require(labels.get(key) == expected, 'Label identity mismatch: ' + key)
    require(labels.get('reading_complete') is True, 'Incomplete reading: not scoreable')
    ids = unique(reference['items'], 'id')
    cov = labels['coverage']
    require(unique(cov, 'item_id') == ids, 'Missing/extra reference item')
    for r in cov:
        require(r['status'] in COVERAGE, 'Invalid coverage label')
        for q in r.get('report_quotes', []):
            require(q and q in text, 'Coverage quote absent from report')
        require(r['status'] != 'CORRECT' or r.get('report_quotes'),
                'Correct item requires report witness')
        evidence(r.get('evidence', []), sources)
        require(bool(r.get('reason')), 'Coverage reason missing')
    c = sum(r['status'] == 'CORRECT' for r in cov)
    u = sum(r['status'] == 'ANNOTATION_UNRESOLVED' for r in cov)
    rr = interval(c, u, len(ids))
    claims = labels['assertions']
    unique(claims, 'id')
    for a in claims:
        require(a['label'] in ASSERTION, 'Invalid assertion label')
        require(a.get('report_quote') and a['report_quote'] in text,
                'Assertion quote absent from report')
        require(a.get('proposition') and a.get('reason'), 'Assertion semantics missing')
        evidence(a.get('evidence', []), sources)
        require(a['label'] != 'SUPPORTED' or a.get('evidence'),
                'Supported assertion needs source witness')
    n = len(claims)
    s = sum(a['label'] == 'SUPPORTED' for a in claims)
    au = sum(a['label'] == 'ANNOTATION_UNRESOLVED' for a in claims)
    inventory_complete = labels.get('assertion_inventory_complete') is True
    pp = interval(s, au, n) if inventory_complete else None
    require(not (inventory_complete and not n and c), 'Content credit with no assertions')
    main = labels['main_answer']
    require(main in ANSWER, 'Invalid main-answer status')
    errors = labels.get('serious_errors', [])
    unique(errors, 'id')
    for e in errors:
        require(e.get('severity_status') in {'CONFIRMED', 'UNRESOLVED'},
                'Invalid serious-error severity')
        require(e.get('materiality'), 'Missing serious-error materiality')
        for q in e.get('report_quotes', []):
            require(q and q in text, 'Serious-error quote absent from report')
        evidence(e.get('source_evidence', []), sources)
    ec = sum(e['severity_status'] == 'CONFIRMED' for e in errors)
    eu = sum(e['severity_status'] == 'UNRESOLVED' for e in errors)
    errors_complete = labels.get('serious_error_inventory_complete') is True
    strict_lower = int(rr[0] == 1 and pp is not None and pp[0] == 1 and not ec
                       and not eu and errors_complete and main == 'SUPPORTED_ANSWER')
    strict_upper = int(rr[1] == 1 and (pp is None or pp[1] == 1) and not ec
                       and main in {'SUPPORTED_ANSWER', 'ANNOTATION_UNRESOLVED'})
    hh = ([harmonic(rr[0], pp[0]), harmonic(rr[1], pp[1])] if pp else
          ([0, 0] if inventory_complete and n == 0 else [0, harmonic(rr[1], 1)]))
    return dict(result, annotation_status=labels.get('annotation_status', 'RECEIVED'),
                R=rr, R_counts={'correct': c, 'unresolved': u, 'total': len(ids)},
                P=pp, P_counts={'supported': s, 'unresolved': au, 'total': n,
                                'inventory_complete': inventory_complete},
                H=hh, strict_success=[strict_lower, strict_upper],
                serious_error_observed=ec, serious_error_unresolved=eu,
                serious_error_inventory_complete=errors_complete, main_answer=main,
                label_kind='SOURCE_GROUNDED_MODEL_REFERENCE_NOT_HUMAN_GOLD')


def score(sources_path, reference_path, packet_path, labels_path):
    source_bytes, ref_bytes = Path(sources_path).read_bytes(), Path(reference_path).read_bytes()
    view, ref = json.loads(source_bytes), json.loads(ref_bytes)
    require(ref['source_view_sha256'] == sha(source_bytes), 'Source-view hash mismatch')
    require(ref['case_id'] == view['case_id'], 'Reference case mismatch')
    require(ref.get('reading_complete') is True, 'Incomplete reference')
    require(bool(ref['items']), 'Empty reference')
    unique(ref['items'], 'id')
    for item in ref['items']:
        require(item.get('criterion') and item.get('importance_reason'), 'Invalid criterion')
        require(item.get('weight', 1) == 1, 'Primary metric requires equal item weights')
        require(item.get('evidence'), 'Criterion requires source witness')
        evidence(item['evidence'], view['sources'])
    packet, labels = read(packet_path), read(labels_path)
    require(packet['case_id'] == ref['case_id'], 'Packet case mismatch')
    require(packet['source_view_sha256'] == sha(source_bytes), 'Packet source-view mismatch')
    require(packet.get('reference_sha256') == sha(ref_bytes), 'Packet reference hash mismatch')
    require(labels['case_id'] == ref['case_id'], 'Labels case mismatch')
    require(labels.get('reference_sha256') == sha(ref_bytes), 'Labels reference hash mismatch')
    require(labels.get('source_view_sha256') == sha(source_bytes), 'Labels source-view mismatch')
    report_ids = unique(packet['reports'], 'blind_id')
    require(unique(labels['reports'], 'blind_id') <= report_ids, 'Unknown blind report')
    lookup = {r['blind_id']: r for r in labels['reports']}
    rows = [score_one(r, lookup.get(r['blind_id']), ref, view['sources'], sha(ref_bytes))
            for r in packet['reports']]
    return {'protocol': 'RAPIDO-EVAL-2.0', 'case_id': ref['case_id'],
            'source_view_sha256': sha(source_bytes), 'reference_sha256': sha(ref_bytes),
            'packet_sha256': sha(Path(packet_path).read_bytes()),
            'labels_sha256': sha(Path(labels_path).read_bytes()), 'reports': rows,
            'semantic_labels_program_verified': False,
            'cohort_superiority_estimated': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['sources', 'reference', 'packet', 'labels', 'output']:
        p.add_argument('--' + name, required=True, type=Path)
    args = p.parse_args()
    require(not args.output.exists(), 'Output exists; choose a new path to preserve prior scores')
    result = score(args.sources, args.reference, args.packet, args.labels)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(args.output), 'reports': len(result['reports']),
                      'no_model_calls': True}))


if __name__ == '__main__':
    main()
