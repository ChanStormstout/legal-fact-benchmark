"""Explicit Codex source-review labels, not an automatic semantic evaluator or model run."""
import json
from pathlib import Path

B = Path(__file__).resolve().parent
D = B / 'case1251841'
texts = {k:(D/(k+'.txt')).read_text() for k in ['A0','C38_candidate','C38_delivered']}
sources = json.loads((D/'allowed-sources.json').read_text())['sources']
rubric = [
 ('K01','问题与时间','正确识别核心是1929年前出租权能否拘束抵押权人，不把尚存问题改成仅核算担保金额；不强制重复问题句。',['S34eef73a1804','S3f8801f7bc98']),
 ('K02','问题与时间','说明1925年租约不能直接按1929年新增65-A的授权处理。',['S2066678d6807','S34eef73a1804','L502721c563fa']),
 ('K03','主体','原银行与本案原告明确区分，不能称原告就是原银行。',['S0db31d39ce4d','S49d549822256','Sd45be3f5fd91']),
 ('K04','主体','说明Court of Wards管理人代表原告财产利益，而非把该机构直接当成原告。',['S49d549822256','Sd45be3f5fd91']),
 ('K05','交易链','明确存在1914年旧抵押与1926年新抵押，保留两者的先后。',['S0db31d39ce4d','S49d549822256']),
 ('K06','交易链','明确新贷款清偿银行债务，并导致原银行拍卖被撤销。',['Sd45be3f5fd91']),
 ('K07','租约范围','交代1925年Wazir出租，Hiraman与Chohan父子取得永久租约。',['S2066678d6807']),
 ('K08','租约范围','明确租赁的是四村，不能把四村与整个Gadi Sirampur无区别地合并。',['S2066678d6807','S0db31d39ce4d']),
 ('K09','执行阶段','交代1931年出售判令与1935年原告拍买的顺序。',['S44aa752640f7']),
 ('K10','执行阶段','交代1936年交付占有与被告继续实际占有、1939年另诉收回土地的关系。',['S44aa752640f7','S8053e9e4e79b']),
 ('K11','竞争主张','以原告主张的身份交代代位、判令拘束和拍卖后租约应终止的论证链。',['S2e0ba5982107']),
 ('K12','竞争主张','以当事人主张的身份交代至少两项重要反论：未参诉/代表资格、租约不随拍卖消灭、否认Karta或分家。',['Sf05a6bb45a8e','Sd6e9439ddc2d']),
 ('K13','此前认定','交代此前法院关于原告代位于银行的认定，而非自行发明其根据或当前裁判。',['S601d5df39aca','S3f8801f7bc98']),
 ('K14','此前认定','交代此前法院关于第二被告已被充分代表的认定。',['S601d5df39aca','S3f8801f7bc98']),
 ('K15','高院处理','交代高院按66条分析担保是否不足、计算后认为未损害担保，尽管诉状未作该指控。',['Sd3c548138ec6','S978119f4c532']),
 ('K16','高院处理','明确高院认为租约不受抵押执行影响并驳回原告诉讼，不得在同报告结论中反转。',['S0c80c8bdc534']),
 ('K17','法律边界','区分66条本身的担保损害限制与高院据此解释出租权，不能将66条写成当然的永久租约授权或否定。',['L4cb87a2c0ccd','Sd3c548138ec6']),
 ('K18','法律边界','说明高院已否定原告的constructive res judicata主张，不用该条文替代尚存核心争点。',['S2d91d1862dc2']),
 ('K19','当前范围','明确两项此前认定未受挑战，当前只剩出租权能否拘束原告的问题，而非只剩金额计算。',['S3f8801f7bc98']),
 ('K20','当前范围','给出符合隐藏目标边界的有限回答及具体未知原因，不编写目标法院已认可的结论或把系统失败当材料缺失。',['S34eef73a1804','S0c80c8bdc534','S3f8801f7bc98']),
]

