"""Resolve independent excerpts then prepare rule-only decomposition tasks."""
import re,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[0]))
from irac02_prepare import R,OLD,IDS,rd,put,task,sha
pool={x['id']:x for x in rd('outputs/rgcn-sbc-finalization-11/sources-laws.json')}
raw=rd(R/'independent-sources/recovered-web.json')
parts=raw.split('--------------------------------------------------------------------------------\n')
# Explicit named response boundaries. Never combine lines across different documents.
def excerpt(doc,a,b,raw_name='recovered-web.json'):
 text=rd(R/'independent-sources'/raw_name);chunks=text.split('--------------------------------------------------------------------------------\n');hits=[c for c in chunks if c.splitlines()[0].endswith('https://indiankanoon.org/doc/'+doc+'/)')];assert len(hits)==1,(doc,len(hits))
 rows=[]
 for line in hits[0].splitlines():
  m=re.match(r'^L(\d+): (.*)$',line)
  if m and a<=int(m[1])<=b:rows.append({'id':'IK-'+doc+':L'+m[1],'text':m[2],'raw_source':raw_name})
 assert rows and rows[0]['id'].endswith(':L'+str(a)) and rows[-1]['id'].endswith(':L'+str(b));return rows
new=[('IRAC02:VN_CONTROL','190902',107,112,'Delhi High Court','1975-03-19','Delhi DRC14(1)(b), distinct sublet/assignment/parting branches; retained legal possession vs mere user', 'Doctrine not a universal rule equating company with tenant; actual ouster/control must be checked','recovered-web.json'),('IRAC02:VN_CORPORATE','190902',93,95,'Delhi High Court','1975-03-19','Corporate form versus real loss of possession/control','Factual illustration of controlling interest, not every company an alter ego; no target-specific conclusion','recovered-web.json'),('IRAC02:RAJBIR_INFERENCE','1946601',516,518,'Supreme Court of India','1988-08-09','East Punjab Urban Rent Restriction Act1949; consideration inference expressly invoked in Delhi precedent','Inference permissive/rebuttable, established exclusive possession and unacceptable explanation needed; not proof from presence alone','rajbir-rule-web.json'),('IRAC02:EA18','565566',38,39,'Parliament of India','1872','Indian Evidence Act1872 section18, historical evidentiary admissibility','Current statutory reproduction, no historical consolidation certification; do not apply successor2023 statute to historical case','recovered-web.json')]
for ident,doc,a,b,court,date,scope,lim,rn in new:
 segs=excerpt(doc,a,b,rn);u={'id':ident,'text':'\n'.join(s['text'] for s in segs),'source':{'document_id':doc,'url':'https://indiankanoon.org/doc/'+doc+'/','date':date,'court_or_publisher':court,'passage_addresses':[{'id':s['id']} for s in segs],'raw_path':str(R/'independent-sources'/rn),'raw_sha256':sha(R/'independent-sources'/rn)},'segments':segs,'scope':scope,'coverage_limit':lim,'legal_status':'INDEPENDENT_STATUTORY_OR_JUDGMENT_TEXT_REPRODUCTION','full_source_status':'EXCERPT_ONLY','source_status':'SOURCE_IDENTITY_AND_ADDRESS_CHECKED_NOT_SEMANTIC_GOLD'};pool[ident]=u
 if not (R/('independent-sources/'+ident.replace(':','_')+'.json')).exists():put('independent-sources/'+ident.replace(':','_')+'.json',u)
