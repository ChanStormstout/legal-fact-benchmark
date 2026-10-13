"""Concentrated development acceptance: four parts, three source reviews/finals.

Reuses the validated inline adapter/checker. No training, old-queue dispatch,
reference-answer inputs, retries or publication. Web review is a separate GPT-6
model judgment, not human gold. All failed prototypes remain immutable.
"""
import argparse
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from legal_bench.proof_carrying import source_repair_v20_6_6 as repair
from legal_bench.proof_carrying import inline_roles_v20_6_6 as inline
from legal_bench.proof_carrying import local_pipeline_v19_8 as core
from legal_bench.proof_carrying import shared_sources_v20_3 as shared
from legal_bench.proof_carrying import evidence_binding_gate_v20_5 as binding
from legal_bench.proof_carrying import declared_references_v20_4 as addresses
from legal_bench.proof_carrying.artifact_state_v20_2 import immutable, byte_hash, freeze_files, verify_files
from legal_bench.proof_carrying.provider_runtime_v20_6_1 import Runner
from legal_bench.proof_carrying.repetition_v20_6 import duplicates

PARENT = ROOT / 'outputs/proof-source-repair-v20-6'
OUT = PARENT / 'completion-01'
PREP = PARENT / 'source-scope-06'
OLD = ROOT / 'outputs/proof-evidence-binding-rerun-v20-5'
ORDER = [('1954254', 'P02'), ('1954254', 'P01'), ('569555', 'P01'), ('1187427', 'P01')]


def read(path):
    return json.loads(Path(path).read_text())


