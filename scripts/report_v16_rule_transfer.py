"""Finish the three-source round without inventing missing application pairs."""
import csv, hashlib, json, pathlib, re, sys
from datetime import datetime, timezone
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.rule_transfer_v16 import inspect_reply, retrieve

ROOT=pathlib.Path('outputs/rules-verdict-v16-rule-transfer')
NAMES=['GENERAL_RADIO','HINDUSTAN_PETROLEUM','TELESOUND']
read=lambda p:json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')

def finish():
    freeze=read(ROOT/'freeze.json');audit=read(ROOT/'start-audit.json')
    assert all(sha(p)==h for p,h in freeze['files'].items())
    assert all(sha(p)==h for p,h in audit['historical_files'].items())
    assert all(sha(p)==h for p,h in audit['code_at_start'].items())
    bundles=[];sources={};rows=[]
    for name in NAMES:
        source=read(ROOT/'sources'/f'{name}.json');run=ROOT/'runs'/name
        task=(ROOT/'tasks'/name/'prompt.txt').read_bytes()
        if (run/'submitted-attachment.txt').exists():
            assert task==(run/'submitted-attachment.txt').read_bytes()==(run/'attachment-preview.txt').read_bytes()
        else:assert task==(run/'submitted-message.txt').read_bytes()
        value,check=inspect_reply((run/'raw-response.txt').read_text(encoding='utf-8'),source)
        assert value==read(run/'rule-cards.json') and check==read(run/'source-check.json')
        bundles.append(value);sources[name]=source
        sub=read(run/'submission.json');comp=read(run/'completion.json');ui=read(run/'ui-observation.json')
        t=lambda v:datetime.fromisoformat(v.replace('Z','+00:00'))
        labels=ui['displayed_reasoning_labels'];seconds=None
        if labels:
            m=re.search(r'(\d+)s',labels[0]);seconds=int(m.group(1)) if m else None
        rows.append({'authority':name,'run_status':'OK','cards':len(value['rule_cards']),
            'source_coverage':source['source_coverage'],'input_chars':sub['task_chars'],
            'raw_output_chars':comp['raw_chars'],'displayed_reasoning_seconds':seconds,
            'observed_completion_upper_bound_seconds':round((t(comp['observed_completed_at'])-t(sub['sent_at'])).total_seconds(),1),
            'exact_generation_seconds':None,'input_tokens':None,'output_tokens':None,'peak_memory':None,
            'new_web_calls':1,'retries':0,'conversation_url':comp['conversation_url']})
    save(ROOT/'rule-collection.json',{'role':'MODEL_EXTRACTED_CANDIDATES_NOT_LEGAL_CERTIFICATION','bundles':bundles})
    save(ROOT/'comparison-table.json',rows)
    with (ROOT/'comparison-table.csv').open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    review={
      'reference_status':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD','one_concentrated_review':True,
      'no_web_review_calls':True,'no_semantic_changes_to_model_cards':True,
      'reviewed_cards':[
       {'id':'GR-R1','finding':'Main quoted statutory conditions supported; transfer OR subletting preserved in text. Territorial/temporal OCR wording is deferred rather than fully represented. ASSIGN is a retrieval tag, not an executable replacement for the disjunction.','sources':['LAW:V16:GENERAL_RADIO:P6']},
       {'id':'GR-R2','finding':'Source supports tenant-sponsored amalgamation not involuntary merely because court-sanctioned, and no automatic immunity. AP/lease scope retained. Apparent contradictory immune sentence flagged instead of isolated into reversed holding. No universal rule for all mergers asserted.','sources':['LAW:V16:GENERAL_RADIO:P6','LAW:V16:GENERAL_RADIO:P7','LAW:V16:GENERAL_RADIO:P9','LAW:V16:GENERAL_RADIO:P10']},
       {'id':'GR-R3','finding':'Source supports exclusion of a person placed in occupation by tenant under this statutory definition. It is not a general bar on every successor tenancy under other statutes.','sources':['LAW:V16:GENERAL_RADIO:P6','LAW:V16:GENERAL_RADIO:P7']},
       {'id':'HP-R1','finding':'Deemed-tenancy date, qualifying license and room-size conditions supported; truncated definition acknowledged. The license definition spans pages 7 and 8; card citation to page 8 alone is less complete than the full input.','sources':['LAW:V16:HINDUSTAN_PETROLEUM:P7','LAW:V16:HINDUSTAN_PETROLEUM:P8']},
       {'id':'HP-R2','finding':'Specific acquisition provisions, prior deemed tenancy and chronology retained. No general transferable personal-license or all-merger immunity asserted. Necessary labels must remain relative to this stated statutory setting.','sources':['LAW:V16:HINDUSTAN_PETROLEUM:P9','LAW:V16:HINDUSTAN_PETROLEUM:P10','LAW:V16:HINDUSTAN_PETROLEUM:P11','LAW:V16:HINDUSTAN_PETROLEUM:P15','LAW:V16:HINDUSTAN_PETROLEUM:P16']},
       {'id':'HP-R3','finding':'Specific government/notification/amalgamation chain and protected successor supported. Correctly CASE_SPECIFIC_APPLICATION; cannot promote its particular steps to universally necessary merger conditions.','sources':['LAW:V16:HINDUSTAN_PETROLEUM:P10','LAW:V16:HINDUSTAN_PETROLEUM:P11','LAW:V16:HINDUSTAN_PETROLEUM:P16']},
       {'id':'TELESOUND-R1','finding':'Broad property includes tenancy contractual rights; transferee rights limited to transferor rights. No final rent-law immunity in this card. Court/date/statute title absent from supplied metadata/excerpts; this is an input provenance gap, not evidence model ignored supplied titles.','sources':['LAW:V16:TELESOUND:PAR12']},
       {'id':'TELESOUND-R2','finding':'Company-law characterization of vesting retained separately from rent-law assignment question; final question reserved. Scope remains limited by excerpt availability.','sources':['LAW:V16:TELESOUND:PAR12','LAW:V16:TELESOUND:PAR16']},
       {'id':'TELESOUND-R3','finding':'Prima facie consent/section14 view and explicit jurisdiction reservation retained. Condition C7 is a reserved legal issue, not a factual antecedent; cannot execute it as a boolean factual condition.','sources':['LAW:V16:TELESOUND:PAR16']}
      ],
      'important_unrepresented_source':{'authority':'GENERAL_RADIO','source':'LAW:V16:GENERAL_RADIO:P10',
         'finding':'The court reports Parasaram: Delhi section14 breadth does not exclude involuntary sale. No extracted card expressly preserves this reported rule; P10 is cited in GR-R2 but the proposition/conditions/effect do not state it. Model explicitly chose other direct rules within the three-card budget. This is consequential candidate-coverage loss, not citation failure.'},
      'retrieval_observation':{'query':'delhi-transfer','rank1':'TELESOUND:TELESOUND-R3',
         'finding':'BM25 places provisional opinion first. Lexical rank does not implement court hierarchy, statutory compatibility or reserved-question semantics. Every candidate and rank remains saved; none is certified as controlling.'},
      'confirmed_core_source_reversals':[],
      'limits':['Nine cards are not nine independently scored gold rules.','No new case application pair completed.','No automatic legal rule induction or legal applicability verification.','Two saved retrieval queries are offline diagnostics, not target-case retrieval scores.'],
      'decision':'RETAIN_SOURCE_EXTRACTION_CANDIDATES_APPLICATION_UNTESTED_SAMPLE_SHORTAGE'}
    save(ROOT/'final-source-review.json',review)
    save(ROOT/'decision.json',{'decision':review['decision'],'rule_extraction_path_completed':True,
         'new_case_application_comparison_completed':False,'compatible_target_shortage':True,
         'no_automatic_next_round':True})
    save(ROOT/'results.json',{'web_calls':3,'local_model_calls':0,'paid_API_calls':0,'retries':0,
         'complete_extraction_replies':3,'candidate_cards':9,'application_calls':0,'application_cases':0,
         'requested_application_cases':2,'new_case_answer':None,
         'application_status':'NOT_RUN_NO_CONFIRMED_COMPATIBLE_PREPARED_TARGETS','runs':rows})
    save(ROOT/'preservation-check.json',{'historical_files_unchanged':len(audit['historical_files']),
         'code_at_start_unchanged':len(audit['code_at_start']),'frozen_inputs_unchanged':len(freeze['files']),
         'semantic_repairs':0,'wrapper_removals':{'TELESOUND':'JSON_CODE_FENCE_ONLY'},'original_raw_preserved':True})
    save(ROOT/'stop.json',{'time':datetime.now(timezone.utc).isoformat(),
         'reason':'THREE_EXTRACTIONS_REVIEW_COMPLETE_NO_TWO_COMPATIBLE_PREPARED_TARGETS',
         'web_calls':3,'unused_application_call_budget':4,'no_source_expansion_old_case_rerun_or_push':True})
    slots=['# V16 Complete Rule-Extraction Results\n\nNo new-case final answers were produced. Insufficient samples prevented the application comparison; answers are null. Rule cards are model proposals, not human gold.\n']
    for name in NAMES:
        slots.append('## '+name+'\n\n'+read(ROOT/'runs'/name/'completion.json')['conversation_url']+'\n\n```json\n'+json.dumps(read(ROOT/'runs'/name/'rule-cards.json'),ensure_ascii=False,indent=2)+'\n```\n')
    (ROOT/'final-answer-slots.md').write_text('\n'.join(slots),encoding='utf-8')
    (ROOT/'report-zh.txt').write_text('''V16: extraction from original legal sources and preparation for cross-case application

Three independent browser High tasks produced nine candidate rule cards without semantic backfilling. Import, source recovery, and local candidate retrieval ran. Two-new-case A/B application did not: no two unused complete-source cases with compatible merger/statutory-succession issues were confirmed. New-case answer improvement cannot be assessed, and readable cards do not establish correct selection or legal authority.

Completed work
Reused V15 General Radio, Hindustan Petroleum, and Telesound originals, each in one fresh ordinary High chat. The model did not see1134266 facts, V15 hand-written cards, old answers, or source reviews. First two tasks used complete saved10-page/16-page PDF text with OCR/headnotes. Telesound had selected paragraph12 sentences and complete paragraph16, explicitly not full text. Tasks were40581/45810/8702 characters. Both attachment previews matched actual tasks; the short task matched after reconstructing editor text nodes/newlines. Exact model was undisplayed, recorded ChatGPT/High rather than assumed GPT-6. No local token constraints applied.

Reused V2 RuleCard fields and SQLite FTS5/BM25, adding provisional/reserved and reported-precedent source statuses. These avoid treating all material as final adopted doctrine, without adding fact ontologies or legal executors. Field/unique-ID/source-address checks and original recovery do not certify semantics. Rules/conditions remain model proposals; empty exceptions do not establish no exceptions. Four deterministic checks passed. No real-case pre-runs, local model generation, paid APIs, or new rule compilation occurred.

One consolidated source review
General Radio retains AP transfer/subletting, written consent, lease terms, and the lack of automatic exemption for voluntary merger approved by a court. The model identifies page7's apparent immune-wording contradiction using pages6/9/10 and the conclusion instead of extracting the opposite effect alone. HP retains deemed tenancy from a1973 licence, specific Esso acquisition legislation/notification/subsequent merger, without generalizing to all mergers. Telesound retains company-law vesting and marks paragraph16's licence/Delhi eviction opinion prima facie and reserved, not a final tenancy exemption. This is model-assisted review, not human gold or rule accuracy.

The key extraction omission is General Radio page10's Parasaram discussion: Delhi wording does not exclude involuntary sales. GR-R2 cites the page but no card proposition/condition/effect expresses that reported rule. The model's limitations say it prioritized other direct rules under the three-card cap. Correct addresses and complete originals do not prevent omission of a crucial distinction.

Selection is another problem. Both fixed offline queries retain all nine candidates/scores. Telesound's provisional opinion ranks first for Delhi merger; HP leads Bombay/Esso. BM25 ranks lexical relevance, not precedent hierarchy, statutory compatibility, or controlling status. Its top result is not passed to automatic adjudication. With no target cases/independent retrieval references, these are not retrieval-effectiveness evaluations.

Expression/source limits remain. Telesound C7 places a reserved legal question in an UNKNOWN condition, not an executable factual premise. HP necessity labels apply only to its situation. Existing Telesound metadata/excerpts lack full title, court, date, and statutory title; new cards retain these task-source gaps rather than blaming the model for missing supplied information. HP's licence definition spans pages7/8, but a page8-only citation gives incomplete context. Original cards stay unchanged; review records the issues.

Why the two-case comparison did not run
Following existing candidate-queue order/eligibility decisions, excluded55 previously used/read cases, leaving62 eligible complete-source candidates. Searched these local files for company amalgamation, merger, vesting, and related issue terms, without downloads/browser screening. Three hits concerned land-reform vesting, administrative authority vesting, and territorial merger, not merger-transferred tenancy. No two new cases were confirmed. This does not show all1,006 queued judgments lack candidates or certify dispute independence. Selection/hit passages are saved. Ordinary subletting cases were not forced into merger rules;1134266/69305 were not reused to fill the quota. Four application answers remained NOT_RUN/null, not UNKNOWN masquerading as completion.

Costs and decision
Three browser calls, zero retries/API/local generations, all importable, producing nine candidates. Visible thinking was50/56s for General Radio/HP and unavailable for Telesound. Exact tokens, total generation time, and peak memory are unavailable. Task tables retain visible time and observed completion upper bounds, not precise generation costs. Two local BM25 queries use no model calls.

Retain source-grounded extraction provisionally, without treating candidate rank as applicable-rule selection. Cross-case application benefit is unmeasured. Next requires two compatible merger/statutory-succession cases with target final reasons isolated, or separate authorization to choose a better-populated issue and appropriate authorities. Further69305 fact-format changes do not fill this sample/scope gap. Stop without autonomous screening expansion or new cases.

Complete prompts/schema/raw replies/chat URLs/originals/recovery/rankings/review/hashes/sample-shortage records are retained here. V1–V15 and existing code are byte-checked unchanged. Only V16 files, state, and local review package are added. No commit, push, or automatic next round.
''',encoding='utf-8')
    print(json.dumps({'finished':str(ROOT),'web_calls':3,'rule_cards':9,'application_cases':0,'history_preserved':len(audit['historical_files'])}))

if __name__=='__main__':finish()
