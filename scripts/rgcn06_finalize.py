"""Record one concentrated source review and assemble the completed local delivery. No inference."""
import json,csv,hashlib
from pathlib import Path
from datetime import datetime
R=Path('outputs/rgcn-ranking-development-06')
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
# Source review of neutral renderings; reviewer knew the experiment, so this is not blind human evaluation.
notes={
'R0a053ca6':('110204406','保留雇员居住、家属访客、占有与同意争议；g6把公司1973年归属扩大为租赁权已经归属，原文未明确。遗漏公司书面否认联系与雇佣证言冲突。','L110–111,L136–149'),
'R5f6e2b03':('110204406','同样把公司归属写成租赁权已归属；员工/家属位置基本忠实，但漏书面答辩与证言冲突及1952具体日期限制。','L116–118,L136,L148–155'),
'R743390d5':('110204406','明确保留公司否认联系与雇佣证言冲突、登记缺失与证人无亲历、1952时间界限及访客反论；未发现同等严重错误。对占有和同意保留具体未知。','L110–111,L116–118,L125,L136–155'),
'R50d601a2':('110204406','员工、家属访客及同意争议保留，未把公司归属直接当租赁权归属；但初次答案中的书面答辩/证言冲突及具体日期分析消失。','L110–118,L136–155'),
'Rf0e25308':('110204406','不再断言租赁权已归属；保留员工长期居住与许可缺口，缩减了Roop/Rajiv及公司证言冲突讨论，覆盖仍不足。','L104,L110–118,L136–155'),
'R0032007d':('172908545','区分合伙/公司、共同人员与法律占有，保留遗嘱继承路径及其来源地位；遗漏PW1权限/文书可采性争议，未证明其对最终实体分析的唯一决定作用。','L62–66,L88–121,L122–144,L153–155'),
'Rad5ca309':('172908545','保留共同董事并不自动等于保持法律占有、遗嘱路线与书面同意；没有凭银行法创造公司豁免。仍缺文书可采性和PW1权限反论。','L114–155'),
'R80149dc4':('172908545','保留Ankur作为商号/分支的反论、遗嘱论点来自律师、共同人员不等同于法律实体；仍漏权限与文书证据争议。','L88–111,L118–144,L153–155'),
'R32b8bc17':('172908545','重复答案继续处理遗嘱与公司占有，未把律师引述升级为法院认定；核心方向与首次接近，具体覆盖有变化。','L114–155'),
'R3ccfd665':('172908545','重复答案保留遗嘱、公司独立性及未决占有，未产生明确优于另一条件的完整改善；共同证据程序反论仍缺。','L114–155'),
'Rf9f4bdf8':('58386394','正确将licensee分别归属R1和R6，保留先前ARC同意认定及上诉争议；加入44A机制但承认方案未给出、不能自动豁免。漏17/18通知与14(1)(b)的区分、R2–4认可转租主张展开及附条件交还。','L108–116,L148–170,L186–188'),
'R34ccf3b0':('58386394','保留先前ARC同意认定的层级与争议，正确不把未通知单独当作14(1)(b)成立。仍漏各组被请求人立场和附条件交还；法定合并范围保持未决。','L108–116,L148–170,L186–188'),
'R0827a404':('890045','1959让与与其后清算次序正确；区分assigns条款存在和适用于具体转移；遗漏已经允许输入的Controller/Tribunal/HC不利认定层级。','L192–195,L229–230,L260–263,L278'),
'R509371e3':('890045','事实次序及条款/法定同意区别保留，没有把银行44A当普通公司规则；遗漏既有下级处理。','L192–195,L229–230,L260–263'),
'Ra6e10ec2':('890045','除条款解释限制外，保留Controller、Tribunal与HC此前认定的不利方向，未猜测被排除最终理由；较另两答覆盖完整。','L192–195,L229–230,L260–263'),
'R9b652f86':('1908519','保留独占经营、Controller相反判断和Tribunal/HC认定、家庭反论；g3把未主张书面同意写成未取得或未主张，超出L148。结论仍有其他依据，不能据此说整案结论必错。','L143–150,L161–163'),
'R1c4594a2':('1908519','保留各级判断、经营控制与家庭/收养反论；把同意限定为未主张，时间限定为诉称并结合争点框定；未发现决定性新错。','L143–150,L161–163'),
'R9301ec9f':('1908519','保留相反下级判断和家庭反论；收养仪式证据不足主要来自律师争辩，g5对这一来源限定略弱，不等于法院认定收养无效。','L143–150,L161–163'),
'Rbfc532d1':('869439','保留Tribunal/HC既有不利认定，同时明确转移日期未给出，拒绝把部分认定当全部法定前提已齐。Clause14给予共享许可的point存在解释争议，explanation保留共享与转租区别；漏强制/指示性书面要求反论及商号/公司身份区别。','L163–177,L225–233'),
'Rbc6fc7bb':('869439','保留下级不利认定及条款反论；但g4称法定前提已满足，未处理记录没有转移日期。确定支持较现有可见依据强；条款许可范围仍有解释争议，未必证明最终历史裁判方向错误。','L163–177,L225–233')}
write(R/'source-review/neutral-findings.json',{'role':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD','blinding':'Neutral IDs used in displays; same experiment operator knew run order; not blind independent evaluation. Findings recorded after review, mapping retained for traceability.','rows':[dict(neutral=k,case_id=v[0],finding=v[1],source_locations=v[2])for k,v in notes.items()]})
case_notes={
'110204406':('WORSE','WORSE','A首答明确指出公司书面否认联系与雇佣证言的矛盾；B/C遗漏且把公司归属扩大为租赁权归属。','重复A/C均未再出现归属过度断言，A首次的证言矛盾分析也消失；首答A优势减弱为覆盖差异，不能视为稳定胜出。'),
'172908545':('CLOSE','CLOSE','三者都处理遗嘱及公司/共同人员反论；B覆盖已确认依据较多，但未形成明确完整答案优势，C丢TS段落、引入银行44A。共同遗漏文书可采性/证人权限争议。','重复A/C核心方向仍接近，论据覆盖变化；不以均UNDETERMINED作为正确证据。'),
'58386394':('MIXED_NO_CLEAR_NET_GAIN','MIXED_NO_CLEAR_NET_GAIN','B/C共享输入和回答：角色归属更明确、讨论银行法但不假定方案；A保留通知与腾退条件区分。增加材料没有同时解决许可解释、群体立场及附条件交还。','未预选重复。'),
'890045':('WORSE','WORSE','A保留既有Controller/Tribunal/HC不利认定；B/C遗漏。三者正确区分assigns措辞与具体法定同意，均保留真实解释缺口。','未预选重复。'),
'1908519':('WORSE','CLOSE','B把未主张书面同意扩大为未取得；C准确限定并保留家庭反论，A也已保留家庭反论。C的局部来源归属更谨慎不足以证明材料增量导致净收益。','未预选重复。'),
'869439':('LOCAL_IMPROVEMENT_WITH_DISPUTE','LOCAL_IMPROVEMENT_WITH_DISPUTE','B/C共享回答明确缺少转移日期，较A声称全部前提满足谨慎且具体；但Clause14共享许可解释仍可争议，书面要求强制/指示性反论均漏。不是最终裁判正确性证明。','未预选重复。')}
audit={x['id']:x for x in read(R/'answer-format-audit.json')};order=read(R/'answer-order.json');rows=[]
for q in order:
 a=audit[q['id']];n=notes[a['neutral']]
 rows.append({**q,**a,'finding':n[1],'source_locations':n[2],'raw_path':str(R/'raw'/(q['id']+'.txt')),'answer_path':str(R/'parsed'/(q['id']+'.json'))})
write(R/'final-source-review.json',{'role':'MODEL_ASSISTED_NOT_HUMAN_GOLD','review_count':1,'additional_model_calls':0,'answers':rows,'case_comparisons':[dict(case_id=c,B_vs_A=x[0],C_vs_A=x[1],reason=x[2],repeat=x[3])for c,x in case_notes.items()]})
with (R/'comparison-table.csv').open('w')as f:
 w=csv.writer(f);w.writerow(['case_id','A_answer','B_answer','C_answer','A_outcome','B_outcome','C_outcome','B_vs_A','C_vs_A','source_review','repeat'])
 for c,x in case_notes.items():
  m={m:q for q in rows if q['case_id']==c and q['replicate']==0 for m in q['methods']}
  w.writerow([c,*[m[k]['id']for k in 'ABC'],*[m[k]['outcome']for k in 'ABC'],*x])
ledger=read(R/'web-ledger.json');cost=[]
for k,v in ledger.items():
 secs=None
 if v.get('started')and v.get('finished'):secs=(datetime.fromisoformat(v['finished'].replace('Z','+00:00'))-datetime.fromisoformat(v['started'].replace('Z','+00:00'))).total_seconds()
 p=R/'tasks'/(k+'.txt');raw=R/'raw'/(k+'.txt')
 cost.append(dict(id=k,observed_submission_to_collection_seconds=secs,input_chars=len(p.read_text())if p.exists()else None,raw_chars=len(raw.read_text())if raw.exists()else None,exact_tokens=None,url=v.get('url')))
write(R/'web-cost.json',{'calls':len(cost),'preparation':sum(not x['id'].startswith('ANS')for x in cost),'final_answers':sum(x['id'].startswith('ANS')for x in cost),'exact_model':None,'displayed_model':'Latest','mode':'High','note':'Intervals include queue/browser/collection latency and overlap. They are neither exact generation times nor additive wall-clock cost. Tokens not observable.','rows':cost})
checks=[]
for kind,hashes in [('historical',read(R/'start.json')['historical_hashes']),('frozen',read(R/'training-freeze.json')['hashes'])]:
 bad=[p for p,h in hashes.items()if not Path(p).exists()or hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h];checks.append(dict(kind=kind,count=len(hashes),mismatches=bad))
write(R/'preservation-audit.json',checks)
assert not any(x['mismatches']for x in checks),checks
write(R/'local-weight-manifest.json',{'publication':'LOCAL_ONLY; no environment or language-model weights; small trained ranker arrays retained locally','weights':[dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())for p in sorted((R/'folds').rglob('*.npz'))]})
print('reviewed',len(rows),'calls',len(cost),'preservation',[(x['kind'],x['count'])for x in checks])
