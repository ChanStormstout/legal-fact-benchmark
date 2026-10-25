"""Single decisive-source review and cost ledger, never generates or repairs outputs."""
import csv
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.pipeline_v13_crosscase import ROOT,CASES,ORDER,read,verify,inputs
from legal_bench.rules_verdict_v1.source_views import digest,write_new
from legal_bench.rules_verdict_v1.final_v9 import prompt,final_schema
from legal_bench.rules_verdict_v1.intermediate_v8 import first_prompt
from legal_bench.rules_verdict_v1.checks_v8 import fact_schema

freeze=verify();result=read(ROOT/'results.json')
meta={(r['case'],r['slot']):r for r in result['rows']}
assert result['new_model_calls']==6 and all(r['run_status']=='OK' for r in result['rows'])
answers={};restored={};checks=[]
for c in CASES:
    source,law=inputs(c);cm={s['id']:s['text'] for s in source['segments']};lm={s['id']:s['text'] for s in law['law_segments']}
    proposal=read(ROOT/'intermediates'/f'{c}-proposal.json')
    assert proposal==read(ROOT/'runs'/c/'B-proposal/parsed.json')
    assert (ROOT/'runs'/c/'B-proposal/prompt.txt').read_text()==first_prompt(source,law,'B')
    assert read(ROOT/'runs'/c/'B-proposal/schema.json')==fact_schema(list(cm))
    for m in ['D','B-P']:
        material={} if m=='D' else {'proposal':proposal}
        assert read(ROOT/'prepared'/c/m/'intermediate.json')==material
        assert (ROOT/'runs'/c/m/'prompt.txt').read_text()==prompt(source,law,material)
        assert read(ROOT/'runs'/c/m/'schema.json')==final_schema(list(cm),list(lm))
        a=read(ROOT/'runs'/c/m/'parsed.json');answers[c+'/'+m]=a
        restored[c+'/'+m]=[{'ground':i+1,'point':g['point'],
            'case_sources':[{'id':r,'text':cm[r]} for r in g['case_refs']],
            'law_sources':[{'id':r,'text':lm[r]} for r in g['law_refs']],
            'valid_source_address_not_semantic_certification':True} for i,g in enumerate(a['grounds'])]
    for m in ['D','B-proposal','B-P']:
        r=meta[c,m];p=ROOT/'runs'/c/m
        assert r['actual_parameters']==freeze['actual_parameters']
        assert r['constraint_mode']=='FIXED' and r['schema_mask_calls']>0
        assert r['thinking_disabled_template_verified'] and not r['thinking_output_present']
        assert not r['format_repairs'] and r['finish_reason']=='stop'
        ids=read(p/'token-ids.json');assert len(ids)==r['output_tokens'] and ids[-1]==248046
        assert r['prompt_tokens']+3072<=32768
        assert json.loads((p/'raw-response.txt').read_text())==read(p/'parsed.json')
        checks.append({'case':c,'slot':m,'tokens':r['output_tokens'],'mask_calls':r['schema_mask_calls'],'exact_prompt_schema':True,'no_repair':True})
write_new(ROOT/'protocol-audit.json',{'rows':checks,'order_exact':[[r['case'],r['slot']] for r in result['rows']]==[list(x) for x in ORDER],
    'same_case_source_and_law_for_D_and_B':True,'B_P_current_proposal_unmodified':True,'no_program_checks_in_final':True,
    'no_reference_or_expected_answer_in_input':True,'no_source_truncation':True,'V11_settings_templates_contract_unchanged':True,
    'actual_calls':6,'web_calls':0,'retries':0,'extra_model_pre_runs':0})
write_new(ROOT/'final-answers.json',answers);write_new(ROOT/'restored-final-sources.json',restored)

