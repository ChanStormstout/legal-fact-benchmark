"""Actual orchestration for v2; injection points are also used by entry tests."""
import os,json,tempfile,time
from pathlib import Path

def atomic_json(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(prefix='.atomic-',dir=path.parent)
 try:
  with os.fdopen(fd,'w') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def preflight(root):
 root=Path(root)
 for d in ('training','weights','predictions','analysis'):
  p=root/d;p.mkdir(parents=True,exist_ok=True);fd,f=tempfile.mkstemp(dir=p);os.close(fd);os.unlink(f)
def run_one(root,spec,fit_call,predict_call,export_call,verify_call):
 root=Path(root);preflight(root);stem=spec['id'];rp=root/'training'/f'{stem}.json'
 if rp.exists():raise RuntimeError('ATTEMPT_ALREADY_RECORDED_NO_REFIT')
 record={'spec':spec,'status':'RUNNING','stages':{},'started':time.time(),'answer':None};atomic_json(rp,record)
 model=None
 for stage in ('fit','prediction','weight_export','weight_readback'):
  t=time.perf_counter()
  try:
   if stage=='fit':
    model,log=fit_call();atomic_json(root/'training'/f'{stem}-fit.json',{'actual':spec,'log':log});result={'log_file':f'training/{stem}-fit.json'}
   elif stage=='prediction':
    predictions=predict_call(model);atomic_json(root/'predictions'/f'{stem}.json',predictions);result={'prediction_file':f'predictions/{stem}.json'}
   elif stage=='weight_export':
    dest=root/'weights'/f'{stem}.safetensors';tmp=dest.with_name('.'+dest.name);export_call(model,tmp);os.replace(tmp,dest);result={'weights':str(dest)}
   else:result=verify_call(root/'weights'/f'{stem}.safetensors',predictions)
   record['stages'][stage]={'status':'OK','seconds':time.perf_counter()-t,'result':result};atomic_json(rp,record)
  except Exception as e:
   record['stages'][stage]={'status':'FAILED','seconds':time.perf_counter()-t,'error':repr(e)};record['status']='PAUSED_SHARED_OR_ARTIFACT_FAILURE';record['failed_stage']=stage;record['finished']=time.time();atomic_json(rp,record);return record
 record.update(status='OK',answer='predictions file',finished=time.time());atomic_json(rp,record);return record

def run_schedule(root,specs,callbacks):
 root=Path(root);preflight(root);manifest=root/'run-manifest.json'
 states={s['id']:'PLANNED' for s in specs}
 if manifest.exists():states.update(json.loads(manifest.read_text())['states'])
 if any(v not in ('PLANNED','OK') for v in states.values()):return {'status':'PAUSED','states':states,'no_further_fits':True}
 atomic_json(manifest,{'specs':specs,'states':states})
 for spec in specs:
  if states[spec['id']]!='PLANNED':continue
  result=run_one(root,spec,**callbacks(spec));states[spec['id']]=result['status'];atomic_json(manifest,{'specs':specs,'states':states})
  if result['status']!='OK':return {'status':'PAUSED','states':states,'no_further_fits':True}
 return {'status':'COMPLETE','states':states}
