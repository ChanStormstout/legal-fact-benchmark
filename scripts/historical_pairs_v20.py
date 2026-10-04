"""Four-case source-preserving web pairs; no inference, retrieval, or repairs."""
import argparse
import copy
import hashlib
import json
import random
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.application_chain_v18 import APPLICATION_REQUIREMENTS
from legal_bench.rules_verdict_v1.final_v9 import EXAMPLES, final_schema
from legal_bench.rules_verdict_v1.rule_application_v17 import parse_final, restore_evidence

OUT = Path('outputs/rules-verdict-v20-four-case-pairs')
PARENT = Path('outputs/rules-verdict-v19-historical-pairs')
CASES = ['197892008', '65127929', '39942283', '1033921']
WINDOWS = {'197892008':(68,90), '65127929':(79,106), '39942283':(69,156), '1033921':(52,63)}
QUESTION = ('Using only the supplied allowed record and legal materials, assess whether company amalgamation '
            'or statutory corporate succession supports the landlord\'s claimed eviction ground under Delhi '
            'Rent Control Act section14(1)(b) against the successor occupant. Explain the relevant tenancy, '
            'transfer/possession, consent, statutory-succession and identity arguments where present. '
            'Assess this ground only: do not decide unrelated arrears, repairs, limitation, joinder, or the '
            'overall proceeding outcome. Distinguish unresolved factual premises from unresolved legal effects. '
            'Do not reconstruct the withheld target court\'s final reasoning or disposition.')
FINAL = '''Return exactly one complete JSON object, followed by END. No follow-up questions or alternative draft.
outcome: SUPPORT_GROUND, OPPOSE_GROUND, UNDETERMINED, or UNSUPPORTED, for the fixed ground only.
grounds: at most six decisive propositions. Each has point (one short proposition, no explanation), case_refs and law_refs (source IDs actually supplied in this task), assessment (SUPPORTED/REFUTED/UNRESOLVED/UNSUPPORTED), and explanation (normally1-3 sentences connecting objects, statement status, rule scope, opposition and any decisive gap).
assessment evaluates the proposition in point, not whether eviction is favored. A supported defense may oppose eviction. Unknown is not refutation. reason:1-2 sentences explaining the legal consequence of the grounds, without adding new facts or law.
Keep supported findings at their actual court level and stage, even if another issue is unresolved. Do not convert allegations or arguments into findings, or treat prior outcomes as proof of unstated conditions. Do not confuse a merger's vesting effect with immunity from tenancy restrictions. Missing withheld target reasoning is not itself a factual gap.
Be concise while preserving decisive contrary evidence and scope limitations. Never cite fictional example IDs, cards, or instructions as source evidence. A case name mentioned in a submission is not the full authority's verified holding. Use only the materials supplied here; no external search, other case versions, other chats or project history.
'''
CODE = ['scripts/historical_pairs_v20.py','legal_bench/rules_verdict_v1/application_chain_v18.py',
        'legal_bench/rules_verdict_v1/final_v9.py','legal_bench/rules_verdict_v1/rule_application_v17.py',
        'legal_bench/rules_verdict_v1/contracts.py']
read = lambda p: json.loads(Path(p).read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2); f.write('\n')


def view(cid):
    p = PARENT/'sources'/f'{cid}-rendered-lines.json'; parent = read(p)
    lo,hi = WINDOWS[cid]; by_id={s['line']:s for s in parent['lines']}
    segments=[]; lineage=[]
    for n in range(lo,hi+1):
        raw=by_id[n]['renderings'][0]['rendered_text']
        text=re.sub(r'cite[^†]*†([^]*)', r'\1', raw).strip()
        if not text: continue
        sid=f'CASE:{cid}:L{n}'
        segments.append({'id':sid,'text':text})
        lineage.append({'id':sid,'parent_line':n,'parent_rendering_index':0,'raw_parent_path':by_id[n]['renderings'][0]['raw_path'],
                        'transformation':'Remove web hyperlink wrapper retaining its visible label; trim rendering boundary whitespace. No paraphrase or fact substitution.'})
    return {'case_id':cid,'court':parent['court'],'date':parent['date'],'proceeding':parent['proceeding'],
            'segments':segments,'scope':'Complete selected pre-target-analysis window, not complete judgment or prelitigation facts.',
            'parent_path':str(p),'parent_sha256':sha(p),'selected_line_range':[lo,hi],'lineage':lineage}