base='LAW:S02:DRC14:1b'
selection={
'308216':[base,'LAW:V09:HELP_GENUINENESS'],
'38604742':[base,'LAW:V09:AH_LICENCE','LAW:V09:AH_BURDEN','IRAC02:RAJBIR_INFERENCE'],
'1106992':[base,'IRAC02:VN_CONTROL','IRAC02:VN_CORPORATE'],
'1497837':[base,'LAW:V21:GR:REPORTED_DELHI'],
'1859043':[base,'LAW:S02:DRC:16','LAW:V09:AH_CONSENT_SCOPE'],
'111425525':[base,'LAW:S02:DRC:16','LAW:V09:AH_CONSENT_SCOPE','LAW:V09:CEL_CONTROL'],
'758831':[base,'LAW:V09:KR_BURDEN','IRAC02:RAJBIR_INFERENCE'],
'1381386':[base,'LAW:V09:KR_BURDEN','IRAC02:EA18']}
missing={'308216':['retained legal possession vs mere third-party use'], '38604742':['consideration and burden structure','permissive rebuttable inference'], '1106992':['retained legal possession','corporate form versus actual ouster'],'1497837':[], '1859043':[], '111425525':['retained-control legal possession'], '758831':['consideration may be inferred, not mandatory affirmative payment proof'], '1381386':['Evidence Act18 admission dependency']}
cases=[]
for cid in IDS:
 old=rd(OLD/'inputs'/f'{cid}.json');rules=[]
 for uid in selection[cid]:
  u=pool[uid];assert u['source']['document_id']!=cid
  rules.append({'rule_id':uid,'source_document':u['source'],'authority_type':'STATUTE' if uid in [base,'LAW:S02:DRC:16','IRAC02:EA18'] else 'PRECEDENT','court_jurisdiction':u['source'].get('court_or_publisher',u['source'].get('court','UNKNOWN')),'date':u['source'].get('date'),'exact_quote':u['text'],'scope':u['scope'],'limitations':u.get('coverage_limit',''),'independent_source_verified':True,'verification_meaning':'Different document identity and saved addressed original; independent semantic review still required','legal_status':u.get('legal_status','UNKNOWN')})
 basis={'case_id':cid,'oracle_selection_basis':'Target reasoning identifies only test identity; not an input feature or retrieval result','tests_to_restore':missing[cid],'added_decisive_tests_count':len(missing[cid]),'target_identity_source':str(OLD/'target-construction'/f'{cid}.json'),'target_identity_source_sha256':sha(OLD/'target-construction'/f'{cid}.json'),'source_priority':'Reuse30 pool; named independent Vishwa Nath/Rajbir/Evidence Act18 recovered as excerpts','not_rule_source':True};
 if not (R/('oracle-selection/'+cid+'.json')).exists():put('oracle-selection/'+cid+'.json',basis)
 case={'case_id':cid,'fixed_issue':old['fixed_issue'],'procedure_scope':old['stage'],'rules':rules,'missing_test_identities':missing[cid],'requested_new_tests_max':2};
 if not (R/('rule-candidates/'+cid+'.json')).exists():put('rule-candidates/'+cid+'.json',case);cases.append(case)
for j in range(2):
 task('P-'+str(j+1),'''RULE-ONLY Condition decomposition for four fixed retrospective development tasks. You have independent legal source excerpts, fixed issue/procedural scope and oracle-selected TEST IDENTITIES, but NO target application/element labels or target facts. Do not external-search or invent law. Return complete JSON file and code if short: {cases:[{case_id,rules:[{rule_id,source_document,authority_type,court_jurisdiction,date,exact_quote,scope,limitations,independent_source_verified}],conditions:[{condition_id,rule_id,description,exact_rule_quote,logical_role,dependencies:[{condition_id,operator}],scope,source_refs}],decisive_tests_count,rule_complete,gaps:[{kind,description}]}]}. Preserve provided Rule text/metadata; do not turn precedent illustration into this target's input fact. At most two requested missing decisive tests per case; existing basic statutory conditions may remain. Up to eight meaningful conditions if actually required, do not micro-split every word. Operators only AND,OR,QUALIFICATION. Dependencies must reference real condition IDs, clearly distinguish alternative subletting/assignment/parting routes, consideration only when legally relevant, timing, lack of written consent and evidentiary/retained-control qualifications. State whether a condition supports or qualifies a route; do not make retained possession and divestment simultaneous mandatory positives. Read each rule's full supplied text including exceptions. Never extrapolate Bombay/Goa/Punjab revisional power into Delhi substantive statutory scope, and record post-target dates as retrospective analogical limits. Fixed issue must preserve procedural posture; if independent sources do not support decisive procedural/test reasoning or an intended condition, rule_complete=false and GAP, rather than reverse-engineer labels. independent_source_verified means different saved document identity, NOT automatic legal authority approval. Conditions must only quote exact substrings/whitespace normalized of supplied independent rule; source_refs are rule passage IDs or rule_id when its source uses a different passage wrapper. No bindings/target outcomes/facts in output. Do not fill dates or burden from target unknowns.''',cases[j*4:j*4+4])
print('Rule-only tasks prepared; four named independent excerpts recovered; no labels provided')
