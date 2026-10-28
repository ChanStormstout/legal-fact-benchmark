"""One frozen, whole-cohort fork from actual P prefixes; no A0/prefix reruns."""
import ast, copy, json, os, sys, traceback
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from common import read, save, filehash, utc, digest
from transport import Client, service_metadata
from source_plan_direct_edit import DIRECT_EDIT, execute_f
from prompts import TRUST
OLD=ROOT.parent/'rapido-append-only-dispatch-v50-2026-10-27-v1'
OLDWORK=OLD/'private/ten-case-transfer-v1'
WORK=ROOT/'private/shared-prefix-comparison-v1'


def prepare():
    oldcfg=read(OLD/'protocol.json')
    cfg=copy.deepcopy(oldcfg)
    cfg.update(version='V51_SOURCE_PLAN_DIRECT_EDIT_SHARED_ACTUAL_PREFIX',methods=['A0_inherited','P_prefix_inherited','F'],max_calls=10,max_new_usd=0.25,technical_retries=0,stage_output_caps=dict(A0=16384,plan=4096,draft=6144,direct_edit=6144),sample_role='SAME_TEN_EXPOSED_DEVELOPMENT_CASES_NOT_CONFIRMATORY',execution='One new direct edit per original P prefix in original cohort order; no A0 or successful prefix call reissued.',prior_batch_calls=58,prior_batch_conservative_usd=0.1799799,comparison='Actual inherited P/model calls plus one new edit are charged to F; old A0 remains one ordinary call. No mixing this adaptive method exploration with a new independent test.',confirmatory_run=False)
    cfg['development_decision']={'current_cohort_evaluation':'Incomplete; development evidence from 236012,152211,701211,1825635 helped design F.','all_ten_included_without_output_based_selection':True,'old_draft_freeze_condition_amendment':'Do not wait indefinitely for renderer failures to resolve before exploratory whole-cohort fork. Freeze all prompts and cases before F generation; incomplete old labels remain null. No confirmatory inference from this adaptive development cohort.','substantive_change':'P plan+full writer followed directly by source edit, with no supplied critic interpretation. Direct edit6144 versus old E edit5120; total allocated output16384 equals A0, no isolated claim about removing the critic alone.','inherited_epoch_limit':'Model alias immutable weights unverified; capture current metadata. Reusing actual old prefixes and baseline isolates a controlled fork in saved states, not same-time independent new generation.','no_novelty_or_success_claim':True}
    cfg['resource_allocation']={'recent_research_conservative_before_usd':0.30984678,'new_batch_cap_usd':0.25,'recent_scope_upper_after_usd':0.55984678,'lifetime_cost_claim':False,'no_credit_purchase':True,'F_prefix_cost_charged_but_not_repaid':True,'initial_plan4096_writer6144_new_edit6144_total16384':True}
    for k in ['arm_order','A0_new_calls','research_decision','resume_from','max_total_batch_calls','max_total_batch_usd','dispatcher_change','prior_case_ids_excluded_to_avoid_rerun']:
        cfg.pop(k,None)
    protected={};registry={};checks=[];client=Client(cfg,ROOT/'private/unused-preflight')
    for k,h in read(ROOT/'protected-v50-source.json')['files'].items():assert filehash(OLD/k)==h
    inherited_a0={x['tag']:x['receipt'] for x in read(OLD/'resume-registry.json')['previous_call_receipts']}
    for cid in cfg['case_ids']:
        dossier=read(OLD/'inputs'/(cid+'.json'));prefix=OLDWORK/'cases'/cid/'P'
        assert read(prefix/'input.json')==dossier
        for x in (OLD/'inputs'/(cid+'.json'),OLD/'inputs'/(cid+'-A0-request.json')):protected[str(x)]=filehash(x)
        for x in prefix.rglob('*'):
            if x.is_file():protected[str(x)]=filehash(x)
        a0=OLDWORK/'cases'/cid/'A0/final-report.txt';assert a0.exists();protected[str(a0)]=filehash(a0)
        recs=sorted((OLDWORK/'transport/calls').glob('*-'+cid+'-P-*/receipt.json'));assert len(recs)==2
        a0recs=list((OLDWORK/'transport/calls').glob('*-'+cid+'-A0/receipt.json'))
        a0receipt=a0recs[0] if a0recs else Path(inherited_a0[cid+'-A0'])
        for rec in recs+[a0receipt]:
            for x in rec.parent.iterdir():
                if x.is_file():protected[str(x)]=filehash(x)
        prefixout=read(prefix/'outcome.json');draft=(prefix/'final-report.txt').read_text()
        material={'originals':dossier,'source_plan':read(prefix/'resolved-plan.json'),'draft':draft,'draft_sha256':digest(draft),'plan_failed':any(x.get('stage')=='plan' for x in prefixout.get('failures',[]))}
        wire,body,pre=client.preflight(TRUST+'\n'+DIRECT_EDIT,material,6144);assert pre['fits'];assert json.loads(wire['messages'][1]['content'])==material
        assert all(x['domain'] in ('CASE','LAW') for x in dossier['sources'].values())
        target=ROOT/'inputs'/(cid+'.json');save(target,dossier)
        save(ROOT/'prepared-requests'/(cid+'-F-direct-edit.json'),wire)
        registry[cid]={'prefix_directory':str(prefix),'prefix_full_chain_completed':prefixout['full_chain_completed'],'prefix_report_sha256':filehash(prefix/'final-report.txt'),'prefix_receipts':[str(x) for x in recs],'prefix_conservative_usd':sum(read(x)['cost_usd'] for x in recs),'A0_report':str(a0),'A0_report_sha256':filehash(a0),'A0_receipt':str(a0receipt),'A0_conservative_usd':read(a0receipt)['cost_usd'],'preflight':pre}
        checks.append({'case_id':cid,**pre})
    assert sum(x['reserved_usd'] for x in checks)<=cfg['max_new_usd']
    save(ROOT/'protocol.json',cfg);save(ROOT/'protected-prefix-and-baseline.json',protected);save(ROOT/'prefix-registry.json',registry)
    save(ROOT/'whole-cohort-request-acceptance.json',{'at':utc(),'actual_case_count':10,'cached_actual_model_prefixes_not_ideal_intermediates':True,'all_case_source_bytes_preserved':True,'reference_annotations_or_A0_not_method_inputs':True,'no_model_or_network_calls':True,'new_calls_prepared':10,'reserved_new_upper_usd':sum(x['reserved_usd'] for x in checks),'rows':checks,'not_model_or_semantic_acceptance':True})
    print('PREPARED_ALL_TEN',sum(x['reserved_usd'] for x in checks),flush=True)


