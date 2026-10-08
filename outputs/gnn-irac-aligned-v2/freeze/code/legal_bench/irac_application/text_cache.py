"""Frozen encoder worker. Run in the independent E5 environment, not MLX."""
import hashlib,json,time,re,bisect,resource,sys
from pathlib import Path
import numpy as np

def chunk_ranges(ids,offsets,text,capacity):
    ends=[x[1] for x in offsets]
    boundaries={bisect.bisect_right(ends,m.start()) for m in re.finditer(r'(?<=[.!?])\s+|\n+',text)}
    ranges=[];start=0
    while start<len(ids):
        limit=min(start+capacity,len(ids));eligible=[x for x in boundaries if start<x<=limit]
        end=max(eligible) if eligible and limit<len(ids) else limit
        ranges.append([start,end]);start=end
    return ranges or [[0,0]]

def encode(root):
    import torch,transformers
    from transformers import AutoTokenizer,AutoModel
    root=Path(root);cfg=json.loads((root/'text-cache/encoder.json').read_text())
    tokenizer=AutoTokenizer.from_pretrained(cfg['path'],local_files_only=True)
    model=AutoModel.from_pretrained(cfg['path'],local_files_only=True).eval()
    texts={}
    for p in sorted((root/'graphs').glob('*.json')):
        graph=json.loads(p.read_text())
        for n in graph['nodes']:
            text=n['text'];key=hashlib.sha256(text.encode()).hexdigest();texts[key]=text
    out=root/'text-cache';out.mkdir(exist_ok=True);vectors={};audit=[];t=time.perf_counter()
    # Entire node text is tokenized without truncation, then split reversibly at IDs.
    prefix=tokenizer.encode(cfg['prefix'],add_special_tokens=False)
    capacity=512-len(prefix)-tokenizer.num_special_tokens_to_add(pair=False)
    with torch.no_grad():
        for key,text in sorted(texts.items()):
            encoded=tokenizer(text,add_special_tokens=False,truncation=False,return_offsets_mapping=True)
            ids=encoded['input_ids'];ranges=chunk_ranges(ids,encoded['offset_mapping'],text,capacity)
            chunks=[ids[a:b] for a,b in ranges]
            reps=[]
            for chunk in chunks:
                input_ids=torch.tensor([tokenizer.build_inputs_with_special_tokens(prefix+chunk)])
                attention=torch.ones_like(input_ids)
                hidden=model(input_ids=input_ids,attention_mask=attention).last_hidden_state
                v=hidden.mean(dim=1);v=torch.nn.functional.normalize(v,p=2,dim=1);reps.append(v[0].numpy())
            vector=np.mean(reps,axis=0);vector/=max(np.linalg.norm(vector),1e-12);vectors[key]=vector
            audit.append(dict(text_sha256=key,tokens=len(ids),chunk_count=len(chunks),token_ranges=ranges,char_ranges=[[encoded['offset_mapping'][a][0],encoded['offset_mapping'][b-1][1]] if b>a else [0,0] for a,b in ranges],truncated=False))
    np.savez(out/'vectors.npz',**vectors)
    report=dict(model=cfg['model'],revision=cfg['revision'],torch=torch.__version__,transformers=transformers.__version__,device='CPU',unique_texts=len(texts),seconds=time.perf_counter()-t,peak_process_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if sys.platform=='darwin' else 1024),chunking='prefer deterministic sentence/paragraph token boundaries; split overlong single sentence at capacity; full token coverage',pooling='mean tokens then L2; long nodes mean normalized complete chunks then L2',prefix=cfg['prefix'],max_length=512,audit=audit,legal_correctness_claim=False)
    (out/'encoding.json').write_text(json.dumps(report,indent=2));return report
if __name__=='__main__':
    import sys
    print(json.dumps(encode(sys.argv[1]),indent=2))
