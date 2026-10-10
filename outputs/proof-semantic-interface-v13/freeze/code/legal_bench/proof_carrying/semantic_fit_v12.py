"""Fixed three-class training. Logs/predictions saved before attempting weight export.
No TEST input is accepted by this module. Weight reload generates downstream predictions.
"""
import json,time,traceback,hashlib
from pathlib import Path
LABELS=('USABLE','UNUSABLE','UNRESOLVED')
def write(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def evaluate(pred,rows):
 import math
 ix={r['key']:r for r in rows};by={};false_accepts=0;covered=0
 for x in pred:
  r=ix[x['key']];g=LABELS.index(r['label']);p=x['probabilities'];by.setdefault(r['dispute_id'],{}).setdefault(r['request_id'],[]).append(-math.log(max(p[g],1e-12)))
  guess=max(range(3),key=lambda k:p[k]);false_accepts+=guess==0 and g==1;covered+=guess==0 and g==0
 losses=[sum(sum(v)/len(v) for v in q.values())/len(q) for q in by.values()]
 return {'hierarchical_nll':sum(losses)/len(losses) if losses else None,'false_accepts':false_accepts,'confirmed_usable_predicted':covered,'disputes':len(by)}
def fit_graph(kind,seed,graphs,rows,out,deadline):
 import numpy as np,mlx.core as mx,mlx.nn as nn,mlx.optimizers as optim
 from .semantic_models_v12 import UseClassifier,parameter_hash
 from mlx.utils import tree_flatten
 out=Path(out);out.mkdir(parents=True,exist_ok=False);start=time.monotonic();stage='INITIALIZE';history=[];pred=[]
 try:
  if any(r['split'] not in ('TRAIN','DEV') for r in rows):raise ValueError('TEST_IN_FIT')
  train=[r for r in rows if r['split']=='TRAIN'];dev=[r for r in rows if r['split']=='DEV'];mx.random.seed(seed)
  m=UseClassifier(kind,next(iter(graphs.values()))['x'].shape[1]);mx.eval(m.parameters());initial=parameter_hash(m);opt=optim.AdamW(.001,weight_decay=.0001)
  def forward(model,r):
   d=graphs[r['dispute_id']];dyn=mx.zeros((d['x'].shape[0],16));dyn[d['request_indices'][r['request_id']],14]=1
   return model(d,dyn,r['request_id'])[d['ids'].index(r['use_id'])]
  def predictions(model,rr):
   model.eval();result=[]
   for r in rr:
    pp=mx.softmax(forward(model,r));mx.eval(pp);result.append({'key':r['key'],'probabilities':np.array(pp).tolist()})
   return result
  groups={d:[r for r in train if r['dispute_id']==d] for d in sorted({r['dispute_id'] for r in train})}
  def loss(model,rr):
   requests={q:[r for r in rr if r['request_id']==q] for q in {r['request_id'] for r in rr}}
   return mx.mean(mx.stack([mx.mean(mx.stack([nn.losses.cross_entropy(forward(model,r)[None,:],mx.array([LABELS.index(r['label'])])) for r in req])) for req in requests.values()]))
  grad=nn.value_and_grad(m,loss);best=float('inf');bestparams=None;stale=0;stage='TRAIN'
  with (out/'training.jsonl').open('x') as log:
   for epoch in range(100):
    m.train();ls=[]
    for rr in groups.values():
     if time.monotonic()>=deadline:raise TimeoutError('TOTAL_TRAIN_BUDGET')
     value,g=grad(m,rr);opt.update(m,g);mx.eval(m.parameters(),opt.state,value);ls.append(float(value.item()))
    pred=predictions(m,dev);metric=evaluate(pred,dev);score=metric['hierarchical_nll'];row={'epoch':epoch+1,'train_dispute_mean_loss':sum(ls)/len(ls),'dev':metric,'seconds':time.monotonic()-start};history.append(row);log.write(json.dumps(row)+'\n');log.flush();write(out/'latest-dev-predictions.json',pred)
    if score<best:best=score;stale=0;bestparams=[(k,np.array(v).copy()) for k,v in tree_flatten(m.parameters())]
    else:stale+=1
    if stale>=10:break
  m.load_weights([(k,mx.array(v)) for k,v in bestparams]);mx.eval(m.parameters());pred=predictions(m,dev);write(out/'dev-before-export.json',pred);write(out/'training-complete.json',{'kind':kind,'seed':seed,'initial_hash':initial,'final_hash':parameter_hash(m),'seconds':time.monotonic()-start,'epochs':len(history),'evaluation':evaluate(pred,dev)})
  stage='WEIGHT_EXPORT';m.save_weights(str(out/'weights.safetensors'))
  stage='RELOAD_AND_DOWNSTREAM';fresh=UseClassifier(kind,next(iter(graphs.values()))['x'].shape[1]);fresh.load_weights(str(out/'weights.safetensors'));fresh.eval();after=predictions(fresh,dev);write(out/'dev-reloaded-predictions.json',after)
  if not np.allclose([x['probabilities'] for x in pred],[x['probabilities'] for x in after],atol=1e-6):raise ValueError('RELOAD_PREDICTION_MISMATCH')
  write(out/'run.json',{'status':'OK','reload_used_for_prediction':True,'seconds':time.monotonic()-start});return after
 except Exception as e:
  write(out/'failure.json',{'status':'TECHNICAL_FAILURE','answer':None,'stage':stage,'error':repr(e),'traceback':traceback.format_exc(),'seconds':time.monotonic()-start});raise

def fit_ce(seed,pairs,rows,out,deadline,model_path='.runtime/proof-semantic-v12-model'):
 import torch,numpy as np
 from transformers import AutoTokenizer,AutoModelForSequenceClassification
 from safetensors.torch import save_file,load_file
 out=Path(out);out.mkdir(parents=True,exist_ok=False);start=time.monotonic();stage='INITIALIZE'
 try:
  if any(r['split'] not in ('TRAIN','DEV') for r in rows):raise ValueError('TEST_IN_FIT')
  torch.manual_seed(seed);torch.set_num_threads(4);tok=AutoTokenizer.from_pretrained(model_path,local_files_only=True)
  def model():
   m=AutoModelForSequenceClassification.from_pretrained(model_path,local_files_only=True,num_labels=3,ignore_mismatched_sizes=True,attn_implementation='sdpa',reference_compile=False)
   for n,p in m.named_parameters():p.requires_grad_(n.startswith(('model.layers.20.','model.layers.21.','head.','classifier.')))
   return m
  m=model();train=[r for r in rows if r['split']=='TRAIN'];dev=[r for r in rows if r['split']=='DEV'];encoded={}
  stage='INPUT_COVERAGE'
  for r in rows:
   pair=pairs[r['key']];x=tok(pair['left'],pair['right'],truncation=False,return_tensors='pt')
   if x['input_ids'].shape[1]>8192:raise ValueError('CE_INPUT_TOO_LONG:'+r['key'])
   encoded[r['key']]=x
  write(out/'input-lengths.json',{k:int(v['input_ids'].shape[1]) for k,v in encoded.items()})
  opt=torch.optim.AdamW([{'params':[p for n,p in m.named_parameters() if p.requires_grad and n.startswith('model.')],'lr':2e-5},{'params':[p for n,p in m.named_parameters() if p.requires_grad and not n.startswith('model.')],'lr':1e-4}])
  from .semantic_data_v12 import hierarchical_weights
  weights=hierarchical_weights(train)
  def predictions(mm):
   mm.eval();result=[]
   with torch.no_grad():
    for r in dev:result.append({'key':r['key'],'probabilities':mm(**encoded[r['key']]).logits.softmax(-1)[0].tolist()})
   return result
  best=float('inf');bestparams=None;stale=0;stage='TRAIN'
  with (out/'training.jsonl').open('x') as log:
   for epoch in range(6):
    m.train();total=0.;order=np.random.default_rng(seed+epoch).permutation(len(train));opt.zero_grad()
    for i,j in enumerate(order):
     if time.monotonic()>=deadline:raise TimeoutError('TOTAL_TRAIN_BUDGET')
     r=train[j];loss=torch.nn.functional.cross_entropy(m(**encoded[r['key']]).logits,torch.tensor([LABELS.index(r['label'])]));scale=weights[j]*len(train)/16;(loss*scale).backward();total+=float(loss.detach())*weights[j]
     if (i+1)%16==0 or i+1==len(train):opt.step();opt.zero_grad()
    pred=predictions(m);metric=evaluate(pred,dev);score=metric['hierarchical_nll'];log.write(json.dumps({'epoch':epoch+1,'train_hierarchical_loss':total,'dev':metric,'seconds':time.monotonic()-start})+'\n');log.flush();write(out/'latest-dev-predictions.json',pred)
    if score<best:best=score;stale=0;bestparams={n:p.detach().clone().contiguous() for n,p in m.named_parameters() if p.requires_grad}
    else:stale+=1
    if stale>=2:break
  m.load_state_dict(bestparams,strict=False);pred=predictions(m);write(out/'dev-before-export.json',pred);write(out/'training-complete.json',{'seed':seed,'seconds':time.monotonic()-start,'evaluation':evaluate(pred,dev)})
  stage='WEIGHT_EXPORT';save_file(bestparams,str(out/'weights.safetensors'));del m
  stage='RELOAD_AND_DOWNSTREAM';fresh=model();fresh.load_state_dict(load_file(str(out/'weights.safetensors')),strict=False);after=predictions(fresh);write(out/'dev-reloaded-predictions.json',after)
  if not np.allclose([x['probabilities'] for x in pred],[x['probabilities'] for x in after],atol=1e-6):raise ValueError('RELOAD_PREDICTION_MISMATCH')
  write(out/'run.json',{'status':'OK','reload_used_for_prediction':True,'seconds':time.monotonic()-start});return after
 except Exception as e:
  write(out/'failure.json',{'status':'TECHNICAL_FAILURE','answer':None,'stage':stage,'error':repr(e),'traceback':traceback.format_exc(),'seconds':time.monotonic()-start});raise
