"""Actual learner input adapters. No labels/references participate in construction."""
import json

def ce_windows(tokenizer,pair,max_tokens=8192):
    import torch
    left=tokenizer(pair['left'],add_special_tokens=False,truncation=False)['input_ids']
    right_text=pair['right']
    if 'shared_case_context' in pair:
        right_text+='\nSHARED SAME-CASE GRAPH INFORMATION:\n'+json.dumps(pair['shared_case_context'],sort_keys=True,ensure_ascii=False)
    right=tokenizer(right_text,add_special_tokens=False,truncation=False)['input_ids']
    cap=max_tokens-len(left)-tokenizer.num_special_tokens_to_add(pair=True)
    if cap<1:raise ValueError('COMPLETE_LEFT_PROPOSITION_EXCEEDS_CONTEXT')
    windows=[]
    for start in range(0,max(1,len(right)),cap):
        ids=tokenizer.build_inputs_with_special_tokens(left,right[start:start+cap])
        if len(ids)>max_tokens:raise ValueError('WINDOW_CONTEXT_ERROR')
        x=torch.tensor([ids]);windows.append({'input_ids':x,'attention_mask':torch.ones_like(x)})
    return windows

def graph_arrays(graph,plan,vectors):
    import numpy as np
    indexed={n['node']:n for n in plan['graph']};x=[]
    for node in graph['nodes']:
        parts=indexed[node['id']]['part_sha256']
        if not parts:raise ValueError('NO_INPUT_PARTS:'+node['id'])
        if any(k not in vectors for k in parts):raise ValueError('ENCODING_INCOMPLETE:'+node['id'])
        value=np.mean([vectors[k] for k in parts],axis=0)
        value=value/max(float(np.linalg.norm(value)),1e-12)
        x.append(np.concatenate([value,np.eye(5)[node['kind']]]))
    adj=np.zeros((16,len(x),len(x)),np.float32)
    for a,b,rel in graph['edges']:adj[rel,b,a]+=1
    adj/=np.maximum(adj.sum(axis=2,keepdims=True),1)
    return {'x':np.asarray(x,np.float32),'adj':adj,'edges':np.asarray(graph['edges'],np.int32).reshape(-1,3),**{k:graph[k] for k in ('ids','candidate_indices','request_indices')}}
