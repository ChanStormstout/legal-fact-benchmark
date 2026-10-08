import sys,json,hashlib,time,fcntl,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from legal_bench.irac_application.text_cache import chunk_ranges
R=Path('outputs/gnn-irac-aligned-v2');O=Path('outputs/gnn-irac-aligned-v1')
def main():
 import torch,transformers
 from transformers import AutoTokenizer,AutoModel
 torch.set_num_threads(4)
 out=R/'text-cache';out.mkdir(exist_ok=True);lock=(out/'.encoding.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);cfg=json.loads((O/'text-cache/encoder.json').read_text());(out/'encoder.json').write_text(json.dumps(cfg,indent=2))
 tok=AutoTokenizer.from_pretrained(cfg['path'],local_files_only=True);model=AutoModel.from_pretrained(cfg['path'],local_files_only=True).eval();prefix=tok.encode(cfg['prefix'],add_special_tokens=False);cap=512-len(prefix)-tok.num_special_tokens_to_add(pair=False)
 old=np.load(O/'text-cache/vectors.npz');prior=np.load(out/'vectors.npz') if (out/'vectors.npz').exists() else {};vectors={};audit=[];t=time.perf_counter();texts={hashlib.sha256(n['text'].encode()).hexdigest():n['text'] for p in (R/'graphs').glob('*.json') for n in json.loads(p.read_text())['nodes']}
 with torch.no_grad():
  for k,text in sorted(texts.items()):
   if k in old:vectors[k]=old[k];audit.append({'text_sha256':k,'reuse':'v1 identical text and encoder'});continue
   if k in prior:vectors[k]=prior[k];audit.append({'text_sha256':k,'reuse':'v2 completed deterministic encoding'});continue
   e=tok(text,add_special_tokens=False,truncation=False,return_offsets_mapping=True);ids=e['input_ids'];ranges=chunk_ranges(ids,e['offset_mapping'],text,cap);vs=[]
   for a,b in ranges:
    x=torch.tensor([tok.build_inputs_with_special_tokens(prefix+ids[a:b])]);assert x.shape[1]<=512;h=model(input_ids=x,attention_mask=torch.ones_like(x)).last_hidden_state;vs.append(torch.nn.functional.normalize(h.mean(dim=1),p=2,dim=1)[0].numpy())
   v=np.mean(vs,axis=0);v/=max(np.linalg.norm(v),1e-12);vectors[k]=v;audit.append({'text_sha256':k,'tokens':len(ids),'token_ranges':ranges,'truncated':False})
 np.savez(out/'.vectors.tmp.npz',**vectors);os.replace(out/'.vectors.tmp.npz',out/'vectors.npz');(out/'encoding.json').write_text(json.dumps({'model':cfg,'seconds':time.perf_counter()-t,'unique_texts':len(texts),'audit':audit,'torch':torch.__version__,'transformers':transformers.__version__},indent=2));print('encoded',len(texts),'seconds',time.perf_counter()-t)
if __name__=='__main__':main()
