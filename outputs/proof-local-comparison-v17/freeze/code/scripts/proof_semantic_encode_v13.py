#!/usr/bin/env python3
"""V13 fixed E5 complete-token encoder; all token chunks retained with original char offsets."""
import sys,json,time,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
def main():
 import torch,numpy as np
 from transformers import AutoModel,AutoTokenizer
 from legal_bench.irac_application.text_cache import chunk_ranges
 out=Path(sys.argv[1]);texts=json.loads((out/'texts.json').read_text());cfg=json.loads(Path('outputs/gnn-irac-aligned-v2/text-cache/encoder.json').read_text());tok=AutoTokenizer.from_pretrained(cfg['path'],local_files_only=True);model=AutoModel.from_pretrained(cfg['path'],local_files_only=True).eval();torch.set_num_threads(2)
 prefix=tok.encode(cfg['prefix'],add_special_tokens=False);cap=512-len(prefix)-tok.num_special_tokens_to_add(pair=False);vectors={};audit=[];t=time.monotonic();reused=0
 if len(sys.argv)>2:
  cache=Path(sys.argv[2]);receipt=json.loads((cache/'encoding.json').read_text())
  if receipt['encoder']!=cfg:raise ValueError('ENCODER_CACHE_CONFIGURATION_MISMATCH')
  old_vectors=np.load(cache/'vectors.npz');old_audit={a['sha256']:a for a in receipt['audit']}
  for key in texts:
   if key in old_vectors and key in old_audit:
    vectors[key]=old_vectors[key];audit.append({**old_audit[key],'reused_exact_text_sha256':True});reused+=1
 with torch.no_grad():
  for key,text in texts.items():
   if key in vectors:continue
   e=tok(text,add_special_tokens=False,truncation=False,return_offsets_mapping=True);ids=e['input_ids'];ranges=chunk_ranges(ids,e['offset_mapping'],text,cap);vs=[];spans=[]
   for a,b in ranges:
    x=torch.tensor([tok.build_inputs_with_special_tokens(prefix+ids[a:b])]);h=model(input_ids=x,attention_mask=torch.ones_like(x)).last_hidden_state;vs.append(torch.nn.functional.normalize(h.mean(1),p=2,dim=1)[0].numpy());spans.append({'tokens':[a,b],'characters':[e['offset_mapping'][a][0],e['offset_mapping'][b-1][1]]})
   v=np.mean(vs,axis=0);v/=max(np.linalg.norm(v),1e-12);vectors[key]=v;
   if len(vectors)%100==0:(out/'progress.json').write_text(json.dumps({'encoded':len(vectors),'total':len(texts),'seconds':time.monotonic()-t}))
   audit.append({'sha256':key,'token_count':len(ids),'chunks':spans,'truncated':False})
 np.savez(out/'vectors.npz',**vectors);(out/'encoding.json').write_text(json.dumps({'encoder':cfg,'audit':audit,'seconds':time.monotonic()-t,'reused_exact_text_parts':reused,'fresh_encoded_parts':len(vectors)-reused},indent=2))
if __name__=='__main__':main()
