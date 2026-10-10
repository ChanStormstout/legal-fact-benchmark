#!/usr/bin/env python3
"""Assemble only the existing TRAIN/DEV candidate pool; never initialize a model."""
import json,sys,hashlib,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.proof_semantic_run_v13 import save
ROOT=Path('outputs/proof-semantic-interface-v13')
def main():
    graphs={};pairs={};contexts={};pool=[];coverage=[]
    inputroot=ROOT/(sys.argv[1] if len(sys.argv)>1 else 'final-model-inputs-02');out=ROOT/(sys.argv[2] if len(sys.argv)>2 else 'learner-bundle')
    for path in sorted(inputroot.glob('*/model-information-fullcontext.json')):
        cid=path.parent.name;case=json.loads((Path('outputs/proof-semantic-search-v12/cohort')/cid/'case.json').read_text())
        assert case['split'] in ('TRAIN','DEV')
        info=json.loads(path.read_text());graphs[case['dispute_id']]=info['graph'];contexts['case:'+cid]=info['shared_case_context']
        for pair in info['ce_pairs']:
            key=cid+'::'+pair['id'];pairs[key]=pair
            if case['split']=='DEV':
                use=next(x for x in info['shared_case_context']['P_uses'] if x['id']==pair['id'])
                pool.append({'key':key,'case_id':cid,'dispute_id':case['dispute_id'],'split':'DEV','request_id':use['request_id'],'use_id':use['id'],'label':'UNLABELED','valid':False,'reason':'INFERENCE_POOL_NOT_REFERENCE_SELECTED'})
        coverage.append({'case_id':cid,'split':case['split'],'raw_relation_records':len(info['shared_case_context']['raw_relations']),'explicit_encoded_relation_records':sum(x['encoded'] for x in info['graph']['relation_audit']),'preserved_unencoded_relation_records':sum(not x['encoded'] for x in info['graph']['relation_audit']),'rule_dependency_edges':info['rule_dependency_edges'],'edges_by_channel':dict(collections.Counter(str(x[2]) for x in info['graph']['edges'])),'restored_unique_source_segments':len(info['shared_case_context']['restored_source']),'candidate_uses':len(info['ce_pairs']),'reference_used':False,'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    for name,value in [('graphs.json',graphs),('pairs.json',pairs),('contexts.json',contexts),('inference-rows.json',pool)]:save(out/name,value)
    save(out/'relationship-and-input-coverage.json',{'cases':coverage,'methods':['Flat','RGCN','CrossEncoder'],'shared_information':'FULL_RAW_P_RULES_RELATIONS_AND_CITED_SOURCE_PLUS_FIXED_CONTEXT','actual_fit_count':0,'scope':'Prepared input; actual numerical loader/tokenizer receipts separate. No trained V13 model has consumed this input.'})
    print(json.dumps({'cases':len(graphs),'pairs':len(pairs),'DEV_candidate_pool':len(pool)}))
if __name__=='__main__':main()
