"""Input-only graph with unsigned, generated computational candidate edges."""
import copy
from legal_bench.rules_verdict_v1.irac_graph_builder_v1 import build_input_graph
from legal_bench.rules_verdict_v1.irac_native_schema_v1 import ContractError,digest

FORBIDDEN={'supervision_mask','class_index','source_review','input_sufficient',
           'substantive_adjudication','explicit_evidentiary_unresolved','label',
           'target_refs','mask_reasons','review_confidence'}

def reject_supervision(value):
    if isinstance(value,dict):
        if set(value)&FORBIDDEN:raise ContractError('SUPERVISION_NOT_INPUT')
        for v in value.values():reject_supervision(v)
    elif isinstance(value,list):
        for v in value:reject_supervision(v)

def build_graph(input_record):
    reject_supervision(input_record)
    if input_record.get('blind_bindings'):
        raise ContractError('SIGNED_BINDINGS_NOT_MAIN_INPUT')
    graph=build_input_graph(input_record)
    graph.pop('graph_hash');graph['schema_version']='IRAC_APPLICATION_GRAPH_V1'
    condition_kinds={c['id']:c.get('kind','UNKNOWN') for c in input_record['conditions']}
    for n in graph['nodes']:
        if n['type']=='Condition':n['features']['condition_kind']=condition_kinds[n['id']]
    facts=[n['id'] for n in graph['nodes'] if n['type'] in {'Fact','Evidence'}]
    conditions=[n['id'] for n in graph['nodes'] if n['type']=='Condition']
    for fid in facts:
        for cid in conditions:
            for a,b in ((fid,cid),(cid,fid)):
                graph['edges'].append({'source':a,'target':b,'type':'CANDIDATE_LINK',
                    'source_refs':[],'provenance_record_id':None,
                    'origin':'DETERMINISTIC_ALL_FACT_CONDITION_COMPUTATIONAL_LINK',
                    'not_source_evidence':True})
    # Preserve already declared input references even if no duplicate relation row
    # was generated. These are model-proposed links, never identity inferred by code.
    existing={(e['source'],e['target'],e['type']) for e in graph['edges']}
    node_types={n['id']:n['type'] for n in graph['nodes']}
    for kind,key,relation,expected in [('facts','entity_ids','FACT_RELATES_TO_ENTITY','Entity'),('evidence','supports_fact_ids','EVIDENCE_SUPPORTS_FACT','Fact')]:
        for record in input_record[kind]:
            for target in record.get(key,[]):
                if node_types.get(target)!=expected:raise ContractError('DECLARED_REFERENCE_ENDPOINT_TYPE_INVALID')
                edge_key=(record['id'],target,relation)
                if edge_key in existing:continue
                graph['edges'].append(dict(source=record['id'],target=target,type=relation,source_refs=copy.deepcopy(record['source_refs']),provenance_record_id=record['id'],origin='DECLARED_MODEL_INPUT_REFERENCE_NOT_INFERRED'))
                existing.add(edge_key)
    # Explicit logical dependencies are given-rule information, not targets.
    for condition in input_record['conditions']:
        for dep in condition.get('dependencies',[]):
            graph['edges'].append({'source':dep['condition_id'],'target':condition['id'],
                'type':'CONDITION_'+dep['operator'],'source_refs':copy.deepcopy(condition['source_refs']),
                'provenance_record_id':condition['id'],'origin':'GIVEN_RULE_DEPENDENCY'})
    original=list(graph['edges'])
    for e in original:
        if e['type']=='CANDIDATE_LINK':continue
        inv=copy.deepcopy(e);inv.update(source=e['target'],target=e['source'],type='INVERSE_'+e['type'])
        graph['edges'].append(inv)
    graph['edges'].sort(key=lambda e:(e['source'],e['target'],e['type']))
    graph['semantics']='Source relations and unsigned computational candidates are distinct; no supervision read.'
    graph['graph_hash']=digest(graph)
    return graph
