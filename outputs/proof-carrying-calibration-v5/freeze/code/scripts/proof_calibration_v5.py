"""Bounded source preparation. No model inference, legal approval or training."""
import argparse
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.contracts import byte_hash, read_json, write_once
from legal_bench.proof_carrying.realcase_contracts import schemas, validate
from legal_bench.rules_verdict_v1.source_identity_v2 import declare_body, validate_view

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/proof-carrying-calibration-v5'


def build():
    specs = read_json(OUT / 'source-review-specifications.json')
    for cid, spec in specs.items():
        dest = OUT / 'cases' / cid
        dest.mkdir(parents=True, exist_ok=True)
        source = read_json(OUT / 'sources' / (cid + '.json'))
        source = declare_body(source, *spec['body'], 'Judgment heading through last disposition/signature; excludes website navigation, headnotes and AI tags.')
        segments = [s for s in source['segments'] if spec['body'][0] <= s['original_line'] <= spec['body'][1]]
        view = {'case_id': cid, 'segments': segments}
        mapping = validate_view(view, source)
        write_once(dest / 'source.json', source)
        write_once(dest / 'allowed-source.json', view)
        write_once(dest / 'source-map.json', mapping)
        byline = {s['original_line']: s for s in segments}

        def refs(lines):
            return [byline[n]['id'] for n in lines]

        def quote(lines):
            return '\n'.join(byline[n]['text'] for n in lines)

        bindings = [{'role': role, 'entity': cid + ':' + role} for role in ('subject', 'opponent', 'property')]
        facts = {'entities': [{'id': b['entity'], 'kind': 'PROPERTY' if b['role'] == 'property' else 'PARTY_GROUP',
                             'label': spec[b['role']], 'refs': refs(spec['records'][0][2])} for b in bindings],
                 'premises': [], 'relations': [], 'coverage_limits': spec['gaps'] + [
                     'Codex-assisted preparation only; no independent reference, accepted-premise policy or legal approval.',
                     'TRUE on a reported finding means the attributed finding is recorded, not independent verification of the underlying event.',
                     'Source references establish addresses, not semantic correctness; final disposition is comparison-only.']}
        for i, (pred, text, lines, status, speaker, state) in enumerate(spec['records'], 1):
            facts['premises'].append({'id': 'P' + str(i), 'predicate': pred, 'text': text, 'bindings': bindings,
                'time_scope': None, 'statement_status': status, 'speaker': speaker,
                'court_level': 'As explicitly attributed in speaker; source is a Supreme Court judgment',
                'stage': spec['stage'], 'state': state, 'refs': refs(lines), 'quote': quote(lines),
                'limitations': ['Draft attributed proposition, not an accepted premise. Original evidence was not independently inspected.']})
        rules = {'rules': [], 'coverage_limits': spec['gaps'] + ['No new legal approval. OPEN_TEXT rules are not automatically executable.']}
        for rid, text, lines, origin, scope, pred in spec['rules']:
            rules['rules'].append({'id': rid, 'version': 1, 'description': text,
                'conclusion_predicate': pred, 'conclusion_text': text, 'jurisdiction': 'India; target judgment historical scope only',
                'stage': spec['stage'], 'origin': origin, 'source_refs': refs(lines), 'source_quote': quote(lines),
                'operator': 'OPEN_TEXT', 'slots': [], 'exception_slots': [], 'scope_limits': [scope, spec['boundary']],
                'burden_policy': 'NOT_SEPARATELY_TRANSLATED; do not infer burdens from missing evidence.',
                'unimplemented': ['Legal interpretation and source acceptance require separate review; no automatic truth from supporting links.']})
        validate(facts, schemas('facts'))
        validate(rules, schemas('rules'))
        write_once(dest / 'facts-draft.json', facts)
        write_once(dest / 'rules-draft.json', rules)
        write_once(dest / 'reconstruction-scope.json', {
            'case_id': cid, 'title': source['titles'][0], 'url': source['url'], 'date': spec['date'],
            'task': 'JUDGMENT_REASONING_RECONSTRUCTION', 'issue': spec['issue'], 'stage': spec['stage'],
            'dispute_group': 'CAL-' + cid, 'intended_role': 'CALIBRATION_TRAIN_ONLY',
            'exposure': 'Existing derived corpus metadata; new Codex preparation. Not an unexposed test case.',
            'related_disputes': 'No same dispute identified among these five and Guide cases by parties/property; no exhaustive litigation audit.',
            'sealed': 'No sealed content or assignments opened; no existing split was altered. Future assignment requires protected-membership check.',
            'mechanism': spec['mechanism'], 'conclusion_boundary': spec['boundary'],
            'conclusion_availability': spec['certainty'], 'decisive_opposition_refs': refs(spec['opposition']),
            'comparison_only_disposition_refs': refs(spec['disposition']),
            'legal_approval': 'PENDING_QUALIFIED_REVIEW', 'independent_reference': 'NOT_GENERATED',
            'certificate': None, 'checker_result': None,
            'next_dependency': 'Independent source reference and acceptance policy; draft rules remain OPEN_TEXT, not executable proofs.'})
        body = '\n\n'.join('[' + s['id'] + ']\n' + s['text'] for s in segments)
        task = ('Prepare an independent source-grounded reference for judgment reasoning reconstruction, not prediction. '
                'Use only the complete judgment below. Distinguish parties, courts, separate judicial opinions, '
                'procedural assumptions, rules reported from other decisions and final disposition. '
                'Do not use the final disposition as a premise proving itself. Preserve decisive opposition and uncertainty. '
                'Do not search externally. The output is a model reference, not human gold or legal approval.\n\n'
                'Selected question: ' + spec['issue'] + '\n\nOutput contract:\n' +
                json.dumps(schemas('reference'), ensure_ascii=False, indent=2) + '\n\nCOMPLETE JUDGMENT:\n' + body)
        (dest / 'independent-reference-task-NOT-SUBMITTED.txt').write_text(task + '\n')
        write_once(dest / 'task-delivery-map.json', {'submitted': False, 'task_sha256': byte_hash(dest / 'independent-reference-task-NOT-SUBMITTED.txt'),
            'mapping': mapping, 'draft_facts_or_rules_in_task': False, 'model_calls': 0})
        rendered = '<!doctype html><meta charset="utf-8"><title>' + html.escape(source['titles'][0]) + '</title>'
        rendered += '<style>body{max-width:1000px;margin:40px auto;font:17px/1.6 system-ui}p{white-space:pre-wrap}small{color:#777}</style>'
        rendered += '<h1>' + html.escape(source['titles'][0]) + '</h1><p>Public judgment rendering; original exhibits not obtained.</p>'
        for s in segments:
            rendered += '<p id="' + s['id'] + '"><small>' + s['id'] + '</small><br>' + html.escape(s['text']) + '</p>'
        (dest / 'source.html').write_text(rendered)
        lines = ['# ' + source['titles'][0], '', spec['issue'], '', '**Status:** Codex-assisted draft; no independent reference or legal approval.', '',
                 '## Attributed propositions', '']
        for p in facts['premises']:
            links = ', '.join('[' + r + '](source.html#' + r + ')' for r in p['refs'])
            lines.extend(['**' + p['id'] + ' — ' + p['statement_status'] + ' / ' + p['speaker'] + '**', '', p['text'], '', links, ''])
        lines.extend(['## Candidate rules (OPEN_TEXT; not executable)', ''])
        for r in rules['rules']:
            lines.extend(['**' + r['id'] + '** ' + r['description'], '', r['scope_limits'][0], '',
                          ', '.join('[' + x + '](source.html#' + x + ')' for x in r['source_refs']), ''])
        lines.extend(['## Opposition and conclusion boundary', '', ', '.join('[' + r + '](source.html#' + r + ')' for r in refs(spec['opposition'])), '', spec['boundary'], '',
                      '## Gaps', ''] + ['- ' + g for g in spec['gaps']])
        (dest / 'walkthrough.md').write_text('\n'.join(lines) + '\n')


