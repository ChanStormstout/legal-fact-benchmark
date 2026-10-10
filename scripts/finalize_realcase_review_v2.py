"""Concentrated source-review report over immutable records; no model invocation.

The assessments below are an explicit model-assisted review, not an automatic
semantic validator or qualified legal approval. No proposal is rewritten here.
"""
import csv
import datetime as dt
import io
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from legal_bench.proof_carrying.realcase_contracts import read_json, write_once

OUT = ROOT / 'outputs/proof-carrying-realcase-v2'

REVIEWS = [
    {
        'case': '789051', 'name': 'Rame Gowda',
        'question': '区分占有保护、所有权证明与后续权利主张。',
        'source_fidelity': '主要区别得到保留：占有认定、双方未证明所有权、禁止干扰与未来产权诉讼不是同一结论。没有把所有权证明失败写成现实中没有所有权。',
        'source_refs': ['IK-789051:L65','IK-789051:L66','IK-789051:L67','IK-789051:L68','IK-789051:L69','IK-789051:L106','IK-789051:L107','IK-789051:L110','IK-789051:L111','IK-789051:L112','IK-789051:L113'],
        'important_opposition': '被告关于未请求产权确认、原告未证明产权便应驳回的论点，以及边界和地块尺寸争议，保留为论点或不确定项；不能借占有保护确定边界或产权。',
        'natural_issues': [
            {'id':'RG-EXEC-01','classification':['EXECUTION_COVERAGE','REPRESENTATION_CONTRACT'],
             'records':['R2@1','S2','S3','S5','S6'],
             'finding':'R2把开放性的稳定占有评价和对法院已经明确记载的稳定占有认定的承接合在一起。程序因此返回UNKNOWN；模型据原文给出的TRUE触发结果不匹配。应报告可执行范围不足，不能计作识别错误法律结论。'},
            {'id':'RG-QUOTE-01','classification':['SOURCE_LOCATOR_OVERBLOCK'],
             'records':['R4@1','S4'],
             'finding':'L111的呈现文本在Londa与撇号之间有空格，模型引文省略该空格；法律含义有原文支持，但严格定位阻止了规则。S1保留，S2只显式更换为原文精确子串。'},
            {'id':'RG-FACT-01','classification':['SEMANTIC_INFERENCE_LIMIT'],
             'records':['F4'],
             'finding':'非短暂占有的否定记录依赖法院稳定占有定性，不能另外解释成独立检查了所有取得占有过程。该限制不影响原文明确记载的稳定占有结论。'}
        ],
        'before_after_interpretation': '原始四项请求的法律方向大体有来源支持，但凭据全部被程序阻止；这不是四项法律结论均错。S2保留可执行的S1前缀，并让开放性后续步骤明确未完成；S2不是新独立模型成绩。',
        'remaining_gaps': ['未实现稳定占有的开放性评价；未明确分离观察法院认定与独立法律定性。','边界、土地原件与被引先例原文未独立取得。','正式法律批准待确认。'],
        'decision':'保留来源及版本机制；在下一版本优先分清法院已作判断的记录与仍需程序重算的判断。'
    },
    {
        'case':'1418721','name':'Karnataka Board of Wakf',
        'question':'区分积极所有权依据与未成立的逆权占有替代理由。',
        'source_fidelity':'保存登记、CTS资料及证言的法院记载，也保存Wakf一方反对；没有以逆权占有不成立推导政府所有权不成立。',
        'source_refs':['IK-1418721:L59','IK-1418721:L79','IK-1418721:L80','IK-1418721:L81','IK-1418721:L82','IK-1418721:L83','IK-1418721:L84','IK-1418721:L85','IK-1418721:L90','IK-1418721:L96','IK-1418721:L97','IK-1418721:L98','IK-1418721:L99','IK-1418721:L100','IK-1418721:L101'],
        'important_opposition':'Wakf的权属主张与对取得过程的攻击需要同法院关于取得方式未受挑战的较窄表述共同保留。登记不是单独自动决定产权；替代主张的张力不等于一般禁止替代诉求。',
        'natural_issues':[
            {'id':'WK-QUOTE-01','classification':['SOURCE_LOCATOR_OVERBLOCK'],
             'records':['R1@1','S1'],
             'finding':'源呈现为Act后空格再句点；引文为Act.，定位失败。规则的来源意义并未因此被否定。本案不补做第二次修正或模型调用。'},
            {'id':'WK-EXEC-01','classification':['EXECUTION_COVERAGE'],
             'records':['R2@1','R5@1','S2','S5','S6'],
             'finding':'法院综合证据确认所有权及评价逆权占有要求属于OPEN_TEXT。源文支持所提结论方向，但程序没有重算这些评价的能力；不能把阻止结果当作正确纠错。'},
            {'id':'WK-SCOPE-01','classification':['OBJECT_GRANULARITY_LIMIT','SOURCE_LIMIT'],
             'records':['E4','F4','F17'],
             'finding':'三处CTS物业只按判决的集合表述保存；不具备逐地块新断言。记录中的历史年代矛盾未擅自调和；未明确放弃原权利不等于确认未放弃。'}
        ],
        'before_after_interpretation':'原始请求中仅“记录了重要主张与证明缺口”获得条件性有效轨迹。其他请求主要受严格引文和开放评价限制；有效S3/S4没有被其他分支失败抹去。',
        'remaining_gaps':['综合证据和逆权占有的开放评价未实现。','证据原件、个别地块对应与历史日期未独立核验。','正式法律批准待确认。'],
        'decision':'保留两条独立理由与局部结果，不把失败替代理由视为推翻独立所有权依据。'
    },
    {
        'case':'1841885','name':'Sopan Sukhdeo Sable',
        'question':'区分诉状筛查、租赁争议的审理范围及尚未裁断的占有实体问题。',
        'source_fidelity':'提议保留下级法院驳回、最高法院对主争点的定性，以及双方对租期、强行夺占、缴款和退租的不同说法。没有把22/44名身份不明租户的退租推为原告已经退租。',
        'source_refs':['IK-1841885:L68','IK-1841885:L69','IK-1841885:L73','IK-1841885:L75','IK-1841885:L79','IK-1841885:L80','IK-1841885:L81','IK-1841885:L98','IK-1841885:L109','IK-1841885:L114','IK-1841885:L129','IK-1841885:L133','IK-1841885:L134','IK-1841885:L135','IK-1841885:L136','IK-1841885:L137','IK-1841885:L138','IK-1841885:L151','IK-1841885:L152','IK-1841885:L153'],
        'important_opposition':'关于无诉因、法定管辖、取得占有合法、租户自愿退出和未付欠款的反论均应按其提出者和阶段保存；程序继续不确认十一年租期、不直接授予禁令，也不认定夺占。',
        'natural_issues':[
            {'id':'SS-RULE-01','classification':['RULE_TRANSLATION_SCOPE_ERROR'],
             'records':['R6@1','rule_review:R6'],
             'finding':'独立规则复核及原文L136/L151确认：R6的必须在审理中评估禁令实体权利表述过强。原文只准许当事人提出强行夺占，并在与继续的租赁争议相关时处理。程序生存不推出实体成立，也不应以UNKNOWN/CONFLICTED状态作为该不蕴含关系的必要前提。R6在研究快照暂停，原草案保存。'},
            {'id':'SS-STATE-01','classification':['PROPOSITION_STATE_AMBIGUITY'],
             'records':['F11'],
             'finding':'F11把已知最高法院没有完成该实体判定与实体权利是否成立未知混在ADJUDICATED谓词的UNKNOWN中。原文叙述保留，但其类型化用途暂停；没有将未知改成否定权利。'},
            {'id':'SS-BIND-01','classification':['ROLE_MAPPING_CONTRACT'],
             'records':['F7','F8','R5@1'],
             'finding':'双方关于同一争议事件的表述使用相反subject/opponent方向，R5却要求相同角色绑定。不能自动交换角色，也不能把这种接口不相容直接当作确有两个不同事件。原记录不改。'},
            {'id':'SS-EXEC-01','classification':['EXECUTION_COVERAGE'],
             'records':['R2@1'],
             'finding':'给定原文明确记载最高法院对租赁争议的定性，但该接口仍要求开放性的全诉状法律判断，不能自动产生完整可执行结论。'}
        ],
        'before_after_interpretation':'R6问题由独立来源复核发现并通过接受政策阻止；检查器只是实施该决定，不能把发现语义错误的能力归给程序。相反角色记录是否能合法接入同一规则，需要显式角色映射，不能由检查器猜测。',
        'remaining_gaps':['未取得原始诉状、租约和临时禁令，事件日期与特定租户身份有真实缺口。','原判决明确没有裁断部分实体问题；不得要求重建补出这些结论。','规则翻译、角色映射和开放性解释仍有限制；正式批准待确认。'],
        'decision':'保留程序与实体分离及反论；下一版本修正规则作用域和角色契约，禁止以诉状继续推定实体胜诉。'
    }
]

