#!/usr/bin/env python3
"""One bounded availability audit, source graph demo, baseline replay; never train by default."""
import sys,json,hashlib,time,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1 import rgcn_feasibility_v1 as g
from legal_bench.rules_verdict_v1 import legal_rule_support_study as m
R=Path('outputs/rgcn-retrieval-feasibility-05');S=Path('outputs/legal-rule-support-study-02')
def load(p):return json.loads(Path(p).read_text())
def save(p,d):
 p=R/p;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise FileExistsError(p)
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if (R/'run-results.json').exists():raise SystemExit('Existing result: no repeated run')
samples=load(S/'samples.json');units=load(S/'library/original-units.json');availability=load(R/'availability.json')
config={'experiment':'FEASIBILITY_NOT_EFFICACY','seed':20261004,'real_training_enabled':False,'train_ids':[],'check_ids':[],'development_ids':[s['case_id'] for s in samples],'pattern_features':False,'graph_role':'GENERAL_RELATIONS_INTERFACE_ONLY','C':{'width':16,'layers':2,'relation_weights':'independent per directed relation','features':'fixed signed token hash, no identity embeddings','loss':'softplus(score(other)-score(preferred)); explicit reviewed within-case preferences only','optimizer':'Adam','learning_rate':0.001,'steps_upper_bound_if_authorized':100,'resource_cap_seconds':300,'node_cap_if_training':512,'config_scope':'interface candidate; not a trained model'},'B':'count distinct candidate-aligned law conditions; BM25 tie break; exactly same graph as C','A':'saved original BM25 ranking','max_legal_characters':20000,'postprocessing':'unchanged select dependency closure and original ordering','unknown_labels':'MASKED_NOT_NEGATIVE','label_graph_edges':'PROHIBITED','scope':'same six exposed cases; no independent generalization claim','formal_comparison':'GATED_NO_GRAPH_ALIGNMENT_OR_PREFERENCE_SUPERVISION','stop':'build inventory/interface; baseline replay only if gate closed; no actual answer calls'}
paths=[Path('legal_bench/rules_verdict_v1/rgcn_feasibility_v1.py'),Path('legal_bench/rules_verdict_v1/rgcn_mlx_v1.py'),Path(__file__),Path('tests/test_rgcn_feasibility_v1.py'),S/'samples.json',S/'library/original-units.json',R/'availability.json']+[S/s['source'] for s in samples]+[S/'retrieval'/s['case_id']/'result.json' for s in samples]
config['file_hashes']={str(p):sha(p) for p in paths};save('frozen-config.json',config)
rows=[];graphs={};t0=time.perf_counter()
for s in samples:
 cid=s['case_id'];src=load(S/s['source']);allowed={x['id']:x['text'] for x in src['segments']}
 graph=g.build_graph(cid,{}, {},units,allowed);graph['input_scope']='ANSWER_ISOLATED';graph['role']='STRUCTURAL_SKELETON_NOT_SEMANTIC_GRAPH';graphs[cid]=graph
 save('graphs/'+cid+'.json',graph)
 old=load(S/'retrieval'/cid/'result.json');base=old['selected']['A'];new=m.select(old['rankings']['A'],units,old['configuration'],base['mandatory_ids'])
 assert new==base
 save('baseline-replay/'+cid+'.json',{'ranking':old['rankings']['A'],'selection':new,'same_as_saved':True})
 rows.append({'case_id':cid,'A_status':'EXACT_DETERMINISTIC_REPLAY','B_status':'NOT_RUN_NO_CONDITION_ALIGNMENTS','C_status':'NOT_RUN_NO_ALIGNED_SUPERVISION','A_selected_ids':new['selected_ids'],'A_legal_characters':new['legal_characters'],'B_ranking':None,'C_ranking':None,'ranking_change':None,'material_change':None,'legal_answer_calls':0})
# Disjoint graph and relevance labels are not silently joined by case ID or reference prose.
gate=g.training_gate([],[],graphs,[],{})
gate['additional_reasons']=['SIX_CASES_ONLY_PARTIAL_POSITIVE_BUNDLES','ZERO_OVERLAP_EARLY_RELATION_CASES_WITH_SIX_SOURCE_LABEL_CASES','NO_FROZEN_FACT_TO_LEGAL_CONDITION_ALIGNMENT','NO_SEPARATE_UNEXPOSED_CHECK_SET']
save('launch-gate.json',gate)
# Explicit old-case representation demo, never a real retrieval input/score.
cid='103193047';base=Path('outputs/development-20-single-pass-v1');src=load(base/'sources'/f'{cid}.json');view=load(base/'views'/f'{cid}.json');rel=load(Path('outputs/development-20-typed-relations-v2/relations')/f'{cid}.json')
demo=g.build_graph(cid,view,rel,[],{s['id']:s['text'] for s in src['segments']});demo['input_scope']='OLD_FULL_JUDGMENT_DEMONSTRATION_ONLY';demo['retrieval_eligible']=False;demo['exclusion_reasons']=['Kerala s11 not Delhi14(1)(b)','No same-corpus relevance supervision','Original source not target-outcome isolated'];save('graph-example-103193047.json',demo)
save('run-results.json',{'rows':rows,'training_runs':0,'ranker_inferences_on_real_cases':0,'baseline_replays':6,'elapsed_local_seconds':time.perf_counter()-t0,'demo_counts':{'nodes':len(demo['nodes']),'edges':len(demo['edges']),'pending':len(demo['pending']),'excluded':len(demo['excluded'])},'decision':'STOP_SUPERVISED_RGCN_COMPARISON_AT_DATA_GATE','quality_scores':None})
print(json.dumps({'gate':gate,'rows':len(rows),'demo_nodes':len(demo['nodes']),'demo_edges':len(demo['edges'])},ensure_ascii=False))
