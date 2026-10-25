"""Import one frozen web result and record one source-grounded development review."""
import csv
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.contracts import validate

ROOT=Path('outputs/rules-verdict-v15-rule-supplement')
BASE=Path('outputs/rules-verdict-v14-web-direct')
read=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(path,value):
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')

freeze=read(ROOT/'freeze.json');audit=read(ROOT/'start-audit.json')
assert all(sha(p)==h for p,h in freeze['files'].items())
assert sha('scripts/prepare_v15_rule_supplement.py')==freeze['actual_preparation_script_sha256']
assert all(sha(p)==h for p,h in audit['historical_files'].items())
assert all(sha(p)==h for p,h in audit['preexisting_code'].items())
run=ROOT/'runs/1134266';task=ROOT/'tasks/1134266'
assert (run/'submitted-attachment.txt').read_bytes()==(run/'attachment-preview.txt').read_bytes()==(task/'case_1134266_task.txt').read_bytes()
raw=(run/'raw-response.txt').read_text();answer,end=json.JSONDecoder().raw_decode(raw.lstrip())
suffix=raw.lstrip()[end:];assert suffix.strip()=='END'
validate(answer,read(task/'schema.json'))
(run/'answer.json').write_text(raw.lstrip()[:end])
save(run/'format-check.json',{'raw_whole_reply_json':False,'format_status':'VALID_AFTER_EXPLICIT_END_SUFFIX_REMOVAL',
    'removed_suffix':suffix,'all_json_values_preserved':True,'attachment_citation_display_retained':True,
    'source_address_valid':True,'semantic_correctness_not_certified':True})
completion=read(run/'completion.json');start=read(run/'start.json');sent=read(run/'submission-time.json')['sent_at']
parse_time=lambda t:datetime.fromisoformat(t.replace('Z','+00:00'))
observed=(parse_time(completion['observed_complete_at'])-parse_time(sent)).total_seconds()
save(ROOT/'results.json',{'case':'1134266','method':'WEB_HIGH_DIRECT_PLUS_FROZEN_RULES','run_status':'OK','answer':answer,
    'baseline':str(BASE/'runs/1134266/answer.json'),'web_answers':1,'retries':0,'local_model_calls':0,'paid_api_calls':0,
    'displayed_model':'ChatGPT','exact_model':None,'displayed_mode':'High','conversation_url':completion['conversation_url'],
    'sent_at':sent,'observed_complete_at':completion['observed_complete_at'],
    'observed_submit_to_complete_upper_bound_seconds':observed,'displayed_thinking_seconds':158,
    'precise_generation_seconds':None,'input_tokens':None,'output_tokens':None,'peak_memory':None,
    'external_search_observed':False,'complete_attachment_verified':True,'internal_complete_read_not_observable':True,
    'same_original_case_and_law_and_answer_contract':True,'additional_source_ids_only':True})
source=read(task/'base-source.json');law=read(task/'base-law-package.json');added=read(ROOT/'rule-package.json')
cm={s['id']:s['text'] for s in source['segments']};lm={s['id']:s['text'] for s in law['law_segments']+added['law_segments']}
save(ROOT/'restored-final-sources.json',[{'ground':i+1,'point':g['point'],
    'case_sources':[{'id':s,'text':cm[s]} for s in g['case_refs']],
    'law_sources':[{'id':s,'text':lm[s]} for s in g['law_refs']]} for i,g in enumerate(answer['grounds'])])

