"""Offline cache/real-case acceptance. No generation, training, or publication."""
import argparse
import hashlib
import io
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from legal_bench.historical_contrasts_v1 import adapter, pipeline, provenance
from legal_bench.historical_contrasts_v1.contracts import ContractError, SCHEMAS, VERSION, digest, read_json, write_immutable

OUT=ROOT/'outputs/historical-contrasts-v1'
DECLARED=ROOT/'outputs/proof-declared-references-v20-4'
SHARED=ROOT/'outputs/proof-shared-sources-v20-3'
PARENT=ROOT/'outputs/proof-source-verification-v20/continuation-01'
REAL=ROOT/'outputs/proof-evidence-binding-rerun-v20-5'


def file_hash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_old(path):
    cid,part=path.parent.parent.name,path.parent.name
    prep=(DECLARED/'preparation'/cid/part if path.is_relative_to(DECLARED) else
          SHARED/'preparation'/cid/part if path.is_relative_to(SHARED) else PARENT/'preparation'/cid)
    f=read_json(prep/'fixture.json')
    scpath=prep/'original-schema.json' if (prep/'original-schema.json').exists() else path.parent/'schema.json'
    slot=next(s for s in read_json(PARENT/'freeze/protocol.json')['slots'] if s['case_id']==cid and s['part']['id']==part)
    raw=read_json(path)
    result=adapter.packet(f['case'],f['rules'],slot['part'],raw,read_json(scpath),query_id=f.get('selected_request'))
    if result['body']['legacy']['payload']!=raw:raise ContractError('CACHE_VALUES_CHANGED')
    return result,[path,prep/'fixture.json',scpath]


def load_real(cid,part):
    prep=REAL/'preparation'/cid/part;src=REAL/'local'/cid/part
    f=read_json(prep/'fixture.json');raw=read_json(src/'expanded.json')
    rvpath=REAL/'reviews'/cid/part/'binding-review.json'
    value=adapter.packet(f['case'],f['rules'],read_json(prep/'part.json'),raw,
        read_json(prep/'original-schema.json'),read_json(rvpath),read_json(src/'run.json')['run_status'],query_id=f.get('selected_request'))
    return value,[prep/'fixture.json',prep/'part.json',prep/'original-schema.json',src/'expanded.json',src/'run.json',rvpath]


