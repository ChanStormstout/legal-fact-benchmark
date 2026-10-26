"""Shared minimal decoder/consumer helpers copied from the parent contract."""
from schema_contract import validate, loads

def obj(fields):
    return {'type':'object','properties':fields,'required':list(fields),'additionalProperties':False}

def text(n=200):
    return {'type':'string','minLength':1,'description':f'Complete concise text, normally within {n} characters; no padding.'}

def enum(values):
    values=list(values)
    if not values: raise ValueError('EMPTY_ENUM')
    return {'type':'string','enum':values}

def arr(item, hi=8, lo=0, unique=False):
    return {'type':'array','items':item,'minItems':lo,'maxItems':hi,'uniqueItems':unique}

def keyed(ids, schema):
    return obj({key:schema(key) if callable(schema) else schema for key in ids})

def boolean(): return {'type':'boolean'}
