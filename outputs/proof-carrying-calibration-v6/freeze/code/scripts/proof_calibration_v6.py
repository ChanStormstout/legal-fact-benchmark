"""Five-case source-reference continuation. No model calls or legal approval here.

Web responses are captured unchanged. This entry only parses, checks provenance,
and executes explicitly reviewed research snapshots through the independent CLI.
"""
import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.contracts import read_json, write_once, byte_hash, content_hash
from legal_bench.proof_carrying.realcase_contracts import schemas, validate
from legal_bench.proof_carrying.realcase_grounding_v4 import source_match, step_semantic_hash
from legal_bench.proof_carrying.realcase_engine import propose

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'outputs/proof-carrying-calibration-v5'
OUT = ROOT / 'outputs/proof-carrying-calibration-v6'
IDS = ('840688', '161859415', '74028', '522414', '1144022')


def ingest(cid):
    dest = OUT / 'cases' / cid
    capture = read_json(dest / 'captured-response.json')
    assert not capture['generating'], 'Do not finalize a streaming answer'
    blocks = capture['code']
    sources = {s['id']: s for s in read_json(OLD / 'cases' / cid / 'allowed-source.json')['segments']}
    result = {'status': 'FORMAT_ERROR', 'answer': None, 'content_changes': [],
              'extraction': 'DOM code-block text; code fence/display chrome removed, no semantic edit'}
    try:
        if len(blocks) != 1:
            raise ValueError('Expected one complete JSON block; do not guess missing output')
        answer = json.loads(blocks[0])
        # A complete JSON value is retained even if the batch contract fails.
        # It remains qualitative source-review material, never a successful run.
        write_once(dest / 'reference-content.json', answer)
        validate(answer, schemas('reference'))
        rows = []
        for index, judgment in enumerate(answer['judgments'], 1):
            rows.append({'index': index, 'predicate': judgment['predicate'],
                         'location': source_match(judgment, sources),
                         'opposition_addresses_exist': all(r in sources for r in judgment['opposition_refs']),
                         'semantic_review': 'PENDING'})
        result.update(status='PARSED', answer='reference.json', records=rows)
        write_once(dest / 'reference.json', answer)
    except (ValueError, TypeError, KeyError) as exc:
        result['error'] = str(exc)
    write_once(dest / 'import.json', result)
    (dest / 'raw-answer.txt').write_text('\n\n'.join(blocks))
    run = read_json(dest / 'run.json')
    run.update(status=result['status'], answer=result['answer'],
               observed_complete_at=capture['observed_at'], url=capture['url'],
               input_bytes=(dest / 'task.txt').stat().st_size,
               output_characters=sum(map(len, blocks)), exact_tokens=None,
               exact_inference_seconds=None, input_read_completeness='ATTACHMENT_COMPLETE; model internal reading not fully observable')
    (dest / 'run.json').write_text(json.dumps(run, ensure_ascii=False, indent=2) + '\n')
    return {k: v for k, v in result.items() if k != 'records'} | {
        'case_id': cid, 'records': len(result.get('records', [])),
        'location_issues': [r['index'] for r in result.get('records', []) if r['location']['error']]}


def accepted(record, basis):
    return {'subject_hash': content_hash(record), 'decision': 'ACCEPT_RESEARCH',
            'actor': 'MODEL_ASSISTED_SOURCE_REVIEW', 'qualified_legal_approval': False, 'basis': basis}


def audit(cid):
    """Local address audit also retains readable contract-failing responses.

    No row is removed, repaired or promoted to a successful batch answer.
    """
    dest = OUT / 'cases' / cid
    answer = read_json(dest / 'reference-content.json')
    sources = {s['id']: s for s in read_json(OLD / 'cases' / cid / 'allowed-source.json')['segments']}
    rows = []
    for i, record in enumerate(answer['judgments'], 1):
        error = None
        try: validate(record, schemas('reference')['properties']['judgments']['items'])
        except (ValueError, TypeError, KeyError) as exc: error = str(exc)
        rows.append({'index': i, 'predicate': record.get('predicate'), 'record_contract_error': error,
                     'location': source_match(record, sources),
                     'opposition_addresses_exist': all(r in sources for r in record.get('opposition_refs', [])),
                     'semantic_verified': False})
    result = {'batch_contract_status': read_json(dest / 'import.json')['status'], 'rows': rows,
              'use': 'Local qualitative source-review aid, not repaired annotation or formal batch success'}
    write_once(dest / 'reference-audit.json', result)
    return {'case_id': cid, 'records': len(rows), 'batch_status': result['batch_contract_status'],
            'location_issues': [r['index'] for r in rows if r['location']['error']],
            'record_contract_issues': [r['index'] for r in rows if r['record_contract_error']]}


def reviewed_record(record):
    record['review'] = accepted(record, 'Explicit case source-review.json decision; no legal approval.')
    return record


