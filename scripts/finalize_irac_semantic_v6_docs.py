# -*- coding: utf-8 -*-
"""Local publication metadata only; never stage, commit or push."""
import json
from pathlib import Path
from irac_semantic_v6 import R, read, save


def main():
    report=str(R/'report-zh.txt')
    summary='两案6次本地调用全部完成，12.44分钟，2份P及4份最终回答，无重试、网页或C。23项相关测试、17个真实tokenizer样例通过；E通过，M/L仍未通过。112400 B新增择一分支及来源问题，188721101 B局部纠错但未形成可靠完整净收益。暂停给当前9B增加提示／字段及强制P；2595项历史文件和旧IRAC源码保留，未读SEALED、未提交推送。'
    policy=read('docs/repository-artifacts.json')
    links=[('中文报告','report-zh.txt'),('逐案比较','case-comparison.csv'),('完整回答与P','answers.md'),
           ('一次来源审阅','final-source-review.json'),('E/M/L','acceptance.json'),('逐调用成本','call-costs.csv'),
           ('冻结配置','freeze/config.json'),('工程验收','engineering/acceptance.json'),
           ('实际输入检查','delivery-validation.json'),('历史保留检查','preservation-after.json')]
    current={'contract_version':2,'review_kind':'IRAC_SEMANTIC_INTERFACE_V6_COMPLETED',
        'title':'IRAC V6 语义接口修复后的两案完整流程比较','report':report,'summary':summary,
        'status':'COMPLETED_E_PASS_M_L_NOT_PASSED_STOPPED_LOCAL_ONLY',
        'links':[{'label':label,'path':str(R/path)} for label,path in links]+[{'label':'实现说明','path':'docs/IRAC_SEMANTIC_INTERFACE_V6.md'}],
        'review_request':'只读审阅V6实际源码、冻结输入及四份完整回答。核对证据相关性与条件真值是否分开，记录与多安排用途是否独立，法源角色与限制是否局部检查，最终空答／漏答／重复请求是否拒收。区分E工程与M安排／用途、L完整法律分析。B只读原始P，不读检查块，不能把B改进归因于程序提示。检查112400住宅用途／住所量词／本人择一路线，188721101租赁日期／反论与工资凭证／同意未知的法律后果；未参与输入的评价文件不能冒充受测来源。既有预测全为DENY不构成gold。审阅不授权新增运行、改答案或发布。'}
    policy['current_review']=current
    for p in ['scripts/report_irac_semantic_v6.py','scripts/review_irac_semantic_v6.py','scripts/finalize_irac_semantic_v6_docs.py']:
        if p not in policy['code_review_files']:policy['code_review_files'].append(p)
    save('docs/repository-artifacts.json',policy)
    cat=read('docs/EXPERIMENTS.json')
    assert not any(x['id']=='irac-semantic-interface-v6' for x in cat['experiments'])
    cat['experiments'].append({'id':'irac-semantic-interface-v6','role':'two_exposed_cases_semantic_interface_development',
                             'report':report,'note':summary})
    save('docs/EXPERIMENTS.json',cat)
    readme=Path('README.md');text=readme.read_text()
    assert text.startswith('# 当前工作：IRAC V5')
    text=text.replace('# 当前工作：IRAC V5 两案完整流程验收已完成','# 历史：IRAC V5 两案完整流程验收',1)
    intro='# 当前工作：IRAC V6 两案完整比较已完成\n\n'+summary+' 见[中文报告]('+report+')、[逐案比较]('+str(R/'case-comparison.csv')+')、[完整回答]('+str(R/'answers.md')+')与[实现说明](docs/IRAC_SEMANTIC_INTERFACE_V6.md)。两案仍是开发材料，结果不代表法律准确率或整个图方法的有效性；下一轮仅提出同接口更强模型比较，尚未执行。\n\n'
    readme.write_text(intro+text)
    log=Path('docs/CHANGELOG.md')
    log.write_text('## 2026-10-08 IRAC V6：证据相关性与条件判断分离，两案A/P/B完成\n\n'+summary+' 修复独立证据／局部用途、代码确定来源角色、可读合法条件目录及最终请求恰好一次。新版本冻结后未改方法；全部检查仅离线，原始P直接送入B。B含P成本为252.80／298.54秒，A为75.61／119.17秒；完整回答收益尚不足。原始输出、失败与快照均保留；完成一次集中来源审阅后停止。\n\n'+log.read_text())
    print('Local docs updated; prepare/verify still required')


if __name__=='__main__':main()
