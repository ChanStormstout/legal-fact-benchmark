# -*- coding: utf-8 -*-
"""The single concentrated, post-batch source review. Never imported by runners."""
from irac_semantic_v6 import R, inputs, read, save


def item(key, where, refs, finding, propagation=None):
    return {'id':key,'output_locations':where,'source_ids':refs,'judgment_zh':finding,
            'propagation':propagation,'semantic_reference':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD'}


def build():
    assert (R/'run-summary.json').exists()
    assert not (R/'final-source-review.json').exists()
    result={
      'reference_role':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD', 'review_rounds':1,
      'after_batch_complete':True,'web_calls':0,'new_annotations':0,
      'scope':'Four complete final answers plus decisive P evidence, reviewed against every allowed case passage and given law; no full-field gold, historical verdict target or new source.',
      'decision':'STOP_ADDING_PROMPTS_OR_FIELDS_TO_CURRENT_9B; PAUSE_MANDATORY_P; PROPOSE_BUT_DO_NOT_RUN_STRONGER_MODEL_SAME_INTERFACE',
      'decision_zh':'本轮没有取得足以保留强制中间提议的完整回答净收益。E工程验收通过；两案M仍有事实安排、来源对应或证据用途错误，四份最终回答均未通过L。112400的B新增择一路径被无关缺口阻止等问题；188721101的B有局部纠错，但重要共同误读、遗漏及无依据的法律后果仍在。暂停向当前9B流程继续添加提示或字段，暂停强制P；A仅保留为低成本开发基线，不能当作已可靠的法律工具。下一轮最有信息量的是另行授权后，用相同接口和材料做更强模型A/B对照；本轮不执行。',
      'cases':{
       '112400':{
        'M':'NOT_PASSED',
        'proposal_summary':'7条记录均保存，但把同一请求的两项后续法院认定另立为安排2、3，全部8条条件分析又只挂在安排1。部分证据序号错位，住宅用途及全称的无其他住所被无依据确认；以产权文件和家属定义制造额外缺口。错误限制将明确反对真实需求的记录3、4都阻止使用。',
        'methods':{
         'A':{'L':'NOT_PASSED','supported':'保留楼层、租赁日期、房东所有权、早期不真实需求认定及发回后住所不适合的认定；识别本人自住路线和给定法律定义的覆盖限制。',
              'errors':'把租赁存在说成住宅用途明确；把已知现住房不适合扩大成不存在其他适宜住所。条件binding分别用b1至b6及条件标题，未清楚表达同一请求中的实际安排。',
              'omissions':'C06标SUPPORTED，reason又称C06 unresolved，内部不一致。虽引用发回后认定，未明确说明维持早期不真实需求判断与后续材料之间的评价假设；这不等于后续认定必然推翻早期结论。'},
         'B':{'L':'NOT_PASSED','supported':'保留早期法院否定真实需求的方向、所有权和后续不适合认定；消除了A关于C06状态的明文自相矛盾。',
              'errors':'重复住宅用途及无其他住所的无依据确定判断；继承P的“家庭五人”，原文是四名列名成年人及复数children；将家属／依赖定义缺失用于阻止含本人路线的整个C03，未处理已给定的SELF择一关系。',
              'omissions':'没有纠正P的安排拆分、住宅用途及量词扩大；intermediate_correction写None。最终b1至b6仍按条件拆分。较A没有形成可靠的完整分析改善。'}},
        'real_gaps':['允许段落未明确原租赁是否为住宅用途；房东提出住宅需要不能代替原租约用途。',
                     '特定现住房不适合，不能完整证明没有其他可用且适宜的住宅。',
                     '给定法条没有进一步真实性、依赖及上诉审查标准；不能因此抹去明确家属关系、所有权或本人路线。'],
        'comparison':'B修复A的一处状态／理由矛盾，但保留两项决定性过度推断，并新增本人择一路径被家属缺口封锁等问题；未见净改善。',
        'findings':[
          item('112-SOURCE-USE',['A:C01','P:conditions[0]','B:C01'],['IK-112400:L123:span1','IK-112400:L124:restored-v2'],
               'L123仅说明1964年1月22日租赁一楼及租金；P和B声称lease document explicitly states residential purposes，允许文本未记载该用途，也未提供原租约文书独立检验。A存在同类错误。','P_ERROR_REPEATED_BY_B; ALSO_PRESENT_IN_A'),
          item('112-QUANTIFIER',['A:C06/reason','P:conditions[7]','B:C06'],['IK-112400:L139:restored-v2','IK-112400:L140:restored-v2'],
               '明确记载的范围是房东正居住的portion不适合，非全部其他住所。A和B均扩大为无其他适宜住所；P还说current premises are the only suitable ones，与不适合相反。B没有复述最后这句，但保留核心量词扩大。A的SUPPORTED与reason中的unresolved矛盾在B中消失。','PARTIAL_CORRECTION_WITH_SHARED_CORE_ERROR'),
          item('112-ALTERNATIVE',['A:C03','P:conditions[2:5]','B:C03'],['IK-112400:L124:restored-v2','IK-112400:L139:restored-v2','IK-18143401:L41:historical-e'],
               'SELF路线不要求先证明家属依赖。P借不存在独立title deed使SELF未决，同时又把C04所有权判SUPPORTED；还说家属关系未定义，而L139列出妻、儿子、儿媳、孙辈。B未带入title deed要求，却仍让家属及依赖定义缺失阻止整个C03；A至少保留本人路线。这里不把本人路线主张等同于已证明真实需要。','P_GAP_PROPAGATED_IN_DIFFERENT_FORM; B_NEW_RELATIVE_TO_A'),
          item('112-ARRANGEMENT',['P:arrangements[1:3]','P:conditions[3:5,7]'],['IK-112400:L137:context-v4','IK-112400:L138:context-v4','IK-112400:L139:restored-v2','IK-112400:L140:restored-v2'],
               '两项法院认定被另列为实际安排；R5是发回，却在家属和住房条件被说成后续Tribunal报告；R6为住房不足，却被当作R7不适合的记录。有效数组编号不证明用途描述与对应文本相符。','SEMANTIC_MAPPING_ERRORS_RETAINED; OFFLINE_CHECKS_NOT_IN_B'),
          item('112-RESTRICTION',['P:limitations[0]','P:checks conditions C02','B:C02'],['IK-112400:L127:restored-v2','IK-112400:L130:span6'],
               'P因为R3、R4否定真实需求而限制它们用于该条件。这是模型对“反证”的用途误解。程序按局部限制保留raw REFUTED、离线组合前提UNRESOLVED，没有把OPPOSE计为满足。B未接收这些检查，仍直接使用反对认定；不能称为程序促成的纠正。','LIMITATION_ERROR_NOT_ENFORCED_ON_B'),
          item('112-STAGE',['A:C02/reason/gaps','B:C02/reason'],['IK-112400:L127:restored-v2','IK-112400:L130:span6','IK-112400:L139:restored-v2','IK-112400:L140:restored-v2'],
               '两者大体正确归属早期不真实需求认定，没有把它改成新的High Court最终采纳。但把早期REFUTED直接代入请求结论时，没有充分限定维持旧判断的假设及后来认定的影响。预测DENY本身不据历史结果判错；不足在理由及范围未交代完整。')
        ]},
       '188721101':{
        'M':'NOT_PASSED_WITH_PARTIAL_ARRANGEMENT_GAIN',
        'proposal_summary':'5条记录独立保存，形成一个兄弟使用15号铺的安排，未再把诉讼阶段各自当作安排；但父亲先前安排仍遗漏。12项用途有4项引用不存在的R6被局部隔离；另有合法编号指错记录、雇佣证言被写成承认、主张租金支付被补造等语义错误，原P仍完整送入B。',
        'methods':{
         'A':{'L':'NOT_PASSED','supported':'保留原审认定可撤销许可及三条法定路线的区别，使用给定先例的法律占有／全部权利标准；雇佣领薪在一处仍以证言记载。',
              'errors':'将1987年租赁日期当作具体交出占有日期，并虚构原审作过这一日期认定；虚构房东明确主张没有书面同意；gaps把同意取得主体反写为landlord，并引入给定法源没有的estoppel。',
              'omissions':'遗漏工资凭证未证明、邻居说经营者不是承租人、6号铺与柜台转移，以及父亲先前安排。主要反论缩成笼统房东指控，不能充分支持维持原审的预测。'},
         'B':{'L':'NOT_PASSED','supported':'不再虚构法院确定转移日期；C05正确保留书面同意材料不足，未再提出房东取得同意或estoppel；明确承认原审许可判断尚在上诉中。回到L83支持撤销权与法律占有，部分绕开P的错序号。',
              'errors':'仍称L72明确把转移发生时间写成06.01.1987，混淆租赁与后续行为；C02把未经证明的领薪证言强化为salary payment足以排斥租金关系。opposition仍添入without consent主张，和C05无此信息的解释不协调；reason又称未决同意缺口prevents a grant，未说明相应证明责任或预测假设。',
              'omissions':'与A共同漏掉工资凭证未证明、邻居的相反证言、6号铺／柜台及父亲安排。没有完整解释这些内容如何影响继续维持原审；intermediate_correction为None，不能据回引正确段落认定模型系统性校正了P。'}},
        'real_gaps':['书面同意或明确否定书面同意的记录未提供。',
                     '精确转移日期未明确；若接受房东先租后转的叙述，可条件化判断晚于1952年，但不能把租赁日写成已确认的转移日。',
                     '父亲先前安排细节有限；雇佣、独立经营与控制权的相反证据尚待评价；给定材料未含完整上诉审查或证明责任规则。'],
        'comparison':'B避免A的部分归属及同意方向错误，有具体局部价值；但日期错读未解决，重要共同反论仍漏，并产生无依据的“未决就阻止授予”表述，尚不能认定完整分析净收益值得额外阶段。',
        'findings':[
          item('188-DATE',['A:C01','P:conditions[0]','B:C01'],['IK-188721101:L72:restored-v2'],
               '06.01.1987修饰房东将店铺出租给Ramesh Kumar；随后才描述先父亲后兄弟。A增造trial court found arrangement occurred on this date；B移除法院归属但仍称房东明确主张该日转移。P保留未决但同样连接错误日期；未决标签不修正含义。','A_FABRICATED_COURT_ATTRIBUTION_REMOVED; EVENT_DATE_ERROR_PERSISTS'),
          item('188-SALARY',['P:records[1:3]','P:C02/C04/C06','A:C04','B:C02/C06'],['IK-188721101:L74:restored-v2','IK-188721101:L80:restored-v2','IK-188721101:L81:restored-v2'],
               'L74只有否认转租及承租人自称占用，没有雇佣工资；工资证言在L81。P将承认的经营与持钥匙扩为承认employment，并遗漏salary vouchers not proved。B把salary payment用于排斥租金关系；A虽说witnesses testified也未保留凭证限制。','P_INCOMPLETE_OR_OVERSTATED_EVIDENCE_PROPAGATED'),
          item('188-CONSENT',['A:C05/gaps','P:C05','B:C05/opposition/reason'],['IK-188721101:L72:restored-v2','IK-188721101:L73:restored-v2','LAW:S02:DRC14:1b'],
               '允许范围未明确记载无书面同意的主张；Slum Authority准许提起程序并非出租人同意交易。B正确保留同意未知并删除A的主体倒置及estoppel，但opposition仍写without consent且reason将未决直接说成阻止grant。给定法条要求缺乏书面同意，不单独提供该证据缺口的举证裁判规则。','PARTIAL_GAIN_AND_NEW_UNSUPPORTED_LEGAL_EFFECT'),
          item('188-OMISSIONS',['A:opposition/reason','P:records/arrangements','B:opposition/reason'],['IK-188721101:L72:restored-v2','IK-188721101:L73:restored-v2','IK-188721101:L80:restored-v2','IK-188721101:L81:restored-v2'],
               '两份最终答案都未处理父亲先前安排、兄弟独立承租6号铺及柜台迁移、邻居证言实际经营者不是Ramesh、工资凭证未证明。P保存部分邻居证言，但B没有将其作为对原审许可判断的重要反论；材料已送达，不能称法源检索或输入缺段。','COMMON_DECISIVE_COVERAGE_FAILURE'),
          item('188-MAPPING',['P:conditions[1,2,3,5]','P:checks-full import_quarantine','B:C03/C04/C06'],['IK-188721101:L80:restored-v2','IK-188721101:L81:restored-v2','IK-188721101:L83:restored-v2','IK-188721101:L84:restored-v2'],
               'P只有R1至R5，却四次引用R6；R5实际为原审家庭成员推论，却被指作经营证言，R3证言又被指作原审许可认定。前者由程序隔离，后两者编号合法但含义不符。B回引L83支持许可，说明最终原文仍能补充依据；检查块没进入B，不能把此归因于程序。','LOCAL_INVALID_USES_ISOLATED_OFFLINE; B_SOURCE_REREADING_ONLY'),
          item('188-ALTERNATIVES',['A:reason','B:reason'],['IK-188721101:L83:restored-v2','IK-190902:L109','IK-190902:L110','IK-190902:L112'],
               'A/B本轮都逐一谈了转租、让与、交出占有，未出现仅一条路线失败就形式上否定其他路线的问题；原审许可认定可成为条件化预测依据。主要不足是对相反事实及原审是否应维持的处理，不要求猜回排除的最终判决。')
        ]}
      }}
    # Exact address restoration for inspection, not new source collection.
    for cid,c in result['cases'].items():
        m,t,law,sm=inputs(cid);sources=dict(m['sources']);sources.update({s['source_id']:s for s in law})
        c['reviewed_allowed_case_ids']=list(m['sources'])
        c['reviewed_law_ids']=[s['source_id'] for s in law]
        c['source_evidence']={s:sources[s] for f in c['findings'] for s in f['source_ids']}
    save(R/'final-source-review.json',result)
    print('One concentrated source review saved')


if __name__=='__main__':build()