def build(cid):
    dest = OUT / 'cases' / cid
    spec = read_json(dest / 'source-review.json')
    assert spec['review_completed'] and spec['legal_approval'] is False
    reference = read_json(dest / 'reference-content.json')
    facts = read_json(OLD / 'cases' / cid / 'facts-draft.json')
    original_rules = read_json(OLD / 'cases' / cid / 'rules-draft.json')
    scope = read_json(OLD / 'cases' / cid / 'reconstruction-scope.json')
    source = read_json(OLD / 'cases' / cid / 'allowed-source.json')
    prep = read_json(OLD / 'cases' / cid / 'preparation-review.json')
    entities = {e['id']: copy.deepcopy(e) for e in facts['entities']}
    for e in prep['entity_source_review']:
        entities[e['entity']]['refs'] = e['refs']
    disposition = set(scope['comparison_only_disposition_refs'])
    base = {'case_id': cid, 'stage': scope['stage'], 'jurisdiction': 'India; this judgment-stage reconstruction',
            'sources': {s['id']: {'text': s['text'], 'document': cid, 'url': scope['url'],
                                  'role': 'DISPOSITION_ONLY' if s['id'] in disposition else 'JUDGMENT_TEXT',
                                  'original_line': s['original_line']} for s in source['segments']},
            'documents': [{'path': '../../../../proof-carrying-calibration-v5/cases/' + cid + '/source.json',
                           'sha256': byte_hash(OLD / 'cases' / cid / 'source.json')}],
            'entities': entities, 'premises': {p['id']: copy.deepcopy(p) for p in facts['premises']},
            'rules': {}, 'reviews': {'premises': {}, 'rules': {}}, 'scope_reviews': {},
            'formal_approval': None, 'policy_version': 'CALIBRATION_V6',
            'independent_reference_sha256': byte_hash(dest / 'reference-content.json'),
            'independent_reference_contract_status': read_json(dest / 'import.json')['status'],
            'decision_record_hash': byte_hash(dest / 'source-review.json')}
    for pid, review in spec['premise_decisions'].items():
        p = base['premises'][pid]
        if review['decision'] == 'ACCEPT_RESEARCH':
            assert not source_match(p, base['sources'])['error']
            base['reviews']['premises'][pid] = accepted(p, review['basis'])
        else:
            base['reviews']['premises'][pid] = {'subject_hash': content_hash(p), **review}
    prop = {'steps': [], 'requests': [], 'counterarguments': reference['decisive_counterarguments'],
            'gaps': spec['remaining_gaps']}
    for item in spec['chains']:
        rule = copy.deepcopy(next(r for r in original_rules['rules'] if r['id'] == item['rule_id']))
        rule['version'] = 2
        rule.update(description=item['translation'], conclusion_text=item['translation'],
                    conclusion_predicate=item['predicate'], origin='RESEARCH_TRANSLATION')
        # Slots describe what recorded premises were used. They do not turn open
        # legal evaluation into a sufficient conjunction or infer truth from votes.
        rule['slots'] = []
        inputs = []
        for pid in item['premises']:
            p = base['premises'][pid]
            assert p['statement_status'] not in ('LEGAL_RULE', 'TARGET_DISPOSITION')
            assert base['reviews']['premises'][pid]['decision'] == 'ACCEPT_RESEARCH'
            slot = 'record_' + pid
            rule['slots'].append({'name': slot, 'predicate': p['predicate'],
                                  'description': 'Recorded attributed premise, not independently proved event: ' + p['text'],
                                  'expected': p['state'], 'allowed_statuses': [p['statement_status']],
                                  'required_roles': ['subject', 'opponent', 'property'], 'time_required': False})
            inputs.append({'slot': slot, 'kind': 'PREMISE', 'id': pid})
        for prior_id in item.get('depends_on', []):
            prior_step = next(s for s in prop['steps'] if s['id'] == prior_id)
            prior_rule = base['rules'][prior_step['rule_ref']]
            slot = 'prior_' + prior_id
            rule['slots'].append({'name': slot, 'predicate': prior_rule['conclusion_predicate'],
                                  'description': 'Earlier attributed conclusion with all its assumptions retained.',
                                  'expected': 'TRUE', 'allowed_statuses': [],
                                  'required_roles': ['subject', 'opponent', 'property'], 'time_required': False})
            inputs.append({'slot': slot, 'kind': 'STEP', 'id': prior_id})
        key = rule['id'] + '@2'
        base['rules'][key] = rule
        base['reviews']['rules'][key] = accepted(rule, item['basis'])
        base['scope_reviews'][key] = {'subject_hash': content_hash(rule), 'jurisdiction_compatible': True,
                                    'stage_compatible': True, 'basis': item['scope']}
        step = {'id': item['step_id'], 'rule_ref': key,
                'bindings': copy.deepcopy(facts['premises'][0]['bindings']), 'time_scope': None,
                'inputs': inputs, 'proposed_state': 'TRUE',
                'explanation': item['basis'] + ' Court evaluation remains an explicit assumption, not independent calculation.'}
        prop['steps'].append(step)
        prop['requests'].append({'id': 'Q-' + item['step_id'], 'step_id': item['step_id'],
                                 'predicate': rule['conclusion_predicate'], 'text': rule['conclusion_text'],
                                 'proposed_state': 'TRUE'})
    for track in ('engine-only', 'attributed-reconstruction'):
        snap = copy.deepcopy(base)
        snap['snapshot_id'] = cid + '-CAL-V6-' + track
        snap['court_assessments'] = {}
        if track == 'attributed-reconstruction':
            for item, step in zip(spec['chains'], prop['steps']):
                rule = snap['rules'][step['rule_ref']]
                refs = item['assessment_refs']
                assert refs and not disposition.intersection(refs)
                assessment = {'id': 'CA-' + cid + '-' + step['id'], 'case_id': cid,
                    'stage': snap['stage'], 'step_semantic_hash': step_semantic_hash(step),
                    'rule_ref': step['rule_ref'], 'rule_hash': content_hash(rule),
                    'predicate': rule['conclusion_predicate'], 'bindings': step['bindings'], 'time_scope': None,
                    'statement_status': 'TARGET_COURT_FINDING', 'state': 'TRUE', 'refs': refs,
                    'quote': '\n'.join(snap['sources'][r]['text'] for r in refs),
                    'scope': item['scope'], 'speaker': item['speaker'],
                    'role': 'Attributed judicial evaluation only; separate opinion is not a unified holding.'}
                snap['court_assessments'][step['id']] = reviewed_record(assessment)
        folder = dest / track
        write_once(folder / 'snapshot.json', snap)
        write_once(folder / 'proposal.json', prop)
        write_once(folder / 'certificate.json', propose(snap, prop))
        write_once(folder / 'manifest.json', {'snapshots': {snap['snapshot_id']: {
            'path': 'snapshot.json', 'sha256': byte_hash(folder / 'snapshot.json')}}})
        process = subprocess.run([sys.executable, str(ROOT / 'scripts/check_realcase_certificate_v4.py'),
                                  str(folder / 'certificate.json'), '--manifest', str(folder / 'manifest.json')],
                                 cwd=ROOT, text=True, capture_output=True)
        result = json.loads(process.stdout)
        write_once(folder / 'checker-result.json', result)
        write_once(folder / 'process.json', {'returncode': process.returncode, 'stderr': process.stderr})
        assert result['status'] == 'COMPLETED', result
    write_once(dest / 'lineage.json', {'parent': str((OLD / 'cases' / cid).relative_to(ROOT)),
        'old_facts_unchanged': True, 'rules_changed': 'Version 2 explicit attributed reconstruction slots and proposition boundaries; OPEN_TEXT retained.',
        'proposal_origin': 'SOURCE_REVIEWED_MAINTAINER_ASSEMBLY_NOT_NEW_WEB_DERIVATION',
        'reference_used_for_research_acceptance': True,
        'not_independent_model_accuracy_experiment': True, 'legal_approval': False})


