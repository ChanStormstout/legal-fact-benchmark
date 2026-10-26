"""Audit real cached evidence and build actual wires without dispatching a model."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
OLD = ROOT.parent/'rapido-role-extraction-experiment-v6-2026-10-25'
sys.path[:0] = [str(ROOT), str(REPO/'outputs/rapido-ontology-source-v25-2026-10-25-v1/src'), str(REPO)]
from source_reading import catalog, reading_request, initial_packet, review_request, run, save_new, NULLABLE
from communication import request_wire


def read(path):
    return json.loads(path.read_text())


def transport(req, cfg):
    return request_wire({'policy': req['policy'], 'task': req['task'], 'schema': req['schema'],
        'material': {k: v for k, v in req.items() if k not in ['policy', 'task', 'schema']},
        'output_token_cap': cfg['diagnostic_output_tokens']}, cfg)


def empty_read(focus):
    return {'records': [], 'coverage': {sid: {'state': 'UNRESOLVED', 'indices': [],
             'reason': 'Offline transport fixture; no source interpretation.'} for sid in focus}, 'conflicts': []}


def unresolved_review(c, packet):
    return {'reviews': [], 'additions': [], 'coverage': {sid: {'state': 'UNRESOLVED',
             'targets': [], 'addition_indices': [], 'source_basis': 'Offline fixture, not an evaluation.'}
             for sid in packet['focus']},
             'cue_decisions': {key: {'decision': 'UNRESOLVED', 'targets': [], 'addition_indices': [],
              'source_basis': 'No model interpretation was requested.'} for key, cue in c['qualification_cues'].items()
              if cue['source_id'] in packet['focus']}, 'conflicts': []}


def sizing_packet(c, focus):
    """Eight synthetic unknown propositions measure structure, never real-case quality."""
    records = []
    for i in range(8):
        sid = focus[i % len(focus)]
        records.append({'anchor': sid, 'kind': 'UNRESOLVED',
            'attribution': {k: None for k in ['speaker', 'forum', 'stage', 'time']},
            'proposition': {'subject': 'Sizing fixture', 'relation': 'has no semantic meaning',
                            'object': str(i), 'event_time': None},
            'qualification_state': 'UNRESOLVED', 'qualifications': [], 'evidence': [sid],
            'unknowns': [{'field': field, 'reason': 'READER_UNRESOLVED', 'detail': 'Synthetic sizing only.'}
                         for field in NULLABLE]})
    return initial_packet(c, focus, {'records': records,
        'coverage': {sid: {'state': 'RECORDS', 'indices': [i for i, r in enumerate(records) if r['anchor'] == sid],
                     'reason': 'Synthetic structure only.'} for sid in focus}, 'conflicts': []})


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--destination', required=True, type=Path)
    args = parser.parse_args(); dest = args.destination
    if dest.exists():
        raise ValueError('EXISTING_AUDIT_NOT_OVERWRITTEN')
    dest.mkdir(parents=True)
    cfg = read(ROOT/'protocol.json'); report = {'new_model_calls': 0, 'semantic_quality': None,
        'offline_fixture_results_are_not_extractions': True, 'cases': {}, 'transport': []}
    protected = read(ROOT/'private/protected-v6.json')
    old_freeze = read(OLD/'freeze.json')['files']
    for relative, expected in {**old_freeze, **protected}.items():
        assert hashlib.sha256((REPO/relative).read_bytes()).hexdigest() == expected, relative
    report['old_files_verified'] = len(set(old_freeze) | set(protected))
    for cid in cfg['cases']:
        inp = ROOT/'private/inputs'/f'{cid}.json'
        assert inp.read_bytes() == (OLD/'private/inputs'/f'{cid}.json').read_bytes()
        sources = read(inp)['sources']; c = catalog(sources); wires = []
        def ask(tag, req):
            wire = transport(req, cfg); material = json.loads(wire['messages'][1]['content'])
            assert material['sources'] == sources
            assert 'question' not in material and 'reference_answer' not in material
            assert wire['max_tokens'] == 65536
            wires.append({'tag': tag, 'message_characters': sum(len(x['content']) for x in wire['messages']),
                          'decoder_characters': len(json.dumps(wire['response_format']))})
            save_new(dest/cid/'wires'/f'{tag}.json', wire)
            if tag.startswith('reading'):
                return empty_read(req['focus_source_ids'])
            packet = initial_packet(c, req['focus_source_ids'], empty_read(req['focus_source_ids']))
            return unresolved_review(c, packet)
        output = run(sources, ask, dest/cid/'synthetic-orchestration', cfg['paragraphs_per_batch'])
        # Technical orchestration with zero semantic interpretation must not create a quality score.
        assert output['technical_complete'] and output['semantic_quality'] is None
        assert all(b['pending'] for b in output['batches'])
        focus = list(sources)[:cfg['paragraphs_per_batch']]
        sized = transport(review_request(c, sizing_packet(c, focus)), cfg)
        report['cases'][cid] = {'input_hash': hashlib.sha256(inp.read_bytes()).hexdigest(),
            'source_characters': sum(map(len, sources.values())), 'paragraphs': len(sources),
            'qualification_cues_are_lexical_not_legal_labels': len(c['qualification_cues']),
            'planned_logical_calls': len(wires), 'fixed_focus_batches': output['expected_batches'],
            'all_requests_contain_exact_originals': True, 'wire_sizes': wires,
            'eight_record_synthetic_review_decoder_characters': len(json.dumps(sized['response_format'])),
            'eight_record_synthetic_review_message_characters': sum(len(x['content']) for x in sized['messages'])}
    for raw in OLD.glob('private/**/calls/*/raw-sse.txt'):
        chunks = []; finished = []; done = False
        for line in raw.open():
            if not line.startswith('data:'):
                continue
            value = line[5:].strip()
            if value == '[DONE]':
                done = True; continue
            if not value:
                continue
            event = json.loads(value)
            for choice in event.get('choices', []):
                delta = choice.get('delta', choice.get('message', {})) or {}
                if delta.get('content'):
                    chunks.append(delta['content'])
                if choice.get('finish_reason') is not None:
                    finished.append(choice['finish_reason'])
        exact = ''.join(chunks) == (raw.parent/'response.txt').read_text()
        assert exact
        report['transport'].append({'path': str(raw.relative_to(REPO)), 'raw_sha256': hashlib.sha256(raw.read_bytes()).hexdigest(),
            'replay_equals_saved_response': exact, 'done_received': done, 'finish_reasons': finished,
            'provider_internal_cause': 'UNKNOWN' if not finished else 'NOT_A_FAILED_STREAM'})
    save_new(dest/'audit.json', report)
    print(json.dumps({k: v for k, v in report.items() if k not in ['cases', 'transport']}, indent=2))
    print(json.dumps({cid: {k: v for k, v in row.items() if k != 'wire_sizes'} for cid, row in report['cases'].items()}, indent=2))


if __name__ == '__main__':
    main()
