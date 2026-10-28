"""Byte-preserving stream progress guards copied without semantic changes from frozen V38."""
import re,json
from common import digest
from collections import Counter

class BlankNoProgress(RuntimeError):
    pass

class RepeatedTextNoProgress(RuntimeError):
    pass

class ProgressWriter:
    """Save raw chunks; abort a long repeated block in one unclosed string.

    A detector is an abnormal-stop policy, not a semantic correction. It neither
    edits JSON nor treats the prefix as a usable answer. Ordinary repeated IDs
    in separate strings and short repeated phrases do not trigger this guard.
    """
    def __init__(self,out,limit,repetition_min_chars=2048,repetition_min_repeats=8,repetition_window_chars=32768):
        self.out=out;self.limit=limit;self.run=0;self.longest=0
        self.in_string=False;self.escaped=False;self.characters=0
        self.string_raw='';self.last_string_length=None;self.completed_strings=0
        self.string_length=0;self.repetition=None
        self.repeat_min=repetition_min_chars;self.repeat_count=repetition_min_repeats
        self.repeat_window=repetition_window_chars
    def check_repetition(self):
        tail=self.string_raw[-self.repeat_window:]
        # Sentence repetitions detect V19's failure even across wire chunks.
        sentences=re.findall(r'[^.!?\n]{80,}[.!?](?:\s|$)',tail)
        counts=Counter(' '.join(s.split()) for s in sentences)
        for sentence,count in counts.items():
            if count>=self.repeat_count and len(sentence)*count>=self.repeat_min:
                self.repetition={'kind':'REPEATED_SENTENCE','count':count,
                    'block_characters':len(sentence),'block_hash':digest(sentence)}
                raise RepeatedTextNoProgress('REPEATED_PROSE_IN_UNCLOSED_JSON_STRING')
        # Covers repeated paragraphs with no sentence terminator. Compare exact
        # contiguous periods; do not infer semantic repetition from vocabulary.
        if len(tail)<self.repeat_min:return
        anchor=tail[-128:];end=len(tail)-128;at=tail.rfind(anchor,0,end)
        while at>=max(0,end-4096):
            period=end-at
            if period>=80 and period*self.repeat_count>=self.repeat_min and len(tail)>=period*self.repeat_count:
                block=tail[-period:]
                if tail[-period*self.repeat_count:]==block*self.repeat_count:
                    self.repetition={'kind':'PERIODIC_BLOCK','count':self.repeat_count,
                        'block_characters':period,'block_hash':digest(block)}
                    raise RepeatedTextNoProgress('REPEATED_PROSE_IN_UNCLOSED_JSON_STRING')
            if at==0:break
            at=tail.rfind(anchor,0,at)
    def write(self,text):
        result=self.out.write(text);self.out.flush()
        for char in text:
            self.characters+=1
            if self.in_string:
                self.run=0
                self.string_length+=1
                if self.escaped:self.escaped=False;self.string_raw+=char
                elif char=='\\':self.escaped=True;self.string_raw+=char
                elif char=='"':
                    self.in_string=False;self.completed_strings+=1
                    try:self.last_string_length=len(json.loads('"'+self.string_raw+'"'))
                    except ValueError:self.last_string_length=None
                    self.string_raw=''
                else:self.string_raw+=char
                if self.in_string and self.string_length%256==0:
                    self.check_repetition()
            elif char=='"':self.in_string=True;self.run=0;self.string_raw='';self.string_length=0
            elif char in ' \t\r\n':
                self.run+=1;self.longest=max(self.longest,self.run)
                if self.run>=self.limit:raise BlankNoProgress('OUTSIDE_STRING_WHITESPACE_WITHOUT_CONTENT_PROGRESS')
            else:self.run=0
        return result
    def flush(self):self.out.flush()
    def diagnostic(self):
        return {'characters_examined':self.characters,'outside_string_whitespace_run':self.run,
            'longest_whitespace_run':self.longest,'in_string':self.in_string,
            'completed_strings':self.completed_strings,'last_completed_string_characters':self.last_string_length,
            'repetition':self.repetition,'repetition_is_not_semantic_validation':True,
            'provider_internals_known':False,'raw_content_preserved':True}
