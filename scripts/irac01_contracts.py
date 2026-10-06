"""Crosswalk, task contract and read-only group implementation audit."""
import json,csv
from pathlib import Path
R=Path('outputs/gnn-irac-feasibility-01')
def put(n,v):p=R/n;p.parent.mkdir(exist_ok=True,parents=True);assert not p.exists();p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
rows=[]
def row(field,role,mode,limit,provenance):rows.append({'group_field':field,'IRAC_role':role,'mode':mode,'limitations':limit,'provenance':provenance})
row('LegalIssue','Issue','DIRECT_REUSE','Separate pleaded issue from target-court resolution','node.source_refs; original node_id')
row('Fact','Pre-outcome fact candidate','ADAPTER','Full canonical may contain target-court findings; require source/field grants; never promote record support to proven truth','source_refs plus field-level grants; keep raw record_status/court_status')
row('Evidence','Evidence/record support','DIRECT_REUSE_WITH_ADAPTER','Deterministic source-passage evidence is a record anchor, not independent corroboration or an actual exhibit','source_refs; preserve canonicalizer-generated origin')
row('Claim','Claim context','ADAPTER','Claim viability prunes orphan claims; absence is not false or rejected. Schema lacks typed claimant/element/burden','Party ASSERTS plus provenance; unknown claimant retained')
row('Party','Party/context actor','DIRECT_REUSE','Same role/string is not same person; object/property has no separate node type','node_id, party_side, refs; no similarity merge')
row('Court','Court/procedural context','ADAPTER','Court node plus description/refs required; no typed court-level/stage field','retain original refs; reviewed task sidecar supplies stage only when evidenced')
row('Precedent','Authority context','ADAPTER','APPLIES_TO/target FOLLOWS is semantic treatment, not rule text; current-court treatment must not enter input','refs + normalized citation; reviewed rule stores own source separately')
row('record_status','Record status','DIRECT_REUSE','ALLEGED/ADMITTED/etc separate from truth or element label','retain unchanged and preserve field grant')
row('court_status','Target adjudicative treatment','EXCLUDE_OR_SIDECAR','ACCEPTED/REJECTED outcome-bearing. Lower-court report must retain level without target endorsement','exclude current treatment from input, target-only lineage')
row('source_refs/source_span_id','Source grounding','ADAPTER','Locator success does not prove semantics; group spans not same as our IK line IDs','document_id, exact_quote, span/paragraph map, raw-response provenance')
row('Evidence→Fact→Claim','Primitive proof route','ADAPTER','No direct Evidence→Claim; context-only merits gaps do not yield condition truth','preserve edge IDs/refs; rebuild chains after input filtering')
row('semantic relations / canonical_merge_key','Relations and identities','DIRECT_REUSE_WITH_ADAPTER','No new identity/part-of semantics invented; generic edges may not encode property/event binding directly','keep explicit edge direction and original IDs, no label-similarity merging')
row('Conclusion / court_conclusion_issue chains','Application/issue supervision candidates','TARGET_ONLY','Mixed full-judgment canonical is unsafe as model input; not one label for all elements','original conclusion refs + target-only files')
row('Rule','Reviewed rule','TASK_LAYER_MISSING','Not a canonical node; Prompt1 rule_and_authority does not imply canonical preservation','exact independent authority text/scope/date/stance')
row('Condition / Element','Rule condition','TASK_LAYER_MISSING','No typed canonical rule conditions or logical dependencies','rule ID, exact quote, logical role, AND/OR/qualification, scope')
row('Fact↔Condition binding','Candidate binding','TASK_LAYER_MISSING','Signed candidate ≠ established fact; unknown roles not wildcard; cannot invent input fact from label','existing fact ID, source/status/court/stage + input/target flag')
row('Application target','Element supervision','TASK_LAYER_MISSING','Three states plus nonclass cause distinguish fact false/burden/not-decided','target-court reasoning refs only; never features')
put('canonical-to-irac-crosswalk.json',rows)
with (R/'canonical-to-irac-crosswalk.csv').open('x',newline='') as fp:w=csv.DictWriter(fp,list(rows[0]));w.writeheader();w.writerows(rows)
# Task layer: no expansion of group ontology; source refs are separate across information zones.
string={'type':'string','minLength':1};arr=lambda item:{'type':'array','items':item}
def obj(props):return {'type':'object','additionalProperties':False,'required':list(props),'properties':props}
ref=obj({'id':string,'quote':string});dependency=obj({'condition_id':string,'operator':{'enum':['AND','OR','QUALIFICATION']}})
condition=obj({'id':string,'rule_id':string,'exact_rule_quote':string,'description':string,'logical_role':string,'scope':string,'dependencies':arr(dependency),'law_refs':arr(string)})
binding=obj({'id':string,'fact_id':string,'condition_id':string,'relation':{'enum':['SUPPORTS','DEFEATS','RELEVANT_TO']},'statement_status':string,'court':string,'stage':string,'case_refs':arr(string),'reason':string,'input_candidate':{'const':True},'target_only':{'const':False}})
target=obj({'condition_id':string,'status':{'enum':['SATISFIED','DEFEATED','UNRESOLVED']},'basis_kind':{'enum':['FACT_ACCEPTED','FACT_FALSE','BURDEN_NOT_CARRIED','NOT_DECIDED','INSUFFICIENT_RECORD','LEGAL_INTERPRETATION','AMBIGUOUS_REASONING']},'target_refs':arr(ref),'reason':string})
schema=obj({'case_id':string,'conditions':dict(arr(condition),maxItems=6),'bindings':dict(arr(binding),maxItems=12),'element_targets':arr(target),'issue_target':obj({'status':{'enum':['SUPPORTED','NOT_SUPPORTED','UNRESOLVED']},'target_refs':arr(ref),'reason':string}),'gaps':arr(obj({'kind':string,'description':string,'affected_ids':arr(string)})),'chain_status':{'enum':['PROPOSED_COMPLETE','GAP']}});schema['$schema']='https://json-schema.org/draft/2020-12/schema';put('irac-task-schema.json',schema)
(R/'group-schema-audit.md').write_text('''# 组内实际接口审计

读取 main `88ff082cce05b948119fcd54f6ef8fe8540baedb`，完整文件与哈希见 group-read-manifest.json。当前本仓库远端 research/rules-and-verdict 为 `6ac6de5...`；本地V11完成但尚未发布，不能假称远端已包含V11。

实际 config.yaml → prompts/prompt2_v5_2_rich_canonical.md → src/run_case.py。production prompt 行为v5.3.2，候选/最终Schema标识仍v5.2；README仍写v5.2。兼容标识与行为版本必须分别记录。候选由 llm_candidate_schema 接收，canonicalizer 再生成最终九类型Schema，不直接输出IRAC图。source_validator验证源span；semantic_admission/semantic_audit处理语义诊断；production_guardrails限制修复。我们没有运行这些昂贵上游步骤或其ASU API。

实际类型为Case/Court/Party/Claim/Fact/Evidence/LegalIssue/Precedent/Conclusion。没有Rule/Element/Application节点；Prompt1A有rule_and_authority及elements、Prompt1B有elements_analyzed，不意味着这些内容以独立结构进入canonical。

canonicalizer `_prune_orphan_claims`要求Claim有Fact SUPPORTS/DEFEATS/CONTESTS实质边；孤立Claim会被剪去。没有Claim不能解释为没有请求。`_materialize_record_proof`可按Fact出处生成source-passage Evidence；它是文字来源锚，不是第二份实物证据。生产prompt明确区分当前法院采纳与下级法院事实经过，但Schema本身没有typed court-level/stage、property、event或rule-condition槽位；这部分需要有出处的下游sidecar，不能按名字猜测。

全判决canonical保留court_status与Conclusion，适合来源分析，直接进入预测图会泄漏。adapter要求逐节点、逐字段pre-outcome许可，排除目标Conclusion/接受拒绝处理及悬空边，不复制全判决proof_chains。两个空ID、同角色、同引文均不创建新身份边。

组内main未发现任何这8案的canonical JSON产物。本轮真正canonical adapter用完整合成合法fixture验证，8案数据验证复用现有local weak inventory，来源身份明确，不声称上游复现或真实canonical数据端到端通过。实际canonical数据验收是后续接入前置条件；可以在不修改组内production schema的情况下添加任务层，但缺失信息不能由adapter自动补造。

评价代码EVALUATOR_LOGIC.md依原文双lane生成自动参考，再做关系匹配。其精度/召回依赖模型参考，不是人工gold；没有以其自动得分替代本轮逐链核查。
''')
print('Crosswalk, audit, minimal task schema written.')
