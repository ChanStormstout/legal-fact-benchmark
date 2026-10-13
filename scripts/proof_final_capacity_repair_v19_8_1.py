#!/usr/bin/env python3
"""Versioned correction after a deterministic tokenizer-shape fault; no generation."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import proof_pipeline_contract_v19_8 as entry
from scripts.proof_pipeline_diagnostic_v19_8 import OUT,CONFIG,frozen
from legal_bench.proof_carrying import final_delivery_v19_8_1 as delivery
NEW_CODE=['legal_bench/proof_carrying/'+s for s in ('capacity_v19_8_1.py','presentation_v19_8_1.py','final_delivery_v19_8_1.py')]+['scripts/proof_pipeline_contract_v19_8_1.py','scripts/proof_final_capacity_repair_v19_8_1.py','tests/test_final_capacity_v19_8_1.py']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    protocol=frozen();out=OUT/'capacity-correction-01'
    result=subprocess.run([sys.executable,'-m','unittest','tests.test_final_capacity_v19_8_1','-v'],cwd=ROOT,capture_output=True,text=True)
    entry.text(out/'tests.txt',result.stdout+result.stderr)
    if result.returncode:raise RuntimeError('CAPACITY_ACCEPTANCE_FAILED')
    entry.save(out/'diagnosis.json',{'original_capacity':'../final-capacity.json','original_token_counts_invalid':True,
        'root_cause':'len(BatchEncoding) counted its input_ids/attention_mask fields instead of the actual token ID array.',
        'actual_shape':'Mapping with flat input_ids','first_detected_in':'FROZEN_LOCAL_TOKENIZER_REPLAY_BEFORE_ANY_GENERATION',
        'affected_scope':'Six V19_8 final-preparation capacity observations only; no generation/weights/P conversion or rule computation affected.',
        'preserved_original_bad_capacity_record':True,'no_extra_model_call':True,
        'same_legal_semantics':'V19_8 processing unchanged; presentation adds exact repeated subtrees, reversible and non-semantic.',
        'old_generation_not_replayed':True})
    code={s:sha(ROOT/s) for s in NEW_CODE}
    entry.save(OUT/'freeze/final-capacity-revision-01.json',{'version':'V19_8_FINAL_DELIVERY_2','frozen_at':entry.utc(),
        'base_protocol_sha256':sha(OUT/'freeze/protocol.json'),'new_code_hashes':code,'config':CONFIG,
        'processing_rule_source_P_unchanged':True,'capacity_shape_policy':'Mapping input_ids / flat list / singleton batch; all nonnegative integer IDs, reject unsupported shape.',
        'presentation_policy':'Exact repeated JSON values of at least160serializedcharacters; one-level original-value pool; complete roundtrip equality required.',
        'tests':4,'new_model_calls':0,'stop':'Recalculate saved-input capacity only; no model dispatch.'})
    for s in NEW_CODE:entry.text(out/'code'/s,(ROOT/s).read_text())
    from transformers import AutoTokenizer
    model_path=(ROOT/'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip()
    tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True);rows=[]
    for t in protocol['tasks']:
        f,part=entry.context({'case_id':t['case_id'],'part_contract':t['part_contract']})
        cached=entry.read(OUT/'replay'/t['case_id']/'entry.json')
        for method in ('A','C','D'):
            value=delivery.task(f['case'],f['rules'],cached,method,part,full_rules=f['full_rules'])
            cap=delivery.capacity(value,tokenizer,CONFIG);dest=out/'final-material'/t['case_id']/method
            entry.save(dest/'task.json',value);entry.text(dest/'prompt.txt',value['prompt']);entry.save(dest/'schema.json',value['schema']);entry.save(dest/'capacity.json',cap)
            old=entry.read(OUT/'final-material'/t['case_id']/method/'task.json')
            rows.append({'case_id':t['case_id'],'method':method,**cap,'input_sha256':value['input_sha256'],
                'prompt_characters':len(value['prompt']),'source_count':len(value['source_ids']),
                'source_alias_count':len(value['P_source_aliases']),'source_ids_unchanged':value['source_ids']==old['source_ids'],
                'presentation_audit':value['presentation_audit'],'generated':False})
    entry.save(out/'final-capacity.json',{'rows':rows,'tests':4,'tokenizer_path':model_path,
        'tokenizer_revision':'8b2b98c00a6b4d291155e4890773ca8f769aee53','thinking':False,
        'config_hashes':{s:sha(Path(model_path)/s) for s in ('tokenizer_config.json','config.json') if (Path(model_path)/s).is_file()},
        'model_loaded':False,'model_calls':0,'local_operation_budget_not_native_limit':True})
    assert all(sha(ROOT/s)==h for s,h in code.items()),'Final revision changed during replay'
if __name__=='__main__':main()
