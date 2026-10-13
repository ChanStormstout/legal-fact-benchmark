"""Lossless shared source-list transport. No source discovery or semantic edits."""
import copy
import json
from .schema_contract_v19_6 import validate

VERSION = 'SHARED_SOURCES_V20_3'
MAX_GROUPS = 16384  # Representation ceiling, above what the output budget can encode.


def schema(original):
    result = copy.deepcopy(original)
    def choice(empty=False):
        return {'type':'string','pattern':r'^C[0-9]{1,5}$',
                'description':'EMPTY_SOURCE_SET_ALLOWED' if empty else 'NONEMPTY_SOURCE_SET'}
    def walk(spec):
        if not isinstance(spec, dict):
            return
        props = spec.get('properties', {})
        if 'refs' in props:
            old = props.pop('refs')
            props['ref_set'] = choice(old.get('minItems', 0) == 0)
            spec['required'] = ['ref_set' if k=='refs' else k for k in spec.get('required', [])]
        if 'source' in props:
            props.pop('source')
            props['source_set'] = choice()
            spec['required'] = ['source_set' if k=='source' else k for k in spec.get('required', [])]
        for value in spec.values():
            if isinstance(value, dict):
                walk(value)
            elif isinstance(value, list):
                for item in value:
                    walk(item)
    walk(result)
    source = copy.deepcopy(original['$defs']['source_choice'])
    groups = {'type':'array','minItems':0,'maxItems':MAX_GROUPS,'uniqueItems':True,
              'items':{'type':'array','items':source,'minItems':1,
                       'maxItems':len(source['enum']),'uniqueItems':True}}
    result['properties'] = {'source_sets':groups, **result['properties']}
    result['required'] = ['source_sets', *result['required']]
    return result


def pack(value):
    groups, index = [], {}
    def group(refs):
        if not refs:
            return 'C0'
        if any(not isinstance(x,str) for x in refs) or len(refs)!=len(set(refs)):
            raise ValueError('INVALID_SOURCE_SEQUENCE')
        key = tuple(refs)
        if key not in index:
            groups.append(list(refs))
            index[key] = 'C'+str(len(groups))
        return index[key]
    def walk(node):
        if isinstance(node,list):
            return [walk(v) for v in node]
        if not isinstance(node,dict):
            return copy.deepcopy(node)
        result = {}
        for key, item in node.items():
            if key == 'refs':
                result['ref_set'] = group(item)
            elif key == 'witnesses':
                compact = []
                for witness in item:
                    attrs = {k:copy.deepcopy(v) for k,v in witness.items() if k!='source'}
                    if compact and compact[-1][0]==attrs:
                        compact[-1][1].append(witness['source'])
                    else:
                        compact.append((attrs,[witness['source']]))
                result[key] = [{'source_set':group(refs),**attrs} for attrs,refs in compact]
            else:
                result[key] = walk(item)
        return result
    body = walk(value)
    if len(groups)>MAX_GROUPS:
        raise ValueError('SOURCE_SET_CAPACITY')
    return {'source_sets':groups, **body}


def expand(value):
    groups = value['source_sets']
    if not isinstance(groups,list) or any(not isinstance(g,list) or not g or
            any(not isinstance(s,str) for s in g) or len(g)!=len(set(g)) for g in groups):
        raise ValueError('INVALID_SOURCE_TABLE')
    if len({tuple(g) for g in groups})!=len(groups):
        raise ValueError('DUPLICATE_SOURCE_SET')
    def refs(name):
        if name=='C0':
            return []
        if not isinstance(name,str) or not name.startswith('C') or not name[1:].isdigit():
            raise ValueError('INVALID_SOURCE_SET_ID')
        n = int(name[1:])
        if name!='C'+str(n) or not 1<=n<=len(groups):
            raise ValueError('UNDEFINED_SOURCE_SET:'+name)
        return copy.deepcopy(groups[n-1])
    def walk(node):
        if isinstance(node,list):
            return [walk(v) for v in node]
        if not isinstance(node,dict):
            return copy.deepcopy(node)
        result = {}
        for key, item in node.items():
            if key == 'ref_set':
                result['refs'] = refs(item)
            elif key == 'witnesses':
                result[key] = []
                for witness in item:
                    sources = refs(witness['source_set'])
                    if not sources:
                        raise ValueError('EMPTY_WITNESS_SOURCE_SET')
                    attrs = {k:copy.deepcopy(v) for k,v in witness.items() if k!='source_set'}
                    result[key].extend({'source':source,**attrs} for source in sources)
            elif key == 'source_sets':
                continue
            else:
                result[key] = walk(item)
        return result
    return walk(value)


def check_expansion(compact, expanded, original_schema):
    """Independent schema-directed reconstruction; does not call expand()."""
    validate(compact, schema(original_schema))
    groups = compact['source_sets']
    def lookup(name):
        if name=='C0':return []
        if not isinstance(name,str) or name not in {'C'+str(i+1) for i in range(len(groups))}:
            raise ValueError('INDEPENDENT_UNDEFINED_SOURCE_SET')
        return list(groups[int(name[1:])-1])
    def rebuild(node,spec):
        if '$ref' in spec:spec=original_schema['$defs'][spec['$ref'].split('/')[-1]]
        if spec.get('type')=='array':return [rebuild(v,spec['items']) for v in node]
        if spec.get('type')!='object':return copy.deepcopy(node)
        result={}
        for key,sub in spec.get('properties',{}).items():
            if key=='refs':result[key]=lookup(node['ref_set'])
            elif key=='witnesses':
                result[key]=[]
                for w in node[key]:
                    for source in lookup(w['source_set']):
                        result[key].append({'source':source,**{k:copy.deepcopy(v) for k,v in w.items() if k!='source_set'}})
            elif key in node:result[key]=rebuild(node[key],sub)
        return result
    expected=rebuild(compact,original_schema)
    validate(expanded,original_schema)
    if expected!=expanded:
        raise ValueError('INDEPENDENT_SOURCE_EXPANSION_MISMATCH')
    return {'status':'OK','source_sets':len(groups),'exact_values_and_order':True,
            'witness_attributes_preserved':True,'semantic_approval':False}


INSTRUCTION = '''SHARED SOURCE TRANSPORT V20_3 (replaces only the source-reference representation):
Write source_sets FIRST. It is an array of nonempty arrays of unique SRC:n addresses.
Its first array is C1, second C2, etc.; C0 means an empty refs list and has no table entry.
Define each distinct ordered source list ONCE; reuse its C identifier in every relevant field.
The table contains source references only, never claims or legal conclusions. Do not enumerate
the entire document or pad a list; select the actual relevant source addresses.
Every old refs array becomes ref_set:"C1". An old witness {source:"SRC:7",necessity:"REQUIRED"}
becomes {source_set:"C1",necessity:"REQUIRED"} when C1=["SRC:7"]. A witness group expands
to one witness PER MEMBER with the SAME necessity; split groups when necessity differs.
For example source_sets:[["SRC:7","SRC:9"]] can be reused by a record's ref_set, an object's
ref_set and a use's witnesses:[{source_set:"C1",necessity:"REQUIRED"}]. Source membership does
not establish object identity, support or truth. Retain all separate semantic judgments.
Only previously defined C identifiers are allowed. Reusing a set in another field is allowed;
copying its source list into another table entry is invalid. Finish the whole JSON normally.
All other fixed propositions, roles, dynamic EV/OBJ/USE references and legal constraints remain.
'''
