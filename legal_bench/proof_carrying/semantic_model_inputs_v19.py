"""Complete same-information block windows, shared token cache. Fixed mean-logit pooling."""
from .semantic_model_inputs_v13 import graph_arrays
_CACHE={}

def token_blocks(tokenizer,pair):
    key=(id(tokenizer),pair['shared_material_hash'])
    if key not in _CACHE:
        _CACHE[key]=[(b['id'],tokenizer(b['id']+'\n'+b['text'],add_special_tokens=False,truncation=False)['input_ids']) for b in pair['shared_material_blocks']]
    return _CACHE[key]

def window_plan(tokenizer,pair,max_tokens=8192):
    left=tokenizer(pair['left'],add_special_tokens=False,truncation=False)['input_ids']
    cap=max_tokens-len(left)-tokenizer.num_special_tokens_to_add(pair=True)
    if cap<1:raise ValueError('COMPLETE_LEFT_PROPOSITION_EXCEEDS_CONTEXT')
    windows=[];tokens=[];spans=[];audit=[]
    def flush():
        if tokens:windows.append({'right_ids':list(tokens),'spans':list(spans)});tokens.clear();spans.clear()
    # No per-use recopy of source. Candidate is identified by left + stable ID block.
    target=tokenizer('TARGET_USE_ID:'+pair['id'],add_special_tokens=False)['input_ids']
    blocks=[('target',target)]+token_blocks(tokenizer,pair)
    for name,ids in blocks:
        if len(ids)<=cap:
            if len(tokens)+len(ids)>cap:flush()
            spans.append({'block':name,'start_token':0,'end_token':len(ids)});tokens.extend(ids)
        else:
            flush()
            for start in range(0,len(ids),cap):
                chunk=ids[start:start+cap];tokens.extend(chunk);spans.append({'block':name,'start_token':start,'end_token':start+len(chunk),'limitation':'OVERSIZED_SEMANTIC_BLOCK_SPLIT; CROSS_WINDOW_RELATION_NOT_GUARANTEED'});flush()
        audit.append({'block':name,'tokens':len(ids)})
    flush()
    if not windows:windows=[{'right_ids':[],'spans':[]}]
    return left,windows,{'complete':True,'blocks':audit,'right_tokens':sum(len(t) for _,t in blocks),'windows':len(windows),
                         'aggregation':'UNCHANGED_MEAN_WINDOW_LOGITS; COMPLETE_TOKEN_VISIBILITY_IS_NOT_COMPLETE_RELATION_UNDERSTANDING',
                         'shared_tokenization_cached':True,'source_stored_once_per_case':True}

def ce_windows(tokenizer,pair,max_tokens=8192):
    import torch
    left,plan,audit=window_plan(tokenizer,pair,max_tokens);out=[]
    for window in plan:
        ids=tokenizer.build_inputs_with_special_tokens(left,window['right_ids'])
        if len(ids)>max_tokens:raise ValueError('WINDOW_CONTEXT_ERROR')
        x=torch.tensor([ids]);out.append({'input_ids':x,'attention_mask':torch.ones_like(x)})
    return out
