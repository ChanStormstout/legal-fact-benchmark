"""One immutable Guide 4 teaching run, no LLM calls, no legal approval invented."""
import argparse
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.contracts import certificate_schema, content_hash, digest, read_json, write_once
from legal_bench.proof_carrying.engine import propose
from legal_bench.proof_carrying.teaching import build, graph, patch_record, file_entry, proposition, review, source, validate_revision

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/proof-carrying-teaching-v1'


def independent(cert, store, out, current_snapshot=None):
    write_once(out / 'certificate.json', cert)
    cmd = [sys.executable, str(ROOT / 'scripts/check_legal_certificate.py'), str(out / 'certificate.json'), '--trust-root', str(store)]
    if current_snapshot:
        cmd += ['--current-snapshot', current_snapshot]
    proc = subprocess.run(cmd, text=True, capture_output=True, cwd=ROOT)
    write_once(out / 'invocation.json', {'argv': cmd, 'exit_code': proc.returncode, 'stderr': proc.stderr,
        'independent_process': True, 'new_model_calls': 0})
    (out / 'checker-stdout.txt').write_text(proc.stdout)
    value = json.loads(proc.stdout)
    write_once(out / 'checker_result.json', value)
    return value


def add_gate_fixture(store, s1):
    s = copy.deepcopy(s1); s['snapshot_id'] = 'GATE'
    for pid, val in [('LEFT', 'TRUE'), ('RIGHT', 'UNKNOWN'), ('EXCEPTION', 'FALSE')]:
        ref = 'synthetic-' + pid
        source(store, s, pid, 'Synthetic test assessment ' + pid + ': ' + val + '.\n', ref)
        p = proposition(pid, 'TEST_ASSESSMENT', [ref], assessment=val)
        review(p, s['reviews'], 'EXERCISE_FIXTURE'); s['propositions'][pid] = p
    write_once(store / 'snapshots/GATE.json', s)
    man = read_json(store / 'trust-manifest.json')
    man['snapshots']['GATE'] = file_entry(store, 'snapshots/GATE.json')
    # Separate manifest; existing trust manifest is not overwritten.
    write_once(store / 'gate-manifest.json', man)
    return s, man