def protect():
    for p,h in read(ROOT/'protected-prefix-and-baseline.json').items():assert filehash(p)==h,p


def freeze():
    protect();save(ROOT/'service-metadata-frozen.json',service_metadata())
    files=[ROOT/'run.py',*sorted((ROOT/'src').glob('*.py')),*sorted((ROOT/'inputs').glob('*.json')),*sorted((ROOT/'prepared-requests').glob('*.json')),*[ROOT/n for n in ['protocol.json','protected-prefix-and-baseline.json','prefix-registry.json','whole-cohort-request-acceptance.json','service-metadata-frozen.json','README.md']]]
    for p in files:
        if p.suffix=='.py':ast.parse(p.read_text())
    save(ROOT/'freeze.json',{'at':utc(),'files':{str(p.relative_to(ROOT)):filehash(p) for p in files},'quality_verified':False});print('FROZEN',len(files),flush=True)


def run():
    frozen=read(ROOT/'freeze.json')
    for p,h in frozen['files'].items():assert filehash(ROOT/p)==h,p
    protect();cfg=read(ROOT/'protocol.json');registry=read(ROOT/'prefix-registry.json');WORK.mkdir(parents=True,exist_ok=False)
    save(WORK/'started.json',{'at':utc(),'pid':os.getpid(),'command':'V51 run.py run','frozen_sha256':filehash(ROOT/'freeze.json'),'API_model':cfg['parameters']['model'],'new_calls_planned':10,'baseline_reissued':False})
    client=Client(cfg,WORK/'transport');results=[];error=None
    try:
        for i,cid in enumerate(cfg['case_ids']):
            protect()
            if client.halt:results.append({'case_id':cid,'status':'NOT_RUN_SERVICE_HALTED','final_report_available':False});continue
            result=execute_f(client,read(ROOT/'inputs'/(cid+'.json')),WORK/'cases'/cid/'F',cfg['stage_output_caps'],Path(registry[cid]['prefix_directory']))
            result['inherited_prefix_conservative_usd']=registry[cid]['prefix_conservative_usd'];results.append(result)
            save(WORK/'progress'/(str(i+1).zfill(2)+'-'+cid+'.json'),{'at':utc(),'results':results,'resources':client.ledger(),'R':None,'H':None})
    except BaseException as exc:
        error={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()};save(WORK/'error.json',error);raise
    finally:
        ledger=client.ledger();done={x['case_id'] for x in results};slots=[]
        for cid in cfg['case_ids']:
            result=next((x for x in results if x['case_id']==cid),{'case_id':cid,'status':'NOT_COMPLETED_INTERRUPTED','final_report_available':False});path=WORK/'cases'/cid/'F/final-report.txt';slots.append({'case_id':cid,'result':result,'report_sha256':filehash(path) if path.exists() else None,'inherited_A0':registry[cid]['A0_report'],'inherited_A0_sha256':registry[cid]['A0_report_sha256']})
        out={'at':utc(),'terminal':True,'error':error,'slots':slots,'new_resources':ledger,'inherited_P_resources_usd':sum(x['prefix_conservative_usd'] for x in registry.values()),'inherited_A0_resources_usd':sum(x['A0_conservative_usd'] for x in registry.values()),'same_prefixes_used_for_P_and_F_no_double_payment':True,'R':None,'H':None,'goal_achieved':False,'independent_test':False}
        save(WORK/'outcome.json',out);save(WORK/'summary.json',{'at':utc(),'terminal':True,'final_reports':sum(x['result'].get('final_report_available',False) for x in slots),'full_chains_completed':sum(x['result'].get('full_chain_completed',False) for x in slots),'new_calls':ledger['new_calls'],'new_conservative_usd':ledger['new_conservative_usd'],'error':error,'goal_achieved':False});save(WORK/'exit.json',{'at':utc(),'exit_code':1 if error else 0})
    print('TERMINAL',len(results),ledger['new_calls'],ledger['new_conservative_usd'],flush=True)


if __name__=='__main__':
    {'prepare':prepare,'freeze':freeze,'run':run}[sys.argv[1]]()
