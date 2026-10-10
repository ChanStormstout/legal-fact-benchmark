"""One authorized synthetic smoke and pinned download, never real-case tuning."""
import json,time,sys,hashlib,traceback,subprocess
from pathlib import Path
OUT=Path('outputs/proof-semantic-search-v12');MODEL='Alibaba-NLP/gte-reranker-modernbert-base';REV='f7481e6055501a30fb19d090657df9ec1f79ab2c'
def main():
 dest=OUT/'environment';dest.mkdir(exist_ok=True);result=dest/'synthetic-validation.json'
 if result.exists():raise SystemExit('Already attempted; inspect saved result, do not rerun')
 t=time.monotonic();stage='DOWNLOAD';meta={'model':MODEL,'revision':REV,'synthetic_only':True,'real_case_calls':0,'modelcard_url':'https://huggingface.co/'+MODEL,'license':'apache-2.0','weight_bytes':598436708}
 try:
  from huggingface_hub import snapshot_download
  path=snapshot_download(MODEL,revision=REV,allow_patterns=['*.json','model.safetensors','README.md'],local_dir='.runtime/proof-semantic-v12-model')
  stage='LOAD';import torch
  from transformers import AutoTokenizer,AutoModelForSequenceClassification
  torch.manual_seed(20261001);torch.set_num_threads(4)
  tok=AutoTokenizer.from_pretrained(path,local_files_only=True)
  model=AutoModelForSequenceClassification.from_pretrained(path,local_files_only=True,num_labels=3,ignore_mismatched_sizes=True,attn_implementation='sdpa',reference_compile=False)
  names=[]
  for n,p in model.named_parameters():
   p.requires_grad_(n.startswith(('model.layers.20.','model.layers.21.','head.','classifier.')))
   if p.requires_grad:names.append(n)
  assert any(n.startswith('model.layers.21.') for n in names)
  # CPU is deliberate portable local validation; MPS capability recorded separately.
  model.train();stage='FORWARD_BACKWARD'
  inp=tok(['The witness asserted access.','Permission covers Tuesday.'],['A witness statement asserts access, not a judicial finding.','The document grants access on Monday only.'],padding=True,truncation=False,return_tensors='pt')
  assert inp['input_ids'].shape[1]<=8192
  loss=model(**inp,labels=torch.tensor([0,1])).loss;loss.backward()
  assert all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)
  stage='SAVE';w=OUT/'weights/synthetic-smoke';w.mkdir(parents=True,exist_ok=True)
  from safetensors.torch import save_file
  save_file({n:p.detach().contiguous() for n,p in model.named_parameters() if p.requires_grad},str(w/'trainable.safetensors'))
  meta.update(status='PASS',loss=float(loss.detach()),trainable_names=names,trainable_parameters=sum(p.numel() for p in model.parameters() if p.requires_grad),total_parameters=sum(p.numel() for p in model.parameters()),device='cpu',mps_available=torch.backends.mps.is_available(),torch=torch.__version__,input_tokens=int(inp['attention_mask'].sum()),optimizer_steps=0,weights_sha256=hashlib.sha256((w/'trainable.safetensors').read_bytes()).hexdigest())
 except Exception as e:meta.update(status='FAILED',failed_stage=stage,error=repr(e),traceback=traceback.format_exc())
 meta['seconds']=time.monotonic()-t;result.write_text(json.dumps(meta,indent=2)+'\n');(dest/'pip-freeze.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True));print(json.dumps(meta))
if __name__=='__main__':main()
