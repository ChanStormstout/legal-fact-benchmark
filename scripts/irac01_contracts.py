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
(R/'group-schema-audit.md').write_text('''# Audit of the group's actual interface

Read main `88ff082cce05b948119fcd54f6ef8fe8540baedb`; full files/hashes are in group-read-manifest.json. This repository's remote research/rules-and-verdict was `6ac6de5...`. Local V11 was complete but unpublished; it was not represented as already remote.

Actual path: config.yaml → prompts/prompt2_v5_2_rich_canonical.md → src/run_case.py. Production prompt behavior is v5.3.2, while candidate/final schema identifiers and README still say v5.2. Compatibility identifiers and behavior versions must be recorded separately. llm_candidate_schema receives candidates, then canonicalizer builds the final nine-type schema, not an IRAC graph directly. source_validator checks source spans; semantic_admission/semantic_audit provide semantic diagnostics; production_guardrails restrict repair. These expensive upstream steps and the ASU API were not run here.

Actual types are Case/Court/Party/Claim/Fact/Evidence/LegalIssue/Precedent/Conclusion. There are no Rule/Element/Application nodes. Prompt1A's rule_and_authority/elements and Prompt1B's elements_analyzed do not establish independent canonical structures for that content.

canonicalizer `_prune_orphan_claims` requires substantive Fact SUPPORTS/DEFEATS/CONTESTS edges for a Claim and prunes orphans. Absence of Claim does not mean absence of a legal claim. `_materialize_record_proof` may create source-passage Evidence from Fact provenance; this is a textual anchor, not a second physical exhibit. Production prompts distinguish current-court adoption from lower-court history, but the schema has no typed court-level/stage, property, event, or rule-condition slots. A sourced downstream sidecar is needed; names cannot supply missing semantics.

Full-judgment canonical data retain court_status and Conclusion. They support source analysis but leak outcomes if directly used as prediction inputs. The adapter requires node/field pre-outcome grants, excludes target Conclusion/acceptance/rejection and dangling edges, and does not copy full-judgment proof_chains. Empty IDs, shared roles, or shared quotations do not create identity edges.

No canonical JSON outputs for these eight cases were found on the group's main branch. The actual canonical adapter was tested with a complete valid synthetic fixture; eight-case data checks reused the existing local weak inventory with explicit provenance. This does not establish upstream reproduction or end-to-end acceptance of real canonical data. Actual canonical-data acceptance remains a prerequisite for integration. A task layer can be added without changing the group's production schema, but the adapter cannot fabricate missing information.

EVALUATOR_LOGIC.md generates automatic references in two source-reading lanes and then matches relations. Precision/recall depend on model references, not human gold. Its automatic score did not replace chain-level inspection here.
''')
print('Crosswalk, audit, minimal task schema written.')
