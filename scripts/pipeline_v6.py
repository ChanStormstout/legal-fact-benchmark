"""Frozen three-case shared-retrieval A/B statutory-ground experiment."""
import argparse,json,sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import write_new,digest
from legal_bench.rules_verdict_v1.authority_index import build,search
from legal_bench.rules_verdict_v1.runtime import SETTINGS
from legal_bench.rules_verdict_v1.pipeline_v6 import extraction_schema,answer_schema,prompts,import_data,execute
R=Path('outputs/rules-verdict-v6-end-to-end');V3=Path('outputs/rules-verdict-v3');V2=Path('outputs/rules-verdict-v2');CASES=['661475','69305','1134266'];DATES={'661475':'1973-05-22','69305':'1989-08-08','1134266':'2004-08-13'}
def read(p):return json.loads(Path(p).read_text())
def prepare():
    refs=read(V2/'references/rule-materials-reference-v2.json');full={c['case_id']:read(c['source_path']) for c in read(V2/'protocol/sample.json')['development']}
    units=read(V2/'authorities/judgment-units.json');reference=[]
    for cid in CASES:
        source=read(V3/'sources'/(cid+'-allowed.json'));write_new(R/'sources'/(cid+'.json'),source)
        # For 1973/1989 explicitly retrospective leave-target-out demonstration. For 2004 earlier authorities only.
        candidates=[c for c in refs['rule_cards'] if c['source_case']!=cid and (cid!='1134266' or DATES[c['source_case']]<DATES[cid])]
        allowed={c['source_case'] for c in candidates};eligible=[u for u in units if u['source']['case_id'] in allowed]
        index=R/'retrieval'/cid/'index.sqlite';build(eligible,index)
        query='Delhi Rent Control Act 1958 14 subletting assignment parting possession tenant landlord written consent'
        hits=search(index,query,200);ranks={h['id']:h['rank'] for h in hits}
        ranked=sorted(candidates,key=lambda c:(min([ranks.get(e['case_id']+':'+e['segment_id'],10000) for e in c['evidence']]),c['rule_card_id']))
        selected=ranked[:4];legal_segments={};cards=[]
        for c in selected:
            card=copy.deepcopy(c)
            for e in card['evidence']:
                # Entire source paragraph of each existing rule evidence, not target judgment.
                seg=next(s for s in full[e['case_id']]['segments'] if s['id']==e['segment_id'])
                assert e['quote'] in seg['text']
                key='LAW:'+e['case_id']+':'+e['segment_id'];legal_segments[key]={'id':key,'text':seg['text'],'source_case':e['case_id']}
            cards.append(card)
        package={'target_case':cid,'cards':cards,'law_segments':list(legal_segments.values()),
          'scope':{'mode':'RETROSPECTIVE_LATER_AUTHORITY_DEMONSTRATION' if cid!='1134266' else 'EARLIER_AUTHORITY_WITH_LOWER_COURT_INFORMATION',
             'target_reasoning_and_own_cards_excluded':True,'law_version':'AS_QUOTED_NOT_VERIFIED_HISTORICAL_CONSOLIDATED_VERSION',
             'effect_limit':'Quoted statutory ground only; no full appeal disposition or general exception coverage',
             'card_provenance':'REUSED_WEB_MODEL_SOURCE_REVIEWED_RULE_EXTRACTION_NOT_HUMAN_GOLD',
             'compiled_logic':'RESEARCHER_CONFIGURATION_NOT_RULE_INDUCTION'}}
        write_new(R/'retrieval'/cid/'result.json',{'query':query,'hits':hits,'selected_card_ids':[c['rule_card_id'] for c in selected],'eligible_source_cases':sorted(allowed),'excluded_target_case':cid,'future_material_policy':package['scope']['mode']})
        write_new(R/'prepared'/cid/'law-package.json',package)
        # Input model only sees source, law package; never evaluation reference or V3 outputs.
        pa,pb=prompts(source,package);outscope=copy.deepcopy(source);outscope['segments']+=package['law_segments']
        for arm,p,schema in [('A',pa,answer_schema(outscope)),('B',pb,extraction_schema(source))]:
            dest=R/'prepared'/cid/arm;dest.mkdir(parents=True,exist_ok=True);f=dest/'prompt.txt'
            if f.exists() and f.read_text()!=p:raise ValueError('Changed prepared prompt')
            f.write_text(p);write_new(dest/'schema.json',schema)
        oldref=next(x for x in refs['case_materials'] if x['case_id']==cid)
        historical=oldref['historical_target'];checks=[]
        for ev in historical['evidence']:
            s=next((x for x in full[cid]['segments'] if x['id']==ev['segment_id']),None)
            checks.append({'evidence':ev,'exact':bool(s and ev['quote'] in s['text'])})
        reference.append({'case_id':cid,'historical_target':historical,'source_quote_checks':checks,'reference_status':'MODEL_REFERENCE_FULL_JUDGMENT_WITH_TARGET_REASONING_EVALUATION_ONLY',
           'same_issue_limit':'Historical reasons address eviction and possession; appeal result alone is not condition-level truth. Record compatible direction only, not accuracy.',
           'expected_ground_direction':'SUPPORT_GROUND','allowed_input_sufficiency':'NOT_INDEPENDENTLY_ESTABLISHED'})
    write_new(R/'references/evaluation-only.json',{'rows':reference,'never_in_model_input':True})
    files=['scripts/pipeline_v6.py','legal_bench/rules_verdict_v1/pipeline_v6.py','legal_bench/rules_verdict_v1/authority_index.py','legal_bench/rules_verdict_v1/conditions_v3.py','legal_bench/rules_verdict_v1/runtime.py','legal_bench/rules_verdict_v1/contracts.py','legal_bench/model_output.py','legal_bench/mlx_json_constraint.py','tests/test_pipeline_v6.py']
    for p in files:
        dest=R/'freeze/code'/p;dest.parent.mkdir(parents=True,exist_ok=True);raw=Path(p).read_bytes()
        if dest.exists() and dest.read_bytes()!=raw:raise ValueError('Frozen code changed')
        dest.write_bytes(raw)
    frozen=[p for p in R.rglob('*') if p.is_file() and p.suffix!='.sqlite' and p.name!='config.json']
    write_new(R/'freeze/config.json',{'cases':CASES,'settings':SETTINGS,'calls':{'A':3,'B':3,'repair':0,'maximum':6},'max_output_tokens':{'A':2048,'B':4096},
        'reuse_decision':'V3 conditions and V4/V5 selected spans do not extract complete ground conditions or use same law inputs; reuse sources/cards/runtime, not incompatible answers.',
        'missing_components_implemented':['shared retrieval/input package','narrow source-grounded conjunction and outcome interface','full three-case A/B report'],
        'no_cross_case_induction':True,'deep_review_maximum':3,'files':{str(p):digest(p.read_bytes()) for p in frozen}})
