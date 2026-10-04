#!/usr/bin/env python3
"""Versioned local study preparation/import/verify. Never generates or publishes."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXECUTION_WRAPPER='Execute the attached complete task once, using only its supplied material and no external search or other conversations. Return the full final JSON in this chat; a downloadable JSON may also be provided. Do not use other versions of the case.'
sys.path.insert(0,str(ROOT))
from legal_bench.rules_verdict_v1 import legal_rule_support_study as method
from legal_bench.rules_verdict_v1.source_views import write_new


def read(path):return json.loads(Path(path).read_text())


def save_text(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if path.read_text()!=text:raise FileExistsError(str(path))
    else:path.write_text(text)


def verify(root):
    freeze=read(root/'run-freeze.json')
    bad=[name for name,h in freeze['files_sha256'].items() if method.sha((root/name).read_bytes())!=h]
    if bad:raise ValueError('FROZEN_BYTES_CHANGED '+str(bad))
    return dict(status='VERIFIED',files=len(freeze['files_sha256']),legal_correctness_certified=False)


def prepare_v23(root):
    root=root/'v23-development'
    if (root/'run-freeze.json').exists():return verify(root)
    units=read(root/'library/original-units.json'); descriptions=read(root/'library/admitted-descriptions.json')
    samples=read(root/'samples.json'); samples=samples.get('cases',samples) if isinstance(samples,dict) else samples
    config=method.V23_CONFIG; slots=[]; grouped=[]
    for n,sample in enumerate(samples):
        cid=sample['case_id'];path=root/'sources'/(cid+'-allowed.json'); original=read(path)
        view=method.legacy.reading_view(original['segments']);source={**original,'segments':view['segments']}
        write_new(root/'prepared'/cid/'reading-view.json',view)
        query=method.legacy.query_text(sample['issue'],sample['explicit_act_names'],sample['neutral_description'])
        result=method.retrieve_arms(units,{'L':descriptions},query,root/'indexes',config,
                                    excluded=sample.get('definite_scope_exclusions',{}))
        write_new(root/'prepared'/cid/'retrieval-trace.json',result)
        seen={}; order=['A','L'] if n%2==0 else ['L','A']
        for arm in order:
            selection=result['selected'][arm]
            if selection['run_status']!='OK':
                slots.append(dict(id='R%02d'%(len(slots)+1),case_id=cid,methods=[arm],status='BUDGET_ASSEMBLY_ERROR',answer=None));continue
            text=method.prompt(source,selection['units'],sample['question'],config)
            complete_submission=EXECUTION_WRAPPER+'\n'+text
            key=method.shared_key(cid,0,complete_submission,{'mode':'High','model':'Latest','exact_model':None})
            if key in seen:
                seen[key]['methods'].append(arm);continue
            tid='R%02d'%(len(slots)+1);target=root/'tasks'/(tid+'.txt');save_text(target,text)
            slot=dict(id=tid,case_id=cid,methods=[arm],replicate_id=0,status='NOT_STARTED',prompt_path=str(target.relative_to(root)),
                      complete_submission_hash=method.sha(complete_submission),attachment_sha256=method.sha(text),execution_wrapper=EXECUTION_WRAPPER,shared_key=key,input_characters=len(complete_submission),
                      legal_characters=selection['legal_characters'],case_ids=[s['id'] for s in source['segments']],law_ids=selection['selected_ids'])
            slots.append(slot);seen[key]=slot
        grouped.append(dict(case_id=cid,grouping='Ordinary lease development, not primary DRC cohort',same_treatment=len(seen)==1))
    write_new(root/'run-order.json',slots);write_new(root/'sharing.json',grouped)
    write_new(root/'output-schema.json',method.legacy.output_schema())
    for name in ['scripts/legal_rule_support_study.py','legal_bench/rules_verdict_v1/legal_rule_support_study.py',
                 'legal_bench/rules_verdict_v1/rule_retrieval_v21.py','legal_bench/rules_verdict_v1/authority_index.py',
                 'legal_bench/rules_verdict_v1/retrieve.py','legal_bench/rules_verdict_v1/final_v9.py']:
        dest=root/'freeze/code'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/name).read_bytes())
    files=[p for p in root.rglob('*') if p.is_file() and p.suffix!='.sqlite' and 'runs' not in p.parts]
    write_new(root/'run-freeze.json',dict(version=method.VERSION,configuration=config,
        files_sha256={str(p.relative_to(root)):method.sha(p.read_bytes()) for p in files},
        new_final_call_cap=4,retries=0,source_only_calls_already_planned=2,ordinary_High=True,
        no_primary_cohort_pooling=True,scope='Exposed source-screened ordinary lease development',
        final_template_unchanged=True,payload_warning_change='coverage_limit plus available dates/status retained and budgeted',
        final_answer_cost_not_just_description_coverage=True))
    return verify(root)


def import_final(root,tid,raw_path,url):
    root=root/'v23-development';verify(root)
    task=next(x for x in read(root/'run-order.json') if x['id']==tid)
    dest=root/'runs'/tid;dest.mkdir(parents=True,exist_ok=True)
    raw=Path(raw_path).read_bytes()
    raw_file=dest/'raw.txt'
    if raw_file.exists() and raw_file.read_bytes()!=raw:raise FileExistsError('Raw result differs')
    raw_file.write_bytes(raw)
    try:answer,status=method.legacy.parse_answer(raw.decode(),task['case_ids'],task['law_ids'])
    except (ValueError,UnicodeError) as err:answer=None;status=dict(run_status='FORMAT_ERROR',error=str(err))
    write_new(dest/'answer.json',answer)
    write_new(dest/'format-check.json',dict(**status,conversation_url=url,task=task,semantic_completion=False,
              model='Latest',mode='High',exact_model=None,exact_tokens=None,exact_generation_seconds=None))
    return status


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['prepare-v23','verify-v23','import-v23']);
    p.add_argument('--root',default=str(ROOT/'outputs/legal-rule-support-study-01'));p.add_argument('--run');p.add_argument('--raw');p.add_argument('--url')
    args=p.parse_args();root=Path(args.root)
    result=prepare_v23(root) if args.command=='prepare-v23' else verify(root/'v23-development') if args.command=='verify-v23' else import_final(root,args.run,args.raw,args.url)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