def main():
    for case in REVIEWS:
        cid=case['case'];check=read_json(OUT/'cases'/cid/'runs/S1/check.json')
        case['original_step_results']={k:{a:v.get(a) for a in ('status','state','errors','gaps')} for k,v in check['steps'].items()}
        case['original_request_results']=check['requests']
        case['source_review_file']=f'cases/{cid}/source-review-S1.json'
        case['independent_reference_file']=f'runs/{cid}/reference/parsed.json'
    write_once(OUT/'final-source-review.json',{
        'reviewed_at':dt.datetime.now(dt.timezone.utc).isoformat(),
        'reference_status':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD',
        'qualified_legal_approval':False,'new_model_review_calls':0,
        'scope':'One concentrated review of decisive source content, original rule/fact/derivation records and checks; no exhaustive gold annotation.',
        'comparison_policy':'Same cached model proposals. Source-review policy decisions precede execution and are not discoveries made by the checker. Formal approval absence is never a detected error.',
        'cases':REVIEWS})
    rows=[]
    for c in REVIEWS:
        counts=Counter(x['draft_status'] for x in c['original_request_results'])
        rows.append({'case':c['case'],'name':c['name'],'question':c['question'],
            'request_statuses':json.dumps(dict(counts)),
            'source_fidelity':c['source_fidelity'],
            'observed_limitations':' | '.join(x['finding'] for x in c['natural_issues']),
            'remaining_gaps':' | '.join(c['remaining_gaps']),
            'decision':c['decision'],'formal_approval':'PENDING'})
    buf=io.StringIO();w=csv.DictWriter(buf,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with (OUT/'case-comparison.csv').open('x') as f:f.write(buf.getvalue())
    graph=[]
    for c in REVIEWS:
        r=read_json(OUT/'cases'/c['case']/'review-order.json')
        components=[]
        for x in r['components']:
            en=list((x['energy'] or {}).values())
            components.append({'nodes':x['nodes'],'fallback_recorded':x['fallback'],
                'min_energy':min(en) if en else None,'max_energy':max(en) if en else None,
                'near_machine_zero_diagnostic':bool(en and max(abs(v) for v in en)<1e-20)})
        graph.append({'case':c['case'],'source_top5':r['source_order'][:5],
            'simple_top5':r['simple_order'][:5],'spectral_top5':r['graph_budget_5'],
            'source_top10':r['source_order'][:10],'simple_top10':r['simple_order'][:10],
            'spectral_top10':r['graph_budget_10'],'components':components})
    write_once(OUT/'graph-diagnostic.json',{'cases':graph,
        'method_changed':False,'evaluated_utility':False,
        'finding':'Several balanced components have energy about 1e-32 to 1e-30. Exact percentile comparison can turn floating-point differences into ordering. The original frozen rankings are retained; a changed ranking here is not evidence of meaningful conflict detection.',
        'threshold_role':'1e-20 is a post-run diagnostic display flag only, not a changed ranking or acceptance threshold.',
        'limits':['Teaching interface only; no confirmed error-recall score.','Proposal-declared conflict is not a legal error.','No lawyer work-time saving estimate.','No truth, review or certificate status is changed by graph scores.']})
    print(json.dumps({'source_reviews':len(REVIEWS),'graph_diagnostics':len(graph),'legal_approval':False}))

if __name__=='__main__': main()
