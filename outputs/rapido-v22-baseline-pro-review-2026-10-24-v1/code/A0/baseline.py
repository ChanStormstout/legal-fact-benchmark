"""One plain-text answer. No model-derived intermediate or feedback is consumed."""
import time
from common import digest, save


def request(snapshot, cfg):
    sources = [s for s in snapshot['directory'].values()
               if s['domain'] in ('CASE', 'LAW') and s['visibility'] == 'ALLOWED']
    material = '\n\n'.join('[' + s['id'] + ' | ' + s['original_id'] + ']\n' + s['text']
                           for s in sources)
    parameters = {k: v for k, v in cfg['parameters'].items() if k != 'response_format'}
    wire = {**parameters, 'messages': [
        {'role': 'system', 'content': 'Answer the question using the supplied materials. Cite the supplied source IDs where relevant.'},
        {'role': 'user', 'content': 'Question:\n' + snapshot['question'] + '\n\nScope:\n' + snapshot['scope']
         + '\n\nAllowed case materials and law:\n' + material}]}
    return {'plain_wire': wire, 'snapshot_id': snapshot['snapshot_id'],
            'source_ids': [s['id'] for s in sources], 'mechanisms': [], 'one_call_only': True}


def run(provider, snapshot, cfg, dest):
    started = time.monotonic()
    req = request(snapshot, cfg)
    save(dest / 'started.json', {'arm': 'A0', 'case_id': snapshot['case_id'], 'request_hash': digest(req)})
    save(dest / 'input-contract.json', {k: v for k, v in req.items() if k != 'plain_wire'})
    try:
        body, receipt = provider.call(snapshot['case_id'], 'A0', 'direct-answer', req, attempt=0)
        (dest / 'final-report.txt').write_text(body)
        result = {'case_id': snapshot['case_id'], 'arm': 'A0', 'technical_complete': True,
                  'stop_reason': 'ONE_CALL_COMPLETED', 'report_hash': digest(body), 'quality_pass': None,
                  'receipt': receipt}
    except Exception as exc:
        result = {'case_id': snapshot['case_id'], 'arm': 'A0', 'technical_complete': False,
                  'stop_reason': type(exc).__name__ + ':' + str(exc), 'quality_pass': None,
                  'receipts': getattr(exc, 'receipts', []), 'answer': None}
    result['elapsed_seconds'] = time.monotonic() - started
    save(dest / 'outcome.json', result)
    return result