# Every quote below must be a literal substring of the preserved output. Labels are
# review decisions; the score calculator will not infer truth from these strings.
matches = {
 'A0': {
  'K01':['prior to the enactment of **Section 65-A'],
  'K02':['as Section 65-A was not yet in force in 1925'],
  'K05':['**1st August 1914:**','**14th August 1926:**'],
  'K07':['**5th November 1925:**','and his son Chohan Ram.'],
  'K08':['four villages (Nawadih, Koldih, Pandna, and Chihutia)'],
  'K09':['**18th September 1931:**','**6th April 1935:**'],
  'K13':['Both the trial court and the High Court found that the plaintiff was subrogated'],
  'K14':['Both lower courts found that Defendant 2 (Chohan Ram) was sufficiently represented'],
  'K15':['Despite no specific allegation in the plaint','did not** render the Bank'],
  'K18': ["The High Court had negated the plaintiff's contention regarding constructive res judicata"],
  'K19':['The Supreme Court noted these findings were not challenged.','sole surviving question for consideration.'],
 },
 'C38_candidate': {
  'K01':['a mortgagor in possession lacked the statutory power to grant a permanent lease binding on the mortgagee'],
  'K02':['prior to the 1929 enactment of Section 65-A'],
  'K12':['the defendants argue its validity persists despite the subsequent auction sale.', 'Defendant 1 contended that a partition occurred'],
  'K13':['The plaintiff is subrogated to the position of the Bank, a finding'],
  'K14':['a finding by the trial court and High Court'],
  'K15':['calculating figures to conclude the lease did not impair the security, despite no such allegation'],
  'K16':["beyond the High Court's dismissal of the suit.",'which the High Court found valid under Section 66.'],
 },
 'C38_delivered': {
  'K01':['power to grant a permanent lease binding on the mortgagee prior to the 1929'],
  'K02':['prior to the 1929 enactment of Section 65-A'],
  'K14':['a finding by the trial court and High Court'],
  'K15':['calculating figures to conclude the lease did not impair the security, despite no such allegation'],
 }
}

# Specific contradictory assertions defeat an otherwise matched required point.
overrides = {
 ('C38_candidate','K01'): ('CONTRADICTED','The application of Section 66\'s security sufficiency test to the specific figures and facts of the 1925 lease remains the unresolved substantive issue','The report explicitly narrows the unresolved issue to factual calculation, while the source says legal power remained. A title about power does not cure this contradiction.'),
 ('C38_delivered','K01'): ('CONTRADICTED','a finding the Privy Council accepted as the sole surviving legal question.','The surviving issue is incorrectly identified as acceptance/review of the High Court security finding, not the open legal power question. This is a semantic contradiction, not a heading-format penalty.'),
}

miss_reasons = {
 'K03':'A0 expressly equates plaintiff with Bank; C does not restore the distinct identity chain.',
 'K04':'No output correctly explains the manager-represented-estate relation.',
 'K06':'Repayment and annulment are absent from both A0 and V38 visible reports.',
 'K10':'No complete delivery-of-possession/continued-possession/new-suit chain.',
 'K11':'A0 does not reconstruct this as the claimant argument; C presents some earlier findings as current conclusions and does not give the complete attributed path.',
 'K17':'A0 generalizes section66 as governing lease power; C invents a pre1929 common-law restriction/current endorsement.',
 'K20':'A0 gives a reversed confident result; C invents target-court endorsement or delivers technical gaps, not a complete limited answer.'
}

claims = {k:[] for k in texts}
def add(output,key,quote,label,refs,reason,kind='FACT',episode=None):
    assert quote in texts[output], (output,key,quote)
    assert all(ref in sources for ref in refs), (key,refs)
    claims[output].append({'id':key,'quote':quote,'label':label,'source_refs':refs,
        'reason':reason,'kind':kind,'error_episode':episode,'semantic_duplicate_of':None})

