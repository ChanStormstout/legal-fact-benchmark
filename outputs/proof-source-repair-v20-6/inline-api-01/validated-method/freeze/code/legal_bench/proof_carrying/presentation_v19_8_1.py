"""Exact repeated JSON subtree interning; no semantic pruning or summarization."""
import copy,json
from collections import Counter
from .rule_contracts_v19_7 import digest
VERSION='V19_8_EXACT_VALUE_POOL_2';MARKER='$exact_value'
def serialize(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'))
def pack(value,minimum_characters=160):
    counts=Counter();original={}
    def collect(x):
        if isinstance(x,dict) and MARKER in x:raise ValueError('PRESENTATION_RESERVED_KEY')
        if isinstance(x,(str,dict,list)):
            key=serialize(x)
            if len(key)>=minimum_characters:counts[key]+=1;original[key]=copy.deepcopy(x)
        if isinstance(x,dict):
            for v in x.values():collect(v)
        elif isinstance(x,list):
            for v in x:collect(v)
    collect(value);pool={};aliases={}
    def encode(x):
        key=serialize(x) if isinstance(x,(str,dict,list)) else None
        if key in original and counts[key]>1:
            if key not in aliases:
                ref='VAL:'+str(len(pool)+1);aliases[key]=ref;pool[ref]=original[key]
            return {MARKER:aliases[key]}
        if isinstance(x,dict):return {k:encode(v) for k,v in x.items()}
        if isinstance(x,list):return [encode(v) for v in x]
        return copy.deepcopy(x)
    result={'presentation_version':VERSION,'exact_value_pool':pool,'material':encode(value)}
    assert unpack(result)==value,'EXACT_PRESENTATION_ROUNDTRIP'
    return result

def unpack(value):
    if value['presentation_version']!=VERSION:raise ValueError('PRESENTATION_VERSION')
    pool=value['exact_value_pool']
    def valid_pool(x):
        if isinstance(x,dict):
            if MARKER in x:raise ValueError('NESTED_POOL_REFERENCE_FORBIDDEN')
            for v in x.values():valid_pool(v)
        elif isinstance(x,list):
            for v in x:valid_pool(v)
    for v in pool.values():valid_pool(v)
    def restore(x):
        if isinstance(x,dict):
            if MARKER in x:
                if set(x)!={MARKER} or x[MARKER] not in pool:raise ValueError('INVALID_EXACT_VALUE_REFERENCE')
                return copy.deepcopy(pool[x[MARKER]])
            return {k:restore(v) for k,v in x.items()}
        if isinstance(x,list):return [restore(v) for v in x]
        return copy.deepcopy(x)
    return restore(value['material'])

def audit(original,packed):
    restored=unpack(packed)
    return {'version':VERSION,'original_sha256':digest(original),'restored_sha256':digest(restored),
        'exact_roundtrip':original==restored,'pool_entries':len(packed['exact_value_pool']),
        'original_json_characters':len(serialize(original)),'pooled_json_characters':len(serialize(packed)),
        'no_semantic_filter_or_truncation':True}
