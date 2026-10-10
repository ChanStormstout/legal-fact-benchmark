# V16 来源到限定推导的轨迹

本轮六个固定请求的根规则均为OPEN_TEXT。前提连接及来源可审阅，开放法律解释未由程序执行。技术失败为null，UNKNOWN只用于真实保存的分析。正式法律批准缺失。

## 136109 / Q1::R2

D=UNKNOWN，P=null，R=null。提议页面称已生成文件，但预览和下载均无法取得内容，用户也确认不能下载。P为null，未提交依赖审阅；D保留原P的对象／角色及OPEN_TEXT阻碍。

没有自动提议正文，不能评价本案的语义连接正确性，不能以文件生成声称替代完整JSON；未将技术失败写成UNKNOWN。

文件访问失败属于工程／传输问题，没有可评价的自然语义错误。

[完整来源与逐步记录](paths/136109/trace.json)

- A01 / R2.P1：The compromise contemplates a perpetual underlease of the disputed 500 bighas between the Singhs and the Deoshis, a form of tenancy that would otherwise fall within the duration addressed by section 17(1)(d).。原提议=null；条件性执行前提=null；独立判断=null；审阅后执行前提=null；审阅后独立判断=null。阻碍：未取得提议，结构检查不可评价。
- A02 / R2.P2：The compromise itself effects an actual demise creating a present and immediate interest in the disputed land upon its execution.。原提议=null；条件性执行前提=null；独立判断=null；审阅后执行前提=null；审阅后独立判断=null。阻碍：未取得提议，结构检查不可评价。
- A03 / R2.P3：The contemplated underlease is expressly conditional upon the Singhs' payment of Rs. 8,000 to Kumar within two months, with execution and possession restricted until that payment.。原提议=null；条件性执行前提=null；独立判断=null；审阅后执行前提=null；审阅后独立判断=null。阻碍：未取得提议，结构检查不可评价。
- A04 / R2.P1：The compromise contemplates a perpetual underlease of the disputed 500 bighas between the Singhs and the Deoshis, a form of tenancy that would otherwise fall within the duration addressed by section 17(1)(d).。原提议=null；条件性执行前提=null；独立判断=null；审阅后执行前提=null；审阅后独立判断=null。阻碍：未取得提议，结构检查不可评价。
- A05 / R2.P2：The compromise itself effects an actual demise creating a present and immediate interest in the disputed land upon its execution.。原提议=null；条件性执行前提=null；独立判断=null；审阅后执行前提=null；审阅后独立判断=null。阻碍：未取得提议，结构检查不可评价。
- A06 / R2.P3：The contemplated underlease is expressly conditional upon the Singhs' payment of Rs. 8,000 to Kumar within two months, with execution and possession restricted until that payment.。原提议=null；条件性执行前提=null；独立判断=null；审阅后执行前提=null；审阅后独立判断=null。阻碍：未取得提议，结构检查不可评价。

## 885778 / Q1::R2

D=UNKNOWN，P=UNKNOWN，R=null。自动提议为Ex.181可靠性、原件控制与未出示、有限发回后错误接纳但后续未排除分别提供对象和原文见证；三个前提结构通过，条件性TRUE。独立审阅已完成但正文为空，R为null。

法院关于Ex.181的证据评价是外部语义前提，不是程序查看原始签字往来。L164高院反论、L154发回范围及L194原接纳不当均保留；没有用最终撤销高院结果循环证明证据可靠。R缺失不由主session来源复核代替。

未确认决定性来源误读。A03使用SUPREME_COURT_DISPOSITION状态但内容实为L194对证据接纳的最终阶段解释，命名宽泛；它不是以裁判结果证明自身。该项无需计成确定法律错误。

[完整来源与逐步记录](paths/885778/trace.json)

- A01 / R2.P1：Ex. 181 was a reliable certified Government record reproducing or recounting the original written offer, signed acceptance, Government sanction, and material contractual terms.。原提议=TRUE；条件性执行前提=TRUE；独立判断=TRUE；审阅后执行前提=UNKNOWN；审阅后独立判断=UNKNOWN。阻碍：无结构阻碍。
- A02 / R2.P2：The original contractual correspondence was within the possession or power of the plaintiffs or their predecessors and was not produced despite notice, while their pleadings and testimony showed knowledge of it.。原提议=TRUE；条件性执行前提=TRUE；独立判断=TRUE；审阅后执行前提=UNKNOWN；审阅后独立判断=UNKNOWN。阻碍：无结构阻碍。
- A03 / R2.P3：Although Ex. 181 was introduced after remand at an improper stage, the High Court did not reject it and the Supreme Court could not exclude it at its own stage of the case.。原提议=TRUE；条件性执行前提=TRUE；独立判断=TRUE；审阅后执行前提=UNKNOWN；审阅后独立判断=UNKNOWN。阻碍：无结构阻碍。