def a(key,quote,label,refs,reason,episode=None):add('A0',key,quote,label,refs,reason,episode=episode)
S='SUPPORTED';U='UNSUPPORTED';X='CONTRADICTED'
a('a01','Wazir Narain Singh (son of the original owner, Raja Nilkanth Narain Singh).',S,['S0db31d39ce4d'],'Explicit father/son relation.')
a('a02','**Mortgagee (Original):** Chota Nagpur Banking Association Limited.',S,['S0db31d39ce4d'],'Original mortgagee.')
a('a03','Hiraman Ram (Manager/Karta of the joint Hindu family) and his son Chohan Ram.',S,['S2066678d6807'],'Both lessees and family capacity are recorded.')
a('a04','**Claimant Mortgagee (Plaintiff/Appellant):** The Bank',X,['S49d549822256','Sd45be3f5fd91'],'Plaintiff estate was represented by manager; Bank was repaid.','identity')
a('a05','**1st August 1914:** Simple mortgage executed by Raja Nilkanth Narain Singh in favor of the Bank.',S,['S0db31d39ce4d'],'Recorded event.')
a('a06','**29th November 1921:** Mortgage decree obtained by the Bank against Wazir Narain Singh.',S,['S0db31d39ce4d'],'Recorded decree.')
a('a07','**28th October 1922:** Bank purchased a third share of the property in execution of the decree.',S,['S0db31d39ce4d'],'Recorded share purchase.')
a('a08','Wazir Narain Singh granted a **permanent lease** of four villages (Nawadih, Koldih, Pandna, and Chihutia) to Hiraman Ram.',S,['S2066678d6807'],'True but omits the joint-name qualification; incompleteness is assessed in R.')
a('a09','**14th August 1926:** Wazir Narain Singh executed a new mortgage in favor of the Court of Wards.',X,['S49d549822256','Sd45be3f5fd91'],'It was to the manager in charge of plaintiff estate, not simply an institutional beneficial mortgagee.','identity')
a('a10','**4th February 1929:** Plaintiff (Court of Wards) filed suit to enforce the 1926 mortgage.',X,['Sd45be3f5fd91'],'Conflates represented plaintiff and representative.','identity')
a('a11','**18th September 1931:** Final decree for sale passed.',S,['S44aa752640f7'],'Recorded decree date.')
a('a12','**6th April 1935:** Plaintiff purchased the property at auction.',S,['S44aa752640f7'],'Role-event is recorded; contradictory plaintiff identity remains an independently scored error.')
a('a13','**16th November 1939:** Plaintiff filed the suit for possession against Hiraman Ram and Chohan Ram',S,['S8053e9e4e79b'],'Recorded new suit and parties; role-event does not repair identity error.')
a('a14','Both the trial court and the High Court found that the plaintiff was subrogated to the position of the Bank.',S,['S3f8801f7bc98'],'Attributed prior finding, not a new legal derivation.')
a('a15','The Supreme Court noted these findings were not challenged.',U,['S34eef73a1804','S3f8801f7bc98'],'Unchallenged status is provided, but the explicit current court name is absent from allowed view.','current_court')
a('a16','Both lower courts found that Defendant 2 (Chohan Ram) was sufficiently represented in the earlier mortgage suit.',S,['S3f8801f7bc98'],'Attributed prior finding.')
a('a17','This finding was also not challenged.',S,['S3f8801f7bc98'],'Unchallenged representation finding.')
a('a18',"The High Court had negated the plaintiff's contention regarding constructive res judicata",S,['S2d91d1862dc2'],'Recorded rejection.')
a('a19','this specific issue was not the surviving question for the Supreme Court.',U,['S3f8801f7bc98'],'Scope of surviving issue is supported, but named current court is unsupported.','current_court')
a('a20','The High Court concluded that Wazir Narain Singh had the power to grant the permanent lease because it did not render the Bank\'s security insufficient.',S,['Sd3c548138ec6','S978119f4c532'],'Properly attributed High Court interpretation.')
a('a21','The Supreme Court accepted this as the sole surviving question for consideration.',U,['S3f8801f7bc98'],'Current named tribunal unsupported; the unchallenged findings are not the security test.','current_court')
a('a22',"The High Court held the lease was valid and not affected by the plaintiff's mortgage or the execution sale.",S,['S0c80c8bdc534'],'Correct historical statement, later contradicted by the conclusion.')
a('a23','**Section 65-A (TPA):** Enacted in 1929',S,['S34eef73a1804'],'Date of statutory change.')
a('a24','subject to conditions (best rent, no premium, no renewal covenant, max 3 years for buildings, etc.).',S,['L502721c563fa'],'These lease conditions appear in the frozen section; no claim that1925 directly satisfies them.')
a('a25','Prior to Section 65-A, the governing provision was Section 66.',U,['L4cb87a2c0ccd','Sd3c548138ec6'],'Turns historical judicial approach into a general settled lease-power rule.','law_generalization')
a('a26','a mortgagor is not liable for deterioration unless they commit an act "destructive or permanently injurious" if the security is insufficient or **will be rendered insufficient** by such act.',S,['L4cb87a2c0ccd'],'Captures statutory security-damage restriction.')
a('a27','A permanent lease is generally considered an act that renders the security insufficient because it transfers the beneficial interest indefinitely',U,['L4cb87a2c0ccd','Sd3c548138ec6'],'No allowed authority supports this generalization.','law_generalization')
a('a28','Despite no specific allegation in the plaint regarding insufficiency, the High Court calculated figures',S,['S978119f4c532'],'Recorded procedural fact.')
a('a29','the lease of the disputed villages **did not** render the Bank\'s security insufficient.',S,['S978119f4c532'],'Correct High Court finding.')
a('a30','as Section 65-A was not yet in force in 1925',S,['S2066678d6807','S34eef73a1804'],'Correct temporal caution.')
a('a31','the lease was valid and **did not bind** the plaintiff',X,['S0c80c8bdc534'],'High Court held lease unaffected and dismissed plaintiff suit.','high_court_reversal')
a('a32','The plaintiff was entitled to possession because the lease was deemed valid but did not defeat the mortgagee\'s rights',X,['S0c80c8bdc534'],'Reverses the High Court disposition.','high_court_reversal')
a('a33','It did not explicitly overturn the High Court\'s finding on the sufficiency of security in the provided excerpts',S,['S34eef73a1804','S3f8801f7bc98'],'Only as an absence claim about supplied excerpts; not evidence of target endorsement.')
a('a34','Under Section 66, a mortgagor cannot commit acts that render the security insufficient.',U,['L4cb87a2c0ccd'],'Omits the destructive/permanently injurious qualification and treats all security-reducing acts alike.','law_generalization')
a('a35','The High Court interpreted this to mean that if the security remains sufficient despite the lease',S,['Sd3c548138ec6','S978119f4c532'],'Only as the historical High Court approach, not independently correct law.')
a('a36','this section explicitly grants a mortgagor in possession the power to make leases binding on the mortgagee, subject to conditions',S,['L502721c563fa'],'Statutory authorization under65A subject to stated conditions; temporal application assessed separately.')
a('a37','whether a mortgagor in possession, prior to the enactment of **Section 65-A of the Transfer of Property Act, 1929**, had the power to grant a permanent lease that would bind the mortgagee.',S,['S34eef73a1804'],'Correct description of the presented legal question, not its answer.')

