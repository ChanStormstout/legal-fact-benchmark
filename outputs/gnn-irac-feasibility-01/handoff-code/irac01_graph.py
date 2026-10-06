"""Export input graph and separate IRAC candidate sidecar; no training features from target-aware tasks."""
import pathlib,json,hashlib
R=pathlib.Path('outputs/gnn-irac-feasibility-01')
def read(p):return json.loads(p.read_text())
def out(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
for cid in read(R/'protocol.json')['case_ids']:
 i=read(R/'inputs'/f'{cid}.json');p=read(R/'web'/f'P-{cid}.raw.json');a=read(R/'audit'/f'{cid}.json');nodes=[{'id':'issue','type':'Issue','text':i['fixed_issue'],'stage':i['stage']}];edges=[]
 for seg in i['pre_outcome_source']['segments']:
  nodes.append({'id':seg['id'],'type':'SourcePassage','text':seg['text'],'not_independent_exhibit':True})
 for f in i['existing_inventory']['facts']:
  nodes.append({'id':'fact:'+f['id'],'type':'Fact','record':f,'semantic_status':'EXISTING_WEAK_PROPOSAL'});edges.append({'source':'fact:'+f['id'],'relation':'CONTEXT_FOR','target':'issue','not_a_truth_or_relevance_label':True})
 for f in i['existing_inventory']['facts']:
  for ref in f['refs']:edges.append({'source':'fact:'+f['id'],'relation':'GROUNDED_IN','target':ref})
 for obj in i['existing_inventory']['objects']:nodes.append({'id':'object:'+obj['id'],'type':'Object','record':obj})
 for rel in i['existing_inventory']['relations']:
  edges.append({'relation':'EXISTING_RELATION_RECORD','record':rel,'not_a_target_label':True})
 for u in i['oracle_rule_material']:
  nodes.append({'id':u['id'],'type':'ReviewedRuleSourceCandidate','record':u,'scope_not_automatically_confirmed':True})
 out(R/'interface-export-v2'/'input-graphs'/f'{cid}.json',{'case_id':cid,'nodes':nodes,'edges':edges,'origin':i['existing_inventory']['origin'],'input_sha256':hashlib.sha256((R/'inputs'/f'{cid}.json').read_bytes()).hexdigest(),'no_post_aware_binding_features':True,'target_adjudication_relation_ids':[x['id'] for x in i['existing_inventory']['relations'] if x.get('court')=='TARGET' and x.get('status') not in ('CLAIMED','REPORTED','UNKNOWN')],'source_partition_semantically_certified':False,'feature_admission':'NOT_ADMITTED','trainable':False,'explanation':'Issue, original weak facts, objects, relations and preselected source-backed rules only. Conditions and signed bindings were constructed with target access, so retained in a separate task layer, not automatically admitted as input features.'})
 out(R/'interface-export-v2'/'task-layer-candidates'/f'{cid}.json',{'case_id':cid,'conditions':p['conditions'],'bindings':p['bindings'],'address_checks':{'conditions':a['conditions'],'bindings':a['bindings']},'origin':'HIGH_WITH_POST_OUTCOME_ACCESS','feature_admission':'NOT_ADMITTED','semantic_rule_source_review_required':True,'conditions_need_pre_only_origin_for_future_test':'derive definitions from rule text only, with outcome-blind task-construction policy; do not regenerate in this round','signed_binding_need_pre_only_generation_for_future_test':'candidate evidence links must be obtainable from same allowed input at inference; current source checks alone cannot certify that procedure'})
print('Eight input graphs and separate task-layer candidates saved; not trainable.')
