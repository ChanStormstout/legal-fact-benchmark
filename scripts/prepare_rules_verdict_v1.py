"""Record a source-reviewed development cohort and explicit pre-decision slices.

Case-specific IDs below are dataset preparation, never inference exceptions.
Sources and original candidate order remain immutable.
"""
import json
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import build_view, write_new, digest
from legal_bench.rules_verdict_v1.runtime import SETTINGS

ROOT = Path('outputs/rules-verdict-v1')
SOURCES = {
    '661475': 'outputs/development-20-single-pass-v1/sources/661475.json',
    '1134266': 'outputs/new-10-pattern-matching-v1/sources/1134266.json',
    '69305': 'outputs/local-qwen-pattern-eval-v3/sources/69305.json',
}


def prepare():
    registered = json.loads(Path('docs/repository-artifacts.json').read_text())['artifact_roots']
    if str(ROOT) not in registered:
        raise ValueError('Output root must be explicitly registered')
    queue_path = Path('outputs/benchmark-pilot-v04/sampling-v1/candidate-queue.json')
    queue = json.loads(queue_path.read_text())
    ranks = {c['case_id']: i for i, c in enumerate(queue['cases'])}
    entries = []
    for cid in sorted(SOURCES, key=lambda c: ranks[c]):
        path = Path(SOURCES[cid])
        source = json.loads(path.read_text())
        selected = []
        for segment in source['segments']:
            sid, text = segment['id'], segment['text']
            allowed = (cid == '661475' and sid.startswith('p0001')) or (
                cid == '1134266' and 'p0001.s003' <= sid <= 'p0004.s003') or (
                cid == '69305' and 'p0003.s003' <= sid <= 'p0004.s004')
            if allowed:
                selected.append({'segment_id': sid, 'reason': 'FACTS_PRIOR_FINDINGS_OR_PARTY_ARGUMENT_BEFORE_TARGET_COURT_ANALYSIS'})
            if cid == '661475' and sid == 'p0002.s002':
                end = text.index('with his permission.') + len('with his permission.')
                selected.append({'segment_id': sid, 'end': end, 'reason': 'COUNSEL_ARGUMENT_ONLY_BEFORE_TARGET_COURT_RESPONSE'})
        view = build_view(source, selected, 'APPEAL_INPUT_RECONSTRUCTED_FROM_JUDGMENT_NOT_TRUE_PRETRIAL_RECORD')
        relative = 'sources/' + cid + '-allowed.json'
        write_new(ROOT / relative, view)
        write_new(ROOT / 'sources' / (cid + '-scope.json'), {
            'case_id': cid, 'original_path': str(path), 'original_file_sha256': digest(path.read_bytes()),
            'selected_slices': selected, 'selection_by': 'CODEX_SOURCE_READING_BEFORE_LOCAL_RUN',
            'excluded_reason': 'HEADNOTES_FINAL_COURT_ANALYSIS_OR_TARGET_DISPOSITION',
            'limits': ['Earlier court findings are available appeal history, not pretrial evidence.',
                       'Original documents remain complete; this view defines the task scope.',
                       'Party arguments can mention cited laws; this is not a citation-blind retrieval test.']})
        entries.append({'case_id': cid, 'candidate_rank_zero_based': ranks[cid], 'source_path': str(path),
                        'source_file_sha256': digest(path.read_bytes()), 'input_view': relative,
                        'group': 'DELHI_1958_S14_1_B_APPEAL', 'role': 'EXPOSED_DEVELOPMENT',
                        'association_status': 'NO_KNOWN_SAME_DISPUTE_NOT_CERTIFIED_INDEPENDENT',
                        'law_version_compatibility': 'PROVISION_FAMILY_CONFIRMED_HISTORICAL_VERSION_REVIEW_PENDING'})
    task = {'task_id': 'DELHI_SUBLETTING_APPEAL_V1',
            'question': 'Given the supplied pre-decision appeal record, should the tenant appeal against eviction for alleged subletting, assignment or parting with possession be allowed or dismissed? Identify missing decisive conditions and do not assume all necessary conditions are sufficient.',
            'analysis_stage': 'Supreme Court appeal; prior proceedings are known history, current judgment is withheld.',
            'input_contract': 'All supplied allowed segments, including facts, prior findings and party arguments. No target-court reasoning, headnotes or disposition. Only given information; no inference that an absent fact is false.',
            'outcome_labels': ['ALLOW_APPEAL', 'DISMISS_APPEAL', 'PARTIAL_OR_REMAND', 'UNDETERMINED'],
            'current_role': 'DEVELOPMENT_RESOURCE_FORMAT_ONLY_NOT_LEGAL_ACCURACY_EVALUATION',
            'scope_review': 'PROVISION_FAMILY_ONLY; full law version and rule coverage pending',
            'reference_policy': 'ORDINARY_HIGH_WEB_MODEL_SOURCE_REVIEW_NOT_HUMAN_GOLD',
            'frozen_for_new_cases': False}
    write_new(ROOT / 'protocol/task.json', task)
    write_new(ROOT / 'protocol/sample.json', {'development': entries,
        'format_check_cases': [x['case_id'] for x in entries[:2]], 'new_cases': [],
        'selection': 'Existing exposed sources with source-confirmed Delhi 1958 s14(1)(b) appeal issue, retaining original queue order. Scope is provisional; no claim of exhaustive compatible-family audit.',
        'source_queue': str(queue_path), 'source_queue_hash': digest(queue_path.read_bytes()),
        'new_case_selection_status': 'NOT_STARTED_UNTIL_RESOURCE_FORMAT_GATE_AND_LAW_SCOPE_READY',
        'independence_proven': False})
    write_new(ROOT / 'protocol/config-candidate.json', SETTINGS)
    queries = [{'id': 'D1_LEASE_AND_POSSESSION_SAME_PROPERTY', 'origin': 'PREDEFINED_ENGINE_FUNCTION_CHECK_NOT_DISCOVERED_LEGAL_RULE',
                'query': {'op': 'all', 'children': [
                    {'op': 'atom', 'id': 'lease', 'predicate': 'LEASE', 'roles': {'premises': '$p'}, 'polarity': 'POSITIVE'},
                    {'op': 'atom', 'id': 'possession', 'predicate': 'POSSESSION', 'roles': {'premises': '$p'}, 'polarity': 'POSITIVE'}]}}]
    write_new(ROOT / 'protocol/diagnostic-queries.json', {'queries': queries, 'not_a_verdict_test': True})
    manifest = json.loads(Path('review/MANIFEST.json').read_text())
    if not (ROOT / 'protocol/legacy-preservation.json').exists():
        legacy = [r for r in manifest['source_files'] if r['path'].startswith(('outputs/', 'legal_bench/', 'scripts/', 'tests/'))
                  and not r['path'].startswith(('outputs/rules-verdict-v1/', 'legal_bench/rules_verdict_v1/'))]
        write_new(ROOT / 'protocol/legacy-preservation.json', {'parent_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
            'legacy_snapshot_id': manifest['snapshot_id'], 'files': legacy,
            'unfinished_draft_sha256': digest(Path('legal_bench/local_chunk_v11.py').read_bytes()),
            'initial_working_changes': subprocess.check_output(['git', 'status', '--short'], text=True)})
    code = sorted(Path('legal_bench/rules_verdict_v1').glob('*.py')) + [Path('scripts/rules_verdict_v1.py'), Path(__file__)]
    frozen = []
    for p in code:
        rel = p.relative_to(Path.cwd()) if p.is_absolute() else p
        destination = ROOT / 'freeze/resource-format-v1/code' / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        raw = p.read_bytes()
        if destination.exists() and destination.read_bytes() != raw:
            raise ValueError('Frozen source differs; new version required')
        if not destination.exists():
            destination.write_bytes(raw)
        frozen.append({'path': str(rel), 'sha256': digest(raw)})
    write_new(ROOT / 'freeze/resource-format-v1/manifest.json', {'role': 'DEVELOPMENT_FORMAT_ATTEMPT', 'code': frozen,
        'config_hash': digest(SETTINGS), 'retry_limit_per_case': 1, 'max_cases': 2, 'gate_failure_action': 'STOP_NO_NEW_CASE_BATCH'})
    print(json.dumps({'development': [c['case_id'] for c in entries], 'format_cases': [c['case_id'] for c in entries[:2]], 'scope': task['current_role']}, indent=2))


if __name__ == '__main__':
    prepare()