def c(key,quote,label,refs,reason,episode=None):add('C38_candidate',key,quote,label,refs,reason,episode=episode)
c('c01','The Privy Council held that',U,['S34eef73a1804','S0c80c8bdc534'],'Earlier leave to Privy Council does not establish current adjudicator or target holding.','hidden_target')
c('c02','a mortgagor in possession lacked the statutory power to grant a permanent lease binding on the mortgagee unless the lease was validated under Section 66',U,['L4cb87a2c0ccd','S34eef73a1804'],'Unprovided general statutory rule.','power_rule')
c('c03',"the High Court's finding on this specific test was not challenged",X,['S3f8801f7bc98'],'Unchallenged findings were subrogation and representation, not this legal test.','surviving_issue')
c('c04',"The application of Section 66's security sufficiency test to the specific figures and facts of the 1925 lease remains the unresolved substantive issue",X,['S3f8801f7bc98'],'Open issue is mortgagor power, not simply calculation of security sufficiency.','surviving_issue')
c('c05','the Privy Council accepted the lower courts\' factual findings',U,['S3f8801f7bc98','S0c80c8bdc534'],'Unchallenged prior findings do not provide target-court endorsement.','hidden_target')
c('c06','Wazir Narain Singh did not possess an inherent common law power to grant a permanent lease binding on the mortgagee',U,['S34eef73a1804','L4cb87a2c0ccd'],'Source poses the question, does not supply this common-law answer.','power_rule')
c('c07','prior to the 1929 enactment of Section 65-A',S,['S34eef73a1804'],'Correct temporal statutory reference.')
c('c08','the High Court applied Section 66',S,['Sd3c548138ec6'],'Correct attribution.')
c('c09',"determining the lease valid only because it did not render the Bank's security insufficient",S,['Sd3c548138ec6','S978119f4c532'],'Correct as High Court reasoning, not universal law.')
c('c10','a finding the Privy Council accepted as the sole surviving legal question.',U,['S3f8801f7bc98'],'Conflates a prior factual calculation and the remaining legal question.','surviving_issue')
c('c11','which was not independently reviewed by the Privy Council.',U,['S34eef73a1804','S3f8801f7bc98'],'Unprovided current-court handling of the calculation.','hidden_target')
c('c12',"The permanent lease granted in 1925 binds the plaintiff only if the High Court's conclusion that it did not render the mortgagee's security insufficient is legally correct",U,['Sd3c548138ec6','S3f8801f7bc98'],'Not established that this test is the necessary/sufficient controlling legal criterion.','power_rule')
c('c13',"the plaintiff's claim to possession relies on the lease being void",S,['S2e0ba5982107'],'Supported as claim that lease no longer defeats possession, not a court finding.')
c('c14','the defendants argue its validity persists despite the subsequent auction sale.',S,['Sf05a6bb45a8e'],'Correctly attributed opposing position.')
c('c15',"beyond the High Court's dismissal of the suit.",S,['S0c80c8bdc534'],'Correct prior outcome; surrounding general legal effect is still unprovided.')
c('c16','Chohan Ram) was sufficiently represented in the mortgage suit by his father Hiraman Ram as Manager and Karta of the joint Hindu family, a finding by the trial court and High Court',S,['S601d5df39aca','S3f8801f7bc98'],'Correct historical finding with participants.')
c('c17','was not challenged before the Privy Council',U,['S3f8801f7bc98','S0c80c8bdc534'],'Only before us is supplied; explicit tribunal unsupported.','hidden_target')
c('c18','thus stands as an unchallenged fact binding the defendant to the mortgage decree.',S,['S601d5df39aca','S3f8801f7bc98'],'Supported only as the preserved prior representation/decree finding; does not decide lease power. This narrower reading is an explicit adjudication boundary.')
c('c19','calculating figures to conclude the lease did not impair the security, despite no such allegation being in the plaint',S,['S978119f4c532'],'Correct High Court description.')
c('c20','The propriety of the High Court raising this issue sua sponte without a plaint allegation is not addressed as a legal error in the provided sources.',S,['S978119f4c532'],'Accurate limitation about allowed text, not a finding of procedural validity.')
c('c21','The plaintiff is subrogated to the position of the Bank, a finding',S,['S601d5df39aca','S3f8801f7bc98'],'Supported as earlier finding.')
c('c22','which entitles the plaintiff to the benefits of the mortgage decree and the right to recover possession, subject to the validity of any intervening leases.',U,['S601d5df39aca','S0c80c8bdc534'],'General current entitlement is not established by old finding alone.','current_effect')
c('c23','The auction sale of the mortgaged property does not automatically terminate a permanent lease granted by the mortgagor prior to the sale',U,['Sf05a6bb45a8e','S0c80c8bdc534'],'Party position and case-specific High Court holding are not a universal rule.','power_rule')
c('c24',"the lease's survival depends on its validity under the Transfer of Property Act at the time of grant",U,['S34eef73a1804','L4cb87a2c0ccd'],'Too general as a current legal sufficiency statement; detailed execution/priority law is not established.','power_rule')
c('c25','Defendant 1 contended that a partition occurred within a year of possession allotting the properties to Defendant 2',S,['Sd6e9439ddc2d'],'Correct party allegation, not fact established.')
c('c26','potentially severing joint liability',U,['Sd6e9439ddc2d'],'No source establishes this legal effect.','partition_effect')
c('c27','this contention was not accepted by the trial court',U,['S601d5df39aca','Sd6e9439ddc2d'],'Being Karta/representing D2 does not supply a separate partition ruling.','partition_ruling')
c('c28','this issue was not raised before the Privy Council.',U,['S3f8801f7bc98'],'Not the same as stating only one issue remained; no basis to assert never raised before a named court.','partition_ruling')
c('c29','The existence and effect of the alleged partition remain unresolved',S,['Sd6e9439ddc2d','S601d5df39aca'],'As a visibility limit only; contradicts the preceding invented rejection, recorded separately.')
c('c30',"the defendants cannot deny the decree's validity on the ground of non-participation.",U,['S601d5df39aca','S3f8801f7bc98'],'An unqualified legal prohibition on arguments goes beyond the attributed prior finding.','current_effect')
c('c31','None; subrogation is a settled fact for the appeal.',S,['S3f8801f7bc98'],'Narrowly treated as unchallenged status within this appeal; does not supply the missing current tribunal name.')
c('c32','None; the representation finding is treated as settled fact for the purpose of the appeal.',S,['S3f8801f7bc98'],'Narrow record status is supported; tribunal identity and general legal effects remain separate unsupported claims.')
c('c33','The legal effect of an auction sale on a pre-existing lease under the historical statute is not explicitly resolved in the provided sources',S,['S34eef73a1804','S3f8801f7bc98'],'As a limit on the supplied target assessment, with the following High Court exception preserved; not a claim that the judgment never resolves it.')

