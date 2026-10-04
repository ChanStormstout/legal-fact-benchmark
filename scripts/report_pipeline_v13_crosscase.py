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
report=f'''V13：固定现有方法，两个已有案件的开发检验

投入决定：两案收益方向不同，暂不选赢家，也不把结构化前置设为强制步骤。661475中D和B-P都保留下级交出占有认定，但B-P新增虚构分隔日期和转移方式组合错误；1134266中B-P比D准确保留法院批准合并，减少明确来源误读，仍增加“法院批准等于房东默示同意”的无依据抗辩。没有一致的完整答案净收益，不认定D可靠或结构化普遍无效。停止围绕旧案增加字段、检查或提示，保留当前组件作为可复现候选，本轮不启动修复或下一轮。

实际运行与版本
HEAD {start['head']}，分支{start['branch']}。既有未提交V11/V12代码、文档及local_chunk_v11.py全部保留。原两案在V6/V7已经开发过，因此称跨案件开发检验，不是独立测试；各案允许来源、法律包和检索结果原字节复用，D/B看到相同材料，但两案原法律包不同。661475保留后出法源和历史版本未验证限制；1134266排除目标专用规则卡，仍继承研究者提供的目标来源基础公式，不是规则盲测。
模型revision8b2b98c00a6b4d291155e4890773ca8f769aee53、MLX-VLM0.7.4、LMFE0.11.2、greedy、seed20261001、repetition_penalty1、thinking off、FIXED约束、max_tokens3072、总上下文32768全部与V11实际一致。V11的D/B-P最终模板、完整示例、Schema和B提议合同都通过实际prompt重建核验。本轮只换案件/既有法律包/合法来源编号，不含旧答案、参考事实、正确段落提示或程序检查块。
运行器逐字复用V11，actual_parameters由过滤后的新字典保存，不含mask对象；V12日志修复核对确实仅两处字典副本，其旧D失败和null原样保留，没有补计旧成本。约束回归5项通过、零跳过，真实tokenizer fixture和回放沿用V11已完成记录并核验相同源码；无额外模型预跑。生成前冻结代码、模板、schema、材料哈希、顺序及停止规则；动态B-P实际输入在各次调用前保存并检查预算。
指定六次调用全部OK/stop，四个最终结论均UNDETERMINED。推理{result['inference_seconds']:.1f}秒、整轮{result['round_wall_seconds']:.1f}秒，加载另计{result['model_load_seconds']:.1f}秒；网页0、重试0、额外预跑0。没有截断来源、补写JSON、修提议、改提示或thinking；未因错误换案。技术完成不等于法律回答正确。

| 案件 | 方法 | 技术状态 | 最终结论 | 含抽取总输入/输出IDs | 含抽取秒 |
| --- | --- | --- | --- | --- | --- |
{table}
B-P两阶段成本相对D分别约2.83倍、3.48倍，总输入约2.14倍、2.20倍。其最终输入还分别多1571、2030 tokens，另有完整抽取调用成本。比较的是添加结构化前置的净收益/成本；不能声称同调用预算，也不能把收益全归表示形式。

661475：正确保留了什么，错误在哪里
允许来源p0001.s004写明Rent Controller认定两儿子独占其部分、父亲交出占有；p0001.s005写明共同经营抗辩未成立。D g1准确保留前一认定，没有升级为最高法院终审。B-P g1同样保留分隔和独占事实，但g4又要求明确SUBLET或ASSIGN，忽略法律包中PART_WITH_POSSESSION已是三方式择一之一，reason再据此制造模式缺口；这是条件整合及内部不一致，不是原文没有交出占有认定。
D把1965-01-12起诉日期用于证明转移在1952以后；B-P更进一步称分隔当天发生。来源没有该事件日期，起诉日期只能给先前事件上界，不能给所需1952下界。B提议d2已经填入虚构分隔日期，coverage又说模式/共同经营未裁定，最终复述对应错误；这是传播线索，不能据内容相似断言完整因果机制。
许可出自租户律师关于父亲允许两儿子占用的主张，不是房东许可。D g3较正确区分主张，但g4 point错写房东一般许可；B-P g3引用不对应的p0001.s002/s003，g4称房东主张许可。B提议t2将房东写成租户，x1/x2受让人也写成房东；最终没有明确照抄该错误人名，不能说每项提议错误都传播。两边reason将肯定的written consent说成腾退必要条件，未正确解释法条要求的是without consent以及该事实未定如何影响结论。
真实缺口包括转移是否在1952后、房东具体书面同意/缺乏同意、历史法条适用范围。UNDETERMINED可以有依据，但当前解释混入虚构日期和条件错误，两份不能认证为完整正确。D遗漏共同经营被否定；B-P g4保留该认定，却未将它与已确认交出占有及择一法条正确结合。两边未展开否定共同经营的具体证据；审阅没有只看模型引用的段落。

1134266：B-P有局部收益，仍有遗漏和改写
p0002.s001明确registered lease deed，D g3反写unregistered，并把69305未登记租约条款不可采规则搬到本案；来源也没给出目标存在该许可条款。D g2/reason还称没有证据证明Bombay High Court批准合并，直接反于p0002.s003明确31.12.1981批准及租赁/占有等权利转归Indian Company。法律效果争议不能使批准事件缺失。D g1把房东无书面同意指控及未展示反证，当成absence established，混淆主张和事实。
B-P g1准确将无同意归为房东指控，g3保留批准及归属，不再套用不可采规则，reason认识到RC-05的程序性规则不能证明合并例外。这是相对D具体可核验的改善。它仍在g4增加租户把法院批准当房东默示同意的说法，原文主张的是FERA强制合并使S14不适用，不是房东同意。提议c3把法院批准列入consents且保留未决字段，与最终改写有对应；不能确定收益/错误全归结构形式。
两边未保留ARC驳回、Tribunal反转命令腾退、Delhi High Court维持的明确层级变化。B-P也未具体处理房东“仅要求降股本、合并是可选择行为”的主要反驳，且没有明确registered事实。B-P g3承认归属，reason强调没有法院确认parting，必须区分既有归属事件和未决S14法定定性；不能直接将vesting等同parting，也不能将定性未决说成没有归属事实。因此保留解释争议，不强行判此为同69305一样的直接矛盾。
本案包内只有特定书面同意、未登记条款和迟提出家庭许可等规则，确实没有完整合并/法定强制的S14解释；目标自己的RC-01/RC-02没有恢复。无法判断可包含真实法源覆盖缺口，但不能用没有目标最终裁判作为唯一理由，更不能要求模型猜回历史判决。

是否复现69305问题与方法投入
另外两案仍出现许可主体/主张归属混淆、已知事实被改写为缺失、条件极性和内部不一致；同类错误不只出现在69305。但661475两边确实保留下级交出占有认定，1134266 B-P保留法院批准，不应概括成每份答案都抹去所有法院事实。没有一份在全部关键依据上被确认可靠；也不能因为全部UNDETERMINED就判定全部错误。661475的时间/同意缺口、1134266合并法律解释缺口都应保留。
两案的收益方向不同：661475增加前置提议没有收益并新增严重错误，1134266减少D明确误读而成本增加且仍有语义问题。因此暂不选赢家，不设置强制结构化前置，不为表现较差案调整提示。当前证据支持报告共同理解/整合问题，不能证明结构化普遍无效、D普遍更好或裁判能力已验证。

交付与停止
四份完整答案见final-answer-slots.md及final-answers.json；两份原样提议见intermediates；comparison-table.json/csv区分技术状态、原文支持、已确认错误、遗漏/矛盾、真实缺口、结论及含抽取成本。final-source-review.json保存唯一集中来源审阅，标记模型辅助来源审阅，非人工金标准；关键引用逐段恢复于restored-final-sources.json。完整来源、既有法律包/检索、实际prompt/schema、raw、token IDs、mask轨迹和元数据均保留。offline-checks仅验证来源地址/提议结构/连接限制，未供最终模型读取，也不认证语义。
{len(start['historical_outputs'])}历史文件和{len(start['preexisting_code_hashes'])}原有源码文件原字节不变；旧V12日志失败/null不修补。更新实验索引、状态及本地审阅包后核验完整性，不提交、不推送，不重跑69305、不换模型、不增加字段/法源/样本、不启动下一轮。本轮结束。
'''
(ROOT/'report-zh.txt').write_text(report,encoding='utf-8')
print(json.dumps({'report':str(ROOT/'report-zh.txt'),'decision':review['decision'],'calls':6}))
