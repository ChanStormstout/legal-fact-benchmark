"""Strict import and explicit syntax-only presentation repairs for model output."""
import json,re

def parse_one(raw):
 text=raw.decode('utf-8-sig').strip();repairs=[]
 if text.startswith('```'):
  m=re.fullmatch(r'```(?:json)?\s*([\s\S]*?)\s*```',text)
  if m:text=m.group(1);repairs.append('REMOVED_CODE_FENCE')
 try:obj=json.loads(text)
 except json.JSONDecodeError:
  obj,end=json.JSONDecoder().raw_decode(text)
  tail=text[end:].strip()
  # Only an already complete leading JSON value can be preserved. Extra
  # unmatched closing tokens contain no semantic cells, and are logged.
  if not tail or not re.fullmatch(r'[\s\]\}]+',tail):raise ValueError('No complete unambiguous JSON value')
  repairs.append({'action':'REMOVED_EXTRA_TRAILING_CLOSERS','removed':tail})
 if not isinstance(obj,dict):raise ValueError('Top-level JSON object required')
 return obj,repairs

def failure_answers(tasks,run_status,reason):
 if run_status=='OK':raise ValueError('Not a failure')
 return [{'task_id':t['task_id'],'answer_status':None,'run_status':run_status,'reason':reason} for t in tasks]
