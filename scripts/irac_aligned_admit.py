#!/usr/bin/env python3
"""One documented, pre-training source review; preserve raw reference versions."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.irac_application.aligned_tasks import ROOT,put
from legal_bench.irac_application.aligned_quality import validate_reference,admission
from legal_bench.irac_application.aligned_graph import check_refs
NOTES={
'112400':'逐一对照八段允许来源。原租赁用途未记载；所有权明确；下级法院否定善意需求仍限于该层级。现住处不适合不证明不存在所有其他住处。C02/C03/C05另作一次独立复核。',
'1114159':'允许材料支持原租赁为住宅用途；主要内容是其他使用及付费住客争议，没有当前善意需求、所有权及替代住所事实。不从亲属关系补造所有权或依赖关系。这个旧问题包的材料覆盖很薄，保留缺口。',
'114533':'租赁承认、丈夫经营、下级法院否定转租与其确认均在来源中；转租租金仍为指称。来源没有书面同意、处分日期及完整法律占有事实。引文去掉工具标记后无法原样定位的行屏蔽，未修写引文。',
'1870868':'1954起租与既有下级法院转租认定可支持条件性时间及无同意判断；缺少具体转租要素和占有资料。C01与C02集中复核；不把下级结果直接当目标请求结果。',
'489898':'两名既有占有人早于该租赁且经房东同意；日期、同意形式及租户后续处分未交代。物业范围与处分是否发生须分开，C07另行复核。',
'14884716':'保留1944指称与前1952未举证的相反记载，不把没有前1952证明当作已证明后1952。Tribunal无书面同意的认定与仅有知情的反论分别保存，C02另行复核。',
'33810117':'1979租赁、1990公司承租、1992分离及另一公司占用均明确；个人董事留在现场不等于租户公司保留法律占有。下级未证明转租不等于所有转移事实被否定。',
'50313565':'专有占有证言与父亲控制、儿子帮助的相反证言并存。不得把家人身份当自动法律例外；日期、书面同意和处分法律性质仍缺。',
'52547606':'1963电话只证明存在时间，不直接证明处分日期。下级相反认定须同时保留；无推断与反驳的差别交独立复核C03。未通过地址校验的行不进入监督。',
'55384096':'1983被指称商业安排可作有条件的时间判断；亲属/合伙不当然排除转租，伪造指称和继续经营证言均保留。部分引用跨排版文字不能定位，局部屏蔽。',
'68065690':'5500租金和独占为房东指称；家人帮助、不收租与口头合伙是相反材料。1975合伙日期不自动对应同一个被指称转移。',
'68096693':'Divya Jyoti占有与法律继承人持续经营互相争议，许可证/GST仅有目录记载，不能补造其中内容。处分日期及书面同意未确定。',
'84524189':'1991起租及之后伙伴变化支持有条件时间；公司/合伙实体和个人伙伴不能互换。持续占有说法与原伙伴退出指称冲突，缺少处理实体连续性的法源。',
'125596702':'招牌、电话、银行账户及儿子在店不能直接证明法律占有已转移；父亲继续控制为相反说法。处分时间、书面同意、完整租赁要素未确定。',
'133241208':'旧资料没有转租实质细节；空白业主姓名和无证明不自动构成否定事实。多行UNSUPPORTED与事实未决的区分，以及1979时间绑定，集中复核一次。',
'188721101':'弟弟开店持钥匙与工资、可撤销许可的下级认定同时保留；另外父亲的早期处分指称不能由弟弟组合替代。C02/C03/C04/C06集中复核，争议不强行标注。',
'191402169':'1985许可是被指称同一酒类经营安排的时间，不证明其构成转租；免租许可、保留法律占有与房东反对指称都在允许来源内。许可形式未知不能推定书面与否。'}
def main():
    overrides={}
    for p in sorted((ROOT/'web').glob('review-0[123].json')):
        for item in json.loads(p.read_text())['items']:overrides[(str(item['case_id']),item['test_id'])]=(item,str(p))
    if len(list((ROOT/'web').glob('review-0[123].json')))!=3:raise ValueError('WAIT_FOR_THREE_BUDGETED_REVIEWS')
    for p in sorted((ROOT/'references').glob('*.json')):
        d=json.loads(p.read_text());cid=d['case_id'];mat=json.loads((ROOT/'sources'/p.name).read_text());family=mat['family'];template=json.loads((ROOT/'templates'/f'{family}.json').read_text());sources=dict(mat['sources']);sources.update({x['source_id']:x for x in json.loads((ROOT/'sources'/f'{family}-law.json').read_text())})
        decisions=[];revised=json.loads(json.dumps(d));changes=[]
        for i,row in enumerate(revised['tests']):
            decision='ADMIT';why=NOTES[cid];key=(cid,row['test_id'])
            if key in overrides:
                item,origin=overrides[key];why=item['reason'];decision='ADMIT' if item['decision'] in ('ADMIT','CORRECTED') else 'DISPUTED'
                if item['decision']=='CORRECTED':
                    replacement=item['reference_row'];changes.append(dict(test_id=row['test_id'],before=row,after=replacement,review=origin));row=dict(replacement);revised['tests'][i]=row
            row['automatic_check_errors']=check_refs(row.get('support_refs',[])+row.get('opposition_refs',[])+[ref for b in row.get('bindings',[]) for ref in b.get('source_refs',[])],sources)
            if cid=='133241208' and row['test_id'].endswith(('C02','C03','C04','C05')):
                why+=' Local source review accepts UNRESOLVED because these are missing or contested factual predicates. The web reviewer incorrectly describes UNSUPPORTED as affirmative refutation; that characterization is rejected. UNSUPPORTED was never encoded as a negative class.'
            if cid=='188721101' and row['test_id'].endswith(('C02','C03','C06')):
                decision='DISPUTED';why+=' Local review does not accept absence of target-court approval as sufficient reason to discard a prior-court finding. The separate father arrangement and brother arrangement also lack separately resolved labels. Retain this disagreement, mask supervision, and do not infer a new status.'
            if row['automatic_check_errors']:decision='MASK';why+=' Address/reference validation failed; original text retained.'
            if row['status']=='UNSUPPORTED':decision='MASK';why+=' Unsupported is retained separately, not relabeled negative or unresolved.'
            decisions.append(dict(test_id=row['test_id'],decision=decision,reason=why))
        audit=validate_reference(revised,template,sources)
        bad={r['test_id'] for r in audit['rows'] if r['errors']}
        for decision in decisions:
            if decision['test_id'] in bad:decision['decision']='MASK';decision['reason']+=' Structural reference audit failed.'
        review=dict(case_id=cid,basis='ALLOWED_SOURCES_AND_GIVEN_LAW',kind='MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD',source_review_notes=NOTES[cid],raw_reference_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),source_sha256=hashlib.sha256((ROOT/'sources'/p.name).read_bytes()).hexdigest(),tests=decisions,corrections=changes,audit=audit,scope='one concentrated pre-training review; no model-fit results read')
        put(ROOT/'reference-review-v2'/p.name,review);put(ROOT/'references-admitted-v2'/p.name,admission(revised,review))
if __name__=='__main__':main()
