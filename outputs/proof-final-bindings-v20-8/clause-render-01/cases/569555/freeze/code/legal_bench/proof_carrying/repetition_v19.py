"""Incremental exact record repetition, scoped to a premise analysis unit."""
import json
from collections import Counter
from legal_bench.rules_verdict_v1.repetition_v9 import RepetitionAbort

class RecordGuard:
    def __init__(self,threshold=3):
        self.threshold=threshold;self.hit=None;self.buffer='';self.stack=[];self.in_string=False;self.escaped=False;self.start_string=0;self.key=None;self.counts=Counter()
    def feed(self,chunk):
        begin=len(self.buffer);self.buffer+=chunk
        for pos in range(begin,len(self.buffer)):
            char=self.buffer[pos]
            if self.in_string:
                if self.escaped:self.escaped=False
                elif char=='\\':self.escaped=True
                elif char=='"':
                    self.in_string=False
                    try:value=json.loads(self.buffer[self.start_string:pos+1])
                    except ValueError:value=None
                    if self.stack and self.stack[-1]['kind']=='{':
                        top=self.stack[-1]
                        if top['expect_key']:top['key']=value;top['expect_key']=False
                        elif top['key']=='premise':top['premise']=value
                continue
            if char=='"':self.in_string=True;self.start_string=pos;continue
            if char in '{[':
                parent=self.stack[-1] if self.stack else None
                name=parent.get('key') if parent and parent['kind']=='{' else parent.get('name') if parent else None
                unit=next((x for x in reversed(self.stack) if x['kind']=='{' and x.get('premise')),None)
                self.stack.append({'kind':char,'start':pos,'name':name,'key':None,'expect_key':char=='{','unit':unit})
            elif char in '}]' and self.stack:
                top=self.stack.pop()
                if char=='}' and top['name']=='records' and self.stack and self.stack[-1]['kind']=='[' and top['unit']:
                    try:r=json.loads(self.buffer[top['start']:pos+1])
                    except ValueError:continue
                    if not {'text','refs','status','stage'}<=set(r):continue
                    key=(top['unit']['start'],top['unit']['premise'],json.dumps({k:r[k] for k in ('text','refs','status','stage')},sort_keys=True,ensure_ascii=False),r.get('court_level'))
                    self.counts[key]+=1
                    if self.counts[key]>=self.threshold:
                        self.hit={'premise':key[1],'record':r,'exact_copies':self.counts[key],'scope':'SAME_ANALYSIS_UNIT','threshold':self.threshold}
                        raise RepetitionAbort('V19 mechanically repeated identical record in same analysis unit')
            elif char==',' and self.stack and self.stack[-1]['kind']=='{':self.stack[-1]['expect_key']=True
