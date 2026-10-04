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
    slots=['# V16 完整规则提取结果\n\n本轮没有新案最终回答；应用比较因样本不足未运行，答案为null。规则卡是模型提议，非人工金标准。\n']
    for name in NAMES:
        slots.append('## '+name+'\n\n'+read(ROOT/'runs'/name/'completion.json')['conversation_url']+'\n\n```json\n'+json.dumps(read(ROOT/'runs'/name/'rule-cards.json'),ensure_ascii=False,indent=2)+'\n```\n')
    (ROOT/'final-answer-slots.md').write_text('\n'.join(slots),encoding='utf-8')
    (ROOT/'report-zh.txt').write_text('''V16：从法源原文提取规则与跨案应用准备

结论：三份独立网页High任务完成，得到9张未经语义补写的候选规则卡，规则导入、出处恢复和本地候选检索已运行。两件新案的A/B应用比较没有运行：现有完整来源候选中没有确认符合公司合并／法定承继争点的两个未使用案件。不能据此判断自动规则材料改善了新案回答，也不能把规则卡可读取解释为规则已被正确选择或具有法律效力。

已完成的工作
沿用V15保存的General Radio、Hindustan Petroleum、Telesound原文，三者分别进入新的普通High对话，一份一次。网页没有看到1134266案情、V15手写规则卡、旧模型答案或来源评价。前两份提供完整既存PDF文本，分别10页、16页，保留OCR与headnote；Telesound仅有第12段选句与完整第16段，明确不是全文。完整任务40581、45810、8702字符；两个附件预览与实际任务逐字相同，短任务按编辑器文本节点与换行恢复后逐字相同。具体模型未显示，记录ChatGPT/High，不假定GPT-6型号；网页没有本地逐token约束。

实现复用V2 RuleCard字段及现有SQLite FTS5/BM25，增加两种来源性质：暂定且保留最终问题、对另一判例的转述。它们避免把来源地位统一成法院已经采用的最终规则，不新增事实ontology或法律执行器。程序检查字段、唯一卡ID和有效出处，原文按ID恢复；这些检查不认证语义。候选规则及条件都标为模型提议，空exceptions不解释为不存在例外。4项必要确定性测试通过，没有真实案件预跑、本地模型生成、付费API或新规则编译。

一次集中原文核查的发现
General Radio保留AP法的转移／转租、书面同意与租约条件，以及公司自发提出合并后法院批准不自动产生豁免。模型还识别了第7页immune字句与上下文的表面矛盾，以第6、9、10页推理和结尾为依据，没有单独抽出相反法律效果。Hindustan Petroleum保留1973年既存licence产生的deemed tenancy、特定Esso收购法、通知和后续合并链，未把它扩成任何合并都无需许可。Telesound保留公司法上的权利转归，并把第16段关于许可和Delhi腾退的prima facie意见标为保留问题，没有升级为最终租赁法豁免。上述是本次模型辅助来源审阅，非人工gold；不据此计算规则准确率。

最关键的遗漏发生在规则提取。General Radio第10页转述Parasaram，明确说Delhi条款的范围不排除非自愿出售；模型虽在GR-R2引文地址中包含该页，却没有在任何卡的命题、条件或效果中写出这条转述规则。模型的limitations说明因三卡预算优先选择了其他直接规则。出处正确和原文完整都不能防止规则摘要丢掉关键法律区别。
第二个问题发生在规则选择。两个固定离线检索查询已保存全部9个候选及分数；Delhi合并查询第一名是Telesound的暂定意见，Bombay/Esso查询前列是HP材料。BM25只排序词汇相关性，不能决定先例层级、法条兼容性或暂定意见是否控制争点。目前不把它的第一名交给程序裁判。没有目标案件及独立检索参考，不能把这两次检索称为检索效果评价。
第三个问题是表达与来源边界。Telesound卡C7把保留的法律问题放在UNKNOWN条件中，它不是可机械执行的事实前提；HP案例链的必要标签也仅适用于其具体场景。Telesound旧metadata与摘录未保存完整标题、法院、日期和法条标题，所以新卡保留这些来源缺口；这是任务材料不足，不能归因模型遗漏已经提供的信息。HP的licence定义跨第7、8页，卡只引用第8页时出处恢复不够完整。原始卡均不修改，问题留在审阅记录中。

为何没有进行两件新案比较
按既有candidate-queue顺序和先前已完成的资格检查，排除55个此前使用／阅读案件，剩余62个已有完整来源的合格候选。仅在这些本地文件上检索公司合并、merger、vesting等争点词，不新下载或网页筛选。三个有词命中的案件分别涉及土地改革vesting规则、行政权限vesting和地区merger，不是公司合并转移租赁权。没有确认可用于本轮的两件新案；这一结果不声称1006个队列或所有判决都没有相关案件，也不认证纠纷独立性。选择和命中原文全部保存。未将普通转租案件强套公司合并规则，未复用1134266、69305补足新案，未启动4次应用回答。其状态为NOT_RUN，答案为null，不填写UNKNOWN冒充完成。

成本与投入决定
实际网页调用3、重试0、API0、本地生成0，三个回复全部可导入，共9张候选卡。General Radio／HP界面显示思考50／56秒，Telesound未显示可读取思考时长。精确tokens、总生成耗时及峰值内存不可得；逐任务表只保存可见时长和从提交至确认完成的观察上界，不能把观察间隔当精确生成成本。两次本地BM25是离线候选检索，不消耗模型调用。
暂时保留有来源规则提取组件，但没有证据支持把候选排序直接当适用规则选择；跨案应用收益尚未测到。接下来需要两个已经隔离目标最终理由的同类公司合并／法定承继案件，或另行授权选定有样本的争点并建立对应法源包。继续修改69305事实格式不会补上这个样本与法源范围缺口。本轮按停止条件结束，不自行扩大筛选或获取新案。

完整prompt、schema、raw、对话URL、原文、恢复结果、候选排名、审阅、哈希与样本不足记录都在本目录。V1–V15和既有代码原字节核验；仅新增V16文件、项目状态与本地审阅包。不提交、不推送，不自动开启下一轮。
''',encoding='utf-8')
    print(json.dumps({'finished':str(ROOT),'web_calls':3,'rule_cards':9,'application_cases':0,'history_preserved':len(audit['historical_files'])}))

if __name__=='__main__':finish()
