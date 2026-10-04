#!/usr/bin/env python3
"""Local preparation/import only. This entry point never calls a model or publishes."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from legal_bench.rules_verdict_v1 import rule_retrieval_v21 as method
from legal_bench.rules_verdict_v1.source_views import write_new


def read(path): return json.loads(Path(path).read_text())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text() != text: raise FileExistsError('Frozen text differs: '+str(path))
    else: path.write_text(text)


def verify(directory):
    directory = Path(directory); freeze = read(directory/'freeze.json')
    for name, expected in freeze['file_sha256'].items():
        if sha(directory/name) != expected: raise ValueError('Frozen bytes changed: '+name)
    return {'status': 'VERIFIED', 'frozen_files': len(freeze['file_sha256']),
            'legal_capability_certified': False}


def prepare(args):
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    if (out/'freeze.json').exists():
        existing = read(out/'freeze.json')
        supplied = {'units': sha(args.units), 'rules': sha(args.rules),
                    'samples': sha(args.samples), 'protocol': sha(args.protocol)}
        if existing['input_file_sha256'] != supplied: raise FileExistsError('Use a new version for changed inputs')
        return verify(out)
    units, cards, samples, protocol = read(args.units), read(args.rules), read(args.samples), read(args.protocol)
    if len(samples) > 8: raise ValueError('More than eight target cases')
    if len({s['case_id'] for s in samples}) != len(samples): raise ValueError('Duplicate targets')
    law_documents = {u['source']['document_id'] for u in units}
    if any(s['case_id'] in law_documents for s in samples): raise ValueError('Target judgment in legal corpus')
    for name, value in [('units',units),('rules',cards),('samples',samples),('protocol',protocol)]:
        write_new(out/'freeze'/('input-'+name+'.json'), value)
    for unit in units:
        origin = ROOT/unit['source']['original_path']
        original = read(origin)
        joined = '\n'.join(s['text'] for s in original.get('segments',original.get('pages',[])))
        start, end = unit['source']['joined_start'], unit['source']['joined_end']
        if joined[start:end] != unit['text']: raise ValueError('Legal unit differs from original: '+unit['id'])
        destination = out/'freeze'/'library-originals'/(unit['source']['document_id']+'.json')
        destination.parent.mkdir(parents=True,exist_ok=True)
        if destination.exists():
            if destination.read_bytes() != origin.read_bytes(): raise FileExistsError('Original source snapshot differs')
        else: destination.write_bytes(origin.read_bytes())
    tasks = []; pairs = []
    for index, sample in enumerate(samples):
        points = sample['evaluation_points']
        if not 3 <= len(points) <= 5: raise ValueError('Need 3-5 pre-generation decisive points')
        if sample.get('known_prior_answer_or_method_exposure') is not False:
            raise ValueError('Only explicitly unexposed targets; screening-only exposure separately recorded')
        source = read(ROOT/sample['source_path'])
        if sha(ROOT/sample['source_path']) != sample['source_sha256']: raise ValueError('Source hash changed')
        if not source.get('input_scope'): raise ValueError('Missing answer-isolation scope')
        view = method.reading_view(source['segments'])
        source['segments'] = view['segments']
        write_new(out/'prepared'/sample['case_id']/'reading-view.json', view)
        write_new(out/'freeze'/'sources'/(sample['case_id']+'.json'), source)
        query = method.query_text(sample['issue'], sample['explicit_act_names'], sample['neutral_description'])
        pair = method.retrieve_pair(units, cards, query, out/'indexes', sample.get('definite_scope_exclusions', {}))
        write_new(out/'prepared'/sample['case_id']/'retrieval.json', pair)
        pairs.append({'case_id': sample['case_id'], 'same_final_input': pair['legal_blocks_identical']})
        order = ['A','B'] if index % 2 == 0 else ['B','A']
        if pair['legal_blocks_identical']: order = ['SHARED_AB']
        for condition in order:
            route = 'A' if condition == 'SHARED_AB' else condition
            text = method.prompt(source, pair['selected'][route]['units'], sample['question'])
            task_id = 'R%02d' % (len(tasks)+1)
            save_text(out/'tasks'/(task_id+'.txt'), text)
            tasks.append({'id':task_id, 'case_id':sample['case_id'], 'condition':condition,
                          'prompt_path':'tasks/'+task_id+'.txt', 'prompt_sha256':sha(out/'tasks'/(task_id+'.txt')),
                          'input_characters':len(text), 'legal_characters':pair['selected'][route]['legal_characters'],
                          'case_ids':[s['id'] for s in source['segments']],
                          'law_ids':pair['selected'][route]['selected_ids']})
    if len(tasks) > 16: raise ValueError('Final answer budget exceeded')
    write_new(out/'run-order.json', tasks)
    write_new(out/'pair-inputs.json', pairs)
    write_new(out/'output-schema.json', method.output_schema())
    dependencies = ['scripts/rule_retrieval_v21.py', 'legal_bench/rules_verdict_v1/rule_retrieval_v21.py',
                    'legal_bench/rules_verdict_v1/authority_index.py', 'legal_bench/rules_verdict_v1/retrieve.py',
                    'legal_bench/rules_verdict_v1/source_views.py', 'legal_bench/rules_verdict_v1/final_v9.py']
    for name in dependencies:
        destination = out/'freeze'/'code'/name; destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if destination.read_bytes() != (ROOT/name).read_bytes(): raise FileExistsError('Snapshot differs')
        else: destination.write_bytes((ROOT/name).read_bytes())
    files = list((out/'freeze').rglob('*')) + [out/'run-order.json',out/'pair-inputs.json',out/'output-schema.json']
    files += list((out/'prepared').rglob('*.json')) + list((out/'tasks').glob('*.txt'))
    frozen = {str(f.relative_to(out)):sha(f) for f in files if f.is_file()}
    freeze = {'version':method.VERSION, 'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'input_file_sha256':{'units':sha(args.units),'rules':sha(args.rules),'samples':sha(args.samples),'protocol':sha(args.protocol)},
              'configuration':method.CONFIG, 'cases':len(samples), 'final_calls_planned':len(tasks), 'file_sha256':frozen,
              'no_model_called_by_preparation':True, 'empty_samples_are_not_a_negative_method_result':True}
    write_new(out/'freeze.json', freeze)
    return verify(out)


def import_answer(args):
    out = Path(args.out); verify(out)
    tasks = {t['id']:t for t in read(out/'run-order.json')}
    if args.run not in tasks: raise ValueError('Run not pre-registered')
    slot = out/'runs'/args.run
    if slot.exists(): raise FileExistsError('No overwrite or retry; existing run remains')
    slot.mkdir(parents=True)
    raw_bytes = Path(args.raw).read_bytes(); (slot/'raw.txt').write_bytes(raw_bytes)
    task = tasks[args.run]
    try:
        answer, status = method.parse_answer(raw_bytes.decode('utf-8'), task['case_ids'], task['law_ids'])
    except (ValueError, UnicodeError) as error:
        answer = None; status = {'run_status':'FORMAT_ERROR', 'format_status':'FORMAT_ERROR', 'error':str(error)}
    write_new(slot/'answer.json', answer)
    write_new(slot/'run.json', {**status, 'task':task, 'conversation_url':args.url,
                              'displayed_model':args.model_display, 'displayed_mode':args.mode,
                              'raw_sha256':hashlib.sha256(raw_bytes).hexdigest(),
                              'exact_tokens':None, 'exact_generation_seconds':None,
                              'no_semantic_or_format_completion':True})
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare')
    for flag in ['out','units','rules','samples','protocol']: p.add_argument('--'+flag, required=True)
    p = sub.add_parser('verify'); p.add_argument('--out',required=True)
    p = sub.add_parser('import')
    for flag in ['out','run','raw','url','model-display','mode']: p.add_argument('--'+flag,required=True)
    args = parser.parse_args()
    result = prepare(args) if args.command == 'prepare' else verify(args.out) if args.command == 'verify' else import_answer(args)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__': main()