review={'review_type':'ONE_CONCENTRATED_FINAL_DECISIVE_SOURCE_AND_OMISSION_REVIEW',
 'reference_status':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD',
 'scope':'Two historically exposed development cases, not independent testing. No demand to recover withheld final dispositions.',
 'full_intermediate_reannotation':False,'new_gold':False,'review_agent_or_web_calls':0,
 'cases':{
 '661475':{
   'source_anchors':[
    {'refs':['p0001.s001','p0001.s002'],'finding':'Dr.Vijay Kumar为租户，Raghbir为房东；1965-01-12是申请腾退日期，1966-12-06是Rent Controller裁定日期。允许来源未给分隔/交出占有的具体日期，起诉发生在1952之后不能证明此前转移也在1952之后。下级命令及两次上诉被驳回可见，最高法院最终理由不在本轮输入。'},
    {'refs':['p0001.s003','p0001.s004','p0001.s005'],'quote':read(ROOT/'sources/661475.json')['segments'][3]['text'],
     'finding':'分隔墙、独立门和锁是依据；Rent Controller明确认定两儿子独占其部分、父亲交出占有，并未接受共同经营抗辩。这些不是仅待定的家庭安排或未裁定叙述。'},
    {'refs':['p0002.s002@0:412'],'finding':'父亲许可两儿子占用是租户律师论点，许可主体为租户父亲，不是房东；未显示房东书面同意或其不存在的独立认定。'},
    {'refs':['LAW:1134266:p0004.s005','LAW:1134266:p0004.s006','LAW:69305:p0005.s004'],'finding':'法源写明SUBLET/ASSIGN/PART_WITH_POSSESSION为择一方式，动机无关；specific written consent讨论必须保持房东与租户许可区别。后出法源历史适用未验证。'}],
   'D':{
    'supported':['g1准确保留Rent Controller交出占有认定及具体部分；没有升级成最高法院终审认可。','g3把父亲许可当律师主张，并没有直接据未展示文书推断确定无同意。'],
    'confirmed_errors':[{'grounds':[2],'type':'PROCEDURAL_DATE_AS_TRANSFER_DATE','finding':'以1965起诉日期证明转移满足1952下界，不成立。起诉时间至多约束转移在其之前，不能提供所需下界。'},
      {'grounds':[4],'type':'WRONG_PERMISSION_SUBJECT','finding':'point称房东所称一般许可，但来源是租户父亲许可；解释虽提到father，未修正point主体。'},
      {'grounds':['reason'],'type':'CONSENT_CONDITION_POLARITY','finding':'将written landlord consent写成成立腾退所需的necessary条件，给定基础条件实际是缺乏这种同意。正确缺口是同意/无同意均未可靠确定，而不是没有证明同意导致请求失败。'}],
    'omissions':['没有保留下级否定共同经营抗辩的理由及法院结论；主要反对理由只转为笼统家庭许可。'],
    'internal_consistency':'g1与转移认定基本一致，但日期SUPPORTED无依据，reason对同意条件极性含混/反向。',
    'real_gaps':['转移是否在1952之后未由允许来源确定；起诉日期不能补足。','房东具体书面同意或缺乏同意未明确给出；父亲许可不能填补。','完整历史法条版本及父亲许可抗辩在目标终审的处理未提供。'],
    'conclusion':'UNDETERMINED可能符合当前信息边界，但现有理由含错误，不能视为完整正确答案。'},
   'B-P':{
    'supported':['g1保留Rent Controller独占部分及分隔事实，承认交出占有；没有恢复目标最高法院最终处理。'],
    'confirmed_errors':[{'grounds':[2],'type':'INVENTED_TRANSFER_DATE','finding':'把分隔事件明确写成1965-01-12同日发生，来源没有这项日期。'},
      {'grounds':[3,4],'type':'PARTY_ROLE_AND_PERMISSION_CONFUSION','finding':'g3把父亲许可当未定形式的同意，引用的p0001.s002/s003没有许可陈述；g4称房东主张许可，实际律师为租户提出父亲许可。'},
      {'grounds':[4,'reason'],'type':'DISJUNCTION_AND_AVAILABLE_FINDING_IGNORED','finding':'已在g1承认交出占有，却要求必须另行确定SUBLET或ASSIGN才能判断，忽略法源三方式择一；以“法律模式缺失”为决定性缺口错误。g4还引用说明动机无关的法源，却以家庭安排制造模式缺口。'},
      {'grounds':[3,'reason'],'type':'CONSENT_CONDITION_POLARITY','finding':'仍把正面的房东书面同意说成成立腾退的必要条件，未正确表达未知如何影响without-consent判断。'}],
    'omissions':['g4保留共同经营抗辩未成立，但没有正确结合交出占有认定与择一法条；人物角色仍混淆，未展开否定共同经营的具体证据。'],
    'internal_consistency':'g1及reason承认parting with possession，g4又认为不能确定法定转移方式；未知标签没有消除条件组合矛盾。',
    'real_gaps':'与D同一时间/房东同意及历史法源边界，不包括交出占有是否已有下级认定。',
    'limited_intermediate_trace':{'records':['t2','x1','x2','d2','c1','c2','coverage_limits'],
      'finding':'t2把房东写成租户，x1/x2把房东写成受让人；d2给分隔虚构1965-01-12；coverage称交出占有和共同经营未裁定。B-P重复虚构日期及模式缺失，与这些提议一致，属于传播线索，不证明单一因果机制。最终没有明确照抄错误人名，不能说所有提议错误都进入最终答案。'},
    'conclusion':'比D新增明确日期和择一条件组合错误，未有净收益。'},
   'comparison':'661475上D保留下级认定较直接，B-P新增同等或更严重错误；二者都有许可主体/极性及时间错误，不把D认证为正确。'},
 '1134266':{
   'source_anchors':[
     {'refs':['p0001.s003','p0002.s001','p0002.s004'],'finding':'原租戶是American Company，Indian Company后更名Singer India Limited；租约原文明确registered lease deed dated11.7.1966。ARC曾驳回，Tribunal反转并命令腾退，Delhi High Court维持；目标最高法院最终处理被排除。'},
     {'refs':['p0002.s001','p0002.s002'],'finding':'1982年房东申请中的“without obtaining any written consent”是指控，未展示完整租约或法院对于同意的具体认定；不能用无人展示反证升为事实已成立。'},
     {'refs':['p0002.s003'],'quote':read(ROOT/'sources/1134266.json')['segments'][3]['text'],
      'finding':'明确记载Bombay High Court于31.12.1981允许申请、批准合并，租赁/占有等权利转归Indian Company；“原公司仍是法律替代/无subtenancy”是抗辩。法定转移效果可争议不使已给出的批准事件消失。'},
     {'refs':['p0002.s007','p0003.s003','p0003.s006','p0003.s007','p0003.s008','p0004.s001'],
      'finding':'租户主张FERA迫使合并、原公司仍在更大整体存续；房东反驳仅要求降低股本、合并可选择，并主张原公司失去身份。这些是相反律师论点，不能作目标最高法院采纳。租户未主张“法院批准等于房东默示同意”。'},
     {'refs':['LAW:69305:p0005.s002','LAW:69305:p0005.s004','LAW:661475:p0002.s004'],
      'finding':'包内规则涉及未登记租约条款、特定转租书面同意、家庭许可与迟提出抗辩；没有提供目标自己的合并法律定性规则。不能据RC-04把已登记租约定为未登记，家庭许可规则也不能证明合并不获法院批准。'}],
   'D':{
    'supported':['将法律替代/法定强制作为租户论点，与房东自愿合并反驳区分；没有凭目标历史最终方向强行下确定结论。'],
    'confirmed_errors':[{'grounds':[1,'reason'],'type':'ALLEGATION_AND_SILENCE_AS_ESTABLISHED_ABSENCE','finding':'把房东无同意指控及未展示相反记录，变成absence established；叙述没有重现完整租约，不能说lease deed contains no consent。'},
      {'grounds':[2,'reason'],'type':'EXPLICIT_COURT_SANCTION_OMITTED_AS_MISSING','finding':'声称没有法院认定或证据证明Bombay High Court批准合并，直接反于p0002.s003已给事实；法律效果争议不使批准缺失。'},
      {'grounds':[3],'type':'REGISTERED_AS_UNREGISTERED_AND_WRONG_RULE_SCOPE','finding':'把registered租约读成unregistered，套用69305非登记条款不可采规则，并隐含目标有许可条款。这是明确来源误读及法源条件不匹配。'}],
    'omissions':['未保留ARC驳回/Tribunal反转/High Court维持的层级变化；遗漏实际批准及权利归属事实，只留下争议说法。'],
    'internal_consistency':'UNDETERMINED标签与其自称缺少批准一致，但这个决定性缺口是虚构的；书面同意无反证被定为不存在。',
    'real_gaps':['目标合并如何满足S14具体转移方式、法定强制/法律替代抗辩的范围，包内未完整解决。','房东书面同意是否存在没有独立明确处理；不推断不存在。'],
    'conclusion':'无法判断可能有真实法律覆盖原因，但D具体缺失判断不忠实。'},
   'B-P':{
    'supported':['g1明确将无同意/交出占有归为房东指控，未当作法院成立事实。','g3保留法院批准合并及权利转归Indian Company；不再说缺少批准。','reason具体指出RC-05是程序性规则，不能证明合并例外；没有套用RC-04宣布目标租约不可采。'],
    'confirmed_errors':[{'grounds':[4],'type':'INVENTED_CONSENT_THEORY','finding':'增加“租户认为法院批准合并构成房东默示同意”，原文只主张法定强制使S14不适用；将反对法律适用的主张改写成同意主张。'}],
    'omissions':['仍未保存ARC/Tribunal/High Court相反程序结果；没有明确保留registered这一足以排除RC-04误用的事实。','只概括statutory compulsion，未具体处理房东“降低股本可有多种途径、合并是自愿选择”的主要反驳。'],
    'internal_consistency':'比D少明显相反的来源断言；g3承认权利转归，reason又强调没有法院确认parting，需明确区别已知归属事实与未决法定定性，否则再次让法律效果未定掩盖已有事实。不把vesting与S14定性直接等同，也不强判该行矛盾。',
    'real_gaps':'对公司合并与法定强制的S14意义，现有包缺完整规则；没有目标最终结论不单独构成无法分析理由。保留这一解释争议，不要求猜回历史裁判。',
    'limited_intermediate_trace':{'records':['x1','c3','coverage_limits'],
      'finding':'x1保留American→Indian合并，c3又把Bombay High Court批准列入consents并标grantor/target未定。最终g3恢复批准，g4出现合并批准作为同意的说法；有内容对应，不能确定收益或错误全由表示形式引起。未全量核查其他提议字段。'},
    'conclusion':'比D有明确的局部来源收益，仍有新增主张和遗漏；不能称为完整验证正确。'},
   'comparison':'1134266上B-P纠正D的明确批准遗漏、主张定性及注册状态误用，额外成本同时增加；这与661475方向不同。'}},
 'cross_case_answer':'来源归属混淆、已有事实被说成缺失、条件极性和内部不一致在另外两案仍出现，但并非每个方法/案件都复现全部错误。661475两种最终答案都保留下级交出占有认定；1134266 B-P保留合并批准，不能说一概遗漏全部法院认定。',
 'decision':'MIXED_CASE_DIRECTIONS_NO_WINNER',
 'decision_zh':'两案收益方向不同，暂不选赢家，也不把结构化前置设为强制步骤',
 'decision_basis':'661475提议及B-P新增日期/对象/择一条件错误，没有收益；1134266 B-P恢复法院批准并减少D的确定误读，但仍改写租户抗辩和遗漏主要反证。额外两阶段成本约2.83/3.48倍，尚没有一致净收益。两边还有共同理解及整合问题，本轮停止增加字段/检查；保留已有组件作为可复现候选，不启动修复。',
 'scope_not_accuracy_ranking':True,'no_auto_next_round':True}
