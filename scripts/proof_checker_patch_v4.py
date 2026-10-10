"""Separate repair revision after the fixed diagnostic; not a rerun of its scores."""
import copy,json,shutil,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.contracts import read_json,write_once,byte_hash,content_hash
from legal_bench.proof_carrying.realcase_engine import propose
from legal_bench.proof_carrying.realcase_grounding_v3 import reviewed
from legal_bench.proof_carrying.realcase_grounding_v4 import step_semantic_hash

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'outputs/proof-carrying-checker-evaluation-v4'
OUT=BASE/'repair-01'

def migrate(snapshot,proposal):
    s=copy.deepcopy(snapshot);steps={t['id']:t for t in proposal['steps']};lineage=[]
    for sid,a in s.get('court_assessments',{}).items():
        if not reviewed(a) or a['step_hash']!=content_hash(steps[sid]):raise ValueError('MIGRATION_PARENT_NOT_VALID')
        prior=content_hash(a);a['step_semantic_hash']=step_semantic_hash(steps[sid])
        a['encoding_migration']={'parent_record_hash':prior,'semantic_content_changed':False,
            'ignored_fields':['explanation'],'order_independent_fields':['inputs','bindings']}
        a['review']['subject_hash']=content_hash({k:v for k,v in a.items() if k!='review'})
        a['review']['carry_forward_basis']='Only hash representation changed; retain earlier source-review assumption, not a new semantic or legal approval.'
        lineage.append({'id':a['id'],'parent_hash':prior,'new_hash':content_hash(a)})
    s['snapshot_id']+='-SEMANTIC-ADDRESS-V4'
    return s,lineage

def prepare():
    for cid in ('789051','1418721','1841885'):
        s=read_json(BASE/'natural'/cid/'snapshot.json');p=read_json(BASE/'natural'/cid/'certificate.json')['proposal']
        migrated,lineage=migrate(s,p);write_once(OUT/'policies'/f'{cid}.json',migrated)
        write_once(OUT/'policies'/f'{cid}-lineage.json',{'records':lineage,'rules_and_premises_unchanged':s['rules']==migrated['rules'] and s['premises']==migrated['premises']})
    files=[ROOT/x for x in ['legal_bench/proof_carrying/realcase_grounding_v4.py','legal_bench/proof_carrying/realcase_checker_v4.py',
        'scripts/check_realcase_certificate_v4.py','scripts/proof_checker_patch_v4.py','tests/test_proof_semantic_address_v4.py']]
    files += [ROOT/p for p in read_json(BASE/'freeze/config.json')['code_hashes'] if not p.endswith('proof_checker_evaluation_v4.py')]
    for p in files:
        q=OUT/'freeze/code'/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
    write_once(OUT/'freeze/config.json',{'code_hashes':{str(p.relative_to(ROOT)):byte_hash(p) for p in files},
        'policy_hashes':{str(p.relative_to(ROOT)):byte_hash(p) for p in (OUT/'policies').glob('*.json')},
        'scope':'Address/display repair only. Fixed diagnostic remains unchanged; no new natural-model performance run.',
        'checks':['equivalent_input_order','equivalent_explanatory_note','prose_ownership_upgrade','wrong_subject','wrong_rule_version','typed_ownership_upgrade'],
        'new_model_calls':0,'new_legal_approval':False})

def validate():
    cfg=read_json(OUT/'freeze/config.json')
    for p,h in {**cfg['code_hashes'],**cfg['policy_hashes']}.items():
        if byte_hash(ROOT/p)!=h:raise ValueError('PATCH_FREEZE_CHANGED:'+p)
    s=read_json(OUT/'policies/789051.json');results=[]
    for name in cfg['checks']:
        dst=OUT/'checks'/name;dst.mkdir(parents=True,exist_ok=False)
        raw=read_json(BASE/'controlled'/name/'certificate.json')['proposal']
        write_once(dst/'certificate.json',propose(s,raw))
        write_once(dst/'manifest.json',{'snapshots':{s['snapshot_id']:{'path':'../../policies/789051.json','sha256':byte_hash(OUT/'policies/789051.json')}}})
        cmd=[sys.executable,str(ROOT/'scripts/check_realcase_certificate_v4.py'),str(dst/'certificate.json'),'--manifest',str(dst/'manifest.json')]
        proc=subprocess.run(cmd,capture_output=True,text=True,cwd=ROOT)
        (dst/'stdout.txt').write_text(proc.stdout);(dst/'stderr.txt').write_text(proc.stderr)
        write_once(dst/'invocation.json',{'argv':cmd,'exit_code':proc.returncode})
        checked=json.loads(proc.stdout);write_once(dst/'result.json',checked)
        q=next(q for q in checked['requests'] if q['id']=='Q1')
        valid=name.startswith('equivalent_') or name=='prose_ownership_upgrade'
        ok=(q['answer']=='TRUE' and q['draft_status']=='CONDITIONAL_RECONSTRUCTION') if valid else q['answer'] is None
        if name=='prose_ownership_upgrade':ok=ok and q['text']!=q['submitted_text'] and q['submitted_text_semantically_checked'] is False
        results.append({'name':name,'pass':ok,'draft_status':q['draft_status'],'answer':q['answer'],
            'claim_text_checked':False,'meaning':'Prose is NOT accepted or rejected semantically; only the reviewed-rule statement is displayed with checked status.' if name=='prose_ownership_upgrade' else 'Structural regression'})
    write_once(OUT/'validation.json',{'checks':results,'passed':sum(x['pass'] for x in results),'total':len(results),
        'not_new_model_accuracy':True,'original_diagnostic_not_replaced':True})
    if not all(x['pass'] for x in results):raise RuntimeError('PATCH_VALIDATION_FAILED')

if __name__=='__main__':{'prepare':prepare,'validate':validate}[sys.argv[1]]()
