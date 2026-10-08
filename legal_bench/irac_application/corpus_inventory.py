"""Discovery may read outcomes; supervised inputs are built separately."""
import json,sqlite3,hashlib,re
from pathlib import Path
SEALED={'38084532','123883887','12668753','120018816','84124','131143878','199292513','57407111'}
FAMILIES={'DRC_SUBLETTING':r'(sub.?let|part(?:ed|ing)? with possession|assign.*tenan)', 'DRC_BONA_FIDE':r'(bona.?fide|14\s*\(?\s*1\s*\)?\s*\(?\s*e\s*\)?)','LEASE_LICENCE':r'(licen[cs]e|lessor|lessee)'}
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def inventory(db,roots):
    con=sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True)
    placeholders=','.join('?' for _ in SEALED)
    metadata={str(i):json.loads(raw) for i,raw in con.execute('select doc_id,raw_json from cases where doc_id not in ('+placeholders+')',sorted(SEALED))};con.close()
    rows=[];seen=set()
    for root in roots:
        for p in sorted(Path(root).glob('*.json'),key=lambda p:int(p.stem) if p.stem.isdigit() else 10**20):
            ident=p.stem
            if ident in SEALED or ident in seen or not ident.isdigit():continue
            d=json.loads(p.read_text())
            if d.get('status')!='COMPLETE_RENDERING':continue
            seen.add(ident);text='\n'.join(s['text'] for s in d['segments'])
            m=metadata.get(ident,{})
            discovery=json.dumps(m,ensure_ascii=False)+'\n'+text
            families=[f for f,pattern in FAMILIES.items() if re.search(pattern,discovery,re.I)]
            rows.append(dict(case_id=ident,source_path=str(p),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),title=d.get('titles'),candidate_families=families,discovery_fields='existing metadata including issues/reasons/outcomes and full source; NOT model input',exposure='PREVIOUS_PREPARATION_OR_DEVELOPMENT_NOT_INDEPENDENT_TEST',association='UNCONFIRMED_UNLESS_EXPLICIT_DUPLICATE',group_id='DOC-'+ident))
    return rows
SCREEN_INSTRUCTIONS='''Task: source-grounded discovery for retrospective rule-given CONDITION application, not case win/lose. No external search. Read every supplied source; stop if any document cannot be read completely. Return downloadable JSON screen-XX.json once. Reference: model generated, not human gold.
For each document, identify at most ONE substantive issue with explicit application findings by the TARGET court (court rendering this judgment). A lower court may instead be target only if detailed reasoning, not mere outcome, is actually quoted; then identify the pre-target boundary. Court level is not a barrier. Do not infer findings from dismissed appeal or restoration alone. Identify family, jurisdiction, statutory version, target court/stage. Allowed families initially DRC_SUBLETTING (actual version separately), DRC_BONA_FIDE (actual provision separately), LEASE_LICENCE (lease/license legal classification). REJECT other claims or merely procedure; BORDERLINE may still contribute locally supervised conditions.
Output {cases:[{case_id,decision:"SUITABLE",family,law_scope,target_stage,target_court,substantive_issue,issue_refs:[{source_id,quote}],application_refs:[{source_id,quote}],allowed_spans:[{source_id,quote,semantic_stage:"PRE_TARGET_RECORD",statement_status:"CLAIMED",court_level:"NONE",reason}],excluded_stage_notes,independent_rule_leads,coverage_gaps,known_association}]}. decision is SUITABLE/BORDERLINE/REJECT, not joined options. REJECT still fill fields with null or [] as appropriate. allowed_spans need 4-12 SHORT EXACT contiguous quotes preserving decisive factual variation, opposing accounts, admissions and documented prior findings. You are specifying annotation partitions; you are NOT constructing model facts or target classes. Exclude the target court's application endorsements, evaluative descriptions, concluding facts, and HEADNOTES. Do NOT turn target findings into admissible factual assertions. A mixed paragraph can supply a separately contiguous neutral quoted span; no ellipses/rewrites. semantic_stage is PRE_TARGET_RECORD or PRIOR_COURT_FINDING; statement_status CLAIMED/DENIED/ADMITTED/DOCUMENT_RECORDED/PRIOR_FOUND/UNKNOWN, prior findings retain actual court level. Identifying speaker names is optional if status remains explicit. Target reasoning excerpts are application_refs, never allowed_spans. Conditions not decided must later be masked, not UNRESOLVED labels. Prefer a merits issue explicitly adjudicated, but no wholesale READY gate. Source support not absence of errors determines eligibility; don't reject a useful issue solely because other conditions incomplete. Do not create a law rule from target application. Include all cases, no quota; no model predictions provided.'''
def prepare(root):
    root=Path(root);out=root/'tasks';out.mkdir(exist_ok=True)
    rows=inventory('outputs/benchmark-pilot/data/cases.sqlite',['outputs/gnn-irac-native-data-01/sources/documents','outputs/rgcn-data-expansion-09/continuation-01/documents'])[:48]
    (root/'candidate-inventory.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False))
    protocol=dict(family_patterns=FAMILIES,max_detailed=48,actual_candidates=len(rows),selection='source root priority then numeric document ID; no verdict/performance selection',sealed_excluded_before_raw_db_read=sorted(SEALED),new_law_scope_per_source=True,grouping='explicit known associations merged before folds; otherwise uncertain marked',screen_output_fields='stage partition annotation separate from input extraction')
    (root/'discovery-protocol.json').write_text(json.dumps(protocol,indent=2))
    for i in range(0,len(rows),4):
        name='screen-%02d'%(i//4+1);body=SCREEN_INSTRUCTIONS.replace('screen-XX',name)+'\n'
        for r in rows[i:i+4]:
            d=json.loads(Path(r['source_path']).read_text());body+='\nDOCUMENT '+r['case_id']+' '+json.dumps(r['title'])+'\n'+json.dumps({'document_id':d['document_id'],'url':d.get('url'),'titles':d.get('titles'),'status':d['status'],'segments':[{'source_id':x['id'],'text':x['text']} for x in d['segments']]},ensure_ascii=False)+'\nEND DOCUMENT\n'
        body+='END_OF_TASK '+name
        (out/(name+'.txt')).write_text(body)
    return protocol
