"""Bounded engineering acceptance only; no model weights, inference or training."""
import copy
import hashlib
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import proof_local_comparison_v18 as entry
from tests.test_local_comparison_v18 import fixture
from legal_bench.proof_carrying import local_pipeline_v18 as pipe


def ordinary():
    out = entry.OUT / 'engineering'
    result = subprocess.run([sys.executable, '-m', 'unittest',
                             'tests.test_local_comparison_v18',
                             'tests.test_local_comparison_v17',
                             'tests.test_mlx_constraint_v2'],
                            cwd=ROOT, capture_output=True, text=True)
    entry.text(out / 'tests.txt', result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError('ENGINEERING_TEST_FAILURE')
    if 'skipped' in result.stderr:
        raise RuntimeError('NECESSARY_TEST_SKIPPED')
    plan = entry.read(entry.PREP / 'capacity-plan.json')
    delivery = []
    for cid in [c['case_id'] for c in plan['cases']]:
        f = entry.fixture(cid)
        original = entry.read(entry.OLD / 'inputs' / cid / 'fixture.json')
        assert f == original
        case, rules = f['case'], f['rules']
        slots = [s for s in plan['P_slots'] if s['case_id'] == cid]
        expected = {x['id'] for x in case['segments']}
        for group in {tuple(s['part']['rule_ids']) for s in slots}:
            selected = [s for s in slots if tuple(s['part']['rule_ids']) == group]
            assert {i for s in selected for i in s['part']['source_ids']} == expected
        for slot in slots:
            p = slot['part']
            prompt = (entry.PREP / 'inputs' / cid / (p['id'] + '-prompt.txt')).read_text()
            assert prompt == pipe.proposal_prompt(case, rules, p)
            restored = prompt.split('\nALLOWED SOURCE:\n', 1)[1].split('\nOUTPUT SCHEMA:\n', 1)[0]
            actual = {x['id']: x for x in case['segments'] if x['id'] in p['source_ids']}
            spans = []
            for sid, segment in actual.items():
                start = restored.find(segment['text'])
                assert start >= 0
                spans.append({'id': sid, 'source_document': segment['source_document'],
                              'original_line': segment.get('original_line'),
                              'source_text_sha256': entry.sha(ROOT / case['source_path']),
                              'fragment_sha256': hashlib.sha256(segment['text'].encode()).hexdigest(),
                              'in_draft_source_block': [start, start + len(segment['text'])]})
            delivery.append({'case_id': cid, 'part': p['id'], 'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
                             'source_map': spans, 'status': 'PRE_SUBMISSION_DRAFT_ONLY'})
    entry.save(out / 'source-delivery-map.json', delivery)
    # Existing successful P is replayed for address recovery only. No old rating or
    # whole-premise decision is promoted into the new task or new supervision.
    replay = []
    for path in sorted((entry.OLD / 'local').glob('*/P/run.json')):
        if entry.read(path)['run_status'] != 'OK':
            continue
        cid = path.parent.parent.name
        f = entry.fixture(cid)
        old = entry.read(path.parent / 'parsed.json')
        p = {'records': copy.deepcopy(old['records']), 'objects': [], 'uses': [], 'premises': [], 'coverage_limits': []}
        for conn in old['connections']:
            bs = []
            for ob in conn['objects']:
                p['objects'].append({'label': ob['object'], 'type': ob['type'], 'refs': ob['refs'], 'identity_basis': ob['basis']})
                bs.append({'address': conn['premise_id'] + '::' + ob['role'], 'object': len(p['objects'])})
            p['uses'].append({'premise': conn['premise_id'], 'records': conn['records'],
                              'opposition_records': conn['opposition_records'], 'bindings': bs,
                              'witnesses': conn['witnesses'], 'claim': conn['proposed_connection'],
                              'direction': conn['direction'], 'stage': conn['stage'],
                              'self_assessment': 'UNRESOLVED', 'limits': []})
        for i, use in enumerate(p['uses']):
            pkg = pipe.packet(f['case'], f['rules'], p, i)
            object_refs = {r for b in use['bindings'] for r in p['objects'][b['object'] - 1]['refs']}
            assert object_refs <= set(pkg['actual_restored_source']['requested_refs'])
            replay.append({'case_id': cid, 'connection': i + 1, 'object_refs_requested': sorted(object_refs),
                           'restore_limits': pkg['actual_restored_source']['limits'],
                           'purpose': 'SOURCE_RECOVERY_ONLY; OLD_SEMANTIC_DECISIONS_NOT_ADAPTED'})
    entry.save(out / 'cached-source-replay.json', replay)
    entry.save(out / 'entry-tests.json', {'tests_passed': True, 'tests_output': str((out / 'tests.txt').relative_to(ROOT)),
               'draft_source_maps': len(delivery), 'cached_source_uses': len(replay),
               'whole_engineering_gate': 'PARTIAL_NOT_FULL_RUN_ACCEPTANCE',
               'model_generation_calls': 0, 'training_runs': 0,
               'actual_encoders_run': False, 'semantic_or_legal_correctness_verified': False})


def tokenizer_fixture():
    from transformers import AutoTokenizer
    from mlx_vlm.prompt_utils import apply_chat_template
    from legal_bench.mlx_json_constraint import tokenizer_data
    from legal_bench.mlx_json_constraint_v2 import SchemaMask
    import mlx.core as mx
    tok = entry.tokenizer()
    model_path = (ROOT / 'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip()
    config = json.loads((Path(model_path) / 'config.json').read_text())
    data = tokenizer_data(tok, tok.eos_token_id)
    c, r, p = fixture()
    sc = pipe.schema(r)
    pipe.validate(p, sc)
    ids = tok.encode(json.dumps(p), add_special_tokens=False)
    mask = SchemaMask(data, sc)
    logits = mx.zeros((len(tok),))
    mask(mx.array([1]), logits)  # Exactly one non-generated prompt token.
    for i, token in enumerate(ids):
        output = mask(mx.array([1] + ids[:i]), logits)
        assert float(output[token].item()) == 0, (i, token)
    output = mask(mx.array([1] + ids), logits)
    assert float(output[tok.eos_token_id].item()) == 0
    assert json.loads(tok.decode(ids)) == p
    plan = entry.read(entry.PREP / 'capacity-plan.json')
    renders = []
    for s in plan['P_slots']:
        prompt = (entry.PREP / 'inputs' / s['case_id'] / (s['part']['id'] + '-prompt.txt')).read_text()
        actual = apply_chat_template(tok, config, prompt, enable_thinking=False, num_images=0, num_audios=0)
        assert actual == entry.render(tok, prompt)
        n = len(tok.encode(actual))
        assert n == s['rendered_input_tokens']
        assert n + s['max_tokens'] <= 32768
        assert '<think>\n\n</think>' in actual[-150:]
        renders.append({'case_id': s['case_id'], 'part': s['part']['id'], 'input_tokens': n,
                        'MLX_VLM_template_matches_static_count': True})
    entry.save(entry.OUT / 'engineering/real-tokenizer.json', {
        'tokenizer_revision': Path(model_path).name,
        'mlx_vlm_version': importlib.metadata.version('mlx-vlm'),
        'lmfe_version': importlib.metadata.version('lm-format-enforcer'),
        'mask_sha256': entry.sha(ROOT / 'legal_bench/mlx_json_constraint_v2.py'),
        'fixture_tokens': len(ids), 'mask_adapter_calls': mask.calls,
        'complete_schema_fixture_EOS_allowed': True, 'all_actual_render_checks': renders,
        'model_weights_loaded': False, 'generation_calls': 0,
        'scope': 'DETERMINISTIC_TOKEN_REPLAY_AND_TEMPLATE; NOT_GENERATION_OR_SEMANTIC_PROOF'})


if __name__ == '__main__':
    ordinary()
    tokenizer_fixture()
    print('PASS: deterministic entry/source/tokenizer checks; no model generation or training.')
