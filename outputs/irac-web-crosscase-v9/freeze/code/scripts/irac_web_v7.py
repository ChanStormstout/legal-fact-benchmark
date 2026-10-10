"""Versioned web transport; frozen V6 semantics, no inference or content repair."""
import json, hashlib, shutil, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.irac_semantic_v6 import inputs, delivery, process, validate_final
R=Path('outputs/irac-web-crossmodel-v7')
OLD=Path('outputs/irac-semantic-interface-v6')
TRANSPORT='只依据任务文件中的材料作答。不要外部搜索，不查找案件其他版本，不依赖其他对话，不读取旧答案或审阅记录。请一次性按给定合同完成输出。允许使用文件工具读取本任务附件或生成JSON，不允许补充外部法律资料。'
ORDER=[(c,s) for c in ('112400','188721101') for s in ('A','P','B')]
def now():return datetime.now(timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text())
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def task(c,s,proposal=None):
 base=OLD/'runs'/c/('A' if s=='B' else s)
 text=(base/'prompt.txt').read_text()
 if s=='B':
  assert proposal is not None
  marker='INTERMEDIATE MATERIAL:\n\n{}\n\nCOMPLETE ALLOWED CASE MATERIAL:'
  assert text.count(marker)==1
  text=text.replace(marker,'INTERMEDIATE MATERIAL:\n\n'+json.dumps({'proposal':proposal},ensure_ascii=False,indent=2)+'\n\nCOMPLETE ALLOWED CASE MATERIAL:')
 out=R/'tasks'/c/s;out.mkdir(parents=True,exist_ok=False)
 (out/'prompt.txt').write_text(text);shutil.copyfile(base/'schema.json',out/'schema.json')
 m,t,l,sm=inputs(c);audit=delivery(text,m,l,sm);save(out/'delivery.json',audit)
 packaged='TRANSPORT INSTRUCTION\n'+TRANSPORT+'\n\nV6 ACTUAL TASK (UNCHANGED)\n'+text+'\n\nV6 OUTPUT SCHEMA (WEB DOES NOT USE TOKENWISE ENFORCEMENT)\n'+(out/'schema.json').read_text()
 (out/'task.txt').write_text(packaged)
 save(out/'manifest.json',{'case':c,'stage':s,'baseline':str(base),'prompt_sha256':h(out/'prompt.txt'),'schema_sha256':h(out/'schema.json'),'task_sha256':h(out/'task.txt'),'bytes':len(packaged.encode()),'proposal_sha256':h(R/'runs'/c/'P'/'parsed.json') if s=='B' else None,'built_at':now()})
 return out
def prepare():
 assert not R.exists()
 cfg=read(OLD/'freeze/config.json')
 for p,expected in {**cfg['code_hashes'],**cfg['material_hashes']}.items():assert h(p)==expected,p
 save(R/'registration.json',{'created_at':now(),'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'branch':subprocess.check_output(['git','branch','--show-current'],text=True).strip(),'dirty':subprocess.check_output(['git','status','--short'],text=True),'historical_hashes':{str(p):h(p) for p in OLD.rglob('*') if p.is_file()},'old_code_hashes':cfg['code_hashes']})
 for c in ('112400','188721101'):
  for s in ('A','P'):task(c,s)
  b=R/'freeze'/'B-templates'/c;b.mkdir(parents=True);shutil.copyfile(OLD/'runs'/c/'A'/'prompt.txt',b/'prompt.txt');shutil.copyfile(OLD/'runs'/c/'A'/'schema.json',b/'schema.json')
 (R/'freeze'/'transport.txt').write_text(TRANSPORT)
 shutil.copyfile(__file__,R/'freeze'/'irac_web_v7.py')
 save(R/'freeze/config.json',{'version':'IRAC_WEB_CROSSMODEL_V7','frozen_at':now(),'base_config_hash':h(OLD/'freeze/config.json'),'material_hashes':cfg['material_hashes'],'old_code_hashes':cfg['code_hashes'],'transport_code_hash':h(__file__),'order':ORDER,'max_generations':6,'retries':0,'local_calls':0,'model_visible':None,'mode_visible':'High (third of five intensity options)','pro':False,'temporary':True,'personalization':'OFF_CURRENT_CHAT','exact_model':None,'sampling':None,'output_token_cap':None,'web_schema_enforcement':False,'B_rule':'Replace exactly the empty INTERMEDIATE MATERIAL JSON in frozen A prompt with {proposal: unmodified parsed current web P}. JSON serialization only; no checks or corrections.','failures':'Null technical answer; unreadable P skips dependent B only. No retries. Access/mode failure pauses unsubmitted slots.','evaluation':['Source fidelity including decisive uncited content and opposition','Legal scope, alternative/necessary conditions and polarity','P errors corrected/ignored/propagated and traceable net benefit','Compare each web A/B to V6; not human gold, not independent test','No winner from label agreement or JSON validity; unavailable cost remains null'],'task_hashes':{str(p):h(p) for p in (R/'tasks').rglob('*') if p.is_file()}})
 save(R/'progress.json',{'slots':[{'case':c,'stage':s,'status':'NOT_SUBMITTED'} for c,s in ORDER]})
def ingest(c,s):
 out=R/'runs'/c/s;raw=(out/'raw-response.txt').read_text();text=raw.strip();ops=[]
 if text.startswith('```') and text.endswith('```'):
  text=text.split('\n',1)[1].rsplit('```',1)[0].strip();ops.append('REMOVE_OUTER_MARKDOWN_FENCE_AND_OUTER_WHITESPACE')
 result={'case':c,'stage':s,'run_status':'OK','answer':None,'format_operations':ops,'semantic_validated':False}
 try:
  value=json.loads(text);save(out/'parsed.json',value)
  m,t,l,sm=inputs(c)
  if s=='P':
   imp,checks=process(value,t,m,l);save(out/'import.json',imp);save(out/'checks-full.json',checks)
   if not imp['usable']:raise ValueError(imp['status'])
  else:validate_final(value,read(R/'tasks'/c/s/'schema.json'),t)
  result['answer']=value
 except (ValueError,KeyError,TypeError) as e:result.update(run_status='FORMAT_ERROR',reason=str(e))
 save(out/'result.json',result)
 if s=='P' and result['run_status']=='OK':task(c,'B',value)
 print(json.dumps({k:v for k,v in result.items() if k!='answer'},ensure_ascii=False))
if __name__=='__main__':
 if sys.argv[1]=='prepare':prepare()
 elif sys.argv[1]=='ingest':ingest(*sys.argv[2:4])