## 1870386 / Q1::R1

D=UNKNOWN，P=UNKNOWN，R=UNKNOWN。A02正确根据L150、L156及L159–161否定全部利益仅加速归于下一个继承人；得到分范围审阅接受并保留FALSE。A03的reversioners_at_1894新变量及单一人列表被独立审阅拒绝，其他角色和用途仍接受。

L148支持放弃经营意图及文书覆盖，不能从法律上无完全surrender推出主观欺诈。A01/A03模型FALSE却complete=false，独立审阅接受的是法律总量不足的狭义否定；程序按完整前提覆盖合同仍UNKNOWN。两者含义差别记录，不强改为AND，也不假报该否定已经进入执行。L149女性继承人可能成立、L166真正先surrender后转移可成立、L174先例仅假设正确，以及保留的estoppel问题均未被吞掉。

一个确定的地址合同错误：A03发明未声明变量。它还把具体next heir的身份用作reversioners集合角色而未证明该集合参与反设备条件；此语义适用范围不足与地址错误分开。A01/A03负向充分性与完整覆盖的分歧属于监督／接受含义争议，不算两项确定错判。

[完整来源与逐步记录](paths/1870386/trace.json)

- A01 / R1.P1：Chanchamma, while holding Narayanappa's estate as his widow, bona fide and totally renounced her entitlement to hold that estate.。原提议=FALSE；条件性执行前提=UNKNOWN；独立判断=UNKNOWN；审阅后执行前提=UNKNOWN；审阅后独立判断=UNKNOWN。阻碍：WHOLE_PREMISE_COVERAGE_NOT_CLAIMED_COMPLETE, COMPONENT_COVERAGE_WITNESS_INCOMPLETE。
- A02 / R1.P2：The entire interest accelerated by Chanchamma's purported surrender would devolve upon Narayanappa's next heir by inheritance, rather than vest jointly in that heir and a stranger to his inheritance.。原提议=FALSE；条件性执行前提=FALSE；独立判断=FALSE；审阅后执行前提=FALSE；审阅后独立判断=FALSE。阻碍：无结构阻碍。
- A03 / R1.P3：The purported surrender was a bona fide total withdrawal and not merely a device to divide the widow's estate with reversioners.。原提议=FALSE；条件性执行前提=UNKNOWN；独立判断=UNKNOWN；审阅后执行前提=UNKNOWN；审阅后独立判断=UNKNOWN。阻碍：WHOLE_PREMISE_COVERAGE_NOT_CLAIMED_COMPLETE, COMPONENT_COVERAGE_WITNESS_INCOMPLETE, BINDING:reversioners:UNKNOWN_ROLE_OR_VARIABLE_ADDRESS。

## 180091 / Q1::R1

D=UNKNOWN，P=UNKNOWN，R=UNKNOWN。正确保留Gaya审判庭与Patna高院的共同认定，及最高法院对书证缺失、口头证据可信度和例外审查的评价。六个地址的独立条件性判断TRUE；A03/A06进入执行前提并经审阅接受，其余四项仍有claimant引文定位歧义。

L116同一段两次the plaintiff firm，短引文不是唯一位置；caption及L114见证本身有效但当前合同要求绑定所列见证全部可定位，故阻止相应执行。独立审阅原始ACCEPT不被篡改，程序的定位后UNRESOLVED另存。它不证明人物身份错误。原文1945/1941日期不一致保留；销售／part performance失败不等于借款替代请求必然失败，选定规则不处理后者。

四处重复的短引文定位歧义是一案的见证选择／来源定位障碍，不是四个独立身份错误。未确认本轮把当事人销售主张升级为法院认定。

[完整来源与逐步记录](paths/180091/trace.json)

