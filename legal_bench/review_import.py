"""Validate and version a web reconciliation reply; do not repair semantics."""
import argparse
import copy
from .core import digest, normalize, read, write_new, log_run
from .scoped_engine import projection_view


def check_reply(reply, task, annotations, source):
    errors = []
    if (source.get('case_id') != task['case_id'] or source.get('text_sha256') != task['source_hash']
            or digest(source.get('segments')) != task['source_hash']):
        errors.append('source hash or case mismatch')
    if reply.get('case_id') != task['case_id']: errors.append('case_id')
    if reply.get('unit_resolution', {}).get('unit_id') != 'current_appeal': errors.append('unit_id')
    segments = {s['id']: s['text'] for s in source['segments']}
    def walk(obj, path='reply'):
        if isinstance(obj, dict):
            if 'evidence' in obj:
                evs = obj['evidence']
                if not isinstance(evs, list) or not evs: errors.append(path + ': missing evidence')
                else:
                    for ev in evs:
                        if not isinstance(ev, dict) or not isinstance(ev.get('quote'), str) or not ev['quote']:
                            errors.append(path + ': malformed evidence'); continue
                        if ev.get('segment_id') not in segments or normalize(ev['quote']) not in normalize(segments.get(ev.get('segment_id'), '')):
                            errors.append(path + ': unlocated quote ' + str(ev))
            for k, value in obj.items():
                if k != 'evidence': walk(value, path + '.' + k)
        elif isinstance(obj, list):
            for i, value in enumerate(obj): walk(value, path + '[%d]' % i)
    walk(reply)
    for label, ann in annotations.items():
        if digest(ann) != task['annotation_hashes'][label]: errors.append(label + ': stale annotation')
        records = reply.get('decisions', {}).get(label, [])
        ids = [r.get('assertion_id') for r in records]
        if len(ids) != len(set(ids)) or set(ids) != set(task['selected'][label]): errors.append(label + ': decision coverage')
        for r in records:
            if r.get('decision') not in ['ACCEPT', 'EXCLUDE', 'UNCERTAIN'] or not r.get('basis'):
                errors.append(label + ': decision fields')
    qids = [x.get('id') for x in reply.get('query_reference', [])]
    if set(qids) != {'Q%d' % i for i in range(1, 11)} or len(qids) != len(set(qids)):
        errors.append('query coverage')
    for q in reply.get('query_reference', []):
        if q.get('status') not in ['MATCH', 'MISMATCH', 'UNKNOWN', 'NOT_FOUND', 'UNSUPPORTED']:
            errors.append('query status')
    return {'valid': not errors, 'errors': errors, 'semantic_correctness': 'MODEL_REVIEW_NOT_ESTABLISHED_BY_VALIDATOR'}


def import_review(reply, task, annotations, source, metadata, out):
    for key in ['conversation_url', 'submitted_at', 'retrieved_at', 'model_display', 'effort_display']:
        if not metadata.get(key): raise ValueError('Missing observed provenance: ' + key)
    validation = check_reply(reply, task, annotations, source)
    write_new(out + '/validation.json', validation)
    if not validation['valid']: return validation
    for label, ann in annotations.items():
        amap = {a['id']: a for a in ann['assertions']}
        decisions = []
        for r in reply['decisions'][label]:
            r = copy.deepcopy(r)
            r['assertion_hash'] = digest(amap[r['assertion_id']])
            decisions.append(r)
        review = {'annotation_hash': digest(ann), 'mode': 'SCOPED_EXISTENTIAL',
                  'unit_id': 'current_appeal', 'unit_resolution': reply['unit_resolution'],
                  'material_scope': 'SELECTED_DEVELOPMENT_ASSERTIONS_NOT_COMPLETE_CASE',
                  'decisions': decisions,
                  'provenance': dict(metadata, prompt_sha256=task['prompt_sha256'], reply_hash=digest(reply),
                                     label_origin='MODEL_GENERATED_AND_MODEL_REVIEWED_NOT_HUMAN_GOLD')}
        # Validate safety rules before saving an executable view.
        view = projection_view(ann, review)
        write_new(out + '/' + label + '-review.json', review)
        write_new(out + '/' + label + '-view.json', view)
    write_new(out + '/reference.json', reply['query_reference'])
    return validation


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['reply', 'task', 'a', 'b', 'source', 'metadata', 'out']:
        p.add_argument('--' + name, required=True)
    args = p.parse_args()
    result = import_review(read(args.reply), read(args.task), {'A': read(args.a), 'B': read(args.b)},
                           read(args.source), read(args.metadata), args.out)
    log_run(args.out, 'import-scoped-review',
            [args.reply, args.task, args.a, args.b, args.source, args.metadata, __file__], [args.out])
    print(result)


if __name__ == '__main__': main()
