"""Lossless assembly of independently bounded outputs without a global20 clamp."""
import copy
from .atomic_extraction_v8 import convert as atomic_convert

def assemble(outputs,edge_outputs,registry,source,tasks):
    base,operations=atomic_convert({},edge_outputs,registry,source,tasks)
    events=[];unit_evidence=[]
    for typ,data in outputs.items():
        part,ops=atomic_convert({typ:data},{},registry,source,tasks)
        operations.extend(ops)
        for event in part['events']:
            event=copy.deepcopy(event);event['id']='e%d'%(len(events)+1)
            events.append(event)
        unit_evidence.extend(part['units'][0]['evidence'])
    unique=[];seen=set()
    for e in unit_evidence:
        key=(e['segment_id'],e['quote'])
        if key not in seen:unique.append(e);seen.add(key)
    base['events']=events;base['units'][0]['evidence']=unique
    operations.append({'action':'ASSEMBLE_ALL_VALIDATED_TYPE_OUTPUTS',
                       'rule':'Preserve all records/values/limits/quotes; assign unique structural event IDs. No global20 event truncation or semantic modification.'})
    return base,operations
