"""Four immutable screening tasks; no construction or target labels."""
import json
from pathlib import Path
from scripts.irac_native01_prepare import ROOT,save,sha

CRITERIA=['issue_clarity','merits_application','rule_test_identifiability','independent_rule_source_availability','input_stage_separability','factual_sufficiency','element_level_target_availability','procedural_only_risk','retrospective_reconstruction_risk','obvious_target_leakage_risk']
INSTRUCTION='''Independently screen these four frozen discovery candidates for an IRAC-native purposive development dataset. Read ALL supplied judgment text, including target reasoning, solely for suitability screening. Do not search externally. Do not construct facts, conditions, bindings, targets or a legal final answer. The fixed claim family is Delhi Rent Control Act 1958 s14(1)(b): subletting, assignment, parting with possession, written consent, retained legal control, burden/inference and necessary limitations. Mere citation, other eviction grounds, other Acts or procedural-only restoration do not qualify. Similar language under the 1952 Act does not establish applicability of the 1958 provision. Do not count target outcomes as all elements decided. Target reasoning may be used to assess whether there is meaningful element-level supervision, never for model input. Retrospective reconstruction is permitted and must be disclosed; that alone is not rejection. Independent rule sources can be a statute or actually named cited precedent; a target-specific application sentence is not an independent source. Require identifiable meaningful legal test with at least two conditions and actual reasoned application to records, not a speculative conversion of disposition into targets. A BORDERLINE case is acceptable only if it genuinely fits the fixed claim family, has substantive rule/application and a finite independently recoverable source/stage limitation; do not accept wrong-ground or pure procedural cases as borderline. No desired quota and no replacement.
Return complete downloadable JSON named SCREEN-N.json (replace N with task number). Full output contract: {cases:[{case_id,status,acceptable_borderline,criteria:{issue_clarity:{assessment,reason,source_refs},merits_application:{assessment,reason,source_refs},rule_test_identifiability:{assessment,reason,source_refs},independent_rule_source_availability:{assessment,reason,source_refs},input_stage_separability:{assessment,reason,source_refs},factual_sufficiency:{assessment,reason,source_refs},element_level_target_availability:{assessment,reason,source_refs},procedural_only_risk:{assessment,reason,source_refs},retrospective_reconstruction_risk:{assessment,reason,source_refs},obvious_target_leakage_risk:{assessment,reason,source_refs}},proposed_issue,identifiable_test,possible_independent_sources:[string],meaningful_conditions_count_estimate,application_clarity_score,independent_source_score,partition_clarity_score,element_coverage_score,reason,full_source_read}],limits:[string]}.
status SUITABLE/BORDERLINE/REJECT; criteria assessment SUPPORTED/QUALIFIED/BLOCKING_GAP; scores integers 0-3, based on source feasibility not model performance or winner. Source_refs always [{source_id,quote}], each a separate short exact contiguous quote from its one source; never concatenate. If full file cannot be read, say so, no guessing. Preserve a reject when evidence insufficient. Four cases exactly. No schema skeletons, ellipses or optional values joined as one string. This is model-generated screening, not human gold.
'''

def main():
    cohort=json.loads((ROOT/'candidate-cohort-16.json').read_text())['cases'];pack=[]
    for r in cohort:
        d=json.loads((ROOT/'sources/documents'/f"{r['case_id']}.json").read_text())
        assert d['status']=='COMPLETE_RENDERING'
        pack.append({'case_id':r['case_id'],'title':r['title'],'url':r['url'],'discovery_only':True,'full_source_status':d['status'],'judgment': [{'source_id':s['id'],'text':s['text']} for s in d['segments']]})
    files={}
    for j in range(4):
        p=ROOT/'tasks'/f'SCREEN-{j+1}.txt';p.parent.mkdir(exist_ok=True);assert not p.exists()
        p.write_text(INSTRUCTION.replace('SCREEN-N.json',f'SCREEN-{j+1}.json')+'\nMATERIAL\n'+json.dumps(pack[j*4:j*4+4],ensure_ascii=False,indent=2)+f'\nEND_OF_TASK SCREEN-{j+1}\n');files[str(p)]=sha(p)
    save('screening-freeze.json',{'files':files,'source_files':{str(p):sha(p) for p in (ROOT/'sources/documents').glob('*.json')},'candidate_hash':sha(ROOT/'candidate-cohort-16.json'),'criteria':CRITERIA,'construction_order':'application clarity, independent rules, partition clarity, element coverage descending, numeric case ID ascending','technical_retry_max':2,'semantic_retry':0})
    print([(p.name,p.stat().st_size) for p in (ROOT/'tasks').glob('*.txt')])

if __name__=='__main__':main()
