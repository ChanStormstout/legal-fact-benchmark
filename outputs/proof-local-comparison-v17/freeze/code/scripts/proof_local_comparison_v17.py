#!/usr/bin/env python3
"""Resumable V17 phases. Each generation attempt immutable, zero retries.

prepare -> local-P -> offline labels/reference -> encode -> fit -> final ->
blind evaluation. References and supervision cannot be read by final phase.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from legal_bench.proof_carrying.local_pipeline_v17 import (proposal_prompt, proposal_schema,
    final_prompt, FINAL_SCHEMA, audit, learner_inputs, reviewer_material)
from legal_bench.proof_carrying.local_evaluation_v17 import LABELS, CLAIM_RULE, blind_order, hash_value, local_metrics

OUT = ROOT / 'outputs/proof-local-comparison-v17'
DEV = ('136109','885778','121775','396336','1870386','180091','907531','732701','594273','948916')
CONDITIONS = ('A','B','C','D','E','F','G')
MODEL_ENV = ROOT / '.runtime/qwen35-v1/bin/python'

def read(p): return json.loads(Path(p).read_text())
def save(p, value):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    if p.exists():
        if p.read_text() != data: raise ValueError('IMMUTABLE_RECORD_MISMATCH:' + str(p))
    else: p.write_text(data)
def text(p, value):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        if p.read_text() != value: raise ValueError('IMMUTABLE_TEXT_MISMATCH:' + str(p))
    else: p.write_text(value)
def sha_file(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def fixture(cid): return read(OUT/'inputs'/cid/'fixture.json')

def prepare():
    if (OUT/'freeze/protocol.json').exists(): return read(OUT/'freeze/protocol.json')
    oldrows = read(ROOT/'outputs/proof-semantic-search-v12/continuation-02/supervision-35/rows.json')
    train = list(dict.fromkeys(str(r['case_id']) for r in oldrows if r['split']=='TRAIN'))
    if len(train) != 30: raise ValueError('FIXED_TRAIN_COUNT_CHANGED')
    queue = []; material_hashes = {}
    for split, cids in [('TRAIN',train),('DEV',DEV)]:
        for cid in cids:
            casefile = ROOT/'outputs/proof-semantic-search-v12/cohort'/cid/'case.json'
            case = read(casefile)
            if case['split'] != split or not any(q['id']=='Q1' for q in case['targets']): raise ValueError('SPLIT_OR_REQUEST_CHANGED')
            if sha_file(ROOT/case['source_path']) != case['source_sha256']: raise ValueError('SOURCE_HASH_CHANGED')
            if any(s['source_document'] != cid for s in case['segments']): raise ValueError('DOCUMENT_IDENTITY_CONFLICT')
            # Only the already given law drafts are taken from old proposals.
            # Old facts/bindings/uses/answers and reference labels are excluded.
            if split == 'TRAIN':
                row = next(r for r in oldrows if str(r['case_id']) == cid)
                rule_origin = ROOT/row['proposal_dir']/'input-snapshot.json'
                old = read(rule_origin)['raw_proposal']
            else:
                rule_origin = ROOT/'outputs/proof-semantic-interface-v13/dev-restored'/cid/'proposal.json'
                if not rule_origin.exists(): rule_origin = ROOT/'outputs/proof-semantic-search-v12/continuation-02/generated'/cid/'proposal/resolved.json'
                old = read(rule_origin)
            rules = old['rules']
            ps = [p['id'] for r in rules for p in r['premises']]
            if len(set(ps)) != len(ps): raise ValueError('DUPLICATE_PREMISE_ADDRESS')
            data = {'case':case, 'rules':rules, 'rule_origin':str(rule_origin.relative_to(ROOT)),
                    'rule_origin_hash':sha_file(rule_origin), 'selected_request':'Q1',
                    'old_semantic_proposal_excluded':True, 'rules_status':'GIVEN_MODEL_DRAFT_NOT_APPROVED'}
            save(OUT/'inputs'/cid/'fixture.json', data)
            prompt = proposal_prompt(case,rules); schema = proposal_schema(rules)
            text(OUT/'inputs'/cid/'P-prompt.txt',prompt); save(OUT/'inputs'/cid/'P-schema.json',schema)
            text(OUT/'inputs'/cid/'A-prompt.txt',final_prompt(case,rules,{}))
            material_hashes[cid] = {'fixture': hash_value(data), 'source_file':case['source_sha256'],
                                    'allowed_segments':hash_value(case['segments']), 'given_rules':hash_value(rules)}
            queue.append({'slot':len(queue)+1,'case_id':cid,'split':split,'role':'P','max_tokens':4096})
    for cid in DEV:
        for condition in CONDITIONS:
            queue.append({'slot':len(queue)+1,'case_id':cid,'split':'DEV','role':condition,'max_tokens':3072})
    settings = read(ROOT/'outputs/irac-semantic-interface-v6/freeze/config.json')
    save(OUT/'freeze/v6-config-provenance.json', settings)
    sources = ['legal_bench/proof_carrying/local_pipeline_v17.py','legal_bench/proof_carrying/local_evaluation_v17.py',
               'legal_bench/proof_carrying/local_fit_v17.py','legal_bench/proof_carrying/local_runtime_v17.py','scripts/proof_local_comparison_v17.py',
               'legal_bench/mlx_json_constraint_v2.py','legal_bench/rules_verdict_v1/runtime_constraint_diag_v1.py',
               'legal_bench/proof_carrying/quote_locator_v16.py','legal_bench/proof_carrying/semantic_interface_v13.py',
               'legal_bench/proof_carrying/semantic_models_v12.py','legal_bench/proof_carrying/state_ranker_v11.py',
               'legal_bench/proof_carrying/semantic_model_inputs_v13.py','scripts/proof_semantic_encode_v13.py']
    hashes = {p:sha_file(ROOT/p) for p in sources}
    for p in sources: text(OUT/'freeze/code'/p,(ROOT/p).read_text())
    evaluation = {
      'reference_status':'MODEL_GENERATED_SOURCE_REVIEWED_NOT_HUMAN_GOLD',
      'reference_freeze_before_any_DEV_final':True,
      'reference_policy':'Reuse independent Q1 sources; only missing/unclear/conflicting items may be supplemented. Preserve originals and revisions uniformly across all methods.',
      'reference_input_isolation':'DEV evaluation reference never enters local prompt, graph, candidates, checker acceptance policy, or final generation. DEV local classification labels used only for validation/evaluation, not gradients.',
      'claim_split_rule':CLAIM_RULE,
      'full_answer_primary_metrics':{
        'key_content_coverage':'correctly_handled_distinct_reference_items / all_frozen_key_items; correct sourced uncertainty counts; omitted/wrong items do not',
        'unsupported_judgement_rate':'confirmed_erroneous_or_unsupported_substantive_judgements / evaluable_distinct_substantive_judgements; disputes separate; zero denominator -> null',
        'major_error_dispute_proportion':'disputes_with_at_least_one_decisive_confirmed_error / semantically_evaluable_disputes'},
      'major_error_definition':'Decisive wrong source attribution, object, court stage, rule scope, necessary condition, or conclusion direction. Cosmetic differences excluded.',
      'overall_categories':['COMPLETE_AND_SOURCED','PARTIAL','MAJOR_ERROR','DISPUTED_OR_UNEVALUABLE'],
      'aggregation':'request metrics -> within-dispute means -> equal dispute weighting. Completion on all planned conditions; semantic metrics on eligible completed answers with denominators retained.',
      'local_metrics':['three_class_confusion','precision','recall','macro_f1','UNSUPPORTED_to_SUPPORTED_error_allow','SUPPORTED_to_UNSUPPORTED_error_block','UNRESOLVED_destinations_separate'],
      'local_baselines':['exact_same_semantics_raw_P_else_unmapped','TRAIN_label_prior_with_explicit_family_match_or_global_fallback'],
      'blind_evaluation':{'seed':20261001,'neutral_ids':True,'order':{cid:blind_order(cid,CONDITIONS) for cid in DEV},
        'limits':'Structure/content may reveal method; do not claim complete blinding. No method names/model confidence provenance shown to reviewer.'},
      'evaluation_evidence':'Complete allowed source plus frozen checklist; new out-of-checklist claims must be checked against source, never marked wrong merely because absent from checklist.',
      'decisive_disagreement_review':'One concentrated local source review; retain reference amendments and rescore ALL related conditions uniformly. No local answer retries.',
      'no_composite_score_or_forced_winner':True,
      'prediction_to_answer_trace':'connection id, raw P label, predicted label, audit/material consequence, final adoption/rejection/reinterpretation, source-grounded effect; common fixes not attributed to learners'}
    web_slots = []
    for cid in train: web_slots.append({'case_id':cid,'role':'TRAIN_connection_annotation','required_when':'local_P_readable'})
    for cid in DEV: web_slots.append({'case_id':cid,'role':'DEV_connection_annotation','required_when':'local_P_readable','evaluation_only':True})
    for cid in DEV: web_slots.append({'case_id':cid,'role':'reference_gap_patch','required_when':'existing_independent_reference_missing_unclear_or_conflicting_only','before_DEV_answers':True})
    for cid in DEV: web_slots.append({'case_id':cid,'role':'blind_final_evaluation','required_when':'one_or_more_answers_readable'})
    protocol = {'version':'V17','frozen_at':utc(),'phase':'METHOD_AND_EVALUATION_FROZEN; REFERENCE_CHECKLIST_AND_REALIZED_SUPERVISION_FROZEN_BEFORE_FITS_AND_DEV_FINALS',
      'task':'JUDGMENT_REASONING_RECONSTRUCTION','TRAIN':train,'DEV':list(DEV),'TEST_SEALED_READ':False,
      'request':'Q1_BY_EXISTING_ORDER','source_hashes':material_hashes,'code_hashes':hashes,
      'local_model':{'name':'mlx-community/Qwen3.5-9B-4bit','revision':'8b2b98c00a6b4d291155e4890773ca8f769aee53','mlx_vlm':'0.7.4','lmfe':'0.11.2','seed':20261001,'greedy':True,'repetition_penalty':1,'thinking':False,'context':32768,'mask':'FIXED_V2','P_max_tokens':4096,'final_max_tokens':3072},
      'context_policy':'Complete ordered allowed segments for every condition. Actual rendered input+reserved output checked before every call; oversize is technical null without truncation. No extra segmentation generation permitted under one-P-per-dispute cap. Recoverable learner source uses fixed cited windows, full-window encoding with maps.',
      'local_generation_slots':queue,'local_slot_cap':110,'total_local_generation_seconds_cap':28800,'per_call_seconds_cap':1200,
      'models':{'Flat':{'seed':20261001,'architecture':'V12_64hidden_2layers_same16relations','max_seconds':7200,'epochs':100,'early_stop':10,'AdamW_lr':.001,'weight_decay':.0001,'dropout':.1},
                'RGCN':{'seed':20261001,'architecture':'V12_64hidden_2layers_4bases_same16relations','max_seconds':7200,'epochs':100,'early_stop':10,'AdamW_lr':.001,'weight_decay':.0001,'dropout':.1},
                'CrossEncoder':{'seed':20261001,'architecture':'existing_ModernBERT_V12','max_seconds':86400,'epochs':6,'early_stop':2,'trainable':'layers20_21_head','layer_lr':2e-5,'head_lr':1e-4,'accumulate':16,'threads':4,'all_complete_windows':8192}},
      'max_fits':3,'fit_order':['Flat','RGCN','CrossEncoder'],'training_time_basis':'old CE approximately5.3h; source/peer information longer; one fixed 24h CE cap, no hyperparameter search',
      'label_contract':{'classes':LABELS,'unit':'specific_source_connection_with_bound_objects_status_stage_scope','SUPPORT_does_not_imply_TRUE':True,'opposition_can_be_SUPPORTED':True,'old_USABLE_not_renamed':True},
      'web_mode':'ordinary_High_actual_UI_recorded; noPro_noAPI','web_slots':web_slots,'web_slot_cap':60,'web_resource_policy':'maximum60one-shot slots, no retries/continuations; compatible cached refs reused; reference patch only demonstrated gaps. Access failure preserves unsubmitted slots for recovery.',
      'evaluation':evaluation,'retries':0,'extra_model_preruns':0,'new_cases':0,'new_law':0,'no_commit_push':True}
    save(OUT/'freeze/protocol.json',protocol); save(OUT/'freeze/evaluation-contract.json',evaluation)
    save(OUT/'freeze/final-schema.json',FINAL_SCHEMA)
    save(OUT/'freeze/web-call-list.json',web_slots)
    return protocol

def assert_frozen():
    p=read(OUT/'freeze/protocol.json')
    for path,sha in p['code_hashes'].items():
        if sha_file(ROOT/path)!=sha:raise ValueError('FROZEN_CODE_CHANGED:'+path)
    return p

def run_local(role):
    p=assert_frozen()
    if role=='final' and not (OUT/'freeze/reference-checklists-manifest.json').exists():raise ValueError('REFERENCES_NOT_FROZEN')
    from legal_bench.proof_carrying.local_runtime_v17 import Runner,SETTINGS
    model_path = (ROOT/'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip()
    settings=dict(SETTINGS);settings['timeout_seconds']=1200
    runner=Runner(model_path,settings)
    slots=[s for s in p['local_generation_slots'] if (s['role']=='P') == (role=='P')]
    for slot in slots:
        cid=slot['case_id']; tag=slot['role']; dest=OUT/'local'/cid/tag
        if (dest/'run.json').exists():continue
        if (dest/'start.json').exists():
            print('INCOMPLETE_ATTEMPT_NO_RETRY',cid,tag,flush=True);continue
        f=fixture(cid);case=f['case'];rules=f['rules']
        consumed=sum(read(x).get('elapsed_seconds',0) for x in (OUT/'local').glob('*/*/run.json'))
        remaining=p['total_local_generation_seconds_cap']-consumed
        if remaining<=0:
            save(dest/'run.json',{'run_status':'BUDGET_EXHAUSTED','answer':None});continue
        if tag=='P':prompt=proposal_prompt(case,rules);schema=proposal_schema(rules)
        else:
            inter={};pfile=OUT/'local'/cid/'P/parsed.json'
            if tag=='B':
                afile=OUT/'local'/cid/'A/parsed.json'
                if not afile.exists():save(dest/'run.json',{'run_status':'SKIPPED_A_DEPENDENCY','answer':None});continue
                inter={'previous_direct_answer_model_proposed':read(afile)}
            elif tag!='A':
                if not pfile.exists():save(dest/'run.json',{'run_status':'SKIPPED_P_DEPENDENCY','answer':None});continue
                pp=read(pfile);inter={'proposal':pp}
                if tag in ('D','E','F','G'):inter['program_checks']=audit(case,rules,pp)
                if tag in ('E','F','G'):
                    kind={'E':'Flat','F':'CrossEncoder','G':'RGCN'}[tag]
                    predfile=OUT/'training'/kind/'all-candidate-predictions.json'
                    if not predfile.exists():save(dest/'run.json',{'run_status':'SKIPPED_MODEL_FAILURE','answer':None});continue
                    predicted=[x for x in read(predfile) if x['key'].startswith(cid+'::')]
                    inter['fallible_model_review']=[{'connection_id':x['key'].split('::')[-1],
                        'assessment':LABELS[max(range(3),key=lambda k:x['probabilities'][k])],
                        'probabilities':x['probabilities'],'independent_approval':False} for x in predicted]
            prompt=final_prompt(case,rules,inter);schema=FINAL_SCHEMA
        meta=runner.run(prompt,schema,dest,slot['max_tokens'],min(1200,remaining),constraint_mode='FIXED')
        answer=read(dest/'parsed.json') if meta['run_status']=='OK' else None
        save(dest/'formal-answer.json',{'answer':answer,'status':meta['run_status']})
        if tag=='P' and answer is not None:
            save(dest/'offline-audit.json',audit(case,rules,answer))
            save(OUT/'inputs'/cid/'learner-inputs.json',learner_inputs(case,rules,answer))
            annotation_task(cid)
        if meta['run_status'] in ('OUT_OF_MEMORY','UNSUPPORTED'):
            save(OUT/'resource-stop.json',{'at':utc(),'case_id':cid,'role':tag,'reason':meta['run_status']});break

ANNOTATION_INSTRUCTION = '''Offline source-grounded annotation in English. Do not search outside the supplied source. No tested answer or old label is supplied. Judge each proposed connection in its exact object/statement status/court stage/scope. SUPPORTED means that this connection is supported, including a correct opposition or a correctly attributed claim. It does not mean the whole proposition is true. UNSUPPORTED means an incompatible or unsupported upgrade. UNRESOLVED means missing source or unresolved interpretive dispute. Do not force balance and do not rewrite proposals. Check decisive contrary source passages, not only the proposed quote. The P self-rating and justification are hidden; the actual claim remains visible. Return JSON {"connections":[{"connection_id":"K01","label":"SUPPORTED","basis":"...","refs":["sourceID"],"quote":"verbatim short excerpt","dispute":false}],"limitations":[]}, with exactly one row per listed connection. Ground every label in the supplied source; unresolved cannot be guessed into a negative label. Model source review is not human gold.'''

def annotation_task(cid):
    f=fixture(cid);pp=read(OUT/'local'/cid/'P/parsed.json');visible=reviewer_material(pp)
    for i,c in enumerate(visible['connections'],1):c['connection_id']='K%02d'%i
    task=ANNOTATION_INSTRUCTION+'\n'+json.dumps({'given_rules':f['rules'],'proposals':visible},ensure_ascii=False)+'\nALLOWED SOURCE:\n'+common_source(f['case'])
    text(OUT/'web/tasks'/cid/'connection-annotation.txt',task)

def common_source(case):
    from legal_bench.proof_carrying.local_pipeline_v17 import source_text
    return source_text(case)

def encode_plan():
    assert_frozen();texts={};plans={};graphs={};pairs={};inference=[]
    for cid in read(OUT/'freeze/protocol.json')['TRAIN']+list(DEV):
        path=OUT/'inputs'/cid/'learner-inputs.json'
        if not path.exists():continue
        f=fixture(cid);data=read(path);g=data['graph'];nodes=[]
        for n in g['nodes']:
            h=hashlib.sha256(n['text'].encode()).hexdigest();texts[h]=n['text'];nodes.append({'node':n['id'],'part_sha256':[h]})
        plans[cid]={'graph':nodes};graphs[cid]=g
        for pair in data['ce_pairs']:
            key=cid+'::'+pair['id'];pairs[key]=pair
            inference.append({'key':key,'case_id':cid,'dispute_id':f['case']['dispute_id'],'request_id':'Q1','use_id':pair['id'],'split':f['case']['split']})
    save(OUT/'encoding/texts.json',texts);save(OUT/'encoding/plans.json',plans);save(OUT/'encoding/graphs.json',graphs)
    save(OUT/'encoding/pairs.json',pairs);save(OUT/'encoding/inference-rows.json',inference)

def training_rows():
    from legal_bench.proof_carrying.quote_locator_v16 import source_match
    rows=[];unresolved=[]
    for base in read(OUT/'encoding/inference-rows.json'):
        cid=base['case_id'];file=OUT/'web/labels'/cid/'parsed.json'
        if not file.exists():unresolved.append({**base,'reason':'ANNOTATION_TECHNICAL_MISSING'});continue
        annotations=read(file)['connections'];matches=[x for x in annotations if x['connection_id']==base['use_id']]
        if len(matches)!=1:unresolved.append({**base,'reason':'LABEL_MISSING_OR_DUPLICATE'});continue
        row=matches[0];f=fixture(cid);sources={s['id']:{'document':s['source_document'],'original_line':s.get('original_line'),'text':s['text']} for s in f['case']['segments']}
        location=source_match(row,sources)
        if row.get('label') not in LABELS or location.get('error') or not row.get('basis'):
            unresolved.append({**base,'reason':'LABEL_NOT_SOURCE_TRACEABLE','raw_label':row,'location':location});continue
        conn=read(OUT/'local'/cid/'P/parsed.json')['connections'][int(base['use_id'][1:])-1]
        prem=next(p for rule in f['rules'] for p in rule['premises'] if p['id']==conn['premise_id'])
        family=prem.get('family') or 'EXACT_PROPOSITION:'+hash_value(prem['text'])
        rows.append({**base,'label':row['label'],'premise_family':family,'premise_address':conn['premise_id'],
                     'origin':'OFFLINE_MODEL_ANNOTATION_SOURCE_LOCATION_CHECKED_NOT_HUMAN_GOLD',
                     'basis':row['basis'],'source_location':location,'P_self_assessment':conn['self_assessment']})
    save(OUT/'freeze/training-rows.json',rows);save(OUT/'freeze/unsupervised-candidates.json',unresolved)
    save(OUT/'freeze/training-manifest.json',{'rows_hash':hash_value(rows),'unlabeled_hash':hash_value(unresolved),'inference_pool_hash':hash_value(read(OUT/'encoding/inference-rows.json')),
             'source_support_target':LABELS,'unlabeled_not_negative':True,'reference_labels_not_graph_features':True,'frozen_at':utc()})
    return rows

def fit(kind):
    import numpy as np
    from legal_bench.proof_carrying.local_fit_v17 import fit_graph,fit_ce
    from legal_bench.proof_carrying.semantic_model_inputs_v13 import graph_arrays
    protocol=assert_frozen();rows=read(OUT/'freeze/training-rows.json');inf=read(OUT/'encoding/inference-rows.json')
    if not any(r['split']=='TRAIN' for r in rows) or not any(r['split']=='DEV' for r in rows):raise ValueError('NO_SOURCE_GROUNDED_TRAIN_OR_DEV_LABELS; NOT_RANDOM_TRAINING')
    dest=OUT/'training'/kind
    if dest.exists():raise ValueError('NO_FIT_RESTART')
    deadline=time.monotonic()+protocol['models'][kind]['max_seconds']
    if kind=='CrossEncoder':
        return fit_ce(20261001,read(OUT/'encoding/pairs.json'),rows,dest,deadline,inference_rows=[r for r in inf if r['split']=='DEV'])
    vectors=np.load(OUT/'encoding/vectors.npz');graphs=read(OUT/'encoding/graphs.json');plans=read(OUT/'encoding/plans.json')
    d={fixture(cid)['case']['dispute_id']:graph_arrays(g,plans[cid],vectors) for cid,g in graphs.items()}
    import mlx.core as mx
    for g in d.values():
        for k in ('x','adj','edges'):g[k]=mx.array(g[k])
    return fit_graph(kind,20261001,d,rows,dest,deadline,inference_rows=[r for r in inf if r['split']=='DEV'])

def reference_tasks():
    """Reuse ALL existing Q1 reference content, not selected good answer fragments.
    Only missing source mappings/ambiguities are eligible for the patch task.
    No P, predicted labels, or new DEV answer is read in this phase."""
    from legal_bench.proof_carrying.quote_locator_v16 import source_match
    manifest=[]
    for cid in DEV:
        f=fixture(cid);case=f['case']
        original=ROOT/'outputs/proof-semantic-search-v12/continuation-02/generated'/cid/'reference/resolved.json'
        if not original.exists():original=ROOT/'outputs/proof-semantic-interface-v13/web'/cid/'reference/parsed.json'
        if not original.exists():
            existing=None;key_items=[];gaps=['INDEPENDENT_Q1_REFERENCE_MISSING']
        else:
            whole=read(original);matches=[x for x in whole['targets'] if x['id']=='Q1']
            if len(matches)!=1:raise ValueError('REFERENCE_REQUEST_ID_DUPLICATE_OR_MISSING')
            existing=matches[0];key_items=[];gaps=[]
            sources={s['id']:{'document':s['source_document'],'original_line':s.get('original_line'),'text':s['text']} for s in case['segments']}
            for category in ('necessary_premises','rules','major_opposition','gaps','limited_conclusion'):
                items=existing.get(category,[]);items=items if isinstance(items,list) else [items]
                for item in items:
                    value={'text':item} if isinstance(item,str) else dict(item)
                    kid='KEY%03d'%(len(key_items)+1);value.update(id=kid,category=category)
                    if value.get('quote') is not None and value.get('refs'):
                        loc=source_match(value,sources);value['location']=loc
                        if loc.get('error'):gaps.append({'id':kid,'reason':loc['error']})
                    else:gaps.append({'id':kid,'reason':'SOURCE_LOCATION_NOT_EXPLICIT'})
                    key_items.append(value)
        draft={'case_id':cid,'request_id':'Q1','reference_origin':str(original.relative_to(ROOT)) if original.exists() else None,
               'reference_origin_hash':sha_file(original) if original.exists() else None,
               'key_items':key_items,'gap_patch_needed':gaps,'basis_status':'MODEL_GENERATED_SOURCE_REVIEWED_NOT_HUMAN_GOLD',
               'scope':'CONFIRMED_KEY_ITEMS_NOT_FULL_RECALL','semantic_approval':False}
        save(OUT/'private/reference-drafts'/cid/'draft.json',draft)
        if gaps:
            instruction='''Offline evaluation-reference repair, not a tested answer. Reuse the existing independently produced Q1 checklist. Do not rewrite the complete checklist or add an expected winner. Only repair explicitly listed missing source mappings, unclear or conflicting items using the complete supplied judgment. Never see local P or tested answers. Preserve old versions. For each listed gap return its KEY id, verbatim source quote and exact refs, and whether KEEP, DISPUTED, REVISE or UNRESOLVED with a reason. REVISE requires both old and new text and source justification. An uncertain inference stays disputed. If independent reference is entirely missing, build sourced facts, objects/status/stage, rules/scope, major opposition/limits, permissible limited conclusion and unresolved issues for Q1. Final disposition cannot circularly prove itself. No external source. Output complete English JSON {"patches":[{"id":"KEY001","decision":"KEEP","refs":["sourceID"],"quote":"verbatim","reason":"source mapping only","revised_text":null}],"limitations":[]}. Do not fill in a missing source by guessing. This is model-assisted reference, not human gold.'''
            task=instruction+'\nEXISTING INDEPENDENT CHECKLIST AND SPECIFIC GAPS:\n'+json.dumps(draft,ensure_ascii=False)+'\nALLOWED JUDGMENT:\n'+common_source(case)
            text(OUT/'web/tasks'/cid/'reference-gap-patch.txt',task)
        else:
            save(OUT/'private/reference-ready'/cid/'checklist.json',draft)
        manifest.append({'case_id':cid,'reference_reused':existing is not None,'key_items':len(key_items),'specific_gap_count':len(gaps),'new_task_needed':bool(gaps)})
    save(OUT/'reference-reuse-inventory.json',manifest)

def freeze_references():
    from legal_bench.proof_carrying.quote_locator_v16 import source_match
    manifest=[]
    if any((OUT/'local'/cid/condition/'start.json').exists() for cid in DEV for condition in CONDITIONS):raise ValueError('REFERENCE_FREEZE_AFTER_DEV_ANSWER_FORBIDDEN')
    for cid in DEV:
        ref=read(OUT/'private/reference-drafts'/cid/'draft.json');case=fixture(cid)['case'];changes=[]
        if ref['gap_patch_needed']:
            patchfile=OUT/'web/reference-patches'/cid/'parsed.json'
            if not patchfile.exists():raise ValueError('REFERENCE_GAP_PATCH_NOT_AVAILABLE:'+cid)
            patches=read(patchfile)['patches'];index={x['id']:x for x in ref['key_items']}
            sources={s['id']:{'document':s['source_document'],'original_line':s.get('original_line'),'text':s['text']} for s in case['segments']}
            for p in patches:
                if p['id'] not in index:raise ValueError('PATCH_UNKNOWN_KEY')
                item=index[p['id']];old=dict(item)
                if p['decision'] in ('KEEP','REVISE'):
                    loc=source_match(p,sources)
                    if loc.get('error'):raise ValueError('REFERENCE_PATCH_QUOTE_NOT_LOCATED:'+cid+':'+p['id'])
                    item.update(refs=p['refs'],quote=p['quote'],location=loc)
                    if p['decision']=='REVISE':
                        if not p.get('revised_text') or not p.get('reason'):raise ValueError('UNSUPPORTED_REFERENCE_REVISION')
                        item['text']=p['revised_text']
                elif p['decision'] in ('DISPUTED','UNRESOLVED'):
                    item['evaluation_limit']=p['decision'];item['limit_reason']=p['reason']
                else:raise ValueError('INVALID_REFERENCE_PATCH_DECISION')
                changes.append({'old':old,'new':dict(item),'patch':p})
            expected={x['id'] for x in ref['gap_patch_needed'] if isinstance(x,dict)}
            if {x['id'] for x in patches}!=expected:raise ValueError('MISSING_OR_EXTRA_REFERENCE_PATCH')
        if not ref['key_items']:raise ValueError('NO_SCORABLE_REFERENCE_CHECKLIST')
        ref.update(frozen_before_DEV_answers=True,revision_changes=changes,frozen_at=utc())
        save(OUT/'private/frozen-references'/cid/'checklist.json',ref)
        manifest.append({'case_id':cid,'request_id':'Q1','checklist_sha256':sha_file(OUT/'private/frozen-references'/cid/'checklist.json'),'key_items':len(ref['key_items']),'model_reference_not_human_gold':True})
    save(OUT/'freeze/reference-checklists-manifest.json',manifest)

def blind_evaluation_tasks():
    from legal_bench.proof_carrying.local_evaluation_v17 import semantic_metrics
    p=assert_frozen()
    for cid in DEV:
        mapping=p['evaluation']['blind_evaluation']['order'][cid];answers=[]
        for neutral,condition in mapping.items():
            runfile=OUT/'local'/cid/condition/'run.json';answerfile=OUT/'local'/cid/condition/'formal-answer.json'
            if not runfile.exists():raise ValueError('UNFINISHED_PLANNED_LOCAL_SLOT:'+cid+':'+condition)
            status=read(runfile)['run_status'];value=read(answerfile)['answer'] if answerfile.exists() else None
            answers.append({'answer_id':neutral,'technical_status':status,'answer':value})
        ref=read(OUT/'private/frozen-references'/cid/'checklist.json');case=fixture(cid)['case']
        instruction='''Offline blind full-answer source evaluation. No method names are provided. Read the full allowed judgment and common frozen checklist; do not restrict source review to answer citations. Evaluate attributed facts, objects, court stage, rules/scope, major opposition, limits, linked reasoning and conclusion. OPEN_TEXT does not make a sourced answer automatically incomplete. Correctly explained real uncertainty can cover a checklist item. More length/citations/confidence or fewer unknowns do not prove quality. Check any new substantive claim against the original text even if absent from checklist. Real interpretive disputes remain DISPUTED, not forced errors. Technical failures have null answers and no semantic score. Score every planned neutral answer. Do not fix or regenerate answers. Model source review is not human gold.
For each OK answer return every reference key exactly once with status CORRECTLY_HANDLED/OMITTED/INCORRECT/DISPUTED and source reason. Enumerate distinct substantive judgements using the frozen split rule and classify SUPPORTED/CONFIRMED_ERROR_OR_UNSUPPORTED/DISPUTED/UNEVALUABLE. Provide exact source refs and brief verbatim quotes for decisive determinations. A major=true flag only for a confirmed error affecting reasoning/conclusion (attribution, object, stage, scope, necessary condition or conclusion direction). Cosmetic errors excluded. Overall is COMPLETE_AND_SOURCED/PARTIAL/MAJOR_ERROR/DISPUTED_OR_UNEVALUABLE; any confirmed major error requires MAJOR_ERROR. Return JSON {"answers":[{"answer_id":"ANSWER_01","technical_status":"OK","answer":null,"key_items":[{"id":"KEY001","status":"CORRECTLY_HANDLED","refs":["id"],"reason":"..."}],"substantive_judgements":[{"id":"J001","text":"single assessable proposition","status":"SUPPORTED","major":false,"refs":["id"],"quote":"verbatim","reason":"..."}],"overall":"PARTIAL"}],"reference_disagreements":[],"blinding_limitations":[]}. For failed answers return just answer_id, technical_status, answer:null. Do not invent precision tokens/times.'''
        task=instruction+'\nFIXED JUDGEMENT SPLIT RULE:\n'+CLAIM_RULE+'\nFROZEN REFERENCE:\n'+json.dumps(ref,ensure_ascii=False)+'\nNEUTRAL ANSWERS:\n'+json.dumps(answers,ensure_ascii=False)+'\nCOMPLETE ALLOWED SOURCE:\n'+common_source(case)
        text(OUT/'web/tasks'/cid/'blind-evaluation.txt',task)
        save(OUT/'private/blind-mappings'/cid/'mapping.json',mapping)

def baselines():
    from collections import Counter
    rows=read(OUT/'freeze/training-rows.json');train=[r for r in rows if r['split']=='TRAIN'];dev=[r for r in rows if r['split']=='DEV']
    global_counts=Counter(r['label'] for r in train);family={}
    for r in train:family.setdefault(r['premise_family'],Counter())[r['label']]+=1
    raw=[];prior=[]
    for r in dev:
        raw.append({'key':r['key'],'label':r['P_self_assessment'],'origin':'EXACT_V17_CONNECTION_SELF_ASSESSMENT_NOT_OLD_USABLE'})
        match=r['premise_family'] in family;c=family.get(r['premise_family'],global_counts);n=sum(c.values())
        prior.append({'key':r['key'],'probabilities':[c[x]/n for x in LABELS],'exact_family_match':match,'fallback':'GLOBAL_TRAIN_CLASSES' if not match else None,'matched_family':r['premise_family'] if match else None})
    save(OUT/'baselines/raw-P.json',{'predictions':raw,'metrics':local_metrics(raw,dev)})
    save(OUT/'baselines/TRAIN-prior.json',{'predictions':prior,'metrics':local_metrics(prior,dev),'class_counts':dict(global_counts),'family_matching':'EXACT_FAMILY_IF_PRESENT_ELSE_GLOBAL; NEVER_MATCH_BY_REUSED_ADDRESS'})

def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','P','final','encode-plan','training-rows','fit','reference-tasks','freeze-references','evaluation-tasks','baselines']);parser.add_argument('--kind',choices=['Flat','RGCN','CrossEncoder']);args=parser.parse_args()
    os.chdir(ROOT)
    if args.phase=='prepare':prepare()
    elif args.phase in ('P','final'):run_local(args.phase)
    elif args.phase=='encode-plan':encode_plan()
    elif args.phase=='training-rows':training_rows()
    elif args.phase=='fit':fit(args.kind)
    elif args.phase=='reference-tasks':reference_tasks()
    elif args.phase=='freeze-references':freeze_references()
    elif args.phase=='evaluation-tasks':blind_evaluation_tasks()
    elif args.phase=='baselines':baselines()

if __name__=='__main__':main()
