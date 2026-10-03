"""Incremental JSON-string guard. Four nonoverlapping exact 64-character windows."""
import json
class RepetitionAbort(Exception):pass
class StringGuard:
 def __init__(self):
  self.inside=False;self.escape=False;self.raw='';self.is_key=False;self.stack=[];self.last_key=None;self.windows={};self.decoded='';self.hit=None
 def feed(self,chunk):
  for ch in chunk:
   if not self.inside:
    if ch=='{':self.stack.append({'kind':'object','key':True,'name':None})
    elif ch=='[':self.stack.append({'kind':'array','name':self.last_key})
    elif ch in '}]':
     if self.stack:self.stack.pop()
    elif ch==',' and self.stack and self.stack[-1]['kind']=='object':self.stack[-1]['key']=True
    elif ch==':' and self.stack:self.stack[-1]['key']=False
    elif ch=='"':
     self.inside=True;self.raw='';self.escape=False;self.windows={};self.decoded=''
     self.is_key=bool(self.stack and self.stack[-1]['kind']=='object' and self.stack[-1]['key'])
     self.field=(self.stack[-1].get('name') if self.stack and self.stack[-1]['kind']=='array' else self.last_key)
    continue
   if ch=='"' and not self.escape:
    if self.is_key:
     self.last_key=json.loads('"'+self.raw+'"')
     if self.stack:self.stack[-1]['name']=self.last_key
    self.inside=False;continue
   self.raw+=ch
   if ch=='\\' and not self.escape:self.escape=True
   else:self.escape=False
   if self.is_key or self.field not in {'point','coverage_limits','text','event_date','record','application_or_gap','reason'}:continue
   try:value=json.loads('"'+self.raw+'"')
   except (ValueError,json.JSONDecodeError):continue
   for end in range(len(self.decoded)+1,len(value)+1):
    if end<64:continue
    window=value[end-64:end];pos=end-64;occ=self.windows.setdefault(window,[])
    if not occ or pos>=occ[-1]+64:occ.append(pos)
    if len(occ)>=4:
     self.hit={'field':self.field,'fragment':window,'positions':occ[:4],'characters':64,'same_string_only':True}
     raise RepetitionAbort('Four exact nonoverlapping fragments in one free-text string')
   self.decoded=value
