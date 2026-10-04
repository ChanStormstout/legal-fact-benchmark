#!/usr/bin/env python3
"""Assemble the bounded study-02 report; never changes frozen inputs or answers."""
import csv, datetime, hashlib, io, json, subprocess
from pathlib import Path
R=Path('outputs/legal-rule-support-study-02')
def rd(p): return json.loads((R/p).read_text())
def write(p,d):
 (R/p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def sha(b):return hashlib.sha256(b).hexdigest()
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
ledger=rd('call-ledger.json'); calls=ledger['new_calls']
assert len(calls)==28 and all(x['status'] in ('OK','JSON_READABLE') for x in calls)
for x in ('AUD01','AUD02'): assert (R/'runs'/x/'copied-answer.json').exists()
order=rd('run-order.json'); evaluations=rd('evaluation-order.json')
notes={
'110204406':('UNDETERMINED','SAME_TREATMENT','首次把公司转归证言写成租赁权益已法定转归，证据地位过实；重复避免该强说法并增加时间缺口。两次均未充分处理答辩与证言之间的矛盾。','实际占有控制、同意及公司转归的Delhi法后果未定；首次结论并非因这些缺口之外的所有事实都未知。'),
'172908545':('UNDETERMINED','SAME_TREATMENT','保留共同合伙人／公司争点，但遗漏遗嘱继承这一独立腾退理由及双方相关论点（L122–123、128–131）。','供给的公司材料不能直接解决遗嘱继承与租赁权转移；完整下级理由与相关法律测试不齐。'),
'58386394':('UNDETERMINED','SAME_TREATMENT','将不同被请求人的立场合并成许可使用：R1主张licensees，R2–4主张认可的次承租人，R6主张licensee（L108、112–116）。下级法院的同意认定及争议地位则保留。','租约／同意范围、占有性质及具体设立时间仍有缺口；第16条存在于库但未送达，不能将这一项全归因于模型理解。'),
'890045':('UNDETERMINED','SAME_TREATMENT','1959让与及合同含assigns保留，未确认决定性事实反写；合同全文和历史版本限制说明仍有限。','assigns措辞是否构成此次书面同意缺少直接解释依据；不要求猜回排除的终局理由。'),
'1908519':('SUPPORT_GROUND','CLOSE','首次A与G/L均遗漏租金管制官的相反判断及父子／收养反论。A有一个无效L12引用，但相关主张由L148支持。G/L多讨论并排除不相干的法定转归；未显示重要净改善。','已有上诉审占有事实可作为支持依据；它们不等于完整法律测试或目标终局认可。支持标签本身不判错，确定程度及未处理反论另列。'),
'869439':('SUPPORT_GROUND','SAME_TREATMENT','保留下级不利认定和Clause14共享许可，但直接依靠下级结论化解许可范围，遗漏写面形式仅为directory的反论及交易时间。集中审阅认为结论过强；主审保留程度争议，不把引用下级认定本身判为错误。','实际共享／交出占有及Clause14覆盖的关系、日期和下级理由未提供；这些缺口不能由不相干的合并先例补齐。')}
rows=[]
for e in evaluations:
 cid=e['case_id'];outcome,category,issue,gap=notes[cid]
 runs=[x for x in order if x['case_id']==cid]
 rows.append(dict(case_id=cid,technical_status='OK',outcome=outcome,A_vs_G=category,A_vs_L=category,G_vs_L='SAME_TREATMENT',decisive_source_review=issue,remaining_gap=gap,actual_final_calls=len(runs),final_input_characters=sum(next(c['input_characters'] for c in calls if c['id']==x['id']) for x in runs),answer_ids=[x['id'] for x in runs],review='runs/'+e['id']+'/copied-answer.json',reference_role='MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD'))
write('comparison-table.json',rows)
s=io.StringIO();w=csv.DictWriter(s,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows);(R/'comparison-table.csv').write_text(s.getvalue())
repeat={
 '110204406':{'same_inputs_all_arms':True,'first':'ANS01','repeat':'ANS08','outcome_stable':True,'change':'Repeated answer preserves pleadings/evidence status more explicitly and avoids strong tenancy-vesting claim; adds timing uncertainty. Same treatment, not L advantage.'},
 '1908519':{'first_A':'ANS06','repeat_A':'ANS09','first_GL':'ANS05','repeat_GL':'ANS10','outcome_stable':True,'change':'A repeat addresses family/adoption counterargument and removes invalid citation, but drops explicit historical-version caveat. G/L repeat does not cure the same main omissions. First CLOSE; repeat favors A on one important issue but not an established stable direction.'}}
write('repeat-stability.json',repeat)
root_qualifications=[
 {'case_id':'869439','review':'EVAL06','position':'QUALIFIED_NOT_SILENTLY_ACCEPTED','reason':'Prior-court findings are allowed evidence and may support a conditional conclusion. Their use alone is not factual error, nor must every admitted finding be independently re-proved. The defensible criticism is unresolved scope of written sharing permission, omitted concrete opposition and timing, and over-definitive synthesis. Do not count three overlapping reviewer allegations as three independent failures.','source_ids':['IK-869439:L163','IK-869439:L166','IK-869439:L168','IK-869439:L169','IK-869439:L171','IK-869439:L176','IK-869439:L177@0:232'],'effect_on_comparison':'None; shared A/G/L final input and answer.'},
 {'case_id':'1908519','review':'EVAL05','position':'SUPPORT_LABEL_NOT_AUTOMATIC_ERROR','reason':'L161 expressly supplies accepted exclusive-possession and no-control findings. SUPPORT_GROUND can express evidential support without claiming withheld final outcome. Missing family counterargument and prior opposing finding remain substantive coverage weaknesses.','effect_on_comparison':'First treatments CLOSE; repeat coverage movement reported.'},
 {'case_id':'110204406','review':'EVAL01','position':'MAPPING_AUTHORITATIVE','reason':'N1 is ANS08 repeat and N2 is ANS01 first. One review sentence has ambiguous repeat wording; immutable mapping and actual answers govern.'}]
write('final-source-review.json',dict(role='MODEL_ASSISTED_NOT_HUMAN_GOLD',evaluations=evaluations,independent_audits=rd('independent-review-order.json'),root_source_checks=rd('audit/concentrated-source-notes.json'),root_qualifications=root_qualifications,reference_corrections_applied=False,reference_disputes_retained=True,comparison_counts={'A_vs_G':{'same_treatment':5,'close':1,'net_improvement':0,'worse':0,'undetermined':0},'A_vs_L':{'same_treatment':5,'close':1,'net_improvement':0,'worse':0,'undetermined':0},'G_vs_L':{'same_treatment':6}},note='SAME_TREATMENT is an identical-input shared run, not independently measured equality. Counts describe observed treatment effects, not answer correctness. Independent reviews may disagree; preserve their original reports and root qualifications.'))
links=['# 本轮完整回答入口','', '10次实际最终回答对应24个方法位置；相同输入仅在同案同重复编号内共享。各runs目录保留copied-response.txt、copied-answer.json、parse-record.json；任务全文在tasks/。','']
for x in order:
 c=next(z for z in calls if z['id']==x['id']); p='runs/'+x['id']+'/copied-answer.json'
 links.append('- %s：案件%s，%s，重复编号%s；[完整答案](%s)、[原始回复](runs/%s/copied-response.txt)、[实际任务](tasks/%s.txt)、[网页对话](%s)。'%(x['id'],x['case_id'],'/'.join(x['arms']),x['replicate'],p,x['id'],x['id'],c['url']))
(R/'final-answer-slots.md').write_text('\n'.join(links)+'\n')
# Costs are character counts and observed windows, never fabricated token/generation measurements.
by={}
for c in calls:
 group='reference' if c['id'].startswith('REF') else 'description' if c['id'].startswith(('G','L')) else 'final' if c['id'].startswith('ANS') else 'case_review' if c['id'].startswith('EVAL') else 'independent_review'
 d=by.setdefault(group,dict(calls=0,input_characters=0,output_characters=0,observed_elapsed_seconds=[]));d['calls']+=1;d['input_characters']+=c['input_characters'];d['output_characters']+=c['output_characters'] or 0
 if c['completed_observed_utc']: d['observed_elapsed_seconds'].append((datetime.datetime.fromisoformat(c['completed_observed_utc'].replace('Z','+00:00'))-datetime.datetime.fromisoformat(c['started_utc'].replace('Z','+00:00'))).total_seconds())
for d in by.values():
 v=d.pop('observed_elapsed_seconds');d['submission_to_collection_min_seconds']=min(v);d['submission_to_collection_max_seconds']=max(v)
write('cost-summary.json',dict(actual_web_calls=28,maximum=58,groups=by,transport_retries=0,local_model_calls=0,paid_API_calls=0,model_visible='Latest',exact_model=None,mode='High',tokens=None,precise_generation_seconds=None,measurement_warning='Submission-to-collection windows include other tasks and review delay; parallel windows overlap and are not summed as model compute.',old_costs=ledger['old_costs']))
# Actual submitted text is checked after capture, not just the nominal prompt template.
submissions=[]
for c in calls:
 s=rd('runs/'+c['id']+'/submission.json'); task=(R/'tasks'/f"{c['id']}.txt").read_text()
 assert s['submitted_text']==task and s['wrapper']==(R/'execution-wrapper.txt').read_text() and s['attachment_exact']
 if c['id'].startswith('ANS'): assert sha((task+'\n'+s['wrapper']).encode())==next(x['complete_submission_sha256'] for x in order if x['id']==c['id'])
 submissions.append(dict(id=c['id'],task_bytes_equal=True,submission_fields=list(s),task_sha256=sha(task.encode()),wrapper_sha256=sha(s['wrapper'].encode()),complete_submission_sha256=sha((task+'\n'+s['wrapper']).encode()),attachment_preview_equal=s['attachment_exact'],visible_model=s.get('visible_model'),mode=s.get('mode')))
write('audit/final-submission-check.json',dict(rows=submissions,all_equal=True,scope='UI preview equality recorded at submission; this proves supplied text, not internal model attention or semantic correctness.'))
# Verify preserved history and all published frozen inputs; never modify them.
a=rd('start-audit.json');bad=[]
for p,h in a['historical_file_hashes'].items():
 if not Path(p).exists() or sha(Path(p).read_bytes())!=h:bad.append(p)
assert not bad,bad
frozen=[]
for name in ['source-freeze.json','reference-freeze.json','representation-freeze.json','run-freeze.json']:
 for p,h in rd(name)['files_sha256'].items():
  assert sha((R/p).read_bytes())==h,(name,p)
  frozen.append((name,p))
for rec in rd('evaluation-task-freeze.json')['tasks']+rd('independent-review-order.json'):
 assert sha((R/rec['path']).read_bytes())==rec['sha256']
assert sha(Path('legal_bench/local_chunk_v11.py').read_bytes())==a['excluded_untracked_sha256']
write('audit/final-integrity.json',dict(checked_utc=now,historical_files_unchanged=len(a['historical_file_hashes']),frozen_entries_checked=len(frozen),frozen_all_unchanged=True,unrelated_untracked_unchanged=True,head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),no_commit_no_push=True))
write('decision.json',dict(decision='PRIORITIZE_ORIGINAL_SOURCE_RETRIEVAL_KEEP_G_L_OPTIONAL_BENEFIT_UNESTABLISHED',reason='No G/L treatment separation; five shared all-arm packs and one close distinct-pack case. Preserve identity gates and targeted candidate locator. No rule-induction or legal accuracy claim.',completed=True,next_round_started=False,commit=False,push=False))
print('Reports assembled; all 28 calls and immutable history verified.')