def save_text(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() != value:
        raise ValueError('IMMUTABLE_TEXT_CHANGED:' + str(path))
    if not path.exists():
        path.write_text(value)


def prior_cost():
    rows = []
    for path in PARENT.glob('**/run.json'):
        if OUT in path.parents:
            continue
        row = read(path)
        if str(row.get('runtime', '')).startswith('TOGETHER') and row.get('run_status') not in ('HTTP_FAILURE', 'COST_CAP_NOT_DISPATCHED'):
            rows.append((str(path.relative_to(ROOT)), row.get('listed_price_token_cost_usd', row.get('reserved_cost_upper_bound_usd', 0))))
    return rows


def prepare():
    costs = prior_cost()
    immutable(OUT / 'plan.json', {
        'cases': ['1954254', '569555', '1187427'], 'tasks': ORDER,
        'maximum_total_cost_usd': 0.50, 'prior_cost_or_conservative_bound_usd': sum(v for _, v in costs),
        'prior_cost_receipts': costs, 'maximum_calls': 7, 'attempts_per_task': 1,
        'part_tokens': 16384, 'final_tokens': 16384,
        'source_reviewer': 'GPT-6 via ChatGPT Web, visible model selection; not human gold',
        'generation_model': 'Qwen/Qwen3.5-9B serverless FP8; not the local 4-bit snapshot',
        'source_input_truncated': False, 'old_queue_stays_paused': True,
        'training': False, 'commit_or_push': False, 'reference_used': False,
        'success_requires': 'Complete final answers plus concentrated whole-case source audit; checker acceptance alone is insufficient.'})
    prepared = [str((OUT / 'plan.json').relative_to(ROOT))]
    for cid, part in ORDER:
        task = read(PREP / 'preparation' / cid / part / 'task.json')
        immutable(OUT / 'preparation' / cid / part / 'task.json', task)
        prepared.append(str((OUT / 'preparation' / cid / part / 'task.json').relative_to(ROOT)))
    manifest = freeze_files(ROOT, OUT, ['scripts/proof_source_repair_completion_v20_6.py'], prepared)
    immutable(OUT / 'freeze/protocol.json', manifest)
    print('PREPARED 4 parts and 3 final calls; prior cost/bound', sum(v for _, v in costs), flush=True)


def runner():
    plan = read(OUT / 'plan.json')
    return Runner(out=OUT, maximum_cost_usd=plan['maximum_total_cost_usd'] - plan['prior_cost_or_conservative_bound_usd'])


def generate():
    verify_files(ROOT, read(OUT / 'freeze/protocol.json'))
    client = runner()
    for cid, part in ORDER:
        task = read(OUT / 'preparation' / cid / part / 'task.json')
        dest = OUT / 'local' / cid / part
        meta = client.run(task['prompt'], task['schema'], dest / 'repair', 16384, 900)
        if meta['run_status'] != 'OK':
            raise ValueError('PART_GENERATION_FAILED:' + cid + '/' + part + '/' + meta['run_status'])
        packed = read(dest / 'repair/parsed.json')
        raw = inline.expand(packed, task)
        audit = addresses.audit(shared.pack(raw), binding.generation_schema(task['original_schema'], task['case'], task['rules']))
        repeated = duplicates(packed)
        if audit['violations'] or repeated:
            raise ValueError('PART_STRUCTURAL_REJECTION:' + cid + '/' + part)
        immutable(dest / 'replacement.json', raw)
        immutable(dest / 'transport-check.json', {'references': audit, 'duplicates': repeated, 'local_addresses_assigned_by': 'PROGRAM'})
        immutable(dest / 'critique-task.json', repair.critique_task(task['case'], task['rules'], raw))
        print('PART_READY', cid, part, len(raw['analyses']), 'analyzed units', flush=True)
    for cid in read(OUT / 'plan.json')['cases']:
        reviews = {}
        rules = []
        for case_id, part in ORDER:
            if case_id != cid:
                continue
            t = read(OUT / 'local' / cid / part / 'critique-task.json')
            reviews[part] = {key: {k: v for k, v in row.items() if k != 'aliases'} for key, row in t['claims'].items()}
            rules.extend(read(OUT / 'preparation' / cid / part / 'task.json')['rules'])
        case = read(OUT / 'preparation' / cid / next(p for c, p in ORDER if c == cid) / 'task.json')['case']
        contracts = [{'rule': r['id'], 'premises': [{
            'id': p['id'], 'text': p['text'], 'variables': p['variables'],
            'input_contract': p['input_contract']} for p in r['premises']]} for r in repair.model_rules(rules)]
        # Full original source, exact declarations and contracts are supplied;
        # aliases/duplicate source enums are transport details, not source cuts.
        prompt = (
            'Independently verify EVERY declaration below against the COMPLETE judgment. '
            'This is a research development review, not legal advice or human gold. '
            'Check identities, dates/events, quantities/units, attribution/stage, direction, '
            'and the EXACT fixed premise scope. An expected rule precondition is not an observed truth. '
            'A quoted allegation is not an adopted finding. A hypothetical or legal prerequisite '
            'does not prove it occurred. Contested first actual knowledge is not an established date. '
            'A legal term is not a person. An absent optional document must not fabricate an identity. '
            'SUPPORTED requires relevant source text for the complete particular claim. '
            'UNSUPPORTED requires a demonstrable semantic mismatch; otherwise UNRESOLVED. '
            'A correct opposing proposition can be SUPPORTED without making the main premise TRUE. '
            'For PREMISE_BASIS assess the entire supplied fixed proposition, not a nearby question '
            'or a convenient true component. Read beyond candidate citations. '
            'Return ONLY one JSON object with parts keyed by the supplied part IDs. Each part must '
            'contain verdicts keyed by EVERY supplied D identifier, each {"label":'
            '"SUPPORTED|UNSUPPORTED|UNRESOLVED","refs":["SRC:n"],"reason":"specific short reason"}, '
            'and coverage_limits:[] (or up to 8 actual source limitations). '
            'Use SRC source addresses, not IK IDs, in verdict refs. SUPPORTED and UNSUPPORTED '
            'need at least one nonblank relevant ref. No omissions, no replacement facts, no prose outside JSON. '
            'Keep reasons within 240 characters; usually a short sentence suffices. '
            '\nFIXED PREMISES AND ROLE CONTRACTS:\n' + repair.compact(contracts) +
            '\nEXACT DECLARATIONS BY PART:\n' + repair.compact(reviews) +
            '\nCOMPLETE ALLOWED JUDGMENT:\n' + repair.sources(case))
        save_text(OUT / 'web-review' / cid / 'prompt.txt', prompt)
        immutable(OUT / 'web-review' / cid / 'input.json', {
            'prompt_sha256': byte_hash(OUT / 'web-review' / cid / 'prompt.txt'),
            'source_sha256': repair.digest(case['segments']),
            'parts': {p: list(v) for p, v in reviews.items()}, 'reference_used': False,
            'source_input_truncated': False, 'reviewer': 'GPT-6 ChatGPT Web'})
        print('WEB_REVIEW_READY', cid, len(prompt), {p: len(v) for p, v in reviews.items()}, flush=True)


def apply():
    verify_files(ROOT, read(OUT / 'freeze/protocol.json'))
    for cid in read(OUT / 'plan.json')['cases']:
        verdict = read(OUT / 'web-review' / cid / 'parsed.json')
        applied = []
        all_rules = None
        for case_id, part in ORDER:
            if case_id != cid:
                continue
            task = read(OUT / 'preparation' / cid / part / 'task.json')
            dest = OUT / 'local' / cid / part
            result = repair.apply_critique(task['case'], task['rules'], read(dest / 'replacement.json'),
                read(dest / 'critique-task.json'), verdict['parts'][part])
            result['reviewer'] = 'GPT-6 ChatGPT Web separate source review; model-generated, not human gold'
            immutable(dest / 'application.json', result)
            applied.append((part, result))
            case = task['case']
            all_rules, _ = repair.corrected_rules(read(OLD / 'preparation' / cid / part / 'fixture.json')['rules'])
        selected = {r['id'] for c, p in ORDER if c == cid for r in read(OUT / 'preparation' / cid / p / 'task.json')['rules']}
        merged = repair.merge_applied(case, [r for r in all_rules if r['id'] in selected], applied)
        immutable(OUT / 'final' / cid / 'recomputed.json', merged)
        final = repair.final_task(case, all_rules, merged, applied)
        immutable(OUT / 'final' / cid / 'task.json', final)
        print('FINAL_READY', cid, {p: row['decision_counts'] for p, row in applied}, flush=True)


def finals():
    verify_files(ROOT, read(OUT / 'freeze/protocol.json'))
    client = runner()
    results = []
    for cid in read(OUT / 'plan.json')['cases']:
        task = read(OUT / 'final' / cid / 'task.json')
        dest = OUT / 'final' / cid
        meta = client.run(task['prompt'], task['schema'], dest / 'generation', 16384, 900)
        raw = (dest / 'generation/raw-response.txt').read_text() if (dest / 'generation/raw-response.txt').exists() else ''
        accepted = core.accept_final(task, raw, meta['run_status'])
        if accepted.get('answer') is not None and duplicates(accepted['answer']):
            accepted.update(answer=None, contract_status='FINAL_REPETITION_REJECTED')
        immutable(dest / 'formal-answer.json', accepted)
        results.append({'case_id': cid, 'run_status': meta['run_status'],
            'contract_status': accepted.get('contract_status'), 'answer_available': accepted.get('answer') is not None,
            'output_tokens': meta.get('output_tokens'), 'source_semantic_success': 'PENDING_WHOLE_CASE_AUDIT'})
        print('CASE_FINAL', results[-1], flush=True)
    immutable(OUT / 'run-summary.json', {'results': results, 'training': False, 'old_queue_stays_paused': True})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'generate', 'apply', 'finals'])
    action = parser.parse_args().action
    {'prepare': prepare, 'generate': generate, 'apply': apply, 'finals': finals}[action]()
