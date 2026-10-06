"""Source-partitioned downstream adapter; no inference, label input or ID merging."""
import copy, hashlib, json
NODE_ROLES={'Case':'CaseContext','Court':'CourtContext','Party':'Party','Claim':'ClaimContext','Fact':'Fact','Evidence':'Evidence','LegalIssue':'Issue','Precedent':'AuthorityContext'}
ADJUDICATIVE={'ACCEPTS','PARTIALLY_ACCEPTS','REJECTS','FOLLOWS','DISAPPROVES','OVERRULES','REACHES','RESOLVES'}
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def adapt_canonical(canonical, source_partition):
    """Explicit field grants required. Valid quotation alone does not license a field.
    No current-court accepted/rejected treatment or Conclusion enters input.
    Lower findings must be expressed in reviewed description/status sidecars.
    """
    grants=source_partition['node_grants'];eg=source_partition.get('edge_grants',{})
    known=set(source_partition['pre_source_ids']);nodes=[];excluded=[]
    for n in canonical['nodes']:
        g=grants.get(n['node_id'],{});refs=n['source_refs']
        approved=g.get('field_zones',{}); semantic_fields=('label','description','record_status','court_status')
        if any(approved.get(k)!='PRE_OUTCOME' for k in semantic_fields):
            excluded.append({'id':n['node_id'],'reason':'SEMANTIC_FIELD_NOT_PRE_OUTCOME_GRANTED'});continue
        if n['node_type']=='Conclusion' or not g.get('input_allowed') or not all(x.get('paragraph_id') in known for x in refs):
            excluded.append({'id':n['node_id'],'reason':'NO_PRE_OUTCOME_GRANT_OR_POST_SOURCE'});continue
        if n['court_status'] in ('ACCEPTED','PARTIALLY_ACCEPTED','REJECTED'):
            excluded.append({'id':n['node_id'],'reason':'TARGET_COURT_STATUS_ON_INPUT_NODE'});continue
        node=copy.deepcopy(n);node['irac_role']=NODE_ROLES[n['node_type']]
        node['provenance']={'upstream_node_id':n['node_id'],'upstream_node_sha256':digest(n),'source_refs':copy.deepcopy(refs),'field_grant':copy.deepcopy(g),'record_evidence_is_not_verified_fact':True}
        nodes.append(node)
    retained={n['node_id'] for n in nodes};edges=[]
    for e in canonical['edges']:
        if e['source_node_id'] not in retained or e['target_node_id'] not in retained or not eg.get(e['edge_id'],{}).get('input_allowed') or e['relation_type'] in ADJUDICATIVE or not all(x.get('paragraph_id') in known for x in e['source_refs']):
            excluded.append({'id':e['edge_id'],'reason':'EDGE_NOT_PRE_OUTCOME_OR_ENDPOINT_EXCLUDED'});continue
        edges.append(copy.deepcopy(e))
    return {'case_id':canonical['case_id'],'representation_origin':source_partition['origin'],'nodes':nodes,'edges':edges,'excluded_objects':excluded,'input_only':True,'proof_chains_rebuilt_from_retained_edges_only':True,'upstream_proof_chains_not_copied':True}
def legacy_inventory(proposal, source):
    """Reuse existing weak facts; never call this group canonical extraction."""
    ids={s['id'] for s in source['segments']};facts=[];quarantined=[]
    for f in proposal['facts']:
        reasons=[]
        if not f.get('refs') or not set(f['refs'])<=ids:reasons.append('REF_NOT_IN_ALLOWED_SOURCE')
        if f.get('court')=='TARGET' and f.get('status') not in ('REPORTED','CLAIMED','UNKNOWN'):reasons.append('POSSIBLE_TARGET_ADJUDICATION')
        if reasons:quarantined.append({'record':copy.deepcopy(f),'reasons':reasons})
        else:facts.append(copy.deepcopy(f))
    return {'case_id':proposal['case_id'],'origin':'EXISTING_LOCAL_WEAK_INVENTORY_NOT_LATENTWEAVER_CANONICAL','facts':facts,'objects':copy.deepcopy(proposal['objects']),'relations':[copy.deepcopy(x) for x in proposal['relations'] if set(x.get('refs',[]))<=ids],'issue_needs_context_not_application_targets':copy.deepcopy(proposal['needs']),'quarantined':quarantined,'pre_source_ids':sorted(ids)}
def check_binding(binding, inventory, conditions):
    fm={f['id']:f for f in inventory['facts']};cm={c['id']:c for c in conditions}
    errors=[]
    if binding['fact_id'] not in fm:errors.append('UNKNOWN_OR_NEW_FACT_FORBIDDEN')
    if binding['condition_id'] not in cm:errors.append('UNKNOWN_CONDITION')
    if binding['relation'] not in ('SUPPORTS','DEFEATS','RELEVANT_TO'):errors.append('INVALID_BINDING_RELATION')
    if not binding.get('case_refs') or not set(binding['case_refs'])<=set(inventory['pre_source_ids']):errors.append('POST_OUTCOME_REF_FORBIDDEN')
    if binding['fact_id'] in fm and not set(binding.get('case_refs',[]))<=set(fm[binding['fact_id']]['refs']):errors.append('BINDING_REF_NOT_IN_FACT_PROVENANCE')
    return errors
