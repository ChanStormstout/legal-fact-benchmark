import json, copy, pathlib, datetime, hashlib
r=pathlib.Path(__file__).resolve().parent.parent;o=pathlib.Path(__file__).parent
read=lambda n:json.loads((r/n).read_text())
def save(n,d):(o/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
packet=read('packet.json');sources=read('source-view.json');reports={x['blind_id']:x for x in packet['reports']}
files={'BWV':('BWV-coverage-original.json','BWV-assertions-artifact-recovery-raw.json'),'T4K':('T4K-coverage-artifact-recovery-raw.json','T4K-assertions-artifact-recovery-raw.json'),'O1W':('O1W-coverage-artifact-recovery-raw.json','O1W-assertions-original.json')}
raw={k:packet[k] for k in ['case_id','source_view_sha256','reference_sha256']};raw['reports']=[]
for bid,(c,a) in files.items():
 row=copy.deepcopy(read(a));cov=read(c);row.update(coverage=cov['coverage'],main_answer=cov['main_answer'],main_answer_reason=cov['main_answer_reason']);raw['reports'].append(row)
save('labels-raw-web.json',raw)
adj=copy.deepcopy(raw);changes=[]
def change(bid,axis,key,**kwargs):
 row=next(x for x in adj['reports'] if x['blind_id']==bid);lst=row[axis];field='item_id' if axis=='coverage' else 'id';x=next(x for x in lst if x[field]==key);before=copy.deepcopy(x);x.update(kwargs);changes.append({'blind_id':bid,'axis':axis,'key':key,'before':before,'after':copy.deepcopy(x)})
# Literal witness formatting only; reports and sources remain untouched.
for row in adj['reports']:
 if row['blind_id']!='BWV':continue
 for axis in ['coverage','assertions','serious_errors']:
  for x in row[axis]:
   for field in ['report_quote','report_quotes']:
    if field not in x:continue
    values=[x[field]] if field=='report_quote' else x[field];new=[]
    for q in values:
     fixed=q.replace('The Trial Judge held that while','the Trial Judge held that while').replace('The Trial Judge granted declarations','the Trial Judge granted declarations').replace('*Estoppel* does not bar','**Estoppel** does not bar')
     assert fixed in reports['BWV']['text'],repr(fixed)
     if q!=fixed:changes.append({'blind_id':'BWV','kind':'LITERAL_REPORT_WITNESS_ONLY','before':q,'after':fixed})
     new.append(fixed)
    x[field]=new[0] if field=='report_quote' else new
save('labels-web-literal-normalized.json',adj)
# Retain uncertainty over whether contextual widowhood supplies the required adoptive-father binding.
for bid in ['T4K','O1W']:
 for key in ['P04','P14','P15']:
  change(bid,'coverage',key,status='ANNOTATION_UNRESOLVED',reason='Adopter/adoptee and chronology are present. The required deceased adoptive father is only inferable from the earlier widowhood description, not expressly linked to this adoption. Preserve this contextual-entailment uncertainty consistently across the unchanged texts; do not insert the source relation into the report.')
change('T4K','coverage','P27',status='ANNOTATION_UNRESOLVED',reason='The report explicitly states a trial declaration of valid adoption but does not directly connect the declaration to adopted-son-of-Shankar status; that link is inferable through widowhood context. The explicit declaration phrase is later removed in O1W, so preserve the possible old-only content rather than automatically copying a full-coverage label.')
change('O1W','coverage','P41',status='NOT_SATISFIED',reason='This estoppel paragraph is unchanged from T4K: it recites intention in the statute and admits the earlier award, but does not identify the case-specific intentional representation as an unresolved factual condition. Apply the same coverage requirement to both unchanged paragraphs.')
change('BWV','coverage','P19',status='ANNOTATION_UNRESOLVED',reason='The report states the 1944 possession claim and identifies both competing defendants elsewhere, but does not directly state the action is against both. Whether the whole context satisfies this mandatory relationship is unresolved, not supplied from the original.')
change('BWV','assertions','A20',label='ANNOTATION_UNRESOLVED',reason='The actual words say the plaintiff admitted invalidity. In the compromise context this could mean formal acceptance of award terms or an independent admission of legal truth. The source establishes the former, not unequivocally the latter; apply the same reading uncertainty to the paired reports.')
change('BWV','assertions','A35',label='ANNOTATION_UNRESOLVED',proposition='The later adoption supports the property claim regarding title/status, with immediate possession expressly excluded elsewhere.',reason='Do not enrich the report into an assertion of unrestricted present title. Title/status may conflate distinct interests, but the report explicitly limits possession. The legally intended breadth remains unresolved.')
change('T4K','assertions','A14',label='SUPPORTED',proposition='In the reported sequence, Gangabai received advice to adopt Devaji again.',reason='Source says a lawyer seems to have advised her and following the advice she adopted again. Evaluate the report as a summary of this narrated advice, not as independent proof of consultation. Apply consistently to the same statement in all reports.')
change('T4K','assertions','A43',label='SUPPORTED',reason='The qualified statement says earlier acceptance does not necessarily create an automatic bar to every later right. The lower courts recognized valid status and deferred possession despite the compromise, while further legal scope is open. This does not establish a categorical absence of estoppel.')
# Before method unmasking, keep a common inventory for the mostly identical reports.
c=next(x for x in adj['reports'] if x['blind_id']=='T4K');e=next(x for x in adj['reports'] if x['blind_id']=='O1W');old_e=copy.deepcopy(e)
canon=copy.deepcopy(c['assertions']);index={x['id']:x for x in canon}
def replaceunit(key,**kw):index[key].update(kw)
replaceunit('A24',proposition='The lower courts granted declarations favoring the plaintiff, without specifying here the precise adoption-status declaration.',report_quote='the lower courts granted declarations favoring the Plaintiff',label='SUPPORTED',evidence=[{'source_id':'S2433e45f0607','quote':'granted to the Plaintiff the declarations'}],reason='The generic statement is supported; it is weaker than the removed explicit trial declaration of valid adoption and is not evidence of all three specific declarations.')
replaceunit('A25',report_quote='he was entitled to possession of the family properties only after her death')
replaceunit('A35',proposition='The report attributes to the plaintiff the reasoning that the previous decree did not adjudicate an adoption made in 1943 under a new legal regime.',report_quote='The Plaintiff argued that the prior decree did not adjudicate the validity of an adoption made in 1943 under the new legal regime',label='UNSUPPORTED',reason='The supplied plaint establishes the later-adoption basis, but does not record this specific new-regime/preclusion reasoning as the plaintiff\'s argument. Converting an analysis into an attributed argument does not supply missing source support.')
replaceunit('A36',proposition='The plaintiff specifically argued that the 1943 validity issue was not directly and substantially in issue before.',label='UNSUPPORTED',reason='The same literal issue phrase now sits within an unrecorded attribution to the plaintiff. The source reports the claim and remaining issues, not this specific pleading rationale.')
replaceunit('A37',proposition='The lower courts accepted the asserted new-adoption argument as their reason for finding no res judicata.',report_quote='The lower courts accepted this argument and found no bar',label='UNSUPPORTED',reason='The lower-court result is recorded, but acceptance of this specific argument as its rationale is not. The later sentence attributing legal distinctness repeats this same unrecorded rationale, not another independent unit.')
replaceunit('A46',proposition='The plaintiff advanced a property claim based on his later adoption despite the earlier compromise.',report_quote='the Plaintiff argues that the later adoption supports the present property claim despite the compromise',label='SUPPORTED',reason='This weaker attribution of the basic litigation position is supported by the recorded 1944 suit based on the second adoption. It does not supply the specific new-regime reasoning or prove legal success.')
canon.extend([{'id':'A50','proposition':'The postponement of possession reflected the nature of Defendant 1\'s property interest.','report_quote':"reflecting the nature of Defendant 1's interest",'label':'UNSUPPORTED','evidence':[{'source_id':'S3a43f85b5230','quote':'the Plaintiff was estopped from claiming possession of the properties from the Defendant 1'}],'reason':'The source gives estoppel as the reported restriction, not the suggested analysis of the nature of her interest.'},{'id':'A51','proposition':'The permanent property-exclusion clause was a specifically recorded central element of the defendants\' estoppel argument.','report_quote':"A central element of the defense's estoppel argument is the award clause",'label':'UNSUPPORTED','evidence':[{'source_id':'S1fe7eb26b370','quote':"the Plaintiff's claim was barred by estoppel."},{'source_id':'Sf6f730f0b668','quote':'the Plaintiff is not and can never become entitled to the property belonging to the family of Devarao Bapuji Deshpande.'}],'reason':'The clause and pleaded estoppel are both recorded, but this detailed characterization of counsel\'s argument is not. It could instead be offered as an explicitly conditional analytical possibility.'}])
e['assertions']=canon
# Shared uncertain rationale readings must not be scored differently solely because another grader saw them.
for row in [c,e]:
 for key in ['A42','A44','A45','A48']:
  x=next(x for x in row['assertions'] if x['id']==key);x['label']='ANNOTATION_UNRESOLVED';x['reason']='Common unchanged wording: it can mean formal compromise acceptance or a tentative inference about unreported judicial reasoning. The original supplies the disposition, not the exact rationale. Preserve the same uncertainty for both texts.'
# One real but missed forum assertion per report; the leave route alone does not identify the hearing institution.
forum={'source_id':'S8804b7a41057','quote':'leave to appeal to the Federal Court'}
for row in adj['reports']:
 tx=reports[row['blind_id']]['text'];quote='before the Federal Court' if 'before the Federal Court' in tx else 'to the Federal Court';assert quote in tx
 row['assertions'].append({'id':'A_FORUM','proposition':'The present reviewing court was the Federal Court.','report_quote':quote,'label':'ANNOTATION_UNRESOLVED','evidence':[forum],'reason':'The permitted record says leave was obtained to appeal to the Federal Court, but refers to the hearing as before this Court. The excerpt alone does not conclusively identify the institution hearing this appeal. Do not use the full hidden judgment or case memory to resolve it.'})
# Retain the distinct raw serious-error inventories; one harmonized paired inventory follows the changed objects.
e['serious_errors']=copy.deepcopy(c['serious_errors'])
for x in e['serious_errors']:
 if x['id']=='E03':x.update(type='UNRECORDED_ATTRIBUTION_OF_PRECLUSION_REASONING',report_quotes=['The Plaintiff argued that the prior decree did not adjudicate','The lower courts accepted this argument and found no bar'],materiality='The revision changes an unestablished legal endorsement into a purported party argument and judicial rationale not recorded by the supplied originals. Its impact on the substantive assessment remains unresolved.',severity_status='UNRESOLVED')
e['serious_errors']=[x for x in e['serious_errors'] if x['id']!='E06']
changes.append({'kind':'PAIRED_COMMON_UNITS_BEFORE_METHOD_MAP','from_blind':'T4K','to_blind':'O1W','old_web_assertions':len(old_e['assertions']),'common_base_before_forum':49,'new_actual_assertions':2,'weakened_removed_declaration':'No invented three-declaration proposition retained; generic actual statement only.','original_paired_web_labels_preserved':True})
save('labels-source-adjudicated-shared-units.json',adj)
save('source-adjudication-log.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method_map_opened':False,'changes':changes,'all4_reports_and_allowed_case_originals_read':True,'source_not_human_gold':True,'missing_T1W_coverage_not_filled':True,'no_metric_formula_or_report_or_source_changes':True,'canonical_paired_claims':{'T4K':len(c['assertions']),'O1W':len(e['assertions'])},'main_answer_axis_disagreements':'T4K coverage calls WRONG_OR_OVERREACH, assertion grader PARTIAL; both retained in raw files. Current merged scorer uses the original coverage-axis category; R/H do not use this subjective category.'})
# Remaining fourth report assertion pass is saved separately until its coverage can be received.
t=read('T1W-assertions-original.json');save('T1W-assertions-raw-web.json',t);x=next(x for x in t['assertions'] if x['id']=='A24');x.update(proposition='The judgment reports advice leading Gangabai to adopt again.',label='SUPPORTED',reason='Do not add the unspoken adverb definitively to the actual report. Apply the same narrated-advice reading as to the other reports; this is not independent exhibit proof.');t['assertions'].append({'id':'A_FORUM','proposition':'The present reviewing court was the Federal Court.','report_quote':'Before the Federal Court','label':'ANNOTATION_UNRESOLVED','evidence':[forum],'reason':'The recorded leave route does not conclusively identify the institution hearing this appeal; no hidden judgment or case-memory completion.'});save('T1W-assertions-source-adjudicated.json',t)
print({'reports':len(adj['reports']),'missing_coverage':'T1W','map_opened':False})
