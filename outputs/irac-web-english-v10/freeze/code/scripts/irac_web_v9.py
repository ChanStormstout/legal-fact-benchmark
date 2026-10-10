"""Four existing cases; V6 semantics with versioned web transport only."""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.irac_contract_v5 import inputs, read
from scripts.irac_contract_v5_run import delivery
from scripts.irac_web_v7 import TRANSPORT, now, save, h
from legal_bench.irac_application.semantic_v6 import process, validate_final
from legal_bench.irac_application.semantic_v6_tasks import prompt, schema

R = Path('outputs/irac-web-crosscase-v9')
CASES = ('1114159', '52547606', '55384096', '68065690')
ORDER = [(c, s) for c in CASES for s in ('A', 'P', 'B')]
MARK = 'INTERMEDIATE MATERIAL:\n\n'
END = '\n\nCOMPLETE ALLOWED CASE MATERIAL:'


def assemble(cid, stage, proposal=None):
    m, t, law, sm = inputs(cid)
    st = 'proposal' if stage == 'P' else 'final'
    assert stage in ('A', 'P', 'B')
    assert (proposal is not None) == (stage == 'B')
    text = prompt(st, m, t, law, sm, {'proposal': proposal} if stage == 'B' else {})
    sc = schema(st, m, t, law)
    audit = delivery(text, m, law, sm)
    if stage == 'B':
        a = prompt('final', m, t, law, sm, {})
        before, rest = text.split(MARK, 1)
        inter, after = rest.split(END, 1)
        assert json.loads(inter) == {'proposal': proposal}
        assert before + MARK + '{}' + END + after == a
        audit.update(B_only_raw_proposal=True, no_program_checks=True)
    return text, sc, audit


def task(cid, stage, proposal=None):
    assert cid in CASES
    out = R / 'tasks' / cid / stage
    out.mkdir(parents=True, exist_ok=False)
    text, sc, audit = assemble(cid, stage, proposal)
    (out / 'prompt.txt').write_text(text)
    save(out / 'schema.json', sc)
    save(out / 'delivery.json', audit)
    packaged = ('TRANSPORT INSTRUCTION\n' + TRANSPORT + '\n\nV6 ACTUAL TASK (UNCHANGED)\n' + text
                + '\n\nV6 OUTPUT SCHEMA (WEB DOES NOT USE TOKENWISE ENFORCEMENT)\n' + (out / 'schema.json').read_text())
    (out / 'task.txt').write_text(packaged)
    save(out / 'manifest.json', {'case': cid, 'stage': stage, 'built_at': now(),
         'prompt_sha256': h(out / 'prompt.txt'), 'schema_sha256': h(out / 'schema.json'),
         'task_sha256': h(out / 'task.txt'), 'bytes': len(packaged.encode()),
         'raw_P_sha256': h(R / 'runs' / cid / 'P' / 'raw-response.txt') if stage == 'B' else None,
         'parsed_P_sha256': h(R / 'runs' / cid / 'P' / 'parsed.json') if stage == 'B' else None,
         'intermediate_utf8_bytes': len(json.dumps({'proposal': proposal}, ensure_ascii=False).encode()) if stage == 'B' else 2})
    return out


def accept(cid, stage, out):
    """Same V6 partial importer and final validator; no content repair."""
    out = Path(out)
    raw = (out / 'raw-response.txt').read_text()
    text = raw.strip()
    operations = []
    if text.startswith('```') and text.endswith('```'):
        text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        operations.append('REMOVE_OUTER_MARKDOWN_FENCE')
    result = {'case': cid, 'stage': stage, 'run_status': 'OK', 'answer': None,
              'format_operations': operations, 'semantic_validated': False}
    try:
        value = json.loads(text)
        save(out / 'parsed.json', value)
        m, t, law, sm = inputs(cid)
        if stage == 'P':
            imp, checks = process(value, t, m, law)
            save(out / 'import.json', imp)
            save(out / 'checks-full.json', checks)
            if not imp['usable']:
                raise ValueError(imp['status'])
        else:
            validate_final(value, schema('final', m, t, law), t)
        result['answer'] = value
    except (ValueError, KeyError, TypeError) as exc:
        result.update(run_status='FORMAT_ERROR', reason=str(exc))
    save(out / 'result.json', result)
    return result


def ingest(cid, stage):
    assert cid in CASES
    out = R / 'runs' / cid / stage
    assert not (out / 'result.json').exists(), 'Already ingested: reuse saved result.'
    result = accept(cid, stage, out)
    if stage == 'P':
        if result['run_status'] == 'OK':
            task(cid, 'B', result['answer'])
        else:
            save(R / 'runs' / cid / 'B' / 'result.json', {
                'case': cid, 'stage': 'B', 'run_status': 'SKIPPED', 'answer': None, 'reason': 'DEPENDENT_P_UNREADABLE'})
    progress = read(R / 'progress.json')
    for slot in progress['slots']:
        p = R / 'runs' / slot['case'] / slot['stage'] / 'result.json'
        if p.exists():
            slot['status'] = read(p)['run_status']
    save(R / 'progress.json', progress)
    print(json.dumps({k: v for k, v in result.items() if k != 'answer'}, ensure_ascii=False))


