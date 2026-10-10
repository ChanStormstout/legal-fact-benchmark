"""One explicit, versioned research correction; raw model output stays immutable.

Repairs a located quote and distinguishes a source-supported proposed conclusion
from an executable OPEN_TEXT result. It does not change facts or legal semantics.
"""
import copy,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.contracts import read_json,write_once,content_hash,byte_hash
from legal_bench.proof_carrying.realcase_checker_v2_1 import inspect_sources
from legal_bench.proof_carrying.realcase_engine import propose,explanation
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/proof-carrying-realcase-v2';CASE=OUT/'cases/789051'

def main():
    s1=read_json(CASE/'snapshots/S1.json');s2=copy.deepcopy(s1);s2['snapshot_id']='789051-S2'
    r=copy.deepcopy(s1['rules']['R4@1']);oldquote=r['source_quote']
    r['version']=2;r['source_quote']='the learned Single Judge has upheld the maintainability of a suit merely seeking injunction, without declaration of title'
    assert inspect_sources(r,s2['sources']) is None
    s2['rules']['R4@2']=r
    s2['reviews']['rules']['R4@2']={**s1['reviews']['rules']['R4@1'],'subject_hash':content_hash(r),
        'decision':'ACCEPT_RESEARCH','local_source_issue':None,'actor':'CODEX_SOURCE_COMPARISON_RESEARCH_REVISION',
        'reason':'Quote shortened to an exact substring in L111, avoiding renderer space before possessive apostrophe. Rule meaning unchanged.',
        'qualified_legal_approval':False}
    s2['scope_reviews']['R4@2']={**s1['scope_reviews']['R4@1'],'subject_hash':content_hash(r)}
    original=read_json(OUT/'runs/789051/derivation/parsed.json');patched=copy.deepcopy(original)
    for row in patched['steps']:
        if row['rule_ref']=='R4@1':row['rule_ref']='R4@2'
        if row['id']!='S1':
            row['proposed_state']='UNKNOWN'
            row['explanation']='RESEARCH PATCH: the original source-based reasoning is retained in the raw proposal. This executable trace is pending because S2 invokes OPEN_TEXT; downstream effects inherit that computational gap. This does not deny the reported court finding.'
    for q in patched['requests']:
        q['proposed_state']='UNKNOWN'
        q['text']='Conditionally proposed, but not established by this executable registry: '+q['text']
    patched['requests'].insert(0,{'id':'Q0','step_id':'S1','predicate':s1['rules']['R1@1']['conclusion_predicate'],
        'text':'The reported proof of possession remains a distinct basis despite non-proof of title. This does not decide ownership or all injunction requirements.','proposed_state':'TRUE'})
    patch={'id':'RAME_S2_RESEARCH_CORRECTION','parent_snapshot':s1['snapshot_id'],'parent_hash':content_hash(s1),
      'kind':'ACTUAL_REPRESENTATION_AND_EXECUTABILITY_CORRECTION_NOT_LEGAL_ERROR_COUNT',
      'source_refs':['IK-789051:L111','IK-789051:L106','IK-789051:L107'],
      'changes':[{'rule':'R4@1 -> R4@2','old_quote':oldquote,'new_quote':r['source_quote'],'semantic_rule_change':False},
        {'steps':'S2-S6','old_proposed_state':'TRUE','new_computed_trace_claim':'UNKNOWN','reason':'OPEN_TEXT cannot be independently recomputed; do not present a source-supported legal view as executable verification.'},
        {'request':'Q0 added','reason':'Expose the independent valid prefix already present as S1; no new premise or legal rule.'}],
      'unchanged':['original facts including F3 court finding','all original raw output','original rule versions','S1 snapshot and checks','source bytes','independent reference'],
      'approval':'PENDING_QUALIFIED_LEGAL_REVIEW','not_new_model_answer':True,'model_calls':0}
    write_once(CASE/'patch-S2.json',patch);s2['revision_record_hash']=byte_hash(CASE/'patch-S2.json')
    write_once(CASE/'snapshots/S2.json',s2)
    manifests={'snapshots':{s1['snapshot_id']:{'path':'snapshots/S1.json','sha256':byte_hash(CASE/'snapshots/S1.json')},s2['snapshot_id']:{'path':'snapshots/S2.json','sha256':byte_hash(CASE/'snapshots/S2.json')}}}
    write_once(CASE/'manifest-S2.json',manifests)
    dst=CASE/'runs/S2';write_once(dst/'corrected-proposal.json',patched);write_once(dst/'certificate.json',propose(s2,patched))
    checker=ROOT/'scripts/check_realcase_certificate_v2_1.py'
    def invoke(cert,name,current=None):
        cmd=[sys.executable,str(checker),str(cert),'--manifest',str(CASE/'manifest-S2.json')]
        if current:cmd+=['--current',current]
        proc=subprocess.run(cmd,text=True,capture_output=True,cwd=ROOT)
        (dst/(name+'-stdout.txt')).write_text(proc.stdout);(dst/(name+'-stderr.txt')).write_text(proc.stderr)
        result=json.loads(proc.stdout);write_once(dst/(name+'.json'),result)
        write_once(dst/(name+'-invocation.json'),{'argv':cmd,'exit_code':proc.returncode,'checker_sha256':byte_hash(checker)})
        return result
    new=invoke(dst/'certificate.json','check',s2['snapshot_id'])
    old=invoke(CASE/'runs/S1/certificate.json','historical-reopen',s1['snapshot_id'])
    stale=invoke(CASE/'runs/S1/certificate.json','old-as-current',s2['snapshot_id'])
    (dst/'explanation.md').write_text(explanation(new,s2,propose(s2,patched)))
    same=old==read_json(CASE/'runs/S1/check.json')
    write_once(CASE/'revision-validation.json',{'historical_result_identical':same,'old_rejected_as_current':stale.get('reason')=='STALE_CURRENT_SNAPSHOT',
      'premises_unchanged':s2['premises']==s1['premises'],'raw_proposal_unchanged':content_hash(original)==content_hash(read_json(OUT/'runs/789051/derivation/parsed.json')),
      'new_request_statuses':[{k:q[k] for k in ('id','draft_status','answer','formal_status')} for q in new['requests']],
      'legal_accuracy_improvement_claimed':False,'gaps_retained':['OPEN_TEXT','qualified approval','underlying original evidence unavailable']})
    print(json.dumps({'historical_identical':same,'new_requests':[(q['id'],q['draft_status'],q['answer']) for q in new['requests']]}))
if __name__=='__main__':main()