def base_law():
    p=Path('outputs/rules-verdict-v18-application-chain/prepared/661475/law-package.json')
    package=read(p)['original_common_package']; src={s['id']:s for s in package['law_segments']}
    a=src['LAW:1134266:p0004.s004']; b=src['LAW:1134266:p0004.s005']
    tail='writing of the landlord'; end=b['text'].index(tail)+len(tail)
    segments=[{'id':'LAW:BASE:DRC:S14:1','text':a['text']}, {'id':'LAW:BASE:DRC:S14:2','text':b['text'][:end]}]
    return {'role':'BASIC_STATUTORY_QUOTE_NOT_CASE_RULE_OR_FULL_ACT', 'law_segments':segments,
            'provenance':{'parent_path':str(p),'parent_sha256':sha(p),'source_judgment':'Singer India,2004; other case, not any of the four targets',
                          'original_segment_ids':[a['id'],b['id']],'slices':[[0,len(a['text'])],[0,end]],'no_judicial_interpretation_after_quote_included':True},
            'coverage_limits':['Existing judicial quotation of section14(1), not a new independently acquired Act version.',
                               'OCR/control characters preserved via JSON escaping; do not interpret them as law.',
                               'No full Banking Regulation Act or banking acquisition scheme is supplied beyond what the target record quotes or describes.']}


def prompt(source, basic, supplement):
    extra=('\nADDITIONAL HISTORICAL RULE MATERIAL (other cases, not target facts)\n'+json.dumps(supplement,ensure_ascii=False)+'\nEND ADDITIONAL HISTORICAL RULE MATERIAL\n') if supplement else ''
    return ('SELF-CONTAINED LEGAL DEVELOPMENT TASK\nQuestion: '+QUESTION+'\n'
            'Target case: '+json.dumps({k:source[k] for k in ['case_id','court','date','proceeding']})+'\n'
            'Scope: retrospective legal-ground analysis with visible prior-court information; not independent prediction. Target final reasons/outcome are withheld.\n'
            'Read the complete supplied material; do not browse externally or use other conversations.\n'
            'TWO COMPLETE FICTIONAL TEACHING EXAMPLES (NOT target facts or law)\n'+json.dumps(EXAMPLES,ensure_ascii=False)+'\n'
            'BASIC LEGAL MATERIAL\n'+json.dumps(basic,ensure_ascii=False)+'\n'+extra+
            'COMPLETE ALLOWED TARGET RECORD\n'+'\n'.join('['+s['id']+'] '+s['text'] for s in source['segments'])+'\n'
            'APPLICATION CHAIN\n'+APPLICATION_REQUIREMENTS.replace('under the unchanged schema','under the supplied schema')+'\n'
            'FINAL OUTPUT REQUIREMENTS\n'+FINAL)


