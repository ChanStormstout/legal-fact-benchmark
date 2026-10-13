"""Deterministic target-free heterogeneous input graph; no train or embeddings."""
import copy
from .irac_native_schema_v1 import ContractError, validate_input, digest

NODE_TYPES={'entities':'Entity','rules':'Rule','conditions':'Condition','facts':'Fact','evidence':'Evidence'}
EDGE_TYPES={'RULE_HAS_CONDITION','ISSUE_GOVERNED_BY_RULE','FACT_SUPPORTS_CONDITION',
            'FACT_DEFEATS_CONDITION','FACT_RELEVANT_TO_CONDITION','EVIDENCE_SUPPORTS_FACT',
            'PARTY_ASSERTS_FACT','PRIOR_COURT_FOUND_FACT','FACT_RELATES_TO_ENTITY'}
FEATURES=('statement_status','semantic_stage','party_side','court_level','polarity','prospective_availability')

def build_input_graph(input_record):
    errors=validate_input(input_record)
    if errors:raise ContractError(';'.join(errors))
    nodes=[];edges=[]
    def node(r,kind):
        nodes.append({'id':r['id'],'type':kind,'features':{k:copy.deepcopy(r.get(k)) for k in FEATURES},
                      'source_grounded':bool(r.get('source_refs')),'text':r.get('text',r.get('description','')),
                      'source_refs':copy.deepcopy(r['source_refs'])})
    def edge(a,b,kind,refs,record_id):
        if kind not in EDGE_TYPES:raise ContractError('UNSUPPORTED_EDGE:'+kind)
        edges.append({'source':a,'target':b,'type':kind,'source_refs':copy.deepcopy(refs),'provenance_record_id':record_id,'candidate_relation_not_truth':kind.startswith('FACT_') and kind.endswith('_CONDITION')})
    issue=input_record['issue'];node(issue,'Issue')
    for collection,kind in NODE_TYPES.items():
        for r in input_record[collection]:node(r,kind)
    for r in input_record['rules']:
        # Relation must be explicitly proposed and independently quoted.
        if r.get('governs_issue_id')==issue['id']:
            edge(issue['id'],r['id'],'ISSUE_GOVERNED_BY_RULE',r['source_refs'],r['id'])
    for r in input_record['conditions']:
        edge(r['rule_id'],r['id'],'RULE_HAS_CONDITION',r['source_refs'],r['id'])
    for r in input_record['blind_bindings']:
        edge(r['fact_id'],r['condition_id'],'FACT_'+r['relation']+'_CONDITION',r['source_refs'],r['id'])
    for r in input_record['relations']:
        edge(r['source_record_id'],r['target_record_id'],r['relation'],r['source_refs'],r['id'])
    ids={n['id'] for n in nodes}
    if len(ids)!=len(nodes) or any(e['source'] not in ids or e['target'] not in ids for e in edges):raise ContractError('GRAPH_ENDPOINT_INVALID')
    graph={'schema_version':'IRAC_INPUT_GRAPH_V1','case_id':input_record['case_id'],
           'nodes':sorted(nodes,key=lambda n:n['id']),'edges':sorted(edges,key=lambda e:(e['source'],e['target'],e['type'],e['provenance_record_id'])),
           'input_hash':digest(input_record),'semantics':'Directional model-proposed bindings preserve record status; no target, label, automatic identity or truth inference.'}
    graph['graph_hash']=digest(graph)
    return graph

def graph_schema():
    return {'version':'IRAC_INPUT_GRAPH_V1','node_types':['Issue']+list(NODE_TYPES.values()),'edge_types':sorted(EDGE_TYPES),'features':list(FEATURES)+['source_grounded','text'],'target_free_api':'build_input_graph(input_record)','training':False}