write_new(ROOT/'final-source-review.json',review)
write_new(ROOT/'decision.json',{k:review[k] for k in ['decision','decision_zh','decision_basis']})

summaries={
 ('661475','D'):['保留Rent Controller交出占有认定，父亲许可主要仍作律师论点','起诉日期代替转移时间；g4许可主体错置；reason同意条件极性不清','漏下级否定共同经营抗辩','日期支持无依据；未知标签不消除极性错误','转移日期/房东同意真实未定，历史法条边界仍在'],
 ('661475','B-P'):['保留分隔及独占下级事实','虚构分隔日期；将父亲/房东许可混淆；忽略PART_WITH_POSSESSION已满足择一方式','未正确利用共同经营被否定与交出占有认定；未展开相应证据','g1承认交出占有，g4又以缺SUBLET/ASSIGN否定可判断性','真实时间/房东同意缺口不包括交出占有认定缺失'],
 ('1134266','D'):['保留强制合并和房东自愿反驳是双方论点','已登记读成未登记；法院批准被说成无证据；无同意指控变已成立','漏合并批准/归属及ARC→Tribunal→High Court变化','虚构缺口造成看似一致的未知结论','合并法律定性、强制抗辩和同意真实未定'],
 ('1134266','B-P'):['保留法院批准/权利转归；无同意仅作指控；程序性规则不证明合并例外','新增租户主张法院批准等于房东默示同意的说法','漏登记状态、下级审理变化和自愿选择主要反驳','归属事实与S14定性没有清楚展开，保留解释争议','合并法律效果在现有包内确有覆盖缺口，不要求猜历史终审']}