def verify():
    config = read_json(OUT / 'freeze/config.json')
    registration = read_json(OUT / 'registration.json')
    failures = []
    for p, h in registration['old_files'].items():
        if byte_hash(ROOT / p) != h: failures.append('OLD_CHANGED:' + p)
    for p, h in config['method_hashes'].items():
        if byte_hash(ROOT / p) != h: failures.append('CHECKER_CHANGED:' + p)
    for cid in IDS:
        dest = OUT / 'cases' / cid
        if byte_hash(dest / 'task.txt') != config['materials'][cid]['task_sha256']:
            failures.append('TASK_CHANGED:' + cid)
        source = read_json(OLD / 'cases' / cid / 'allowed-source.json')
        task = (dest / 'task.txt').read_text()
        for s in source['segments']:
            if '[' + s['id'] + ']\n' + s['text'] not in task: failures.append('NOT_DELIVERED:' + s['id'])
    result = {'status': 'PASS' if not failures else 'FAIL', 'failures': failures,
              'old_files_preserved': len(registration['old_files']),
              'scope': 'Task delivery and historical/code hashes; not legal correctness'}
    write_once(OUT / 'delivery-validation.json', result)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['ingest', 'audit', 'build', 'verify'])
    p.add_argument('--case', choices=IDS)
    args = p.parse_args()
    if args.command == 'verify': print(json.dumps(verify(), indent=2))
    else:
        for cid in ([args.case] if args.case else IDS):
            print(json.dumps({'ingest': ingest, 'audit': audit, 'build': build}[args.command](cid), indent=2))
