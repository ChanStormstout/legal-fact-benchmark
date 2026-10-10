"""V5 versioned import/prompt entry; generation uses the separately frozen runner."""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.irac_application.contract_v5 import process, compact, display, digest, address_directory
from legal_bench.irac_application.contract_v5_tasks import prompt, schema
from legal_bench.irac_application.aligned_v2_runtime import atomic_json as save

R = Path('outputs/irac-contract-repair-v5')
V4 = Path('outputs/irac-pipeline-repair-v4')
AUDIT_CASES = ['1114159', '112400', '188721101', '52547606', '55384096', '68065690']


def read(path):
    return json.loads(Path(path).read_text())


def hf(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inputs(cid):
    if cid not in AUDIT_CASES:
        raise ValueError('OUTSIDE_EXISTING_ALLOWED_MATERIAL')
    m = read(R / 'sources' / (cid + '.json'))
    t = read(R / 'templates' / (m['family'] + '.json'))
    law = read(R / 'sources' / (m['family'] + '-law.json'))
    sm = read(R / 'input-audit' / (cid + '.json'))['source_map']
    return m, t, law, sm


def prepare():
    assert (R / 'registration.json').exists()
    assert not (R / 'materials.json').exists(), 'Already prepared; do not overwrite.'
    files = {}
    for folder in ('sources', 'templates'):
        for p in (V4 / folder).glob('*.json'):
            dst = R / folder / p.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, dst)
            files[str(dst)] = {'origin': str(p), 'sha256': hf(dst)}
    for cid in AUDIT_CASES:
        prior = read(V4 / 'input-audit' / (cid + '.json'))
        # Verify the existing exact ranges; don't read/recover any additional spans.
        buffers = {}
        for row in prior['source_map']:
            p = row['raw_path']
            if p not in buffers:
                assert 'sealed' not in p.lower()
                assert hf(p) == row['raw_sha256']
                buffers[p] = Path(p).read_text()
            m = read(R / 'sources' / (cid + '.json'))
            assert buffers[p][slice(*row['raw_char_range'])] == m['sources'][row['source_id']]['text']
        m = read(R / 'sources' / (cid + '.json'))
        view, aliases, ordering = display(m, prior['source_map'])
        save(R / 'input-audit' / (cid + '.json'), {'case_id': cid, 'source_map': prior['source_map'],
             'display': view, 'display_map': aliases, 'ordering': ordering,
             'allowed_source_origin': str(V4 / 'sources' / (cid + '.json')), 'new_source_spans': 0})
        t = read(R / 'templates' / (m['family'] + '.json'))
        save(R / 'catalogues' / (m['family'] + '.json'), address_directory(t))
    save(R / 'materials.json', {'files': files, 'audit_cases': AUDIT_CASES,
                               'new_case_or_law_text': False, 'model_calls': 0})


def finish_attempt(run, out, stage, m, t, law, allow_legacy=False):
    """The actual completion/import path; raw bytes are never edited."""
    out = Path(out)
    result = {'case_id': m['case_id'], 'method': stage, 'run_status': run['run_status'], 'prediction': None}
    if run['run_status'] != 'OK':
        save(out / 'result.json', result)
        return result
    try:
        value = json.loads((out / 'raw-response.txt').read_text())
        if not run.get('schema_mask_calls', 0) and not run.get('offline_replay', False):
            raise ValueError('MASK_NOT_EFFECTIVE')
        if stage == 'P':
            sources = dict(m['sources'])
            sources.update({s['source_id']: s for s in law})
            imp, checks = process(value, t, sources, m['case_id'], allow_legacy=allow_legacy)
            save(out / 'import.json', imp)
            save(out / 'evidence-records.json', imp['evidence_records'])
            if not imp['usable']:
                raise ValueError(imp['status'])
            save(out / 'checks-full.json', checks)
            save(out / 'checks-compact.json', compact(checks))
            result.update(prediction=value, import_status=imp['status'])
        else:
            from legal_bench.rules_verdict_v1.contracts import validate
            validate(value, read(out / 'schema.json'))
            result['prediction'] = value
    except (ValueError, KeyError, TypeError, OSError) as e:
        result.update(run_status='FORMAT_ERROR', reason=repr(e), prediction=None)
    save(out / 'result.json', result)
    return result


def final_task(cid, method, proposal, imported, checks):
    """Build B/C without treating an optional absent summary as missing evidence."""
    m, t, law, sm = inputs(cid)
    inter = {}
    if method in ('B', 'C'):
        inter = {'proposal': proposal, 'import_coverage': {k: imported[k] for k in
                 ('status', 'quarantine', 'restriction_coverage', 'condition_summary_required',
                  'computable_use_count', 'empty_projection')}}
        inter['import_coverage']['evidence_records'] = [{k: v for k, v in r.items() if k != 'raw_record'}
                                                      for r in imported['evidence_records']]
        if method == 'C':
            inter['program_checks'] = compact(checks)
    return prompt('final', m, t, law, sm, inter), schema('final', m, t, law), inter


def replay():
    assert not (R / 'replay/summary.json').exists(), 'Replay already saved.'
    summary = []
    # Only the actual V4 proposal outputs, including the truncated one.
    for cid in ('112400', '188721101', '55384096', '52547606'):
        origin = V4 / 'runs' / cid / 'P'
        out = R / 'replay' / cid
        out.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origin / 'raw-response.txt', out / 'raw-response.txt')
        m, t, law, sm = inputs(cid)
        meta = read(origin / 'run.json')
        meta['offline_replay'] = True
        result = finish_attempt(meta, out, 'P', m, t, law, allow_legacy=True)
        if result['prediction'] is not None:
            imp, checks = read(out / 'import.json'), read(out / 'checks-full.json')
            text, sc, intermediate = final_task(cid, 'C', result['prediction'], imp, checks)
            (out / 'C-prompt-not-submitted.txt').write_text(text)
            save(out / 'C-schema.json', sc)
            save(out / 'C-intermediate.json', intermediate)
        summary.append({'case_id': cid, 'run_status': result['run_status'], 'prediction_present': result['prediction'] is not None,
                        'raw_sha256': hf(out / 'raw-response.txt'), 'origin': str(origin),
                        'model_calls': 0, 'C_prompt_submitted': False})
    save(R / 'replay/summary.json', summary)


def verify_preservation():
    before = read(R / 'registration.json')['old_files']
    changed = [p for p, sha in before.items() if not Path(p).is_file() or hf(p) != sha]
    result = {'passed': not changed, 'files_checked': len(before), 'changed': changed}
    save(R / 'preservation-after.json', result)
    if changed:
        raise ValueError('OLD_ARTIFACT_CHANGED')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('prepare', 'replay', 'verify_preservation'))
    print(json.dumps(globals()[parser.parse_args().command](), ensure_ascii=False))
