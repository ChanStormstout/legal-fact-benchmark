"""Pinned local E5 inference. Full BPE token windows; no downloads or fitting."""
import hashlib
from pathlib import Path
from .contracts import ContractError, TASK, digest, validate
from .graph import check_features


def verify_tokenization(graph,features,tokenizer):
    check_features(graph,features);rows={r['uid']:r for r in features['coverage']}
    for n in graph['body']['nodes']:
        encoded=tokenizer(n['text'],add_special_tokens=False,truncation=False,return_offsets_mapping=True)
        row=rows[n['uid']]
        if row['token_ids']!=encoded['input_ids'] or row['offsets']!=[list(x) for x in encoded['offset_mapping']]:
            raise ContractError('INDEPENDENT_TOKEN_REPLAY_FAILED',detail=n['uid'])


def encode(graph,configuration,batch_size=32):
    import torch
    from transformers import AutoModel, AutoTokenizer
    g=validate(graph,'GraphRelease');path=Path(configuration['path'])
    if path.name!=configuration['revision'] or not path.is_dir():
        raise ContractError('ENCODER_REVISION_PATH')
    files={}
    for name in ('config.json','tokenizer.json','tokenizer_config.json','vocab.txt','special_tokens_map.json','model.safetensors','pytorch_model.bin'):
        p=path/name
        if p.is_file():files[name]=hashlib.sha256(p.read_bytes()).hexdigest()
    if not ('model.safetensors' in files or 'pytorch_model.bin' in files) or 'tokenizer.json' not in files:
        raise ContractError('MISSING_PINNED_ENCODER_FILES')
    tokenizer=AutoTokenizer.from_pretrained(path,local_files_only=True,use_fast=True)
    net=AutoModel.from_pretrained(path,local_files_only=True).eval()
    prefixes={'ISSUE':'query: ','DEFAULT':'passage: '}
    cfg={'method':'PINNED_E5_ALL_TOKEN_WINDOWS','model':configuration['model'],
        'revision':configuration['revision'],'dimension':configuration['dimensions'],
        'task_id':TASK,'normalization':'L2','prefix_by_type':prefixes,
        'encoder_files':files,'max_length':configuration['max_length'],
        'pooling':'TOKEN_WEIGHTED_MEAN_OF_NORMALIZED_CHUNKS_THEN_L2',
        'cross_window_relations_guaranteed':False,'fitted_for_new_task':False}
    if cfg['max_length']>net.config.max_position_embeddings:
        raise ContractError('ENCODER_POSITION_LIMIT')
    special=tokenizer.num_special_tokens_to_add(pair=False);jobs=[];ledger=[];key_ids={};vectors={};unique={}
    for n in g['nodes']:
        prefix=prefixes.get(n['node_type'],prefixes['DEFAULT'])
        key=digest([n['text'],prefix]);key_ids[n['uid']]=key
        if key not in unique:
            e=tokenizer(n['text'],add_special_tokens=False,truncation=False,return_offsets_mapping=True)
            ids=e['input_ids'];pre=tokenizer.encode(prefix,add_special_tokens=False)
            cap=cfg['max_length']-len(pre)-special
            if cap<1:raise ContractError('ENCODER_PREFIX_TOO_LONG')
            windows=[[i,min(i+cap,len(ids))] for i in range(0,len(ids),cap)]
            row={'text_sha256':digest(n['text']),'token_count':len(ids),'encoded_tokens':len(ids),
                'windows':windows,'window_capacity':cap,'prefix_token_count':len(pre),'special_token_count':special,
                'token_ids':ids,'token_ids_sha256':digest(ids),'offsets':[list(x) for x in e['offset_mapping']]}
            unique[key]=row
            for a,b in windows or [[0,0]]:
                full=tokenizer.build_inputs_with_special_tokens(pre+ids[a:b])
                if len(full)>cfg['max_length']:raise ContractError('ENCODER_SILENT_TRUNCATION')
                jobs.append((key,full,max(b-a,1)))
        ledger.append({'uid':n['uid'],**unique[key]})
    accum={};weights={}
    with torch.no_grad():
        for start in range(0,len(jobs),batch_size):
            batch=jobs[start:start+batch_size]
            padded=tokenizer.pad({'input_ids':[x[1] for x in batch]},padding=True,return_tensors='pt')
            h=net(**padded).last_hidden_state;mask=padded['attention_mask'].unsqueeze(-1)
            v=torch.nn.functional.normalize((h*mask).sum(1)/mask.sum(1),p=2,dim=1)
            for (key,_,weight),vector in zip(batch,v):
                accum[key]=accum.get(key,torch.zeros_like(vector))+weight*vector
                weights[key]=weights.get(key,0)+weight
    for uid,key in key_ids.items():
        vector=torch.nn.functional.normalize(accum[key]/weights[key],p=2,dim=0)
        if len(vector)!=cfg['dimension']:raise ContractError('ENCODER_DIMENSION')
        vectors[uid]=vector.tolist()
    value={'graph_sha256':graph['sha256'],'config':cfg,'vectors':vectors,'coverage':ledger}
    value['sha256']=digest(value)
    verify_tokenization(graph,value,tokenizer)
    # Detect weights/tokenizer replacement during encoding, without mutating cache.
    for name,h in files.items():
        if hashlib.sha256((path/name).read_bytes()).hexdigest()!=h:
            raise ContractError('ENCODER_CHANGED_DURING_RUN',detail=name)
    return value
