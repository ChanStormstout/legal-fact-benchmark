"""Scoped exact cumulative expansion and repeated address guards, no repair."""
import json
from collections import Counter
from .repetition_v19 import RecordGuard
from legal_bench.rules_verdict_v1.repetition_v9 import RepetitionAbort

class ExpansionGuard(RecordGuard):
    def __init__(self):
        super().__init__();self.previous={};self.runs={};self.address_counts={};self.exact_records=Counter()

    def completed_record(self, record, unit, start, end):
        text=record.get('proposition',record.get('text'))
        if not isinstance(text,str):return
        context=(unit['start'],unit['premise'],tuple(record.get('refs',[])),record.get('status'),record.get('stage'),record.get('court_level'))
        key=(context,text);self.exact_records[key]+=1
        if self.exact_records[key]>=3:
            self.hit={'kind':'IDENTICAL_RECORD','premise':unit['premise'],'exact_copies':3,'record_start':start}
            raise RepetitionAbort('V19_6 identical attributed record')
        previous=self.previous.get(context)
        # Three successive literal prefix extensions in the SAME attributed
        # source context. Never triggers merely on common source or similarity.
        growing=bool(previous and len(previous['text'])>=320 and text.startswith(previous['text']) and len(text)>len(previous['text']))
        self.runs[context]=self.runs.get(context,0)+1 if growing else 0
        self.previous[context]={'text':text,'start':start}
        if self.runs[context]>=3:
            self.hit={'kind':'CUMULATIVE_RECORD_PREFIX_EXPANSION','premise':unit['premise'],
                      'same_attribution_stage_source':True,'successive_extensions':self.runs[context],
                      'previous_record_start':previous['start'],'record_start':start,'trigger_end':end,
                      'previous_characters':len(previous['text']),'new_characters':len(text),
                      'criterion':'Three exact entire-prefix extensions, prior length>=320, in same local attributed source context'}
            raise RepetitionAbort('V19_6 cumulative record expansion')

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
                    elif self.stack and self.stack[-1]['kind']=='[' and self.stack[-1]['name']=='refs':
                        scope=self.stack[-1]['start'];counts=self.address_counts.setdefault(scope,Counter());counts[value]+=1
                        if counts[value]>=2:
                            self.hit={'kind':'REPEATED_SOURCE_ADDRESS_IN_ONE_LIST','address':value,'count':counts[value],
                                      'list_start':scope,'trigger_end':pos,'scope':'ONE_REFS_ARRAY_ONLY_SECOND_COPY_INVALID'}
                            raise RepetitionAbort('V19_6 source-address list repetition')
                continue
            if char=='"':self.in_string=True;self.start_string=pos;continue
            if char in '{[':
                parent=self.stack[-1] if self.stack else None
                name=parent.get('key') if parent and parent['kind']=='{' else parent.get('name') if parent else None
                unit=next((x for x in reversed(self.stack) if x['kind']=='{' and x.get('premise')),None)
                frame={'kind':char,'start':pos,'name':name,'key':None,'expect_key':char=='{','unit':unit}
                if char=='{' and parent and parent.get('name')=='analyses':frame['premise']=name
                self.stack.append(frame)
            elif char in '}]' and self.stack:
                top=self.stack.pop()
                if char=='}' and top['name']=='records' and top['unit']:
                    try:record=json.loads(self.buffer[top['start']:pos+1])
                    except ValueError:continue
                    self.completed_record(record,top['unit'],top['start'],pos)
            elif char==',' and self.stack and self.stack[-1]['kind']=='{':self.stack[-1]['expect_key']=True