def verify(neural_smoke=False,semantic_encoder=False):
    if str(OUT.relative_to(ROOT)) not in read_json(ROOT/'docs/repository-artifacts.json')['artifact_roots']:
        raise ContractError('UNREGISTERED_OUTPUT_ROOT')
    code=[*sorted((ROOT/'legal_bench/historical_contrasts_v1').glob('*.py')),
          ROOT/'tests/test_historical_contrasts_v1.py',Path(__file__).resolve(),
          *[ROOT/'legal_bench/proof_carrying'/name for name in ['spectral.py','evidence_binding_gate_v20_5.py',
             'evidence_binding_gate_v20_5_1.py','shared_sources_v20_3.py','declared_references_v20_4.py',
             'source_contract_v19.py','schema_contract_v19_6.py','rule_contracts_v19_7.py','local_pipeline_v19_8.py']],
          ROOT/'scripts/proof_pipeline_contract_v19_8.py']
    code_hashes={str(p.relative_to(ROOT)):file_hash(p) for p in code}
    run=OUT/'acceptance'/('run-'+digest([code_hashes,neural_smoke,semantic_encoder])[:16])
    stream=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromName('tests.test_historical_contrasts_v1')
    if not neural_smoke:
        suite=unittest.defaultTestLoader.loadTestsFromName('tests.test_historical_contrasts_v1.Contracts')
    tested=unittest.TextTestRunner(stream=stream,verbosity=1).run(suite)
    evidence={'tests_run':tested.testsRun,'failures':len(tested.failures),'errors':len(tested.errors),
              'skipped':len(tested.skipped),'successful':tested.wasSuccessful(),'neural_smoke':neural_smoke}
    write_immutable(run/'tests.json',evidence)
    if not tested.wasSuccessful():
        print(stream.getvalue());raise ContractError('TEST_ACCEPTANCE_FAILED')
    paths=[ROOT/r['origin'] for r in read_json(DECLARED/'engineering/cache-acceptance.json')['cache_rows']]
    paths.append(DECLARED/'local/569555/P01/expanded.json')
    input_hashes={};rows=[];cache_packets=[]
    for path in paths:
        before=file_hash(path);value,dependencies=load_old(path); b=value['body']
        for dep in dependencies:input_hashes[str(dep.relative_to(ROOT))]=file_hash(dep)
        prov=provenance.audit(value,ROOT);input_hashes.update(prov['original_files'])
        write_immutable(run/'private/cache-packets'/(value['sha256']+'.json'),value)
        old_entry=adapter.handoff(value)
        if old_entry['formal_answer'] is not None and b['contract_status']!='READY_FOR_CONDITIONAL_PROCESSING':
            raise ContractError('REAL_GATE_BYPASS')
        if file_hash(path)!=before:raise ContractError('OLD_CACHE_FILE_CHANGED')
        rows.append({'path':str(path.relative_to(ROOT)),'packet_sha256':value['sha256'],
            'case_id':b['case_id'],'part_id':b['part_id'],'source_count':len(b['sources']),
            'canonical_record_count':len(b['records']),'legacy_values_and_array_order_preserved':b['legacy']['payload']==read_json(path),
            'contract_status':b['contract_status'],'formal_answer_null':old_entry['formal_answer'] is None,
            'error_count':len(b['errors']),'original_span_check':prov})
        cache_packets.append(value)
    write_immutable(run/'cache-acceptance.json',{'count':len(rows),'rows':rows,
        'status_counts':dict(Counter(r['contract_status'] for r in rows)),
        'data_repaired':False,'training_calls':0,'generation_calls':0})
    # Four existing real outputs are read; not regenerated or relabeled.
    real=[]
    for cid,part in [('569555','P01'),('1187427','P01'),('1954254','P01'),('1954254','P02')]:
        value,dependencies=load_real(cid,part);prov=provenance.audit(value,ROOT)
        for dep in dependencies:input_hashes[str(dep.relative_to(ROOT))]=file_hash(dep)
        input_hashes.update(prov['original_files']);real.append(value)
        write_immutable(run/'private/real-packets'/(cid+'-'+part+'.json'),value)
    q=real[0]
    provider=None
    if semantic_encoder:
        from legal_bench.historical_contrasts_v1.encoder import encode
        cfg=read_json(ROOT/'outputs/gnn-irac-aligned-v2/text-cache/encoder.json')
        input_hashes['outputs/gnn-irac-aligned-v2/text-cache/encoder.json']=file_hash(ROOT/'outputs/gnn-irac-aligned-v2/text-cache/encoder.json')
        import torch
        torch.set_num_threads(2)
        provider=lambda release:encode(release,cfg)
    first=pipeline.run(q,real[1:],run/'private/real-569555-P01',run_id=run.name,neural_smoke=neural_smoke,feature_provider=provider)
    write_immutable(run/'real-case-summary.json',first)
    # Accepted normal path is synthetic and must be identified as such.
    from tests.test_historical_contrasts_v1 import fixture
    normal=pipeline.run(fixture(),[fixture('A'),fixture('B')],run/'private/synthetic-normal-path',run_id=run.name)
    write_immutable(run/'synthetic-normal-summary.json',{**normal,'scope':'SYNTHETIC_CONTRACT_FIXTURE_ONLY'})
    preserved=read_json(OUT/'preservation-before.json')
    changed=[name for name,h in preserved.items() if not (ROOT/name).is_file() or file_hash(ROOT/name)!=h]
    if changed:raise ContractError('PREEXISTING_FILES_CHANGED',detail=repr(changed))
    for name,h in input_hashes.items():
        if file_hash(ROOT/name)!=h:raise ContractError('INPUT_CHANGED_DURING_ACCEPTANCE',detail=name)
    for name,h in code_hashes.items():
        if file_hash(ROOT/name)!=h:raise ContractError('CODE_CHANGED_DURING_ACCEPTANCE',detail=name)
    write_immutable(run/'preservation-check.json',{'checked_old_files':len(preserved),'changed_old_files':0,
        'original_pause_preserved':read_json(PARENT/'pause-summary.json')['status'] if 'status' in read_json(PARENT/'pause-summary.json') else 'EXACT_BYTES_PRESERVED',
        'source_inputs_checked':len(input_hashes)})
    write_immutable(run/'freeze.json',{'code_hashes':code_hashes,'input_hashes':input_hashes,
        'schemas_sha256':digest(SCHEMAS),'schema_version':VERSION,'generation_calls':0,'training_calls':0,
        'serving_mode':'EXPOSED_DEVELOPMENT_NO_EFFECTIVENESS_CLAIM','test_or_sealed_read':False})
    write_immutable(run/'schema-registry.json',SCHEMAS)
    environment={'python':sys.version,'torch':None,'torch_geometric':None,'new_fit_calls':0}
    if neural_smoke:
        import torch,torch_geometric
        environment.update(torch=torch.__version__,torch_geometric=torch_geometric.__version__)
    write_immutable(run/'environment.json',environment)
    summary={'version':'HISTORICAL_CONTRASTS_V1','run':str(run.relative_to(ROOT)),
        'tests':evidence,'old_cache_count':len(rows),'cache_values_preserved':all(r['legacy_values_and_array_order_preserved'] for r in rows),
        'old_cache_status_counts':dict(Counter(r['contract_status'] for r in rows)),
        'real_case':first,'synthetic_normal_passed':normal['formal_answer_present'],
        'checked_preserved_files':len(preserved),'source_inputs_checked':len(input_hashes),
        'neural_smoke':neural_smoke,'semantic_encoder':semantic_encoder,'training_ready':False,
        'training_blockers':['NO_SOURCE_REVIEWED_RELEVANCE_LABELS_FOR_NEW_TASK','NO_REVIEWED_ROUTE_EQUIVALENCE_AND_OUTCOME_CONTRASTS',
                             'SOURCE_VIEW_NOT_REVIEWED_FOR_HIDDEN_OUTCOME_BLINDING']+([] if semantic_encoder else ['SEMANTIC_ENCODER_NOT_EXERCISED_IN_THIS_RUN']),
        'generation_calls':0,'training_calls':0,'commit_or_push':False,'main_entry_switched':False}
    write_immutable(run/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2));return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=['verify'])
    parser.add_argument('--neural-smoke',action='store_true')
    parser.add_argument('--semantic-encoder',action='store_true');args=parser.parse_args()
    local=ROOT/'.runtime/historical-contrasts-v1/site'
    if args.neural_smoke:sys.path.insert(0,str(local))
    verify(args.neural_smoke,args.semantic_encoder)
