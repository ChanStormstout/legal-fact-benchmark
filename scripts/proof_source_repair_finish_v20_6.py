"""Finish the one bounded acceptance batch with explicit citation-set correction."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import proof_source_repair_completion_v20_6 as base
from legal_bench.proof_carrying.reference_set_normalization_v20_6 import normalize
from legal_bench.proof_carrying.schema_contract_v19_6 import loads, validate
from legal_bench.proof_carrying.artifact_state_v20_2 import freeze_files, verify_files


def complete_parts():
    manifest = freeze_files(ROOT, base.OUT / 'transport-normalization',
        ['scripts/proof_source_repair_finish_v20_6.py'],
        [(base.OUT / 'plan.json').relative_to(ROOT).as_posix()])
    base.immutable(base.OUT / 'transport-normalization/freeze/protocol.json', manifest)
    verify_files(ROOT, base.read(base.OUT / 'freeze/protocol.json'))
    client = base.runner()
    for cid, part in base.ORDER:
        task = base.read(base.OUT / 'preparation' / cid / part / 'task.json')
        dest = base.OUT / 'local' / cid / part
        if (dest / 'replacement.json').exists():
            continue
        # Never replay an already dispatched failed model call.
        if (dest / 'repair/run.json').exists():
            meta = base.read(dest / 'repair/run.json')
        else:
            meta = client.run(task['prompt'], task['schema'], dest / 'repair', 16384, 900)
        if meta['run_status'] != 'OK':
            if meta.get('finish_reason') != 'stop' or not meta.get('done_received'):
                raise ValueError('INCOMPLETE_GENERATION_NOT_NORMALIZABLE:' + cid + '/' + part)
            original = loads((dest / 'repair/raw-response.txt').read_text())
            packed, ledger = normalize(original)
            if not ledger:
                raise ValueError('FAILED_GENERATION_WITHOUT_ALLOWED_CITATION_CORRECTION')
            validate(packed, task['schema'])
            if base.duplicates(packed):
                raise ValueError('REPETITION_NOT_A_CITATION_SET_CORRECTION')
            base.immutable(dest / 'transport-normalized.json', packed)
            base.immutable(dest / 'normalization-ledger.json', {
                'original_raw_sha256': base.byte_hash(dest / 'repair/raw-response.txt'),
                'original_generation_status': meta['run_status'], 'changes': ledger,
                'schema_status': 'PASS_AFTER_EXACT_CITATION_SET_NORMALIZATION',
                'source_semantic_approval': False})
        else:
            packed = base.read(dest / 'repair/parsed.json')
        raw = base.inline.expand(packed, task)
        audit = base.addresses.audit(base.shared.pack(raw), base.binding.generation_schema(
            task['original_schema'], task['case'], task['rules']))
        if audit['violations'] or base.duplicates(packed):
            raise ValueError('NORMALIZED_TRANSPORT_STRUCTURAL_REJECTION')
        base.immutable(dest / 'replacement.json', raw)
        base.immutable(dest / 'transport-check.json', {'references': audit, 'duplicates': [],
            'local_addresses_assigned_by': 'PROGRAM', 'generation_status': meta['run_status'],
            'normalization_saved': (dest / 'normalization-ledger.json').exists()})
        base.immutable(dest / 'critique-task.json', base.repair.critique_task(task['case'], task['rules'], raw))
        print('PART_READY', cid, part, len(raw['analyses']), flush=True)


def web_reviews():
    for cid in base.read(base.OUT / 'plan.json')['cases']:
        reviews, rules = {}, []
        for case_id, part in base.ORDER:
            if case_id != cid:
                continue
            path = base.OUT / 'local' / cid / part / 'critique-task.json'
            if not path.exists():
                break
            task = base.read(path)
            reviews[part] = {key: {k: v for k, v in row.items() if k != 'aliases'}
                            for key, row in task['claims'].items()}
            t = base.read(base.OUT / 'preparation' / cid / part / 'task.json')
            rules.extend(t['rules'])
            case = t['case']
        else:
            contracts = [{'rule': r['id'], 'premises': [{
                'id': p['id'], 'text': p['text'], 'variables': p['variables'],
                'input_contract': p['input_contract']} for p in r['premises']]}
                for r in base.repair.model_rules(rules)]
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
                'A legal source address alone is not support. A correct opposing proposition can be '
                'SUPPORTED without making the main premise TRUE. For PREMISE_BASIS assess the entire '
                'supplied fixed proposition and its role bindings, not a nearby question or a convenient '
                'true component. Read beyond candidate citations. '
                'Return ONLY one JSON object with parts keyed by the supplied part IDs. Each part must '
                'contain verdicts keyed by EVERY supplied D identifier, each {"label":'
                '"SUPPORTED|UNSUPPORTED|UNRESOLVED","refs":["SRC:n"],"reason":"specific short reason"}, '
                'and coverage_limits:[] (or up to 8 actual source limitations). '
                'Use SRC source addresses, not IK IDs, in verdict refs. SUPPORTED and UNSUPPORTED '
                'need at least one nonblank relevant ref. No omissions, no replacement facts, no prose '
                'outside JSON. Keep reasons within 240 characters; a short sentence usually suffices. '
                '\nFIXED PREMISES AND ROLE CONTRACTS:\n' + base.repair.compact(contracts) +
                '\nEXACT DECLARATIONS BY PART:\n' + base.repair.compact(reviews) +
                '\nCOMPLETE ALLOWED JUDGMENT:\n' + base.repair.sources(case))
            dest = base.OUT / 'web-review' / cid
            base.save_text(dest / 'prompt.txt', prompt)
            base.immutable(dest / 'input.json', {'prompt_sha256': base.byte_hash(dest / 'prompt.txt'),
                'source_sha256': base.repair.digest(case['segments']), 'parts': {p: list(v) for p, v in reviews.items()},
                'reference_used': False, 'source_input_truncated': False, 'reviewer': 'GPT-6 ChatGPT Web'})
            print('WEB_REVIEW_READY', cid, len(prompt), {p: len(v) for p, v in reviews.items()}, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['parts', 'web', 'apply', 'finals'])
    action = parser.parse_args().action
    if action in ('apply', 'finals'):
        verify_files(ROOT, base.read(base.OUT / 'transport-normalization/freeze/protocol.json'))
    {'parts': complete_parts, 'web': web_reviews, 'apply': base.apply, 'finals': base.finals}[action]()