rows=[]
for c in CASES:
    for m in ['D','B-P']:
        r=meta[c,m];stage=meta[c,'B-proposal'] if m=='B-P' else None;s=summaries[c,m]
        rows.append({'case':c,'method':m,'technical_status':r['run_status'],'outcome':answers[c+'/'+m]['outcome'],
         'source_supported_key_judgments':s[0],'confirmed_errors':s[1],'decisive_omissions':s[2],
         'internal_contradictions_or_limits':s[3],'real_material_gaps':s[4],
         'final_input_tokens':r['prompt_tokens'],'final_output_ids':r['output_tokens'],'final_seconds':round(r['elapsed_seconds'],3),
         'extraction_input_tokens':stage['prompt_tokens'] if stage else 0,'extraction_output_ids':stage['output_tokens'] if stage else 0,
         'extraction_seconds':round(stage['elapsed_seconds'],3) if stage else 0,
         'method_calls':2 if stage else 1,'total_input_tokens':r['prompt_tokens']+(stage['prompt_tokens'] if stage else 0),
         'total_output_ids':r['output_tokens']+(stage['output_tokens'] if stage else 0),
         'total_seconds':round(r['elapsed_seconds']+(stage['elapsed_seconds'] if stage else 0),3),
         'peak_mlx_gb':max(r['peak_mlx_memory_gb'],stage['peak_mlx_memory_gb'] if stage else 0),
         'reference_status':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD'})
write_new(ROOT/'comparison-table.json',rows)
with (ROOT/'comparison-table.csv').open('x',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
write_new(ROOT/'cost-ledger.json',{'actual_calls':6,'input_tokens':sum(r['prompt_tokens'] for r in result['rows']),
    'output_token_ids':sum(r['output_tokens'] for r in result['rows']),'inference_seconds':result['inference_seconds'],
    'wall_seconds':result['round_wall_seconds'],'model_load_seconds':result['model_load_seconds'],
    'end_token_included':True,'not_equal_call_or_compute_budget_comparison':True,'web_calls':0,'retries':0})
start=read(ROOT/'start-audit.json')
bad=[p for p,h in start['historical_outputs'].items() if digest(Path(p).read_bytes())!=h]
badcode=[p for p,h in start['preexisting_code_hashes'].items() if digest(Path(p).read_bytes())!=h]
assert not bad and not badcode
verify();write_new(ROOT/'preservation-check.json',{'historical_files_checked':len(start['historical_outputs']),
    'preexisting_code_files_checked':len(start['preexisting_code_hashes']),'changed_historical_files':bad,'changed_preexisting_code':badcode,
    'V12_D_RUN_LOG_ERROR_null_unchanged':True,'unrelated_local_chunk_v11_preserved':True})
parts=['# V13四份最终答案\n\n以下内容直接来自本轮parsed.json，未修正语义或补写；六次均技术完成，法律正确性需阅读来源审阅。旧案开发结果不是独立测试或人工gold。\n']
for c in CASES:
    for m in ['D','B-P']:parts.append('\n## '+c+' '+m+'\n\n```json\n'+(ROOT/'runs'/c/m/'parsed.json').read_text()+'\n```\n')
(ROOT/'final-answer-slots.md').write_text(''.join(parts),encoding='utf-8')
table='\n'.join(f"| {r['case']} | {r['method']} | {r['technical_status']} | {r['outcome']} | {r['total_input_tokens']} / {r['total_output_ids']} | {r['total_seconds']:.1f} |" for r in rows)
report=f'''V13: fixed-method development check on two existing cases

Decision: benefits differ by case; choose no winner and do not require a structured front end. In661475, D/B-P preserve lower-court parting-with-possession findings, but B-P adds an invented partition date and erroneous combination of transfer modes. In1134266, B-P better preserves court-approved merger and reduces clear source errors, but invents a defense equating approval with implied landlord consent. There is no consistent complete-answer net benefit. Neither D reliability nor general ineffectiveness of structure is established. Stop adding fields/checks/prompts around old cases; retain components as reproducible candidates, without another repair round.

Execution and version
HEAD {start['head']}, branch {start['branch']}. Existing uncommitted V11/V12 code/docs and local_chunk_v11.py were retained. Both cases were already used in V6/V7, so this is cross-case development, not independent testing. Allowed sources/legal packages/retrieval results are reused byte-for-byte; D/B share materials within a case, while the two cases' old legal packages differ. For661475, later authorities and unverified historical applicability remain limits. For1134266, target-specific rule cards are excluded, but researcher-supplied target-source formulas remain; this is not a rule-blind test.

Model revision8b2b98c00a6b4d291155e4890773ca8f769aee53, MLX-VLM0.7.4, LMFE0.11.2, greedy, seed20261001, repetition_penalty1, thinking off, FIXED constraints, max_tokens3072/context32768 match actual V11. Reconstructed actual prompts verify V11 D/B-P final templates, full examples, schema, and B proposal contracts. Only cases/existing legal packages/valid source IDs change; no old answers, reference facts, correct-passage hints, or program-check blocks enter input.

The runner reuses V11 verbatim; actual_parameters is saved in a fresh filtered dictionary without mask objects. V12's logging repair was verified as only two dictionary copies. Old D failure/null remain, without backfilled costs. Five constraint regressions passed without skips. Existing V11 real-tokenizer fixtures/replay records were reused after matching source hashes, with no model pre-runs. Code/templates/schema/material hashes/order/stop rules were frozen before generation; dynamic B-P inputs were saved/budget-checked before each call.

All six scheduled calls were OK/stop; all four final conclusions UNDETERMINED. Inference {result['inference_seconds']:.1f}s, round wall time {result['round_wall_seconds']:.1f}s, loading separately {result['model_load_seconds']:.1f}s. No browser calls/retries/pre-runs, source truncation, JSON completion, proposal repair, prompt/thinking changes, or replacement cases. Technical completion is not legal correctness.

| Case | Method | Technical status | Final conclusion | Total input/output IDs including extraction | Seconds including extraction |
| --- | --- | --- | --- | --- | --- |
{table}

B-P two-stage time is about2.83x/3.48x D, with total input2.14x/2.20x. Final inputs alone add1571/2030 tokens, plus full extraction calls. This measures net benefit/cost of a structured front end, not equal-call-budget performance or representation alone.

661475: preserved facts and errors
p0001.s004 records the Rent Controller finding that the sons exclusively occupied their parts and the father parted with possession; s005 rejects the joint-business defense. D g1 preserves the former without Supreme Court promotion. B-P g1 does too, but g4 demands SUBLET or ASSIGN despite PART_WITH_POSSESSION already being one alternative in the legal package. Its reason invents a missing-mode gap. This is condition-integration/internal inconsistency, not missing source findings.

D uses the1965-01-12 filing date to establish a post1952 transfer; B-P says partition occurred on that date. No source gives the event date. Filing supplies an upper bound for an earlier transfer, not the needed1952 lower bound. B proposal d2 already invents the date, and coverage says transfer/joint business were undecided. Final repetition is a propagation clue, not a complete causal mechanism established by textual similarity.

Permission comes from tenant counsel's claim that the father allowed his sons to occupy, not landlord permission. D g3 distinguishes the claim, but g4's point assigns general permission to the landlord. B-P g3 cites unrelated p0001.s002/s003, and g4 also assigns the claim to the landlord. Proposal t2 calls the landlord the tenant; x1/x2 name the landlord as transferee. Final text does not explicitly repeat the wrong names, so not every proposal error propagated. Both reasons treat positive written consent as necessary for eviction rather than explaining the statutory without-consent condition and its unresolved evidence.

Real gaps concern post1952 transfer timing, specific landlord written consent/absence, and historical statutory scope. UNDETERMINED may be warranted, but invented dates/condition errors prevent acceptance of either complete answer. D omits rejection of joint business; B-P retains it but fails to integrate it with possession findings and alternative statutory modes. Both omit specific evidence against joint business. Review included uncited passages.

1134266: local B-P benefit, with omissions and rewritten arguments
p0002.s001 expressly says registered lease deed. D g3 reverses this and applies69305's unregistered-clause inadmissibility rule, though no source establishes that clause in the target lease. D g2/reason deny evidence of Bombay High Court merger approval, contradicting p0002.s003's31.12.1981 approval and vesting of lease/possession rights in Indian Company. Disputed legal effects do not erase the approval event. D g1 turns the landlord's no-consent allegation and absence of displayed counterevidence into established absence.

B-P g1 correctly attributes no consent to the landlord's allegation; g3 preserves approval/vesting, avoids the inadmissibility rule, and recognizes that procedural RC-05 cannot prove a merger exception. These are verifiable improvements over D. But g4 invents a tenant argument that approval is implied landlord consent. The source instead argues FERA-compelled merger makes S14 inapplicable. Proposal c3 classifies approval under consents with unresolved fields, matching the final rewrite; representation alone cannot be assigned all gains/errors.

Both omit ARC dismissal, Tribunal reversal/eviction, and Delhi High Court affirmance. B-P also omits the landlord's central rebuttal that capital reduction had alternatives and merger was voluntary, and fails to state registration explicitly. B-P g3 recognizes vesting while its reason stresses no judicial parting characterization. Existing vesting events and unresolved S14 characterization must be distinguished: vesting is not automatically statutory parting, nor does unresolved characterization imply no vesting fact. This interpretive issue is retained rather than forced into the same direct-contradiction category as69305.

The package includes specific-consent, unregistered-clause, and late-family-permission rules, but not full S14 merger/statutory-compulsion interpretation. Target RC-01/RC-02 were not restored. Indeterminacy can reflect a real legal-source gap, but absence of the target's final judgment is not the sole reason and historical outcomes must not be guessed.

Recurrence and investment decision
Permission-subject/claim-attribution confusion, known facts recast as missing, condition polarity, and contradictions recur beyond69305, but not every error in every answer. Both661475 answers preserve lower-court possession findings;1134266 B-P preserves merger approval. It is wrong to say all answers erase all judicial facts. None is confirmed reliable on every decisive basis; equally, all UNDETERMINED answers are not automatically wrong. Retain661475 timing/consent gaps and1134266 merger-interpretation gaps.

The direction differs:661475 gains nothing from the proposal and adds serious errors;1134266 reduces D misreadings at higher cost while retaining semantic issues. Choose no winner, impose no mandatory structure, and do not tune prompts for the worse case. Evidence supports shared comprehension/integration problems, not universal structural failure, universal D superiority, or verified adjudication capability.

Delivery and stopping
Four complete answers are in final-answer-slots.md/final-answers.json; two unchanged proposals in intermediates. comparison-table.json/csv separate technical status, source support, confirmed errors, omissions/contradictions, genuine gaps, conclusions, and extraction-inclusive costs. final-source-review.json is the single model-assisted review, not human gold. restored-final-sources.json restores key citations. Complete originals, old legal/retrieval packages, actual prompts/schema/raw text/IDs/masks/metadata remain. offline-checks validate addresses/proposal structure/link restrictions only; they neither enter final-model input nor certify semantics.

All {len(start['historical_outputs'])} historical files and {len(start['preexisting_code_hashes'])} original source files are byte-identical. Old V12 logging failure/null remain. After local index/state/review updates and integrity checks, stop without commit/push, rerunning69305, changing models, adding fields/authorities/cases, or starting another round.
'''
(ROOT/'report-zh.txt').write_text(report,encoding='utf-8')
print(json.dumps({'report':str(ROOT/'report-zh.txt'),'decision':review['decision'],'calls':6}))