- A01 / R1.P1：The trial court and the High Court made concurrent factual findings that the plaintiff failed to prove a concluded sale agreement for the Gaya house and that possession was not delivered in part performance of such an agreement.。原提议=TRUE；条件性执行前提=UNKNOWN；独立判断=TRUE；审阅后执行前提=UNKNOWN；审阅后独立判断=TRUE。阻碍：BINDING:claimant:OBJECT_WITNESS_NOT_VERIFIED。
- A02 / R1.P2：The controversy over the alleged sale agreement principally depended on the assessment of oral evidence and witness credibility, with no written agreement produced in proof of the asserted contract.。原提议=TRUE；条件性执行前提=UNKNOWN；独立判断=TRUE；审阅后执行前提=UNKNOWN；审阅后独立判断=TRUE。阻碍：BINDING:claimant:OBJECT_WITNESS_NOT_VERIFIED。
- A03 / R1.P3：The Supreme Court found no exceptional, unusual, legal, or procedural reason in this appeal warranting departure from the normal practice of accepting the concurrent factual findings.。原提议=TRUE；条件性执行前提=TRUE；独立判断=TRUE；审阅后执行前提=TRUE；审阅后独立判断=TRUE。阻碍：无结构阻碍。
- A04 / R1.P1：The trial court and the High Court made concurrent factual findings that the plaintiff failed to prove a concluded sale agreement for the Gaya house and that possession was not delivered in part performance of such an agreement.。原提议=TRUE；条件性执行前提=UNKNOWN；独立判断=TRUE；审阅后执行前提=UNKNOWN；审阅后独立判断=TRUE。阻碍：BINDING:claimant:OBJECT_WITNESS_NOT_VERIFIED。
- A05 / R1.P2：The controversy over the alleged sale agreement principally depended on the assessment of oral evidence and witness credibility, with no written agreement produced in proof of the asserted contract.。原提议=TRUE；条件性执行前提=UNKNOWN；独立判断=TRUE；审阅后执行前提=UNKNOWN；审阅后独立判断=TRUE。阻碍：BINDING:claimant:OBJECT_WITNESS_NOT_VERIFIED。
- A06 / R1.P3：The Supreme Court found no exceptional, unusual, legal, or procedural reason in this appeal warranting departure from the normal practice of accepting the concurrent factual findings.。原提议=TRUE；条件性执行前提=TRUE；独立判断=TRUE；审阅后执行前提=TRUE；审阅后独立判断=TRUE。阻碍：无结构阻碍。

## 732701 / Q1::R3

D=UNKNOWN，P=UNKNOWN，R=UNKNOWN。正确连接Trustees、1925年Municipality承继、Princess Street Estate、New Sitaram Building及Block B/2；两条替代路线四个前提均条件性TRUE并经分范围审阅接受。区分Society的lessee利益与法院认可的lessor所有权。

L141租户主张、L178–180长期租约／自建楼及高院相反解释保留；L183–191的合同解释为最高法院外部判断。不能推广成所有承租人建楼都归出租人；特定历史合同和法条版本不变。根OPEN_TEXT未程序执行。

集中对照未确认影响所选路径的重大新错误；两种Block B/2描述的同一对象依据明确，未凭名称相似合并。

[完整来源与逐步记录](paths/732701/trace.json)

- A01 / R3.P1：The claimed owner is Government or a local authority, and the relevant authority's ownership or succession is established in the case history.。原提议=TRUE；条件性执行前提=TRUE；独立判断=TRUE；审阅后执行前提=TRUE；审阅后独立判断=TRUE。阻碍：无结构阻碍。
- A02 / R3.P2：The specific premises for which statutory protection is claimed belong to that qualifying authority, including the building or part of the building at issue, notwithstanding the lessee's rights of enjoyment.。原提议=TRUE；条件性执行前提=TRUE；独立判断=TRUE；审阅后执行前提=TRUE；审阅后独立判断=TRUE。阻碍：无结构阻碍。
- A03 / R3.P1：The claimed owner is Government or a local authority, and the relevant authority's ownership or succession is established in the case history.。原提议=TRUE；条件性执行前提=TRUE；独立判断=TRUE；审阅后执行前提=TRUE；审阅后独立判断=TRUE。阻碍：无结构阻碍。
- A04 / R3.P2：The specific premises for which statutory protection is claimed belong to that qualifying authority, including the building or part of the building at issue, notwithstanding the lessee's rights of enjoyment.。原提议=TRUE；条件性执行前提=TRUE；独立判断=TRUE；审阅后执行前提=TRUE；审阅后独立判断=TRUE。阻碍：无结构阻碍。

## 948916 / Q1::R1

D=UNKNOWN，P=UNKNOWN，R=UNKNOWN。四条既有替代路线都连接同一1945-03-10程序遗漏、1945-04-25恢复令；十二地址均条件性TRUE，84个局部审阅决定保留。明确区分下级恢复令、最高法院采纳的未给机会判断，以及反方律师的疏忽／时效反论。