review={
 'type':'ONE_CONCENTRATED_FINAL_SOURCE_REVIEW','reference_status':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD',
 'no_new_reference_labels_or_web_review':True,'baseline_review_preserved':str(BASE/'final-source-review.json'),
 'baseline_answer_not_gold':True,'baseline_review_revision_required':False,
 'source_checked_outside_model_active_citations':['p0002.s002','p0002.s005','p0002.s007','p0003.s001','p0003.s003','p0003.s007','p0004.s001'],
 'improvements':[
  {'item':'Separate vesting from rent-law consequences','baseline':'g3 repeated corporate-shell positions and missing amalgamation authority','new':'g2 preserves rights vesting; g3 applies supplied transfer authorities separately',
   'evidence':['p0002.s003','LAW:V15:GENERAL_RADIO:P6','LAW:V15:TELESOUND:PAR12'],'assessment':'Concrete supported improvement in explanation, not certification of final adjudication'},
  {'item':'Scope of Telesound','baseline':'No substantive treatment of the cited company-scheme view','new':'g3 expressly notes that Telesound reserves the Delhi eviction issue',
   'evidence':['LAW:V15:TELESOUND:PAR16'],'assessment':'Correctly retained reserved jurisdiction; does not promote prima facie view into final rent-law immunity'},
  {'item':'Scope of Hindustan Petroleum','baseline':'HP/compulsion argument not substantively handled','new':'g3 distinguishes the special statutory acquisition and vesting regime',
   'evidence':['p0003.s006','LAW:V15:HINDUSTAN_PETROLEUM:P15','LAW:V15:HINDUSTAN_PETROLEUM:P16'],'assessment':'Supported distinction; not a complete analysis of every route to statutory compulsion'},
  {'item':'No need for withheld target reasoning','baseline':'g3 pointed to absence of target-court reasoning when keeping characterization unresolved','new':'g3 offers a legal characterization on supplied authorities without requesting the withheld outcome',
   'evidence':['LAW:V15:GENERAL_RADIO:P6','LAW:V15:GENERAL_RADIO:P10'],'assessment':'Useful source-based application; cross-statute migration and target compulsion still deserve qualified explanation'}],
 'preserved_correct_parts':[
  {'item':'Registered 1966 lease and original American tenant','sources':['p0001.s003','p0002.s001'],'ground':1},
  {'item':'Sanctioned scheme transfers tenancy/occupancy rights to Indian company','sources':['p0002.s003'],'ground':2},
  {'item':'No-consent allegation not upgraded through added law or appellate disposition','sources':['p0002.s001','p0002.s004'],'ground':4},
  {'item':'Tribunal/High Court hierarchy retained in g4, not upgraded to target final adoption','sources':['p0002.s004'],'ground':4}],
 'remaining_omissions_or_disputes':[
  {'item':'Alternative ways to reduce equity and no direction specifically requiring amalgamation','sources':['p0003.s007','p0003.s008'],
   'finding':'Still not explicitly assessed. New answer contrasts equity reduction and alleged compulsion but does not articulate or evaluate the landlord alternative-modes counterargument.'},
  {'item':'AP principal holding migrated to Delhi transfer characterization','sources':['LAW:V15:GENERAL_RADIO:P6','LAW:V15:GENERAL_RADIO:P10'],
   'finding':'Delhi breadth is linked to Supreme Court description of Parasaram, so application has a basis; main AP statutory context is not stated in answer. g3 SUPPORTED is a qualified legal inference, not a source-explicit target adjudication.'},
  {'item':'RBI direction attribution','sources':['p0002.s002','p0002.s005','p0002.s006','p0003.s007'],
   'finding':'g3 calls equity reduction target narration, although p0002.s006 continues counsel submission and p0002.s002 narrates a defense. Both sides refer to equity reduction, but no independent directive or adopted finding is supplied. This should be described as a common premise of submissions, not a court-established directive.'},
  {'item':'Approval date versus effective vesting date','sources':['p0002.s003'],
   'finding':'g2 names the amalgamation by 31 December 1981; original text dates sanction, not a separately established vesting date. Same precision issue was present in baseline. No withheld effective date is imported.'},
  {'item':'Overly narrow formulation of evidence sufficiency','sources':['p0002.s001','p0002.s004'],
   'finding':'reason demands an adopted finding for absence of consent. The task does not universally require a preexisting court finding: evidence and lawful inference could suffice. Here allowed material still does not separately settle consent; UNDETERMINED is defensible, its stated criterion is too narrow.'},
  {'item':'Rent Controller dismissal and corporate-shell argument','sources':['p0002.s004','p0003.s001','p0003.s003'],
   'finding':'ARC initial dismissal no longer stated explicitly; corporate-shell defense handled only indirectly by Telesound and transfer analysis. Do not claim every decisive opposing contention has been fully addressed.'}],
 'confirmed_new_severe_source_reversals':[],
 'no_cross_case_fact_import_confirmed':True,
 'internal_consistency':'g3 supported legal transfer, g4 unresolved absence of consent and UNDETERMINED conclusion are compatible; no supported/refuted polarity contradiction identified.',
 'fact_gaps':['Actual landlord written consent or its absence is not independently settled in allowed record.','Actual RBI directive, alternative compliance choices and mandatory merger status are not independently verified by added authorities.'],
 'law_gaps':['No full historical FERA s29/RBI instrument added.','No complete proof-burden framework added; do not manufacture absent-consent facts.'],
 'benefit_boundary':'Rules improved legal distinctions and applicability explanation, but not a fully complete or independently correct verdict. Single targeted source addition also changes length/attention; summaries and excerpts effects not isolated.',
 'decision':'CONTINUE_SOURCE_GROUNDED_RULE_EXTRACTION_AND_APPLICATION',
 'decision_zh':'补充规则带来具体且可核验的法律分析增益，保留规则提取与应用方向；双方论点处理仍不完整，本案不继续返工。',
 'no_automatic_next_round':True
}
save(ROOT/'final-source-review.json',review)
save(ROOT/'decision.json',{k:review[k] for k in ['decision','decision_zh','benefit_boundary','no_automatic_next_round']})
baseline=read(BASE/'runs/1134266/answer.json');baseline_run=read(BASE/'results.json')['runs'][1]
rows=[
 {'condition':'V14 web High D','case':'1134266','run_status':'OK','outcome':baseline['outcome'],'complete_answers':1,
  'legal_transfer':'UNRESOLVED; no amalgamation-specific law provided','opposition':'Corporate-shell argument retained, HP/FERA/alternative-modes omitted',
  'consent':'UNRESOLVED; allegation not upgraded','legal_scope':'No relevant merger rules to apply','source_errors':'No comparable serious source reversals confirmed; approval/effective-date precision issue',
  'displayed_thinking_seconds':49,'generation_seconds':None,'observed_completion_upper_bound_seconds':baseline_run['observed_submit_to_completion_upper_bound_seconds'],
  'input_tokens':None,'output_tokens':None,'new_calls_this_round':0},
 {'condition':'V15 web High D + three authorities','case':'1134266','run_status':'OK','outcome':answer['outcome'],'complete_answers':1,
  'legal_transfer':'SUPPORTED as qualified legal inference; statutory migration not fully explained','opposition':'HP special regime and Telesound reservation correctly distinguished; landlord alternative-modes argument still omitted',
  'consent':'UNRESOLVED; added law does not create absence of consent','legal_scope':'Concrete new distinctions; AP/Delhi boundary needs more explicit treatment',
  'source_errors':'No new severe reversal confirmed; RBI common submission premise called narration; existing date precision retained',
  'displayed_thinking_seconds':158,'generation_seconds':None,'observed_completion_upper_bound_seconds':observed,
  'input_tokens':None,'output_tokens':None,'new_calls_this_round':1}]