def check():
    specs = read_json(OUT / 'source-review-specifications.json')
    results = []
    for cid, spec in specs.items():
        dest = OUT / 'cases' / cid
        source = read_json(dest / 'source.json')
        view = read_json(dest / 'allowed-source.json')
        mapping = validate_view(view, source)
        lookup = {s['id']: s for s in view['segments']}
        facts = read_json(dest / 'facts-draft.json')
        rules = read_json(dest / 'rules-draft.json')
        validate(facts, schemas('facts')); validate(rules, schemas('rules'))
        entity_ids = {e['id'] for e in facts['entities']}
        disposition = set(read_json(dest / 'reconstruction-scope.json')['comparison_only_disposition_refs'])
        checked = 0
        for items, refkey, quotekey in [(facts['premises'], 'refs', 'quote'), (rules['rules'], 'source_refs', 'source_quote')]:
            for item in items:
                assert all(r in lookup for r in item[refkey])
                assert not disposition.intersection(item[refkey]), (cid, item['id'], 'circular disposition premise')
                assert item[quotekey] == '\n'.join(lookup[r]['text'] for r in item[refkey])
                for b in item.get('bindings', []): assert b['entity'] in entity_ids
                checked += len(item[refkey])
        task = (dest / 'independent-reference-task-NOT-SUBMITTED.txt').read_text()
        for s in view['segments']: assert '[' + s['id'] + ']\n' + s['text'] in task
        assert all(r['operator'] == 'OPEN_TEXT' for r in rules['rules'])
        results.append({'case_id': cid, 'status': 'PASS', 'source_segments': len(mapping),
                        'premises': len(facts['premises']), 'rules': len(rules['rules']), 'refs_checked': checked,
                        'task_bytes': len(task.encode()), 'semantic_approval': False})
    registration = read_json(OUT / 'registration.json')
    changed = [p for p,h in registration['old_files'].items() if not (ROOT/p).exists() or byte_hash(ROOT/p) != h]
    assert not changed, changed
    result = {'status': 'PASS', 'cases': results, 'old_files_preserved': len(registration['old_files']),
              'scope': 'Actual preparation entry: schema, provenance, references, bindings, full delivery, circular-disposition exclusion; NOT legal correctness.',
              'new_model_calls': 0, 'training': 0, 'checked_at': datetime.now(timezone.utc).isoformat()}
    write_once(OUT / 'delivery-validation.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('command', choices=['build', 'check']); a = p.parse_args()
    build() if a.command == 'build' else check()