def run(cid,arm):
    from legal_bench.rules_verdict_v1.runtime import Runner
    f=read(R/'freeze/config.json')
    for p,h in f['files'].items():
        if digest(Path(p).read_bytes())!=h:raise ValueError('Frozen material changed '+p)
    runner=Runner(Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),f['settings'])
    dest=R/'runs'/cid/arm;meta=runner.run((R/'prepared'/cid/arm/'prompt.txt').read_text(),read(R/'prepared'/cid/arm/'schema.json'),dest,f['max_output_tokens'][arm])
    if arm=='B':
        if meta['run_status']=='OK':
            view=import_data(read(dest/'parsed.json'),read(R/'sources'/(cid+'.json')));write_new(dest/'imported.json',view);write_new(dest/'execution.json',execute(view,read(R/'prepared'/cid/'law-package.json')))
        else:write_new(dest/'execution.json',{'run_status':meta['run_status'],'outcome':None,'reason':'MODEL_TECHNICAL_FAILURE'})
def collect():
    rows=[];calls=[]
    for cid in CASES:
        a=read(R/'runs'/cid/'A/run.json');b=read(R/'runs'/cid/'B/run.json');calls.extend([a,b]);aa=read(R/'runs'/cid/'A/parsed.json') if a['run_status']=='OK' else None;bb=read(R/'runs'/cid/'B/execution.json')
        rows.append({'case_id':cid,'retrieval':read(R/'retrieval'/cid/'result.json'),'scope':read(R/'prepared'/cid/'law-package.json')['scope'],'A':{'run_status':a['run_status'],'answer':aa},'B':bb,
          'historical_direction':'SUPPORT_GROUND','A_direction_agreement':None if aa is None else aa['outcome']=='SUPPORT_GROUND','B_direction_agreement':None if bb['outcome'] is None else bb['outcome']=='SUPPORT_GROUND','not_accuracy':True})
    write_new(R/'results.json',{'rows':rows,'calls':len(calls),'web_calls':0,'seconds':sum(c.get('elapsed_seconds',0) for c in calls),'peak_memory_gb':max(c.get('peak_mlx_memory_gb',0) for c in calls),'technical_failures':sum(c['run_status']!='OK' for c in calls)})
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run','collect']);p.add_argument('--case',choices=CASES);p.add_argument('--arm',choices=['A','B']);a=p.parse_args()
    if a.action=='prepare':prepare()
    elif a.action=='run':run(a.case,a.arm)
    else:collect()