def prepare():
    if (OUT/'freeze.json').exists(): raise ValueError('Existing frozenV20: continue, do not prepare twice')
    start=read(OUT/'start-audit.json')
    for p,h in {**start['historical_output_sha256'],**start['code_at_start']}.items():
        if sha(p)!=h: raise ValueError('Starting source/code changed: '+p)
    assert str(OUT) in read('docs/repository-artifacts.json')['artifact_roots']
    basic=base_law(); oldpack_path=Path('outputs/rules-verdict-v15-rule-supplement/rule-package.json'); oldpack=read(oldpack_path)
    supp={'role':'SOURCE_ANCHORED_RULE_EXTRACTION_NOT_INDUCTION; RESEARCHER_SELECTED_ADDITIONAL_INFORMATION',
          'rule_cards':oldpack['rule_cards'],'law_segments':oldpack['law_segments'],
          'source_limitations':'Preserve each card scope/limits, original OCR, provisional/reserved views and reported precedent. This is not an exhaustive legal corpus or automatically retrieved authority.'}
    save(OUT/'rules/basic-law.json',basic);save(OUT/'rules/supplement.json',supp)
    save(OUT/'rules/lineage.json',{'supplement_parent':str(oldpack_path),'sha256':sha(oldpack_path),'card_values_unchanged':True,'passage_values_unchanged':True,
                                  'authority_dates':['1980-12-05','1986-04-17','1988-09-19'],'same_supplement_all_cases':True,
                                  'old_project_specific_coverage_notes_not_model_input':True,'new_authorities':0})
    # Same shape/schema for both conditions; source availability is validated offline.
    schema=final_schema(['unused-case'],['unused-law'])
    props=schema['properties']['grounds']['items']['properties']
    for key in ['case_refs','law_refs']:props[key]['items']={'type':'string'}
    save(OUT/'output-schema.json',schema)
    ready=[];checks=[]
    for cid in CASES:
        source=view(cid);save(OUT/'sources'/f'{cid}.json',source)
        # Boundaries manually source-reviewed once before freeze; exclude all later target analysis.
        sources=source['segments'];assert sources and all(WINDOWS[cid][0]<=int(s['id'].split('L')[-1])<=WINDOWS[cid][1] for s in sources)
        check={'case_id':cid,'selected_range':list(WINDOWS[cid]),'status':'READY_WITH_RECORDED_SCOPE_LIMITATIONS','target_final_reason_included':False,
               'lower_court_or_party_argument_included':True,'known_relationships':'V19 candidate-decisions.json; no proven global independence or exposure absence',
               'company_type':'COMPANY_PROPOSED' if cid=='197892008' else 'BANK_STATUTORY_SUCCESSION','temporal_role':'All supplement decisions precede target decision; not necessarily transaction. Retrospective task.'}
        checks.append(check);ready.append(cid)
        for condition in ['A','B']:
            p=prompt(source,basic,supp if condition=='B' else None)
            if condition=='B':
                block='\nADDITIONAL HISTORICAL RULE MATERIAL (other cases, not target facts)\n'+json.dumps(supp,ensure_ascii=False)+'\nEND ADDITIONAL HISTORICAL RULE MATERIAL\n'
                assert p.replace(block,'',1)==prompt(source,basic,None),'A/B differ outside extra rule material'
            folder=OUT/'tasks'/cid/condition;folder.mkdir(parents=True)
            (folder/'prompt.txt').write_text(p,encoding='utf-8')
            task=p+'\nOUTPUT SCHEMA (format specification; no web per-token enforcement)\n'+json.dumps(schema,ensure_ascii=False)+'\n'
            (folder/'task.txt').write_text(task,encoding='utf-8')
            (folder/'submission-text.txt').write_text('Read the complete attached self-contained task and return one complete JSON answer followed by END. Use only its supplied case and law; no external search, other chats or added materials. Ordinary High, not Pro. Do not discuss the project or request clarification.',encoding='utf-8')
    save(OUT/'preparation-checks.json',{'rows':checks,'exact_pair_difference_check':'PASS','shape_schema_identical':'PASS','source_line_addresses_valid':'PASS','source_semantics_not_certified':True})
    rng=random.Random(20261003); repeats=rng.sample(CASES,2); order=[];initial={}
    for i,cid in enumerate(CASES):
        conditions=['A','B'] if i%2==0 else ['B','A'];initial[cid]=conditions
        for c in conditions:order.append({'run_id':f'R{len(order)+1:02d}','case_id':cid,'condition':c,'replicate':1,'task_path':str(OUT/'tasks'/cid/c/'task.txt')})
    for cid in repeats:
        for c in reversed(initial[cid]):order.append({'run_id':f'R{len(order)+1:02d}','case_id':cid,'condition':c,'replicate':2,'task_path':str(OUT/'tasks'/cid/c/'task.txt')})
    save(OUT/'run-order.json',{'seed':20261003,'cases':CASES,'repeat_case_ids':repeats,'order':order})
    protocol={'version':'V20','status':'FROZEN_BEFORE_FIRST_GENERATION','scope':'FOUR_NEW_TARGET_CANDIDATES_DEVELOPMENT_PAIRS_NOT_INDEPENDENT_TEST',
              'case_count':4,'max_web_answers':12,'ordinary_High_not_Pro':True,'model_display_observed':'High; exact model not yet displayed',
              'exact_model':None,'local_calls':0,'paid_API_calls':0,'retries':0,'new_sources':0,'new_rule_cards':0,'seed':20261003,
              'information_difference':'B additionally receives researcher-selected three historical cards and seven original source passages. Not a card-format, retrieval or induction effect.',
              'failure':'Single technical failure does not block independent runs; preserve raw/null. Access/environment or substantive frozen-material error stops batch. Resume only unsubmitted steps.',
              'per_condition_observation_limit_minutes':15,'review':'One concentrated source review after batch; neutral IDs before revealing A/B; not fully blind, not human gold.',
              'stop':'After planned12 answers or access blocker; no corrections, extra cases/rules, semantic repairs, next round, commit or push.'}
    save(OUT/'protocol.json',protocol)
    save(OUT/'evaluation-rules.json',{'not_model_input':True,'categories':['B_NET_IMPROVEMENT','AB_CLOSE','B_WORSE','INDETERMINATE'],
                                    'dimensions':['Fact/speaker/court-stage fidelity','Rule premise/exception/scope','Decisive facts and opposing argument coverage','Point/assessment/explanation/reason consistency','Real decisive gap vs fabricated absence'],
                                    'not_success':['Longer','More citations','Confident outcome','Less unknown','Historical target outcome agreement'],
                                    'unit':'Case basic pair; repeated pairs separate. No weighted score or fact-level pseudo-sample.',
                                    'repeat_direction_reversal_must_be_reported':True,'reference':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD'})
    for p in CODE:
        dest=OUT/'freeze/code'/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    files={str(p):sha(p) for p in OUT.rglob('*') if p.is_file()}
    save(OUT/'freeze.json',{'frozen_at':datetime.now(timezone.utc).isoformat(),'files':files,'code':{p:sha(p) for p in CODE},'max_calls':12,'before_first_generation':True})
    print(json.dumps({'ready':ready,'repeat_cases':repeats,'order':order,'task_bytes':{f'{c}/{k}':(OUT/'tasks'/c/k/'task.txt').stat().st_size for c in CASES for k in ['A','B']}},indent=2))


def verify():
    frozen=read(OUT/'freeze.json');start=read(OUT/'start-audit.json')
    for p,h in {**start['historical_output_sha256'],**start['code_at_start'],**frozen['files'],**frozen['code']}.items():
        if sha(p)!=h:raise ValueError('Frozen/historical bytes changed: '+p)
    return {'status':'PASS','old_files':len(start['historical_output_sha256']),'old_code':len(start['code_at_start']),'frozen_files':len(frozen['files'])}


def collect(run_id, raw_path, metadata_path):
    verify();row=next(x for x in read(OUT/'run-order.json')['order'] if x['run_id']==run_id)
    folder=OUT/'runs'/run_id
    if folder.exists():raise ValueError('Existing result: no duplicate import or overwrite')
    folder.mkdir(parents=True);raw=Path(raw_path).read_text();metadata=read(metadata_path)
    (folder/'raw-response.txt').write_bytes(Path(raw_path).read_bytes())
    (folder/'submitted-task.txt').write_bytes(Path(row['task_path']).read_bytes())
    save(folder/'run.json',{**row,**metadata,'generation_calls':1,'retries':0,'paid_API':False,'source_review_not_completed':True})
    try:
        answer,plain,fmt=parse_final(raw,read(OUT/'output-schema.json'))
        case=read(OUT/'sources'/f"{row['case_id']}.json")['segments'];law=read(OUT/'rules/basic-law.json')['law_segments']
        if row['condition']=='B':law+=read(OUT/'rules/supplement.json')['law_segments']
        known_cases={x['id'] for x in case};known_laws={x['id'] for x in law}
        invalid=[r for g in answer['grounds'] for r in g['case_refs'] if r not in known_cases]+[r for g in answer['grounds'] for r in g['law_refs'] if r not in known_laws]
        save(folder/'answer.json',answer);save(folder/'format-check.json',{**fmt,'invalid_source_ids':invalid,'citation_validity_not_semantic_support':True})
        if not invalid:save(folder/'restored-evidence.json',restore_evidence(answer,case,law))
        result={'run_status':'OK','outcome':answer['outcome'],'invalid_source_ids':invalid,'answer_path':str(folder/'answer.json')}
    except (ValueError,KeyError,TypeError) as e:
        save(folder/'answer.json',None);save(folder/'format-check.json',{'status':'FORMAT_ERROR','error':str(e),'no_content_repair':True})
        result={'run_status':'FORMAT_ERROR','outcome':None,'answer_path':str(folder/'answer.json')}
    save(folder/'result.json',result);print(json.dumps({**row,**result},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['prepare','verify','collect']);parser.add_argument('--run');parser.add_argument('--raw');parser.add_argument('--metadata');args=parser.parse_args()
    if args.mode=='prepare':prepare()
    elif args.mode=='verify':print(json.dumps(verify()))
    else:collect(args.run,args.raw,args.metadata)
