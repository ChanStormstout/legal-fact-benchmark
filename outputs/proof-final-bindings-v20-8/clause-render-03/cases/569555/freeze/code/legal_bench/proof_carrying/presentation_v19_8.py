"""Lossless presentation only. Does not select, repair or approve semantics."""
import copy
from collections import Counter
from .rule_contracts_v19_7 import digest

VERSION='V19_8_EXACT_STRING_POOL_1'
MARKER='$exact_text'

def pack(value, minimum_characters=160):
    counts=Counter()
    def count(x):
        if isinstance(x,str):counts[x]+=1
        elif isinstance(x,list):
            for y in x:count(y)
        elif isinstance(x,dict):
            if MARKER in x:raise ValueError('PRESENTATION_RESERVED_KEY')
            for y in x.values():count(y)
    count(value)
    pool={};choices={}
    for text,n in counts.items():
        if n>1 and len(text)>=minimum_characters:
            key='TXT:'+str(len(pool)+1);pool[key]=text;choices[text]=key
    def encode(x):
        if isinstance(x,str) and x in choices:return {MARKER:choices[x]}
        if isinstance(x,list):return [encode(y) for y in x]
        if isinstance(x,dict):return {k:encode(y) for k,y in x.items()}
        return copy.deepcopy(x)
    result={'presentation_version':VERSION,'exact_text_pool':pool,'material':encode(value)}
    if unpack(result)!=value:raise ValueError('LOSSLESS_ROUNDTRIP_FAILED')
    return result

def unpack(packed):
    if packed['presentation_version']!=VERSION:raise ValueError('PRESENTATION_VERSION')
    pool=packed['exact_text_pool']
    if any(not isinstance(v,str) for v in pool.values()):raise ValueError('NON_TEXT_POOL_VALUE')
    def decode(x):
        if isinstance(x,dict):
            if MARKER in x:
                if set(x)!={MARKER} or x[MARKER] not in pool:raise ValueError('INVALID_EXACT_TEXT_REFERENCE')
                return pool[x[MARKER]]
            return {k:decode(y) for k,y in x.items()}
        if isinstance(x,list):return [decode(y) for y in x]
        return copy.deepcopy(x)
    return decode(packed['material'])

def audit(original,packed):
    restored=unpack(packed)
    return {'version':VERSION,'original_sha256':digest(original),'restored_sha256':digest(restored),
            'exact_roundtrip':original==restored,'unique_pool_strings':len(packed['exact_text_pool']),
            'no_semantic_filter_or_truncation':True}