# Delivery is a deterministic subset of the candidate's prose. Reuse semantic
# labels for literally preserved assertions; do not invent a fresh reviewer.
for row in claims['C38_candidate']:
    if row['quote'] in texts['C38_delivered']:
        claims['C38_delivered'].append({**row,'id':row['id'].replace('c','d',1), 'label_reused_from':row['id']})

for output,text in texts.items():
    rows=[]
    for key,group,condition,refs in rubric:
        quote=matches[output].get(key,[])
        for q in quote:assert q in text,(output,key,q)
        label='CORRECT' if quote else 'MISSING_OR_INCORRECT'
        reason='Meets this explicit component only; other false clauses are independently scored.' if quote else miss_reasons.get(key,'Missing, only a question title, or not correctly supported as stated.')
        if (output,key) in overrides:
            label,q,reason=overrides[(output,key)]
            quote=[q] if q else []
        rows.append({'id':key,'group':group,'condition':condition,'source_refs':refs,
                     'label':label,'credit':int(label=='CORRECT'),'report_quotes':quote,'reason':reason})
    payload={'report':output,'kind':'NONBLINDED_CODEX_SOURCE_REVIEW_DEVELOPMENT_REFERENCE',
             'keypoint_labels':rows,'assertion_labels':claims[output],
             'annotation_unresolved':[], 'not_human_gold':True,
             'deduplication':'Repeated identical proposition counted once; different actor, time, negation, modality or attribution is a different assertion.',
             'coverage_scope':'Body and substantive remaining-limit statements; questions/headings and system placeholders excluded.',
             'source_binding_policy':'Role-level correctly described prior events can earn their content point; contradictory identity claims independently lose actor points and count as errors. This is not a claim of globally coherent narrative.'}
    (D/(output+'-labels.json')).write_text(json.dumps(payload,ensure_ascii=False,indent=2))

(D/'rubric.json').write_text(json.dumps({'version':'DEVELOPMENT_POSTHOC_RUBRIC_V1','case_id':'1251841',
    'total_points':len(rubric),'weights':'one per explicit condition; no output-specific weights',
    'basis':'Ten question-derived themes already used in V37/V38; split into two conditions each.',
    'items':[{'id':k,'group':g,'condition':t,'source_refs':r} for k,g,t,r in rubric]},ensure_ascii=False,indent=2))
print(json.dumps({o:{'points':sum(x['credit'] for x in json.loads((D/(o+'-labels.json')).read_text())['keypoint_labels']),
                     'assertions':len(claims[o]),'supported':sum(x['label']==S for x in claims[o])} for o in texts},ensure_ascii=False))
