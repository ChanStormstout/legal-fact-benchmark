"""V6 real completion entry. Shared by generation and deterministic acceptance."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.irac_contract_v5 import inputs as old_inputs, read, save, hf, digest
from scripts.irac_contract_v5_run import delivery
from legal_bench.irac_application.semantic_v6 import process, validate_final
from legal_bench.irac_application.semantic_v6_tasks import prompt, schema

R = Path('outputs/irac-semantic-interface-v6')
CASES = ('112400', '188721101')
MAX_TOKENS = {'A': 3072, 'P': 4096, 'B': 3072}


def inputs(cid):
    if cid not in CASES:
        raise ValueError('OUTSIDE_TWO_APPROVED_CASES')
    return old_inputs(cid)


def finish_attempt(meta, out, stage, m, t, law):
    out = Path(out)
    result = {'case_id': m['case_id'], 'method': stage, 'run_status': meta['run_status'], 'prediction': None}
    if meta['run_status'] != 'OK':
        save(out / 'result.json', result)
        return result
    try:
        value = json.loads((out / 'raw-response.txt').read_text())
        if not meta.get('schema_mask_calls') and not meta.get('offline_replay'):
            raise ValueError('SCHEMA_CONSTRAINT_NOT_EFFECTIVE')
        if stage == 'P':
            imp, checks = process(value, t, m, law)
            save(out / 'import.json', imp)
            if not imp['usable']:
                raise ValueError(imp['status'])
            save(out / 'evidence-records.json', imp['records'])
            save(out / 'checks-full.json', checks)
            result.update(import_status=imp['status'], prediction=value,
                          audit_in_final_input=False, semantic_correctness_verified=False)
        else:
            validate_final(value, read(out / 'schema.json'), t)
            result.update(prediction=value, completeness='EACH_REQUEST_ONCE_WITH_ANALYSIS', semantic_correctness_verified=False)
    except (ValueError, KeyError, TypeError) as exc:
        result.update(run_status='FORMAT_ERROR', reason=str(exc), prediction=None)
    save(out / 'result.json', result)
    return result


def final_task(cid, proposal=None):
    m, t, law, sm = inputs(cid)
    inter = {} if proposal is None else {'proposal': proposal}
    return prompt('final', m, t, law, sm, inter), schema('final', m, t, law), inter


def execute_slot(runner, out, cid, stage, text, sc, remaining):
    """Exactly the same entry for real runs, tokenizer-independent fake tests."""
    m, t, law, sm = inputs(cid)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    save(out / 'delivery.json', delivery(text, m, law, sm))
    submitted = json.loads(text.split('INTERMEDIATE MATERIAL:\n\n', 1)[1].split('\n\nCOMPLETE ALLOWED CASE MATERIAL:', 1)[0])
    if stage == 'B':
        assert set(submitted) == {'proposal'}, 'B_RECEIVES_ONLY_RAW_P'
    else:
        assert submitted == {}
    save(out / 'intermediate.json', submitted)
    meta = runner.run(text, sc, out, max_tokens=MAX_TOKENS[stage], remaining_seconds=remaining, constraint_mode='FIXED')
    result = finish_attempt(meta, out, stage, m, t, law)
    return meta, result