def prepare():
    assert str(R) in read('docs/repository-artifacts.json')['artifact_roots']
    assert not R.exists(), 'Inspect and resume existing work.'
    old = Path('outputs/irac-semantic-interface-v6')
    cfg = read(old / 'freeze/config.json')
    for p, expected in {**cfg['code_hashes'], **cfg['material_hashes']}.items():
        assert h(p) == expected, p
    history = {}
    for folder in ('irac-contract-repair-v5', 'irac-semantic-interface-v6', 'irac-web-crossmodel-v7', 'irac-quantization-v8'):
        history.update({str(p): h(p) for p in Path('outputs', folder).rglob('*') if p.is_file()})
    save(R / 'registration.json', {'created_at': now(), 'head': subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
         'branch': subprocess.check_output(['git','branch','--show-current'], text=True).strip(),
         'dirty': subprocess.check_output(['git','status','--short'], text=True), 'historical_hashes': history})
    code = dict(cfg['code_hashes'])
    for p in ('scripts/irac_web_v9.py', 'scripts/irac_web_v7.py', 'tests/test_irac_web_v9.py'):
        code[p] = h(p)
    mats = {}
    case_list = []
    for cid in CASES:
        m,t,law,sm = inputs(cid)
        for row in sm:
            assert 'sealed' not in row['raw_path'].lower()
            assert h(row['raw_path']) == row['raw_sha256']
            assert Path(row['raw_path']).read_text()[slice(*row['raw_char_range'])] == m['sources'][row['source_id']]['text']
        base = Path('outputs/irac-contract-repair-v5')
        for p in (base/'sources'/(cid+'.json'),base/'input-audit'/(cid+'.json'),base/'templates'/(m['family']+'.json'),base/'sources'/(m['family']+'-law.json')):
            mats[str(p)] = h(p)
            dst=R/'freeze/materials'/p.relative_to(base);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
        case_list.append({k:v for k,v in m.items() if k!='sources'})
        for st in ('A','P'): task(cid,st)
        b=R/'freeze/B-templates'/cid;b.mkdir(parents=True)
        for n in ('prompt.txt','schema.json'):shutil.copyfile(R/'tasks'/cid/'A'/n,b/n)
    for p in code:
        dst=R/'freeze/code'/p;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
    save(R/'case-list.json', {'cases':case_list,'selection':'User-fixed existing allowed materials; not selected by performance/verdict',
         'exposure':'All four previously used in development; not independent test',
         'known_cross_case_dispute':'None documented in supplied mappings; association otherwise UNCONFIRMED, not proven independent'})
    (R/'freeze/transport.txt').write_text(TRANSPORT)
    test=subprocess.run([sys.executable,'-m','unittest','tests.test_irac_web_v9'],text=True,capture_output=True)
    (R/'engineering-tests.txt').write_text(test.stdout+test.stderr)
    assert test.returncode==0, test.stderr
    save(R/'preparation-validation.json', {'E':'PASS','tests_exit':0,'new_sources':0,'model_calls':0,
         'old_two_prompt_schema_regression':'byte-identical prompt and equivalent serialized schema',
         'scope_review':'Only existing approved spans; no target final conclusion or new law added. Prior court findings deliberately retained.',
         'semantic_correctness_verified':False})
    save(R/'freeze/config.json', {'version':'IRAC_WEB_CROSSCASE_V9','frozen_at':now(),'code_hashes':code,'material_hashes':mats,
         'base_config_hash':h(old/'freeze/config.json'),'order':ORDER,'max_generations':12,'retries':0,'extra_review_calls':0,
         'model_visible':None,'required_visible_mode':'High','pro':False,'preferred_isolation':'temporary nonpersonalized current chat',
         'exact_model':None,'sampling':None,'output_token_cap':None,'web_tokenwise_schema':False,
         'B_rule':'V6 final prompt with intermediate={proposal: unmodified parsed current P}; no offline checks or human correction.',
         'failure_rule':'Null technical answer. P unreadable skips dependent B only; access/mode failure preserves unsubmitted slots. No retry.',
         'evaluation':{'E':'delivery, isolation, exact raw P, output contract','M':'actual arrangements, source attribution, uses, opposition, limits',
                       'L':'decisive allowed facts, court stages, rule scope/polarity, gaps and explicit prediction assumptions',
                       'trace':'source -> P -> A -> B; do not infer sole causation; one collective source review after batch',
                       'categories':['B_NET_IMPROVEMENT','CLOSE','B_WORSE','INDETERMINATE'],
                       'investment_gate':'4 reviewable pairs, >=2 important B gains, remaining cases no equally serious new errors; otherwise apply user decision rules without adding cases',
                       'reference':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD'},
         'stop':'After at most 12 predefined generations and one review; no method changes, C, retraining, new sources, commit or push',
         'task_hashes':{str(p):h(p) for p in (R/'tasks').rglob('*') if p.is_file()}})
    save(R/'progress.json',{'status':'PREPARED_FROZEN_NOT_SUBMITTED','slots':[{'case':c,'stage':s,'status':'NOT_SUBMITTED'} for c,s in ORDER]})


if __name__ == '__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='ingest':ingest(*sys.argv[2:4])