save(ROOT/'comparison-table.json',rows)
with (ROOT/'comparison-table.csv').open('x',encoding='utf-8') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
(ROOT/'final-answer-slots.md').write_text('# V15 Complete Web Answer\n\nConversation: '+completion['conversation_url']+'\n\nOnly the standalone END after closed JSON is removed. All JSON fields and displayed attachment-reference text are preserved; this is not human gold.\n\n```json\n'+(run/'answer.json').read_text()+'\n```\n\nHistorical comparator: ../rules-verdict-v14-web-direct/runs/1134266/answer.json\n')
save(ROOT/'preservation-check.json',{'historical_files_unchanged':len(audit['historical_files']),'preexisting_code_unchanged':len(audit['preexisting_code']),
    'frozen_files_verified':len(freeze['files']),'base_case_law_examples_requirements_preserved':True,
    'semantic_output_repairs':0,'format_suffix_only':True})
save(ROOT/'stop.json',{'reason':'ONE_NEW_WEB_ANSWER_AND_ONE_CONCENTRATED_SOURCE_REVIEW_COMPLETE','web_answers':1,
    'local_calls':0,'paid_api_calls':0,'retries':0,'new_extractions':0,'no_commit_push_next_round':True})
(ROOT/'report-zh.txt').write_text(f'''V15: direct legal answer for1134266 with source-grounded rule supplementation

Decision: retain source-grounded rule extraction/application as a direction. Three authorities yield concrete gains: distinguish merger vesting from tenancy consequences, identify Telesound's reserved eviction issue, and distinguish HP's special-law protection. No comparably serious new source reversal was confirmed. Major arguments remain inadequately handled, so a fully correct legal answer is not established. Do not further edit prompts or follow up on this case.

Fixed scope and materials
Only1134266; the unchanged V14 browser High direct answer is the historical comparator, not regenerated. Facts, old legal package, question, two teaching examples, and final contract remain complete. Only three frozen earlier-precedent rules and seven original passages are inserted; schema only extends law_refs IDs. Code, materials, selection reasons, evaluation, and stopping were frozen before generation. No old answers, references, error lists, target-passage hints, or target final reasons enter input. A fresh ordinary High chat, not Pro, has no local token constraints. Exact model is unknown from ChatGPT/High UI; internal knowledge, reading, and sampling are unobservable.

The package includes General Radio (Supreme Court1986, primarily AP tenancy law, reporting Delhi Parasaram), Hindustan Petroleum (Supreme Court1988, special Esso acquisition legislation/notification/s396 merger/Bombay s15A), and Telesound (Delhi High Court1980, reported1983, company-scheme approval, prima facie opinion, expressly reserved tenancy jurisdiction). Court approval is not landlord consent; there is no invented universal compulsory-transfer exemption or target-specific answer. General Radio/HP passages are verbatim PDF extraction; HP scan OCR is unchanged. Telesound direct access returned403, so previously read original judgment text was used: paragraph12 explicitly consists of noncontiguous complete sentences, paragraph16 is complete. The official Delhi statute PDF timed out; no guessed text was added. Four documents were checked and three used, stopping within the five-document cap. Retrieval failures and whitespace-anchor repairs preceded freeze/submission and were retained, not answer retries. No automatic-retrieval evaluation or cross-case induction occurred.

Specific changes
V14 g3 left merger characterization unknown for missing authorities and mainly restated the corporate-shell dispute. V15 g3 uses General Radio's transfer reasoning/Delhi precedent discussion, recognizes Telesound's reservation and HP's distinct special-law succession, and offers a supported characterization inference. This uses new legal content, not just more citation IDs. It no longer treats absent target final reasons as an inability to analyze. These are verifiable gains, but AP/Delhi statutory transfer is only briefly justified; SUPPORTED is not a target-court finding.

Both outcomes remain UNDETERMINED. V15 retains the registered1966 lease, American/Indian roles,31.12.1981 approval, and vesting. It does not import another precedent's no-consent facts or equate approval with landlord consent. g4 retains Tribunal/High Court levels but does not elaborate the Rent Controller dismissal. Supported transfer characterization with unresolved consent is not a polarity contradiction with the final label.

Remaining problems
The principal omission is p0003.s007: the landlord argues capital reduction had alternatives and RBI did not require this merger. The answer distinguishes equity requirements from claimed merger compulsion without directly comparing that rebuttal; it does not completely handle both sides. p0002.s006 continues tenant counsel and s002 records the defense. Both parties mention equity requirements, but no independent RBI order appears. g3's target-narration wording should remain a common premise in party statements, not a judicially established order. g2's31 December1981 merger date is actually an approval date, not a confirmed separate effective date; this precision problem also existed in the comparator. g3's SUPPORTED is a legal inference needing an AP/Delhi compatibility explanation. Requiring an adopted finding to resolve consent is overly restrictive: sufficient evidence can support analysis without an existing judgment. Here, however, consent is independently unresolved, so uncertainty remains justified.

Missing material includes sufficient facts establishing consent/absence, the actual RBI order, and compulsory-merger status. No complete historical FERA text or burden rules were added. Legal materials aid characterization but cannot create facts. Excluded target final reasons were unread and historical outcomes were not required.

Evaluation and costs
One consolidated source review included important uncited opposing material such as p0003.s007. There was no new gold, full-case relabeling, browser recheck, or reviewer agent. This is model-assisted review, not human gold. One new browser answer; no local generation/API/retry/extraction. The53,517-character attachment matched preview/submission verbatim. Raw reply is retained; only standalone END after complete JSON was removed, preserving attachment-reference text in reason. Format/ID validation does not establish semantics.

Visible thinking158s versus49s is a109s increase in visible thinking, not exact total inference. Send-to-first-confirmed-completion upper bound is {observed:.1f}s including observation intervals. Tokens, exact generation time, and peak memory are null. This is neither equal-input-cost nor isolated rule-semantic causality: rule summaries, originals, length, and attention change together; one exposed case does not eliminate generation variability.

Delivery and stopping
Complete answer/raw reply/actual task/schema, three rules/originals, URLs/hashes, item-level review, and comparison table are saved. All5,041 old outputs and existing method files are unchanged. V14 is not backfilled with new law. After docs/index/local review updates and publication-manifest inspection, stop without further search, reanswering, reextraction, algorithm changes, commit, or push. Results support considering extraction/application components, not automatic rule acquisition, complete adjudication reliability, or cross-case generalization.
Chat: {completion['conversation_url']}
''')
print(json.dumps({'web_answers':1,'status':'OK','outcome':answer['outcome'],'decision':review['decision'],'observed_upper_bound_seconds':observed},ensure_ascii=False))