def run_demo(out):
    out = Path(out)
    store = out / 'trusted'; store.mkdir(parents=True, exist_ok=False)
    s1, s2, registry, policy = build(store)
    write_once(out / 'schemas/certificate.json', certificate_schema())
    write_once(out / 'source_packet.json', {'case_id': s1['case_id'], 'origin': 'GUIDE_4_EXERCISE',
        'actual_judgment': False, 'documents': s1['documents'], 'sources': s1['sources'],
        'source_root': 'trusted', 'human_review': 'NOT_OBTAINED'})
    write_once(out / 'extracted_packet.json', {'provenance': 'DETERMINISTIC_SYNTHETIC_FIXTURE_NOT_LLM_EXTRACTION',
        'propositions': [{k:v for k,v in p.items() if k!='review_id'} for p in s1['propositions'].values()],
        'approval': 'PENDING_FOR_ANY_REAL_LEGAL_USE'})
    write_once(out / 'canonical_proposals.json', {'method': 'EXPLICIT_GUIDE_MAPPING_NOT_LEARNED',
        'mappings': [{'proposition_id':p['id'], 'predicate':p['predicate'], 'bindings':p['bindings'],
                      'mapping_status':'EXERCISE_SUPPLIED'} for p in s1['propositions'].values()]})
    write_once(out / 'reviewed_packet.json', {'snapshot_ref':'trusted/snapshots/S1.json',
        'review_policy':'TEACHING_ASSUMPTIONS_ONLY', 'qualified_legal_review': 'MISSING',
        'premise_policy_approval_for_real_judgments': 'MISSING'})
    write_once(out / 'approved_rules.json', {'production_approved_rules': [], 'demo_registry':'trusted/rule-registry.json',
        'missing':['qualified legal reviewer', 'real-case premise policy', 'actual authority/exception/burden approval']})
    write_once(out / 'typed_edges.json', graph(s1))
    c1 = propose(s1, registry, policy, ['P1', 'P2'])
    c2 = propose(s2, registry, policy, ['P4', 'P2'], certificate_id='C2')
    rows = []
    def run(name, cert, expected, root=store, current=None):
        result = independent(cert, root, out / 'runs' / name, current)
        rows.append({'id': name, 'expected': expected, 'observed': result['status'],
                     'matches_expected': result['status'] == expected, 'result_path': 'runs/'+name+'/checker_result.json',
                     'reason': result.get('reason') or next((r.get('reason') for r in result['requests'] if r.get('reason')), None)})
        return result
    run('S1-specific-mismatch', c1, 'CHECKED')
    run('S2-corrected-coverage', c2, 'CHECKED')
    run('S1-historical-reopen', c1, 'CHECKED')
    run('S1-as-current-S2', c1, 'INVALID', current='S2')
    for name, claim in [('no-other-authorization', 'NO_AUTHORIZATION_EXISTS'), ('final-liability', 'FINAL_LIABILITY')]:
        c = copy.deepcopy(c1); c['requests'][0]['claim'] = claim
        run(name, c, 'INCOMPLETE')
    c = copy.deepcopy(c1); c['steps'][0]['premise_ids'] = ['P1']; run('missing-premise', c, 'INCOMPLETE')
    c = copy.deepcopy(c1); c['steps'][0]['bindings']['property'] = 'Parcel_Q'; run('wrong-parcel', c, 'INVALID')
    c = copy.deepcopy(c1); c['steps'][0]['proposed_result'] = 'TRUE'; run('false-result-claim', c, 'INVALID')
    c = copy.deepcopy(c1); c['steps'][0]['depends_on'] = ['T1']; run('circular-dependency', c, 'INVALID')
    c = copy.deepcopy(c1); c['steps'][0]['rule_ref'] = 'COVERAGE_DEMO@99'; run('missing-rule-version', c, 'INCOMPLETE')
    c = copy.deepcopy(c1); c['steps'][0]['checker_status'] = 'CHECKED'; run('self-certified-field', c, 'INVALID')
    c = copy.deepcopy(c1); c['requests'] = []; run('empty-answer', c, 'INVALID')
    c = copy.deepcopy(c1); c['requests'].append(copy.deepcopy(c['requests'][0])); run('duplicate-answer', c, 'INVALID')
    # Variants are separate, deliberately corrupted fixture snapshots. No old
    # packet or already checked snapshot is edited by a mutation.
    for name in ('assertion-as-finding', 'wrong-stage', 'unapproved-rule', 'semantic-edit-without-review',
                 'source-changed', 'locator-changed', 'unresolved-source', 'rule-changed-after-freeze'):
        variant = out / 'mutation-inputs' / name
        shutil.copytree(store, variant)
        s, reg = copy.deepcopy(s1), copy.deepcopy(registry)
        if name == 'assertion-as-finding':
            s['propositions']['P1']['statement_status'] = 'PARTY_CLAIM'
            review(s['propositions']['P1'], s['reviews'], 'EXERCISE_FIXTURE')
        elif name == 'wrong-stage':
            s['stage_id'] = 'MERITS'
        elif name == 'unapproved-rule':
            reg['rules']['COVERAGE_DEMO@1']['status'] = 'PENDING'
        elif name == 'semantic-edit-without-review':
            s['propositions']['P1']['interval'] = ['2026-10-12', '2026-10-13']
        elif name == 'source-changed':
            (variant / 'documents/E1.txt').write_text('Corrupted text, not the frozen source.\n')
        elif name == 'locator-changed':
            s['sources']['demo_message_1']['start'] = 1
        elif name == 'unresolved-source':
            del s['sources']['demo_message_1']
        elif name == 'rule-changed-after-freeze':
            (variant / 'rule-registry.json').write_text('{}')
        if name != 'rule-changed-after-freeze':
            (variant / 'rule-registry.json').write_text(json.dumps(reg, indent=2)+'\n')
        (variant / 'snapshots/S1.json').write_text(json.dumps(s, indent=2)+'\n')
        manifest = read_json(variant / 'trust-manifest.json')
        manifest['snapshots']['S1'] = file_entry(variant, 'snapshots/S1.json')
        if name != 'rule-changed-after-freeze':
            manifest['registry'] = file_entry(variant, 'rule-registry.json')
        (variant / 'trust-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
        c = copy.deepcopy(c1); c['snapshot_sha256'] = content_hash(s); c['registry_sha256'] = content_hash(reg)
        run(name, c, 'INCOMPLETE' if name == 'unresolved-source' else 'INVALID', root=variant)
    # Bounded expression gates: separate teaching fixtures, not a second case.
    gate_store = out / 'gate-fixture'; shutil.copytree(store, gate_store)
    gs, gm = add_gate_fixture(gate_store, s1)
    (gate_store / 'trust-manifest.json').write_text(json.dumps(gm, indent=2)+'\n')
    for rule, name, expected in [('AND_GATE_DEMO@1', 'and-unknown-input', 'CONDITIONAL'),
                                  ('OR_GATE_DEMO@1', 'or-independent-branch', 'CHECKED')]:
        cert = propose(gs, registry, policy, ['LEFT','RIGHT','EXCEPTION'], rule_ref=rule)
        run(name, cert, expected, root=gate_store)
    for state, name in [('UNKNOWN', 'exception-unknown'), ('CONFLICTED', 'exception-conflicted'), ('TRUE', 'exception-established')]:
        v = out / 'mutation-inputs' / name; shutil.copytree(gate_store, v)
        snap = copy.deepcopy(gs); snap['propositions']['EXCEPTION']['assessment'] = state
        review(snap['propositions']['EXCEPTION'], snap['reviews'], 'EXERCISE_FIXTURE')
        (v / 'snapshots/GATE.json').write_text(json.dumps(snap, indent=2)+'\n')
        man = read_json(v / 'trust-manifest.json'); man['snapshots']['GATE'] = file_entry(v, 'snapshots/GATE.json')
        (v / 'trust-manifest.json').write_text(json.dumps(man, indent=2)+'\n')
        cert = propose(snap, registry, policy, ['LEFT','RIGHT','EXCEPTION'], rule_ref='OR_GATE_DEMO@1')
        run(name, cert, 'CHECKED' if state == 'TRUE' else 'CONDITIONAL', root=v)
    patch = patch_record(s1,s2)
    write_once(out / 'patch.json', patch)
    write_once(out / 'patch-validation.json', validate_revision(s1,s2,patch))
    write_once(out / 'dependency-index.json', {
        'S1': {'C1': ['P1','P2','demo_message_1','demo_entry_record_2','COVERAGE_DEMO@1']},
        'S2': {'C2': ['P4','P2','demo_message_3','demo_entry_record_2','COVERAGE_DEMO@1']},
        'old_premises_unchanged': all(s1['propositions'][k] == s2['propositions'][k] for k in ('P1','P2')),
        'current_snapshot':'S2','old_current_pointer_stale':True,'old_historical_proof_invalidated':False})
    write_once(out / 'mutation-report.json', {'rows':rows,'all_expected':all(r['matches_expected'] for r in rows),
        'interpretation':'Synthetic mechanics and curated rejection only; not legal accuracy.'})
    from legal_bench.proof_carrying.spectral import examples
    try:
        numeric = examples()
        write_once(out / 'spectral-exercises.json', numeric)
    except ImportError:
        write_once(out / 'spectral-exercises.json', {'status':'UNAVAILABLE_NUMPY',
            'checker_completed_independently':True,'instruction':'Use existing bundled NumPy runtime; no automatic install.'})
    write_once(out / 'approval-gaps.json', {'human_legal_approval':False,
        'teaching_fixture_status':'EXERCISE_SUPPLIED_NOT_HUMAN_GOLD',
        'real_case_reconstruction':'NOT_RUN',
        'missing':['named premise-policy reviewer','qualified legal rule approval','actual judgment teaching packet'],
        'not_implemented':['general legal burden shifts','open-text legal tests','cross-rule derived-premise chaining'],
        'unsupported_is_not_negative':True})
    return rows


def freeze():
    assert (OUT / 'registration.json').exists(), 'Register before writing experiment files.'
    files = list((ROOT / 'legal_bench/proof_carrying').glob('*.py'))
    files += [ROOT / s for s in ('scripts/proof_teaching_v1.py','scripts/check_legal_certificate.py','tests/test_proof_carrying_v1.py',
        'legal_bench/irac_application/contract_v5.py','legal_bench/irac_application/aligned_logic.py',
        'legal_bench/irac_application/aligned_v2_runtime.py','legal_bench/rules_verdict_v1/contracts.py')]
    hashes = {str(p.relative_to(ROOT)):digest(p.read_text()) for p in files}
    for p in files:
        dest = OUT / 'freeze/code' / p.relative_to(ROOT); dest.parent.mkdir(parents=True,exist_ok=True)
        assert not dest.exists(); shutil.copyfile(p,dest)
    write_once(OUT / 'freeze.json', {'method_hashes':hashes,'mode':'SYNTHETIC_TEACHING',
        'calls':0,'legal_approval':'NOT_OBTAINED','stop':'one teaching run and deterministic acceptance; no cohort expansion'})


def main():
    p=argparse.ArgumentParser(); p.add_argument('action',choices=['freeze','run','replay'])
    p.add_argument('--output'); args=p.parse_args()
    if args.action=='freeze':
        freeze(); return
    f=read_json(OUT/'freeze.json')
    assert all(digest((ROOT/k).read_text())==v for k,v in f['method_hashes'].items()), 'FROZEN_CODE_CHANGED'
    target = OUT
    if args.action == 'replay':
        if not args.output:
            p.error('replay requires a new --output directory')
        target=Path(args.output).resolve()
        if target.exists():
            p.error('replay must not overwrite an existing directory')
    rows=run_demo(target)
    print(json.dumps({'status':'COMPLETE' if all(x['matches_expected'] for x in rows) else 'FAILED','checks':len(rows)}))


if __name__=='__main__':
    main()
