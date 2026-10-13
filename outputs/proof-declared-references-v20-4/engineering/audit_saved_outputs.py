"""Read-only lexical inspection of saved raw generations; no repair or model call."""
import ast
import collections
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/proof-declared-references-v20-4'
def spans(raw):
    stack, result = [], []
    inside, escaped, start = False, False, 0
    for pos, c in enumerate(raw):
        if inside:
            if escaped:
                escaped = False
            elif c == '\\':
                escaped = True
            elif c == '"':
                inside = False
                s = json.loads(raw[start:pos+1])
                if stack and stack[-1]['kind'] == '{' and stack[-1]['expect_key']:
                    stack[-1]['key'] = s
                    stack[-1]['expect_key'] = False
            continue
        if c == '"':
            inside, start = True, pos
        elif c in '{[':
            parent = stack[-1] if stack else None
            path = parent['path'][:] if parent else []
            if parent:
                path.append(parent['key'] if parent['kind'] == '{' else parent['index'])
            stack.append({'kind':c,'start':pos,'path':path,'key':None,'expect_key':c=='{','index':0})
        elif c in '}]' and stack:
            f = stack.pop()
            try:
                value = json.loads(raw[f['start']:pos+1])
            except ValueError:
                continue
            result.append({'path':f['path'],'start':f['start'],'end':pos+1,'value':value})
        elif c == ',' and stack:
            if stack[-1]['kind'] == '{':
                stack[-1]['expect_key'] = True
            else:
                stack[-1]['index'] += 1
    return result, stack

def inspect(path):
    raw=path.read_text();nodes,opened=spans(raw);declared={};bad=[];checked=collections.Counter();ev_lengths=[];identical={}
    for f in nodes:
        p=f['path'];v=f['value']
        if len(p)==3 and p[0]=='analyses' and p[-1] in ('records','objects','uses') and isinstance(v,list):
            declared.setdefault(p[1],{})[p[-1]]=len(v)
        if len(p)==3 and p[0]=='analyses' and p[-1] in ('records','objects','uses','judgments') and isinstance(v,list):
            counts=collections.Counter(json.dumps(x,sort_keys=True,ensure_ascii=False) for x in v)
            for key,count in counts.items():
                if count>1:identical[(tuple(p),key)]=count
    def check(values,prefix,count,path,pid):
        for v in values:
            if v=='UNMAPPED':checked['UNMAPPED']+=1;continue
            if isinstance(v,str) and re.fullmatch(prefix+r':[1-9][0-9]*',v):
                checked[prefix]+=1
                if not 1<=int(v.split(':')[1])<=count:
                    bad.append({'path':path,'premise':pid,'value':v,'declared_count':count})
    for f in nodes:
        p=f['path'];v=f['value']
        if p and p[0]=='analyses' and len(p)>2:
            pid=p[1];counts=declared.get(pid,{})
            if p[-1]=='records' and 'uses' in p and isinstance(v,list):
                check(v,'EV',counts.get('records',0),p,pid);ev_lengths.append(len(v))
            elif p[-1] in ('uses','opposition_uses') and 'judgments' in p and isinstance(v,list):
                check(v,'USE',counts.get('uses',0),p,pid)
            elif 'alternatives' in p and isinstance(v,list) and all(isinstance(x,str) for x in v):
                check(v,'USE',counts.get('uses',0),p,pid)
            elif p[-1]=='role_objects' and isinstance(v,dict):
                check(v.values(),'OBJ',counts.get('objects',0),p,pid)
        elif len(p)==2 and p[0]=='object_links' and isinstance(v,dict):
            for side in ('left','right'):
                pid=v.get(side+'_premise');check([v.get(side+'_object')],'OBJ',declared.get(pid,{}).get('objects',0),p+[side+'_object'],pid)
    table=next((f['value'] for f in nodes if f['path']==['source_sets']),None)
    complete_units=[f['path'][1] for f in nodes if len(f['path'])==2 and f['path'][0]=='analyses']
    return {'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'incomplete_prefix':bool(opened),
            'closed_analysis_units':complete_units,'declared_counts':declared,'checked':dict(checked),
            'invalid_local_reference_occurrences':len(bad),'invalid_reference_examples':bad[:12],
            'max_EV_array_length':max(ev_lengths,default=0),'raw_EV_mentions':len(re.findall(r'"EV:\d+"',raw)),
            'source_sets':len(table) if table is not None else None,'source_set_lengths':[len(x) for x in table] if table is not None else None,
            'source_mentions':len(re.findall(r'"SRC:\d+"',raw)),
            'duplicate_source_definitions':len(table)-len({tuple(x) for x in table}) if table is not None else None,
            'identical_records_in_same_array':len(identical),
            'open_path':opened[-1]['path'] if opened else None,'semantic_redundancy_evaluated':False}

if __name__=='__main__':
    assert (OUT/'local/569555/P01/run.json').exists()
    result={'scope':'Saved raw closed structures, includes link endpoints; no repair or model call',
            'old':inspect(ROOT/'outputs/proof-shared-sources-v20-3/local/569555/P01/raw-response.txt'),
            'new':inspect(OUT/'local/569555/P01/raw-response.txt')}
    (OUT/'engineering/rerun-reference-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result['new'].items() if k not in ('declared_counts','invalid_reference_examples')},ensure_ascii=False))