L200–203高院先前要求实际可采取措施的反论与L225–227最高法院不需猜测的处理均保留；不能用未给机会证明债务余额、执行实体权利或一般时效可被151条覆盖。原P含对方争辩的用途仅REPORT_ASSERTION，新的法院判断来自另提见证，不假装旧主张支持发生事实。根OPEN_TEXT保留。

集中审阅未确认决定性陈述地位升级；四路线重复同一历史事件，十二地址／84决定不算十二或84案。

[完整来源与逐步记录](paths/948916/trace.json)

- A01 / R1.P1：The executing judge rejected the decree-holder's request for adjournment and dismissed the pending execution case in the same order.。原提议=TRUE；条件性执行前提=TRUE；独立判断=TRUE；审阅后执行前提=TRUE；审阅后独立判断=TRUE。阻碍：无结构阻碍。
- A02 / R1.P2：Before dismissal, the decree-holder's pleader was not informed that adjournment had been refused and was not afforded an opportunity to make submissions regarding the execution case.。原提议=TRUE；条件性执行前提=TRUE；独立判断=TRUE；审阅后执行前提=TRUE；审阅后独立判断=TRUE。阻碍：无结构阻碍。
- A03 / R1.P3：The executing judge used section 151 to rectify his own identified procedural omission in dismissing the execution case.。原提议=TRUE；条件性执行前提=TRUE；独立判断=TRUE；审阅后执行前提=TRUE；审阅后独立判断=TRUE。阻碍：无结构阻碍。
- A04 / R1.P1：The executing judge rejected the decree-holder's request for adjournment and dismissed the pending execution case in the same order.。原提议=TRUE；条件性执行前提=TRUE；独立判断=TRUE；审阅后执行前提=TRUE；审阅后独立判断=TRUE。阻碍：无结构阻碍。
- A05 / R1.P2：Before dismissal, the decree-holder's pleader was not informed that adjournment had been refused and was not afforded an opportunity to make submissions regarding the execution case.。原提议=TRUE；条件性执行前提=TRUE；独立判断=TRUE；审阅后执行前提=TRUE；审阅后独立判断=TRUE。阻碍：无结构阻碍。
- A06 / R1.P3：The executing judge used section 151 to rectify his own identified procedural omission in dismissing the execution case.。原提议=TRUE；条件性执行前提=TRUE；独立判断=TRUE；审阅后执行前提=TRUE；审阅后独立判断=TRUE。阻碍：无结构阻碍。
- A07 / R1.P1：The executing judge rejected the decree-holder's request for adjournment and dismissed the pending execution case in the same order.。原提议=TRUE；条件性执行前提=TRUE；独立判断=TRUE；审阅后执行前提=TRUE；审阅后独立判断=TRUE。阻碍：无结构阻碍。
- A08 / R1.P2：Before dismissal, the decree-holder's pleader was not informed that adjournment had been refused and was not afforded an opportunity to make submissions regarding the execution case.。原提议=TRUE；条件性执行前提=TRUE；独立判断=TRUE；审阅后执行前提=TRUE；审阅后独立判断=TRUE。阻碍：无结构阻碍。
- A09 / R1.P3：The executing judge used section 151 to rectify his own identified procedural omission in dismissing the execution case.。原提议=TRUE；条件性执行前提=TRUE；独立判断=TRUE；审阅后执行前提=TRUE；审阅后独立判断=TRUE。阻碍：无结构阻碍。
- A10 / R1.P1：The executing judge rejected the decree-holder's request for adjournment and dismissed the pending execution case in the same order.。原提议=TRUE；条件性执行前提=TRUE；独立判断=TRUE；审阅后执行前提=TRUE；审阅后独立判断=TRUE。阻碍：无结构阻碍。
- A11 / R1.P2：Before dismissal, the decree-holder's pleader was not informed that adjournment had been refused and was not afforded an opportunity to make submissions regarding the execution case.。原提议=TRUE；条件性执行前提=TRUE；独立判断=TRUE；审阅后执行前提=TRUE；审阅后独立判断=TRUE。阻碍：无结构阻碍。
- A12 / R1.P3：The executing judge used section 151 to rectify his own identified procedural omission in dismissing the execution case.。原提议=TRUE；条件性执行前提=TRUE；独立判断=TRUE；审阅后执行前提=TRUE；审阅后独立判断=TRUE。阻碍：无结构阻碍。
