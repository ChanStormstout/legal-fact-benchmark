"""Score receipt provenance and authoritative local technical state."""
import json
import hashlib
from pathlib import Path
from .artifact_state_v20_2 import byte_hash, digest, immutable
from .local_evaluation_v20_2 import semantic_metrics, blind_order


def local_answer(out, cid, method):
    dest = Path(out) / 'local' / cid / method
    path = dest / 'formal-answer.json'
    formal = json.loads(path.read_text()) if path.exists() else {'answer':None,'status':'NOT_STARTED'}
    run_path = dest / 'run.json'
    run = json.loads(run_path.read_text()) if run_path.exists() else None
    if formal.get('answer') is not None:
        if run is None or run.get('run_status') != 'OK' or formal.get('status') != 'OK':
            raise ValueError('LOCAL_FINAL_STATE_INCONSISTENT:' + cid + '/' + method)
        status = 'OK'
    else:
        status = formal.get('status') or (run.get('run_status') if run else 'NOT_STARTED')
        if status == 'OK':
            status = 'FINAL_CONTRACT_REJECTED'
    return {'answer':formal.get('answer'),'technical_status':status,
            'formal_sha256':byte_hash(path) if path.exists() else None,
            'run_sha256':byte_hash(run_path) if run_path.exists() else None}


def score_manifest(cid, name, prompt, fixture, reference_path, mapping, actuals):
    return {'version':'SCORE_PROVENANCE_V20_2','kind':'SCORES','case_id':cid,'batch':name,
            'expected_answer_ids':list(actuals),'task_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
            'fixture_sha256':digest(fixture),'checklist_sha256':byte_hash(reference_path),
            'blinding_sha256':digest(mapping),'answers_sha256':digest(actuals),
            'actuals':actuals,'required_mode':'Extra High'}


def validate_score(out, cid, name, fixture, mapping, reference_path):
    out = Path(out)
    task = out / 'web/tasks' / cid / (name + '.txt')
    manifest_path = task.with_suffix('.manifest.json')
    reply = out / 'web/replies' / cid / (name + '.json')
    receipt = reply.with_name(name + '-receipt.json')
    if not all(p.is_file() for p in (task, manifest_path, reply, receipt)):
        raise ValueError('SCORE_PROVENANCE_MISSING:' + cid + '/' + name)
    manifest = json.loads(manifest_path.read_text())
    record = json.loads(receipt.read_text())
    if manifest.get('version') != 'SCORE_PROVENANCE_V20_2' or manifest.get('case_id') != cid or manifest.get('batch') != name:
        raise ValueError('SCORE_MANIFEST_IDENTITY')
    ids = manifest['expected_answer_ids']
    fixed=blind_order(cid,list('ABCDEFG'),20261001)
    expected_ids=list(fixed)[:4] if name=='score-1' else list(fixed)[4:] if name=='score-2' else []
    if mapping!=fixed or ids!=expected_ids or len(ids) != len(set(ids)):
        raise ValueError('SCORE_BLINDING_SCOPE')
    actuals = {aid:local_answer(out,cid,mapping[aid]) for aid in ids}
    expected = score_manifest(cid,name,task.read_text(),fixture,reference_path,mapping,actuals)
    if manifest != expected:
        raise ValueError('SCORE_INPUT_CHANGED')
    if (record.get('thinking') != 'Extra High' or not isinstance(record.get('model_visible'),str)
            or not record['model_visible'].strip() or record.get('task_sha256') != byte_hash(task)
            or record.get('manifest_sha256') != byte_hash(manifest_path)
            or record.get('reply_sha256') != byte_hash(reply)):
        raise ValueError('SCORE_RECEIPT_MISMATCH')
    body = json.loads(reply.read_text())
    return semantic_metrics(body,json.loads(Path(reference_path).read_text()),ids,actuals),ids


def evaluation_row(cid, dispute_id, method, actual, metrics=None):
    metrics = dict(metrics or {})
    if metrics and metrics.get('technical_status') != actual['technical_status']:
        raise ValueError('SCORE_CANNOT_OVERRIDE_LOCAL_TECHNICAL_STATE')
    metrics.pop('technical_status',None)
    return {**metrics,'case_id':cid,'dispute_id':dispute_id,'method':method,
            'technical_status':actual['technical_status'],
            'semantic_evaluation':'SOURCE_REVIEWED' if metrics else 'NOT_EVALUATED'}

