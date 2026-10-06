"""Coarse authority-use task/validation; never infers labels or case identities.

Source-address validation is an engineering check, not semantic verification.
Unreviewed/UNKNOWN uses must not become negative supervision. Sealed cases are
excluded from these task packages until an explicitly frozen evaluation phase.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.rgcn09_data import ROOT, read, save, sha

CATEGORIES = {'CORE', 'BACKGROUND', 'IRRELEVANT', 'UNKNOWN'}
REFERENCE_ROLE = 'MODEL_GENERATED_SOURCE_REVIEWED_NOT_HUMAN_GOLD'


def model_material(case, units):
    """Drop storage/provenance duplication, not legal text/limitations."""
    allowed = {'id', 'text', 'source_document'}
    view = {k: v for k, v in case.items() if k != 'segments'}
    view['segments'] = [{k: v for k, v in s.items() if k in allowed} for s in case['segments']]
    laws = []
    for u in units:
        keep = {k: v for k, v in u.items() if k != 'source'}
        keep['source'] = {k: v for k, v in u['source'].items() if k != 'raw_provenance'}
        laws.append(keep)
    return view, laws

INSTRUCTIONS = '''Read only the allowed case passages and candidate authorities below.
Do not search externally, recover the target judgment's final reasoning, predict
the historical verdict, or read other conversations. This is coarse authority
use annotation, not fact extraction or pairwise preference annotation.
For each authority listed in annotation_target_ids give one use; other supplied
authorities are common legal context. Previously reviewed uses are reused offline,
not re-annotated and not shown as proposed answers in this task.
CORE: materially helps resolve a live issue, including a limiting exception or
counterargument. An unsatisfied condition does not make the governing law irrelevant.
BACKGROUND: meaningful context or a qualified analogy, but not decisive on this record.
IRRELEVANT: supplied facts and issue affirmatively make the unit unhelpful or out of scope.
UNKNOWN: supplied information does not justify choosing the other three categories.
Mere citation is not sufficient. No citation is not evidence of irrelevance.
Distinguish lower-court findings from party claims and target endorsement. Keep
court, statute, version and analogical limitations in the short reason. A later
authority may assist retrospective analysis but is not historical prediction evidence.
Use a brief reason (normally 1-2 sentences), allowed case source IDs, and a
short exact quote from that authority for known uses. UNKNOWN may have no quote.
Return one JSON object with case_id, uses and unresolved. Each use has only
unit_id, category, reason, case_refs and law_quote. Do not add pairwise labels,
new ontology, fine condition tables or a predicted verdict.
Complete synthetic example (not evidence or law for this task):
{"case_id":"EXAMPLE","uses":[{"unit_id":"LAW:EXAMPLE:CONTROL","category":"CORE","reason":"The tenant claims retained control while the lower tribunal found the shop was controlled by another firm; the supplied control principle helps assess that disputed condition.","case_refs":["EXAMPLE:L1"],"law_quote":"Retained legal control must be assessed."}],"unresolved":[]}
Use the actual IDs in the task, not the example IDs. File output is welcome, but
provide the complete JSON once; do not repeat it in an additional narrative.
'''


def validate(payload, case, units):
    if str(payload.get('case_id')) != str(case['case_id']):
        raise ValueError('CASE_ID_MISMATCH')
    if case.get('split') == 'SEALED_TEST':
        raise ValueError('SEALED_TEST_NOT_FOR_DEVELOPMENT_LABELS')
    addresses = {s['id'] for s in case['segments']}
    by_id = {u['id']: u for u in units}
    seen, known, unknown = set(), [], []
    if not isinstance(payload.get('uses'), list) or not isinstance(payload.get('unresolved'), list):
        raise ValueError('INVALID_WRAPPER')
    for row in payload['uses']:
        if set(row) != {'unit_id', 'category', 'reason', 'case_refs', 'law_quote'}:
            raise ValueError('COARSE_FIELDS_ONLY')
        uid = row['unit_id']
        if uid not in by_id or uid in seen:
            raise ValueError('UNKNOWN_OR_DUPLICATE_AUTHORITY')
        seen.add(uid)
        if row['category'] not in CATEGORIES:
            raise ValueError('UNKNOWN_CATEGORY')
        if not isinstance(row['reason'], str) or not row['reason'].strip():
            raise ValueError('MISSING_REASON')
        refs = row['case_refs']
        if not isinstance(refs, list) or any(r not in addresses for r in refs):
            raise ValueError('INVALID_CASE_ADDRESS')
        quote = row['law_quote']
        if not isinstance(quote, str) or (quote and quote not in by_id[uid]['text']):
            raise ValueError('LAW_QUOTE_NOT_EXACT')
        if row['category'] != 'UNKNOWN' and (not refs or not quote):
            raise ValueError('KNOWN_USE_REQUIRES_SOURCE_LOCATORS')
        (unknown if row['category'] == 'UNKNOWN' else known).append(row)
    return {'case_id': str(case['case_id']), 'known': known, 'unknown': unknown,
            'unlabelled': sorted(set(by_id) - seen),
            'semantic_status': 'PENDING_SOURCE_REVIEW_NOT_VERIFIED_BY_VALIDATION',
            'program_check_scope': 'JSON, authority IDs, allowed source addresses and exact quote only',
            'original_payload_unchanged': True}


def reviewed_supervision(validated, reviewed_ids):
    """Explicit reviewed IDs only; unknown/unlabelled never get a class."""
    mapping = {'CORE': 0, 'BACKGROUND': 1, 'IRRELEVANT': 2}
    by_id = {r['unit_id']: r for r in validated['known']}
    if set(reviewed_ids) - set(by_id):
        raise ValueError('REVIEW_ID_NOT_KNOWN_USE')
    return [(uid, mapping[by_id[uid]['category']]) for uid in reviewed_ids]


def training_gate(manifest, accepted_ids, pool):
    """Gate data count/split leakage; this is NOT an efficacy test."""
    rows = manifest['cases']
    groups, roles = {}, {}
    for r in rows:
        cid = str(r['case_id']); group = str(r['group_id']); split = r['split']
        if cid in roles:
            raise ValueError('DUPLICATE_CASE')
        if group in groups and groups[group] != split:
            raise ValueError('KNOWN_DISPUTE_CROSSES_SPLIT')
        groups[group] = split; roles[cid] = split
        if cid in pool['reserved_authority_case_ids']:
            raise ValueError('AUTHORITY_SOURCE_TARGET_LEAKAGE')
    train = {cid for cid, s in roles.items() if s == 'TRAIN'}
    if set(accepted_ids) - train:
        raise ValueError('NONTRAIN_SUPERVISION')
    ready = train & set(accepted_ids)
    return {'open': len(ready) >= 30, 'usable_labelled_train': len(ready),
            'needed': max(0, 30-len(ready)), 'methods': ['S', 'B', 'C'],
            'architecture_search': False, 'test_used_for_development': False}


def prepare_existing():
    protocol = read(ROOT/'data-protocol.json')
    units = read(ROOT/'authority-pool/laws.json')
    ledger = []
    for row in protocol['existing_train']:
        cid = row['case_id']
        src = Path('outputs/rgcn-ranking-diagnostic-07/pilot/sources')/(cid+'.json')
        case = read(src)
        question = read(Path('outputs/rgcn-ranking-diagnostic-07/pilot/task-material')/(cid+'.json'))['question']
        view, laws = model_material(case, units)
        task = {'case_id': cid, 'question': question, 'case': view, 'authority_candidates': laws,
                'annotation_target_ids': [u['id'] for u in units if u['id'].startswith('LAW:V09:')],
                'scope': 'Retrospective Delhi14(1)(b); target final reasoning excluded in inherited approved view'}
        path = ROOT/'label-tasks-v4'/(cid+'.txt')
        text = INSTRUCTIONS+'\nTASK\n'+json.dumps(task, ensure_ascii=False, indent=2)+'\n'
        if path.exists() and path.read_text() != text:
            raise ValueError('TASK_CHANGED_USE_NEW_VERSION')
        path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text)
        ledger.append({'case_id': cid, 'split': 'TRAIN', 'path': str(path),
                       'sha256': sha(path), 'characters': len(text),
                       'case_view_sha256': sha(src), 'authority_pool_sha256': sha(ROOT/'authority-pool/laws.json'),
                       'status': 'PREPARED_NOT_SUBMITTED', 'model_calls': 0})
    save(ROOT/'label-task-ledger-v4.json', ledger)
    print('Prepared', len(ledger), 'coarse-only tasks; no model submissions')


def main():
    p = argparse.ArgumentParser(); p.add_argument('command', choices=['prepare-existing'])
    p.parse_args(); prepare_existing()


if __name__ == '__main__':
    main()
