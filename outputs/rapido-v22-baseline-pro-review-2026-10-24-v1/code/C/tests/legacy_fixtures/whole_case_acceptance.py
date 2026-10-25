"""One offline whole-workflow acceptance suite. SYNTHETIC semantics, never model evidence.

The fake provider is unavailable in run.py. Real cases are used only for original
source integrity/preparation and old failure preservation, never injected answers.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2];REPO=ROOT.parents[1]
sys.path[:0]=[str(ROOT/'src'),str(REPO)]
import contracts as C
import engine as E
from common import digest,prepare_sources,read,save,source_spans,SCOPE_FIELDS
from runner import run_arm,Session,build_shared
from updates import apply_update

PACKET={'case_id':'SYNTHETIC-ENGINEERING-ONLY','question':'Explain Dana possession, procedural permission, counterevidence and unresolved title.',
    'scope':'Fictional test, no legal effect','sources':[
        {'source_id':'fixture:inspection','text':'On 1910-01-01 inspection records Dana occupying the West parcel.','origin_group':'inspection'},
        {'source_id':'fixture:court','text':'The Trial Court previously recorded possession. It is not a title determination.','origin_group':'judgment'},
        {'source_id':'fixture:gate','text':'The procedural application is admitted. No exclusion order is recorded. Title remains unresolved.','origin_group':'docket'}]}
LIB={'version':'SYNTHETIC-RULES-NOT-LAW','authority_clips':[{'id':'LAW:FIXTURE','text':'FICTIONAL TEST ONLY: an occupied parcel and admitted procedure satisfy this limited test. An exclusion order blocks it. Title is independent.','origin_group':'fictional-standard'}],
    'rules':[{'id':'FIXTURE','predicates':{'possession':'Actual possession','gate':'Admitted procedure'},
        'expression':{'op':'AND','args':[{'op':'REF','id':'possession'},{'op':'REF','id':'gate'}]},
        'refs':['LAW:FIXTURE'],'execution_enabled':True,'original_text_verified':True,'effective_from':'1900-01-01','temporal_mode':'GOVERNED_EVENT'}]}

def fixture_wire(tag,value,request=None):
    # Fictional provider emits the public decoder contract. The production adapter
    # then derives addresses exactly as it does for an actual model response.
    tag=tag.removeprefix('repair-')
    if tag in ('objects','direct-objects'):
        for row in value['objects']:
            row.setdefault('extent','SINGLE_UNIT' if row['kind']=='PROPERTY' else 'NOT_PROPERTY')
            row.setdefault('components',[])
    elif tag in ('scopes','direct-scopes'):
        for row in value['scopes']:
            row.setdefault('participant_roles',[{'object_id':row['actors'][0],'role':'occupant','witnesses':[{'span_id':source_spans(row['refs'][0],request['material']['sources'][row['refs'][0]].get('text',''.join(x['text'] for x in request['material']['sources'][row['refs'][0]].get('passages',[]))))[0][0]}]}] if row['actors'] else [])
            if 'time_choice' in row:continue
            literal=row.pop('time')
            row['time_choice']=next(i for i,x in request['material']['literal_time_choices'].items() if x['time']==literal)
    elif tag in ('tasks','direct-report-outline'):
        for row in value['tasks'].values():
            if 'kind_rule' not in row:row['kind_rule']=row.pop('kind')+':'+row.pop('rule_id')
            row.setdefault('source_owner','NONE')
            row.setdefault('rule_condition','FIXTURE:possession' if row['proposition']=='occupancy' else 'FIXTURE:'+row['proposition'] if row['proposition'] in ('possession','gate') else 'NONE')
    elif tag.startswith('identity-'):
        for row in value.values():row.pop('refs',None)
    elif tag.startswith('scope-review-'):
        for parts in value.values():
            for row in parts.values():row.pop('refs',None);row.pop('assessed',None);row['source_event']='Fictional 1910 inspection scope'
            parts['time'].update(event_relation='MATCH',time_role='EVENT_DATE')
    elif tag.startswith('final-review-'):
        for group in ('items','comparisons'):
            for row in value[group].values():
                if 'refs' in row:row['reviewed_refs']=row.pop('refs')
        value['whole_source_coverage'].pop('complete',None)
        inventory=request['material']['material'].get('source_inventory',{})
        report=request['material']['material']['exact_report']
        value['whole_source_coverage']['obligations']={}
        for i,o in inventory.get('obligations',{}).items():
            items=[tid for tid,x in report['items'].items() if i in x['obligation_ids']]
            selected=list(dict.fromkeys(rid for tid in items for rid in report['items'][tid]['support_ids']))
            value['whole_source_coverage']['obligations'][i]={'status':'COMPLETE','report_item_ids':items,
                'answer_record_ids':selected,'answer_relation':'DIRECT_RECORD' if o['answerability']=='KNOWN_RECORD' else 'CONDITIONAL_DERIVATION',
                'refs':o['refs'],'reason':'Fictional explicit question-to-record correspondence','repair_target':'REPORT'}
        for row in value['whole_source_coverage']['omissions']:
            if 'classification' in row:
                pair=(row.pop('classification'),row.pop('information_target'))
                row['finding_class']=next(k for k,v in C.OMISSION_CLASSES.items() if v==pair)
    if request is not None:
        m=request['material']['material'];src=request['material']['sources']
        def sw(ref):
            text=src[ref].get('text',''.join(x['text'] for x in src[ref].get('passages',[])))
            return {'span_id':source_spans(ref,text)[0][0]}
        if tag.startswith('uses-'):
            for part in value.values():
                for row in part['uses']:
                    if 'source_record_mode' in row:continue
                    tid=next(i for i,part2 in value.items() if part2 is part)
                    name=task_name(m['tasks'][tid])
                    row['source_record_id']=next((i for i,r in m['source_records'].items() if r['event']=='fixture:'+name),next(iter(m['source_records'])))
                    for field in ('text','refs','source_owner'):row.pop(field,None)
                    if 'use_mode' not in row:
                        selected={k:row.pop(k) for k in ('content_role','status','purpose')}
                        row['use_mode']=next(k for k,v in C.USE_MODES.items() if v==selected)
                    rid=row.pop('source_record_id');wanted=row.pop('use_mode');selected=C.USE_MODES[wanted]
                    options=[k for k,v in C.USE_MODES.items() if v['status']==m['source_records'][rid]['status'] and v['content_role']==m['source_records'][rid]['content_role'] and v['purpose']==selected['purpose']]
                    row['source_record_mode']=rid+'|'+next((k for k in options if C.USE_MODES[k]['content_role']==selected['content_role']),options[0])
        elif tag.startswith(('use-review-','analogy-review-','task-review-')):
            for ident,parts in value.items():
                for part,row in parts.items():
                    if 'source_meaning' in request['schema']['properties'][ident]['properties'][part]['properties']:
                        row['source_meaning']='Fictional original source meaning for engineering only.'
                        row['witnesses']=[sw(row['refs'][0])] if row['refs'] else []
                if tag.startswith('use-review-'):
                    use=m['subjects'][ident];scope=m['scopes'][m['tasks'][use['task_id']]['scope_id']];record=m['source_records'][use['source_record_ids'][0]]
                    parts['attribution'].update(observed_owner=use['source_owner'],observed_status=use['status'],owner_relation='MATCH')
                    parts['binding'].update(observed_actors=record['actors'],observed_properties=record['properties'],
                        record_event=record['event'],scope_relation='MATCH')
                    parts['scope_bridge']={'source_hash':digest(record),'target_hash':digest(scope),
                        'dimensions':{k:{'relation':'MATCH','reason':'Explicit fictional source/target relation','case_witnesses':[sw(record['refs'][0])],'law_witnesses':[]} for k in ('actors','properties','time','procedure','court','request')},
                        'roles':{str(n):{'target_role':'0','decision':'ACCEPT','reason':'Fictional occupant maps to occupant','witnesses':[sw(record['refs'][0])]} for n,r in enumerate(record['participant_roles'])}}
        elif tag.startswith('analogies-'):
            for row in value['analogies'].values():
                row['history_reading']={k:'Fictional distinct dispute, engineering only.' for k in ('issue','actors_property','proceeding','recorded_position','uncertainty')}
        elif tag in ('report','report-revision'):
            for row in value['comparisons'].values():row.pop('include',None);row.pop('refs',None)
        elif tag.startswith('final-review-'):
            value['source_records']={}
            for item in m['exact_report']['items'].values():
                for segment in item.get('segments',[]):
                    uid=segment.get('source_use_id')
                    if uid:
                        value['source_records'][uid]={'source_meaning':'Fictional reviewed record only','field_findings':[],'witnesses':[sw(segment['refs'][0])],
                            'reason':'Fictional semantic fixture, not a real judgment','refs':segment['refs'],'decision':'ACCEPT',
                            'observed_owner':segment['source_owner'],'observed_status':segment['status'],'observed_content_role':segment['content_role']}
            for hid,row in value['comparisons'].items():
                item=m['exact_report']['comparisons'][hid]
                row['history_meaning']='Fictional historical dispute.';row['current_meaning']='Fictional current record.'
                row['history_witnesses']=[sw(i) for i in item['refs'] if src[i]['domain']=='HISTORY'][:3]
                row['case_witnesses']=[sw(i) for i in item['refs'] if src[i]['domain']=='CASE'][:3]
                if not item['include']:row['decision']='OMISSION_JUSTIFIED'
    return value

def task_name(t):
    return t['rule_condition'].split(':',1)[1] if t.get('question_origin')=='FROZEN_RULE_CONDITION_NOT_CASE_ANSWER' else t['proposition']

def task_names(tasks):
    return {task_name(t):i for i,t in tasks.items()}

class FixtureProvider:
    kind='SYNTHETIC_ENGINEERING_FIXTURE_NOT_MODEL_OUTPUT'
    def __init__(self,scenario='normal'):self.scenario=scenario;self.calls=[]
    def definitions(self,tag):
        return [('prior','ATTRIBUTION','GROUND'),('possession','FACT','GROUND'),('gate','PROCEDURE','PROOF'),('result','DERIVED','SUMMARY'),('exclusion','FACT','COUNTERARGUMENT'),('title','FACT','LIMITATION')]
    def call(self,cid,arm,tag,request,attempt=0):
        self.calls.append(tag);rawtag=tag;tag=tag.removeprefix('repair-');m=request['material']['material'];sources={i:{**v,'text':v.get('text',''.join(x['text'] for x in v.get('passages',[])))} for i,v in request['material']['sources'].items()};case=[i for i,v in sources.items() if v['domain']=='CASE' and v['original_id'].startswith('fixture:')];law=[i for i,v in sources.items() if v['domain']=='LAW']
        refs=case+law
        def dec(accept=True,rs=None):return {'decision':'ACCEPT' if accept else 'UNRESOLVED','reason':'SYNTHETIC TEST verdict; no real legal judgment','refs':rs if rs is not None else refs}
        if self.scenario=='technical_failure' and tag=='objects':raise RuntimeError('SYNTHETIC_TRANSPORT_FAILURE')
        if tag in ('objects','direct-objects'):
            value={'objects':[{'name':'Dana','kind':'PARTY','description':'Fictional possessor','refs':[case[0]]},{'name':'Trial Court','kind':'COURT','description':'Earlier court','refs':[case[1]]},{'name':'West','kind':'PROPERTY','description':'West parcel','refs':[case[0]]}],'unresolved':[]}
        elif tag in ('scopes','direct-scopes'):
            os=m['objects'];value={'scopes':[{'actors':[i for i,o in os.items() if o['kind']=='PARTY'],
                'properties':[i for i,o in os.items() if o['kind']=='PROPERTY'],'time':'1910-01-01','stage':'TRIAL_RECONSTRUCTION','court':next(i for i,o in os.items() if o['kind']=='COURT'),
                'record_level':'PRIOR_PROCEEDING','request':'Fictional limited relief','jurisdiction':'FICTIONAL','procedure':'TRIAL','refs':case}]}
        elif tag.endswith('-counts'):
            definitions=self.definitions(rawtag)
            value={'counts':{section:sum(row[2]==section for row in definitions) for section in C.PLAN_GROUPS},'coverage_limitations':[]}
        elif tag in ('tasks','direct-report-outline'):
            definitions=self.definitions(rawtag)
            value={'tasks':[{'proposition':name,'scope_id':next(iter(m['scopes'])),'kind':kind,'rule_id':'FIXTURE' if kind=='DERIVED' else 'NONE',
                'source_owner':next(i for i,o in m['objects'].items() if o['kind']=='COURT') if kind=='ATTRIBUTION' else 'NONE',
                'effect':'CONTROLLING_GATE' if name=='gate' else 'DESCRIPTIVE','section':'GROUND' if section=='PROOF' else section,'role':'PROOF' if section=='PROOF' else 'REPORT','importance':'IMPORTANT','burden_holder':'Fictional standard','standard':'Fictional source-based condition',
                'authority_refs':law,'question_basis_refs':case,'why_required':'Important fictional question'} for name,kind,section in definitions], 'coverage_limitations':[]}
            counters={section:0 for section in C.PLAN_GROUPS};slots={}
            for row in value['tasks']:
                section='PROOF' if row['role']=='PROOF' else row['section'];counters[section]+=1;slots[section+'_'+str(counters[section])]=row
            value['tasks']=slots
        elif tag=='task-equivalence':value={'groups':[]}
        elif tag.endswith('retrieval-queries'):
            value={i:{a:t['proposition'] for a in ('SUPPORT','OPPOSITION','EXCEPTION')} for i,t in m['tasks'].items()}
        elif tag.startswith('analogies-'):value={'analogies':{}}
        elif tag=='burdens':value={'burdens':[]}
        elif tag=='requests':value={'requests':[]}
        elif tag.startswith('uses-'):
            value={}
            for tid,t in m['tasks'].items():
                name=task_name(t);state='FALSE' if name=='exclusion' else 'UNKNOWN' if name=='title' or (name=='gate' and self.scenario=='unknown_gate') else 'TRUE'
                value[tid]={'uses':[] if name=='result' else [{'text':name+' sourced statement','refs':case,'status':'COURT_RECORDED' if name=='prior' else 'REPORTED_EVIDENCE',
                    'source_owner':next((i for i,o in m['objects'].items() if o['kind']=='COURT'),'UNRESOLVED') if name=='prior' else 'NONE','content_role':'ATTRIBUTION' if name=='prior' else 'OBSERVATION',
                    'purpose':'REPORT_ASSERTION' if name=='prior' else 'ESTABLISH_OCCURRENCE','state':state,'contribution':'Fictional contribution','limitations':[]}]}
        elif tag.startswith('bundles-'):
            value={}
            for tid,t in m['tasks'].items():
                ids=[i for i,u in m['uses'].items() if u['task_id']==tid];state=m['uses'][ids[0]]['state'] if ids else 'UNKNOWN'
                value[tid]={'bundles':[] if not ids else [{'use_ids':ids,'state':state,'proof_status':'SATISFIED' if state=='TRUE' else 'NOT_SATISFIED' if state=='FALSE' else 'UNRESOLVED',
                    'complete':state!='UNKNOWN','components':[{'condition':'Whole fictional condition','use_ids':ids,'covered':state!='UNKNOWN'}],
                    'missing':[] if state!='UNKNOWN' else ['Not established'],'reason':'Fictional joint assessment','alternative_explanation':'No independent alternative claimed',
                    'counter_use_ids':[],'sufficiency_authority_refs':law,'origin_assessment':'Shared origins retained'}]}
        elif tag.startswith('applications-'):
            ts=m['tasks'];by=task_names(ts);value={i:{'selected':True,'premises':{'possession':by['possession'],'gate':by['gate']},
                'applicability':'APPLICABLE','predicate_intervals':{},'event_interval':{'from':'1910-01-01','to':'1910-01-01','refs':case},'reason':'Fictional scope'} for i in request['schema']['properties']}
        elif tag=='paths':
            by=task_names(m['tasks']);value={'paths':[{'name':'Fictional relief path','scope_id':next(iter(m['scopes'])),
                'conclusion_task':by['result'],'supports':[by['result']],'alternatives':[],'gates':[by['gate']],'blockers':[by['exclusion']],
                'exceptions':[],'authority_refs':law,'reason':'Fictional sourced relation'}],'search_complete':True,'unrepresented_paths':[]}
        elif tag.startswith(('scope-review-','task-review-')):
            value={i:{part:dec(rs=case if part!='law' else refs) for part in spec['properties']} for i,spec in request['schema']['properties'].items()}
            if tag.startswith('scope-review-'):
                for ident,parts in value.items():
                    for part,rec in parts.items():
                        fields=SCOPE_FIELDS[part]
                        rec['assessed']={k:m['subjects'][ident][k] for k in fields}
                        rec['witnesses']=[{'span_id':source_spans(case[0],sources[case[0]]['text'])[0][0]}]
        elif tag.startswith(('identity-','path-review-')):
            value={i:dec(not(self.scenario=='wrong_identity' and tag.startswith('identity') and row.get('name')=='Dana'),case if tag.startswith(('identity','scope-review')) else refs) for i,row in m['subjects'].items()}
            if tag.startswith('identity'):
                for i,row in m['subjects'].items():value[i].update(observed_kind=row['kind'],identity_witnesses=[{'span_id':source_spans(row['refs'][0],sources[row['refs'][0]]['text'])[0][0]}])
        elif tag.startswith(('use-review-','bundle-review-','application-review-')):
            value={i:{part:dec(rs=[r for r in refs if r in ps['properties']['refs']['items'].get('enum',[])]) for part,ps in spec['properties'].items() if part!='scope_bridge'} for i,spec in request['schema']['properties'].items()}
        elif tag=='direct-analysis':value={'analysis':'Fictional competing positions, originals rechecked','uncertainties':['Title unresolved']}
        elif tag in ('report','report-revision'):
            value={'items':{},'comparisons':{}}
            allowed=request['schema']['properties']['items']['properties']
            # Support IDs come from the prompt registry and are selected, never invented.
            evidence=json.loads(m.get('fallible_analysis',{}).get('same_model_information','{}'))
            evidence.setdefault('uses',m.get('fallible_analysis',{}).get('qualified_source_uses',{}));evidence.setdefault('analogies',m.get('comparison_registry',{}))
            for tid,t in C.report_tasks(m['tasks']).items():
                ids=allowed[tid]['properties']['support_ids']['items'].get('enum',[])
                us=[i for i in ids if i.startswith('U') and evidence.get('uses',{}).get(i,{}).get('task_id')==tid]
                ps=[i for i in ids if i.startswith('P')]
                kind='ATTRIBUTED' if t['kind']=='ATTRIBUTION' else 'DERIVED' if t['kind']=='DERIVED' else 'UNKNOWN' if t['proposition']=='title' else 'FACTUAL'
                if kind not in allowed[tid]['properties']['kind']['enum']:kind='CONDITIONAL'
                value['items'][tid]={'include':True,'section':t['section'],'text':t['proposition']+' complete fictional report','kind':kind,
                    'attributed_to':next((i for i,o in m['objects'].items() if o['kind']=='COURT'),'UNRESOLVED') if kind=='ATTRIBUTED' else 'NONE','consequence_scope':'LOCAL_ARGUMENT' if kind=='DERIVED' else 'DESCRIPTION','outcome':'DESCRIPTION','refs':refs,'support_ids':ps if kind=='DERIVED' else us}
                if kind=='CONDITIONAL':value['items'][tid]['text']='Fictional relief remains conditional because the required gate is unresolved.'
            comparisons=evidence.get('analogies',m.get('fallible_analysis',{}).get('historical_comparisons',{}))
            for hid in request['schema']['properties']['comparisons']['properties']:
                h=comparisons[hid]
                value['comparisons'][hid]={'include':True,'text':'Different fictional dispute: comparison only, not current facts.',
                    'refs':h['history_refs']+h['case_refs'],'disposition':'USED','reason':'Explains a fictional competing interpretation.'}
        elif tag.startswith('final-review-'):
            value={'items':{},'comparisons':{},'whole_source_coverage':{'complete':True,'reason':'Synthetic complete report','omissions':[]},'source_disagreements':[]}
            for group in ('items','comparisons'):
                for ident,item in m['exact_report'].get(group,{}).items():
                    r=item['refs'][0] if item['refs'] else refs[0]
                    role='COMPARISON' if group=='comparisons' else 'ATTRIBUTION' if item['kind']=='ATTRIBUTED' else 'LEGAL_CONCLUSION' if item['kind']=='DERIVED' else 'CONDITIONAL' if item['kind']=='CONDITIONAL' else 'VIEW_LIMIT' if item['kind']=='UNKNOWN' else 'OBSERVATION'
                    value[group][ident]={**dec(rs=list(dict.fromkeys(item['refs']+[r]))), 'serious_error':False,'important_content_complete':True,'body_meaning':item['text'],'substantive_text':True,
                        'revision_class':'NO_CORRECTION_REQUIRED','revision_refs':[],'repair_target':'REPORT','content_role':role,
                        'source_owner':item.get('attributed_to','NONE'),'witnesses':[{'span_id':source_spans(r,sources[r]['text'])[0][0]}],'error_types':[]}
            if self.scenario=='omission':value['whole_source_coverage']={'complete':False,'reason':'Missing issue not in the proposed task list','omissions':[{'question':'What is the independent omitted issue?','refs':case,'importance':'IMPORTANT','classification':'ALLOWED_SOURCE_OMISSION','information_target':'ALLOWED_RECORD','basis':'Fictional positive source','repair_target':'TASKS'}]}
            if self.scenario=='unchanged_revision':
                tid=next(iter(value['items']))
                value['items'][tid].update(decision='REJECT',serious_error=True,
                    revision_class='ALLOWED_SOURCE_ERROR',revision_refs=case[:1],
                    error_types=['UNSUPPORTED_REASON'],repair_target='REPORT')
        else:raise AssertionError('UNHANDLED_STAGE:'+tag)
        value=fixture_wire(tag,value,request)
        C.validate(value,request['schema'])
        return value,{'status':'OK','usage':{'prompt_tokens':0,'completion_tokens':0},'elapsed_seconds':0,'synthetic':True,'pipeline_request_hash':digest(request)}

class WholeCaseAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=read(ROOT/'protocol.json');cls.snapshot=prepare_sources(PACKET,LIB)
        cls.temp=None if '--record' in sys.argv else tempfile.TemporaryDirectory();cls.dest=(ROOT/'private/engineering'/str(__import__('time').time_ns())) if cls.temp is None else Path(cls.temp.name)
    @classmethod
    def tearDownClass(cls):
        if cls.temp:cls.temp.cleanup()
    def run_case(self,name,scenario='normal',arm='C'):
        dest=self.dest/name;provider=FixtureProvider(scenario)
        result=run_arm(provider,self.snapshot,self.cfg,dest,arm)
        return result,dest,provider
    def test_01_complete_original_to_report(self):
        result,dest,provider=self.run_case('normal')
        self.assertTrue(result['complete_chain'],result)
        self.assertTrue(result['internal_pass'],result)
        self.assertIsNone(result['independent_quality_score'])
        comp=read(dest/'computation.json')
        self.assertTrue(any(v['state']=='TRUE' for v in comp['computed']['rules'].values()))
        self.assertTrue(any(x['report_eligible'] for x in comp['accepted']['uses'].values()))
        shared=read(dest/'shared.json')
        prior=[i for i,t in shared['proposal']['tasks'].items() if t['proposition']=='prior'][0]
        self.assertEqual(comp['computed']['task_states'][prior],'UNKNOWN')
        self.assertTrue(read(dest/'final-report.json')['items'][prior]['include'])
        request=read(next((dest/'requests').glob('identity-*.json')))
        self.assertNotIn('frozen_law',request['material'])
        self.assertEqual(set(request['material']['material']),{'subjects'})
        self.assertNotIn('question',request['material'])
        self.assertTrue(any(t['role']=='PROOF' for t in shared['proposal']['tasks'].values()))
        self.assertFalse(any(tid in read(dest/'final-report.json')['items'] for tid,t in shared['proposal']['tasks'].items() if t['role']=='PROOF'))
        self.assertEqual(len(provider.calls),len(set(provider.calls)))
    def test_02_false_identity_blocks_dependent_execution(self):
        result,dest,_=self.run_case('wrong','wrong_identity')
        self.assertTrue(result['complete_chain']);self.assertFalse(result['internal_pass'])
        comp=read(dest/'computation.json');self.assertFalse(comp['computed']['scope_supported'])
    def test_03_unknown_gate_prevents_relief(self):
        result,dest,_=self.run_case('unknown','unknown_gate')
        self.assertTrue(result['complete_chain'])
        comp=read(dest/'computation.json')['computed']
        self.assertTrue(all(x['state']=='UNRESOLVED' for x in comp['paths'].values()))
        final=read(dest/'final-report.json')
        self.assertFalse(any(x['kind']=='DERIVED' for x in final['items'].values()))
        self.assertTrue(any('gate is unresolved' in x['text'] for x in final['items'].values()))
    def test_04_independent_source_coverage_detects_unlisted_omission(self):
        result,dest,provider=self.run_case('omission','omission')
        self.assertFalse(result['internal_pass']);self.assertIn('repair-tasks',provider.calls)
        self.assertTrue(result['check']['whole_source_coverage']['omissions'])
    def test_05_technical_failure_null_not_unknown_and_one_retry(self):
        result,dest,provider=self.run_case('failure','technical_failure')
        self.assertFalse(result['complete_chain']);self.assertIsNone(result['answer']);self.assertEqual(provider.calls,['objects','objects'])
    def test_06_shared_ABCs_and_exact_intermediate_identity(self):
        result,dest,_=self.run_case('C-shared')
        shared=read(dest/'shared.json');provider=FixtureProvider();bdest=self.dest/'B-shared'
        b=run_arm(provider,self.snapshot,self.cfg,bdest,'B',shared)
        self.assertTrue(b['complete_chain']);self.assertNotIn('objects',provider.calls)
        c_request=read(dest/'requests/report.json')['material']['material']['fallible_analysis']
        b_request=read(bdest/'requests/report.json')['material']['material']['fallible_analysis']
        self.assertEqual(c_request['same_model_information'],b_request['same_model_information'])
        self.assertNotIn('compact_computation',b_request)
        a,adest,ap=self.run_case('A-direct',arm='A');self.assertTrue(a['complete_chain']);self.assertIn('direct-analysis',ap.calls)
        ledger=read(adest/'retrieval-ledger.json')
        report_request=read(adest/'requests/report.json')
        sent=report_request['material']['material']['fallible_analysis']['retrieval']
        self.assertEqual(sent['selected_ids'],ledger['selected_ids'])
        self.assertNotIn('tasks',sent)
        self.assertEqual({t['section'] for t in report_request['material']['material']['tasks'].values()},set(C.SECTIONS))
    def test_07_source_update_changes_identity_and_revokes_old_review(self):
        result,dest,_=self.run_case('update-base');sh=read(dest/'shared.json')
        ev={'kind':'REVEAL_SOURCE','parent_snapshot':self.snapshot['snapshot_id'],'reason':'New actual fixture record',
            'acquisition_record':'fixture-only-not-real-evidence','sources':[{'source_id':'fixture:new','text':'New source, not a correct predicate.'}]}
        updated,receipt=apply_update(self.snapshot,ev)
        self.assertTrue(receipt['new_evidence_obtained']);self.assertFalse(updated['prior_acceptances_transferred'])
        with self.assertRaisesRegex(ValueError,'VERSION'):E.inspect(updated,sh['proposal'],sh['reviews'])
        with self.assertRaisesRegex(ValueError,'REPLACE'):apply_update(self.snapshot,{**ev,'sources':[PACKET['sources'][0]]})
        self.assertEqual(len(self.snapshot['directory']),4)
    def test_08_revocation_rereview_second_revocation(self):
        _,dest,_=self.run_case('revoke-base');sh=read(dest/'shared.json');p=sh['proposal'];r=sh['reviews']
        target=next(i for i,t in p['tasks'].items() if t['proposition']=='possession')
        use=next(i for i,u in p['uses'].items() if u['task_id']==target)
        a=E.inspect(self.snapshot,p,r,[use]);comp=E.compute(self.snapshot,p,r,a,self.cfg)
        self.assertEqual(comp['task_states'][target],'UNKNOWN')
        # A new synthetic whole run is explicitly a simulated re-review, never copied ACCEPT.
        _,other,_=self.run_case('synthetic-rereview');fresh=read(other/'shared.json')
        a=E.inspect(self.snapshot,fresh['proposal'],fresh['reviews']);comp=E.compute(self.snapshot,fresh['proposal'],fresh['reviews'],a,self.cfg)
        self.assertEqual(comp['task_states'][target],'TRUE')
        a=E.inspect(self.snapshot,fresh['proposal'],fresh['reviews'],[use]);self.assertFalse(a['uses'][use]['report_eligible'])
    def test_09_hypothesis_cannot_flip_adverse_fact(self):
        _,dest,_=self.run_case('hypo-base');sh=read(dest/'shared.json');p=sh['proposal'];r=sh['reviews'];a=E.inspect(self.snapshot,p,r)
        by={t['proposition']:i for i,t in p['tasks'].items()}
        with self.assertRaisesRegex(ValueError,'KNOWN_FACT'):E.compute(self.snapshot,p,r,a,self.cfg,{by['exclusion']:'TRUE'})
        hypo=E.compute(self.snapshot,p,r,a,self.cfg,{by['title']:'TRUE'})
        self.assertEqual(hypo['namespace'],'HYPOTHETICAL');self.assertTrue(hypo['conditional_not_actual'])
        self.assertEqual(E.compute(self.snapshot,p,r,a,self.cfg)['task_states'][by['title']],'UNKNOWN')
    def test_10_version_conflict_and_immutable_results(self):
        _,dest,_=self.run_case('version-base');sh=read(dest/'shared.json');p=copy.deepcopy(sh['proposal'])
        p['coverage_limitations'].append('changed version')
        with self.assertRaisesRegex(ValueError,'VERSION'):E.inspect(self.snapshot,p,sh['reviews'])
        with self.assertRaisesRegex(ValueError,'EXISTING_ATTEMPT'):run_arm(FixtureProvider(),self.snapshot,self.cfg,dest,'C')
    def test_11_final_duplicate_and_missing_section_not_passed(self):
        _,dest,_=self.run_case('dup-base');sh=read(dest/'shared.json');artifact=read(dest/'reports/0.json');report=artifact['report'];review=artifact['review'];p=sh['proposal']
        ids=[i for i,item in report['items'].items() if item['kind']=='FACTUAL'];report['items'][ids[1]].update(text=report['items'][ids[0]]['text'],kind=report['items'][ids[0]]['kind'])
        check=E.check_report(self.snapshot,p,report,review)
        self.assertFalse(check['internal_pass']);self.assertTrue(any('DUPLICATE' in str(x) for x in check['problems']))
    def test_12_counterevidence_exception_and_independent_path(self):
        _,dest,_=self.run_case('path-base');sh=read(dest/'shared.json');p=copy.deepcopy(sh['proposal']);r=copy.deepcopy(sh['reviews'])
        by={t['proposition']:i for i,t in p['tasks'].items()};pid=next(iter(p['paths']))
        # Program scenario: exception defeats its named blocker, never an unrelated gate.
        p['paths'][pid]['blockers']=[by['possession']]
        p['paths'][pid]['exceptions']=[{'blocker_task':by['possession'],'exception_task':by['gate'],
            'authority_refs':p['paths'][pid]['authority_refs']}]
        r=E.envelope(self.snapshot,p,r['values']);a=E.inspect(self.snapshot,p,r);c=E.compute(self.snapshot,p,r,a,self.cfg)
        self.assertEqual(c['paths'][pid]['state'],'CONDITIONS_MET_IN_DECLARED_SCOPE')
        # A separate path blocked by a known fact does not invalidate that successful path.
        other=copy.deepcopy(p['paths'][pid]);other['exceptions']=[];p['paths']['P-independent']=other
        r['values']['paths']['P-independent']=copy.deepcopy(r['values']['paths'][pid]);r=E.envelope(self.snapshot,p,r['values'])
        a=E.inspect(self.snapshot,p,r);c=E.compute(self.snapshot,p,r,a,self.cfg)
        self.assertEqual(c['paths'][pid]['state'],'CONDITIONS_MET_IN_DECLARED_SCOPE')
        self.assertEqual(c['paths']['P-independent']['state'],'BLOCKED')
    def test_13_cyclic_derivation_is_unresolved_not_silent_success(self):
        _,dest,_=self.run_case('cycle-base');sh=read(dest/'shared.json');p=copy.deepcopy(sh['proposal']);r=sh['reviews']
        derived=next(iter(p['applications']));p['applications'][derived]['premises']['possession']=derived
        r=E.envelope(self.snapshot,p,r['values']);a=E.inspect(self.snapshot,p,r);c=E.compute(self.snapshot,p,r,a,self.cfg)
        self.assertFalse(c['search_complete']);self.assertEqual(c['task_states'][derived],'UNKNOWN')
        self.assertEqual(c['rules'][derived]['status'],'UNRESOLVED_CYCLE_OR_COMPUTATION_LIMIT')
    def test_14_same_origin_not_independent_votes_and_conflict_not_false(self):
        _,dest,_=self.run_case('conflict-base');sh=read(dest/'shared.json');p=copy.deepcopy(sh['proposal']);rv=copy.deepcopy(sh['reviews']['values'])
        tid=next(i for i,t in p['tasks'].items() if t['proposition']=='possession')
        bid=next(i for i,b in p['bundles'].items() if b['task_id']==tid)
        contrary=copy.deepcopy(p['bundles'][bid]);contrary.update(state='FALSE',proof_status='NOT_SATISFIED')
        p['bundles']['B-opposing']=contrary;rv['bundles']['B-opposing']=copy.deepcopy(rv['bundles'][bid])
        r=E.envelope(self.snapshot,p,rv);a=E.inspect(self.snapshot,p,r);c=E.compute(self.snapshot,p,r,a,self.cfg)
        self.assertEqual(c['task_states'][tid],'CONFLICTED')
        self.assertTrue(a['bundles'][bid]['independence_is_not_sufficiency'])
    def test_15_old_stage_review_cannot_accept_new_stage(self):
        _,dest,_=self.run_case('stage-base');sh=read(dest/'shared.json');p=copy.deepcopy(sh['proposal']);sid=next(iter(p['scopes']))
        p['scopes'][sid]['stage']='OTHER_PROCEEDING'
        with self.assertRaisesRegex(ValueError,'VERSION'):E.inspect(self.snapshot,p,sh['reviews'])
    def test_16_historical_facts_cannot_enter_target_uses(self):
        packet=copy.deepcopy(PACKET);packet['sources'].append({'source_id':'analogy:1','text':'Other dispute had adverse facts','document_role':'ANALOG'})
        snapshot=prepare_sources(packet,LIB);hist=[i for i,x in snapshot['directory'].items() if x['domain']=='HISTORY']
        self.assertEqual(len(hist),1)
        _,dest,_=self.run_case('history-base');p=read(dest/'shared.json')['proposal'];schema=C.uses(snapshot,p['tasks'],self.cfg)
        for spec in schema['properties'].values():
            allowed=spec['properties']['uses']['items']['properties']['refs']['items']['enum'];self.assertNotIn(hist[0],allowed)
    def test_17_cannot_omit_controlling_gate_from_path(self):
        _,dest,_=self.run_case('gate-omission');sh=read(dest/'shared.json');p=copy.deepcopy(sh['proposal']);rv=sh['reviews']['values']
        pid=next(iter(p['paths']));p['paths'][pid]['gates']=[]
        r=E.envelope(self.snapshot,p,rv);a=E.inspect(self.snapshot,p,r);c=E.compute(self.snapshot,p,r,a,self.cfg)
        self.assertIn('OMITTED_CONTROLLING_GATE',c['paths'][pid]['reasons']);self.assertEqual(c['paths'][pid]['state'],'UNRESOLVED')
    def test_18_unmet_burden_does_not_mean_false_and_conflict_survives(self):
        _,dest,_=self.run_case('proof-state-base');sh=read(dest/'shared.json');p=copy.deepcopy(sh['proposal']);rv=sh['reviews']['values']
        tid=next(i for i,t in p['tasks'].items() if t['proposition']=='possession');bid=next(i for i,b in p['bundles'].items() if b['task_id']==tid)
        p['bundles'][bid].update(state='UNKNOWN',proof_status='NOT_SATISFIED')
        r=E.envelope(self.snapshot,p,rv);a=E.inspect(self.snapshot,p,r);c=E.compute(self.snapshot,p,r,a,self.cfg)
        self.assertEqual(c['task_states'][tid],'UNKNOWN');self.assertEqual(a['bundles'][bid]['proof_status'],'NOT_SATISFIED')
        p['bundles'][bid].update(state='CONFLICTED',proof_status='CONTESTED')
        r=E.envelope(self.snapshot,p,rv);a=E.inspect(self.snapshot,p,r);c=E.compute(self.snapshot,p,r,a,self.cfg)
        self.assertEqual(c['task_states'][tid],'CONFLICTED')
    def test_19_real_12_case_source_packets_only(self):
        lib=read(ROOT/'rule-library.json');sizes=[]
        for cid in self.cfg['cases']:
            packet=read(REPO/self.cfg['input_root']/(cid+'.json'));before=digest(packet);snapshot=prepare_sources(packet,lib)
            restored=[s['text'] for s in snapshot['directory'].values() if s['domain']=='CASE']
            self.assertEqual(restored,[s['text'] for s in packet['sources']]);self.assertEqual(before,digest(packet));sizes.append(len(restored))
        self.assertEqual(len(sizes),12)
    def test_20_unchanged_whole_report_remains_failure_without_duplicate_review(self):
        result,dest,provider=self.run_case('unchanged','unchanged_revision')
        self.assertTrue(result['complete_chain']);self.assertFalse(result['internal_pass'])
        self.assertEqual(result['stop_reason'],'REVISION_NO_CONTENT_CHANGE')
        self.assertFalse(read(dest/'revision-effect.json')['content_changed'])
        self.assertIn('report-revision',provider.calls);self.assertNotIn('final-review-1',provider.calls)
        self.assertTrue(read(dest/'reports/1.json')['exact_unchanged_report_review_reused'])

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(WholeCaseAcceptance)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    summary={'kind':'SYNTHETIC_WHOLE_WORKFLOW_ENGINEERING_ACCEPTANCE_NOT_METHOD_QUALITY','tests':result.testsRun,
        'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful(),
        'real_case_scope':'12 allowed source packets preserved only; no new Qwen outputs',
        'new_model_calls':0,'real_case_quality_score':None,'failures_detail':[(str(t),x) for t,x in result.failures+result.errors]}
    if '--record' in sys.argv:save(ROOT/'private/offline-acceptance'/('result-'+str(__import__('time').time_ns())+'.json'),summary)
    raise SystemExit(0 if result.wasSuccessful() else 1)
