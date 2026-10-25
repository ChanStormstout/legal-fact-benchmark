"""One consolidated synthetic whole-workflow acceptance, no experimental model.

Fictional semantics exist ONLY in this test provider. Real model calls import no
test code and receive no old report, manual intermediate answer or reference label.
"""
import copy
import json
import sys
import time
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests/legacy_fixtures'),str(ROOT/'src'),str(ROOT.parents[1])]
from full_mechanisms import CompleteFixture
from whole_case_acceptance import PACKET,LIB,fixture_wire
from common import read,save,digest,prepare_sources,source_spans
from runner import run_arm
import contracts as C
import engine as E
import report_control as RC
from updates import apply_update


class Provider(CompleteFixture):
    def __init__(self,scenario='normal'):
        super().__init__(scenario);self.requests=[]
    def definitions(self,tag):
        rows=super().definitions(tag)
        return [r for r in rows if r[0] not in ('possession','gate')] if self.scenario=='proof_route' else rows
    def call(self,cid,arm,tag,request,attempt=0):
        self.requests.append(copy.deepcopy(request))
        t=tag.removeprefix('repair-');m=request['material']['material'];src=request['material']['sources']
        case=[i for i,x in src.items() if x['domain']=='CASE'];law=[i for i,x in src.items() if x['domain']=='LAW']
        def witness(ref):
            row=src[ref];text=row.get('text',''.join(p['text'] for p in row.get('passages',[])))
            return {'span_id':source_spans(ref,text)[0][0]}
        def done(value):
            self.calls.append(tag);C.validate(value,request['schema'])
            return value,{'synthetic':True,'status':'OK','usage':{'prompt_tokens':0,'completion_tokens':0},'elapsed_seconds':0,'pipeline_request_hash':digest(request)}
        if t.startswith('source-original-read-'):
            assert 'subjects' not in m and 'objects' not in m and 'question' not in request['material']
            return done({'observations':[{'speaker_label':'Original fictional narrator','content':src[i].get('text',''.join(p['text'] for p in src[i].get('passages',[]))),
                'participants':[],'event':'Original fictional occurrence','time':'1910','procedure_and_court':'Fictional proceeding',
                'witnesses':[witness(i)]} for i in m['focus_source_ids']],
                'source_dispositions':{i:'READ_WITH_OBSERVATIONS' for i in m['focus_source_ids']}})
        if t=='rule-screen':
            return done({rid:{'assessment':'ASSESS_CONDITIONS','scope_ids':list(m['scopes']),
                'report_obligation_ids':list(dict.fromkeys(i for q in m['report_questions'] for i in q.get('obligation_ids',[]))),
                'case_refs':case,'law_refs':law,'reason':'Fictional rule candidate assessment, no supplied truth'} for rid in m['frozen_rule_candidates']})
        if t=='source-records':
            court=next(i for i,o in m['objects'].items() if o['kind']=='COURT')
            by={src[i]['original_id']:i for i in case}
            descriptions={'possession':('On 1910-01-01 inspection records Dana occupying the West parcel.','fixture:inspection','OBSERVATION'),
                'prior':('The Trial Court previously recorded possession, without determining title.','fixture:court','ATTRIBUTION'),
                'gate':('The procedural application is admitted.','fixture:gate','OBSERVATION'),
                'exclusion':('No exclusion order is recorded.','fixture:gate','OBSERVATION'),
                'title':('Title remains unresolved.','fixture:gate','OBSERVATION'),
                'record_complete':('The record is complete for possession.','fixture:gate','OBSERVATION')}
            records=[]
            for name,(text,ref,role) in descriptions.items():
                actors=[i for i,o in m['objects'].items() if o['kind']=='PARTY'] if name=='possession' else []
                properties=[i for i,o in m['objects'].items() if o['kind']=='PROPERTY'] if name=='possession' else []
                row={'text':text,'source_owner':court,'owner_label':'Trial Court','status':'COURT_RECORDED',
                    'content_role':role,'participant_roles':[{'object_id':i,'role':'occupant','witnesses':[witness(by[ref])]} for i in actors],
                    'actors':actors,'properties':properties,'event':'fixture:'+name,'time':'1910','date_role':'EVENT_DATE',
                    'procedure':'Fictional permission proceeding','court':court,'court_position':'REPORTING_COURT',
                    'refs':[by[ref]],'witnesses':[witness(by[ref])]}
                if self.scenario=='source_unknown':row['status']='UNRESOLVED'
                if self.scenario in ('review_repair','rejected_record','split_record') and name=='prior':row['text']='The fictional record contains an unsupported phrase.'
                if self.scenario=='missing_record' and name=='prior':continue
                records.append(row)
                if self.scenario=='distinct_roles' and name=='possession':
                    second=copy.deepcopy(row);second['participant_roles'][0]['role']='former owner';records.append(second)
            return done({'records':records,'limitations':[]})
        if t=='use-allocation':
            return done({'slots':[i for i,t in m['tasks'].items() if t['proposition']!='result'],'limitations':[]})
        if t in ('objects-patch','scopes-patch'):
            rows=copy.deepcopy(m['subjects'])
            for row in rows.values():
                if t=='objects-patch':row['components']=[]
                else:
                    for k in ('time','time_precision','time_witnesses'):row.pop(k,None)
                    if self.scenario=='scope_patch':row['stage']='TRIAL_RECONSTRUCTION_CORRECTED'
            additions=[]
            if t=='objects-patch' and self.scenario=='registry_repair':
                additions=[{'name':'Appeal Court','kind':'COURT','description':'Fictional reviewing court','refs':[next(i for i in case if src[i]['original_id']=='fixture:court')],'extent':'NOT_PROPERTY','components':[]}]
            return done({'replacements':rows,'additions':additions,'unresolved':[]})
        if t=='task-owners-patch':
            return done({i:{'source_owner':next((k for k,o in m['objects'].items() if self.scenario=='registry_repair' and o['name']=='Appeal Court'),row['source_owner']) if row['proposition']=='prior' else row['source_owner'],
                'reason':'Fictional reassessment of speaker restriction'} for i,row in m['subjects'].items()})
        if t.startswith('source-record-repair-'):
            output={}
            for rid,rec in m['subjects'].items():
                row={**rec,'text':('The Trial Court previously recorded possession, without determining title.' if rec['event']=='fixture:prior' else rec['text'])}
                replacements=[row]
                if self.scenario=='registry_repair':
                    owner=next(i for i,o in m['objects'].items() if o['name']=='Appeal Court')
                    row.update(source_owner=owner,owner_label='Appeal Court',court=owner,text='The Appeal Court considered the prior record.')
                if self.scenario=='split_record' and rec['event']=='fixture:prior':
                    replacements=[{**row,'text':'The Trial Court previously recorded possession.'},{**row,'text':'The prior record is not a title determination.'}]
                output[rid]={'replacements':replacements,'reason':'Fictional correction from source'}
            return done(output)
        if t=='source-record-additions':
            prior=next(i for i in case if src[i]['original_id']=='fixture:court')
            base=copy.deepcopy(next(iter(m['existing_records'].values())))
            base.update(text='The Trial Court previously recorded possession, without determining title.',event='fixture:prior',content_role='ATTRIBUTION',actors=[],properties=[],participant_roles=[],refs=[prior],witnesses=[witness(prior)])
            return done({'additions':[base] if self.scenario=='missing_record' else [],'limitations':[]})
        if t.startswith('source-record-review-'):
            return done({rid:{'object_hash':digest(rec),'observed_owner':rec['source_owner'],'observed_status':rec['status'],'observed_content_role':rec['content_role'],
                'reading_ids':list(m['candidate_blind_reading']['observations']),
                'reading_alignment':{k:'AGREES' for k in ('meaning','owner_label','participant_roles','event_time','procedure')},
                'field_findings':[{'field':'meaning','finding':'CONTRADICTED','witnesses':[witness(rec['refs'][0])],'conflict':'Fictional source has no such phrase'}] if self.scenario=='rejected_record' and not tag.startswith('repair-') and rec['event']=='fixture:prior' else [],
                'field_checks':{k:'SUPPORTED' for k in ('meaning','owner_label','participant_roles','event_time','procedure')},
                'source_meaning':'Fictional source description','witnesses':[witness(i) for i in rec['refs']],
                'reason':'Fictional whole-record semantic fixture','refs':rec['refs'],
                'decision':'REJECT' if self.scenario=='rejected_record' and not tag.startswith('repair-') and rec['event']=='fixture:prior' else 'ACCEPT'} for rid,rec in m['subjects'].items()})
        if t=='source-record-coverage':
            result={}
            for sid in case:
                ids=[rid for rid,rec in m['records'].items() if sid in rec['refs']]
                result[sid]={'status':'COMPLETE' if ids else 'MISSING','record_ids':ids,
                    'reading_relation':'AGREES','witnesses':[witness(sid)],'reason':'Fictional original-to-record coverage'}
            return done(result)
        if self.scenario=='source_unknown' and t.startswith('uses-'):
            return done({tid:{'uses':[]} for tid in m['tasks']})
        if self.scenario=='source_unknown' and t.startswith('bundles-'):
            return done({tid:{'bundles':[]} for tid in m['tasks']})
        if t=='tasks-inventory':
            rows=[{'question':name,'scope_id':next(iter(m['scopes'])),'section':'GROUND' if section=='PROOF' else section,
                'importance':'IMPORTANT','answerability':'OPEN_QUESTION' if name in ('title','result') else 'KNOWN_RECORD','refs':case}
                for name,kind,section in self.definitions(tag)]
            return done({'obligations':{s:[x for x in rows if x['section']==s] for s in C.SECTIONS},'source_dispositions':{i:{'relevance':'IMPORTANT','reason':'Fictional issue source'} for i in case},'coverage_limitations':[]})
        if t=='tasks':
            definitions={name:kind for name,kind,section in self.definitions(tag)}
            rows={}
            for oid,o in m['source_inventory']['obligations'].items():
                name=o['question'];kind=definitions[name]
                rows[oid]={'proposition':name,'scope_id':o['scope_id'],'kind_rule':kind+(':FIXTURE' if kind=='DERIVED' else ':NONE'),
                    'source_owner':next(i for i,x in m['objects'].items() if x['kind']=='COURT') if kind=='ATTRIBUTION' else 'NONE',
                    'rule_condition':'FIXTURE:'+name if name in ('possession','gate') else 'NONE',
                    'effect':'CONTROLLING_GATE' if name=='gate' else 'DESCRIPTIVE','section':o['section'],'role':'REPORT',
                    'importance':o['importance'],'burden_holder':'Dana','standard':'Fictional source-based standard',
                    'authority_refs':law,'question_basis_refs':case,'why_required':'Fictional required question','obligation_ids':[oid]}
            return done({'tasks':rows,'coverage_limitations':[]})
        if t=='retrieval-queries':
            tids=[i for i,x in m['tasks'].items() if x['proposition'] in ('prior','result')]
            return done({'case_law_queries':{i:{a:'possession court permission' for a in ('SUPPORT','OPPOSITION','EXCEPTION')} for i in m['tasks']},
                'history_needs':[] if self.scenario=='empty_history_needs' else [{'task_id':i,'open_question':'How do separate proceedings treat possession testimony?',
                    'case_refs':case,'purpose':'COUNTERARGUMENT','priority':1,
                    'queries':{a:'historical possession testimony permission' for a in ('SUPPORT','OPPOSITION','EXCEPTION')}} for i in tids],
                'history_coverage_limits':[]})
        if t.startswith(('history-reading-','history-context-')):
            assert 'question' not in request['material'] and 'frozen_law' not in request['material']
            assert all(x['domain']=='HISTORY' for x in src.values())
            assert len({x['document_id'] for x in src.values()})==1
            return done({'assertions':[{'content':'The separate source records disputed possession testimony.',
                'speaker':'Historical court','attribution':'REPORTING_COURT','epistemic_status':'RECORDED_FINDING',
                'witnesses':[witness(next(iter(src)))]}],
                'context_status':'ADEQUATE_FOR_STATED_READING','context_reason':'Whole fictional document shown'})
        if t.startswith('history-compare-'):
            hist=[i for i,x in src.items() if x['domain']=='HISTORY'];assert len({src[i]['document_id'] for i in hist})==1
            return done({'report_task_ids':[i for i,t in m['report_questions'].items() if t['proposition'] in ('prior','result')],
                'current_record_ids':[i for i,r in m['current_records'].items() if r['event']=='fixture:possession'],
                'history_assertion_ids':list(m['historical_reading']['assertions']),
                'similarities':'Both describe possession evidence.','differences':'Different parties and proceedings.',
                'warrant':'A source-specific comparison illustrates the evidence distinction, not a new outcome.',
                'scope_comparison':{k:{'assessment':'DIFFERENT','reason':'Separate fictional scope'} for k in ('actors','property','time','procedure','request')},
                'proposed_use':'MATERIAL_DISTINCTION','limited_use':'Compare the evidentiary context without adopting the historical facts.',
                'limitations':'The legal applicability remains unresolved.','law_status':'UNRESOLVED','authority_refs':[]})
        if t.startswith('history-review-'):
            h=m['comparison'];claims={**h['current_assertions'],**h['history_assertions']}
            value={'object_hash':digest(h),'claims':{i:{'meaning':a['content'],'witnesses':a['witnesses'],
                'decision':'VERIFIED','reason':'Fictional source-consistent assertion'} for i,a in claims.items()},
                'issue_links':{i:{'decision':'SUPPORTED','case_witnesses':[witness(h['case_refs'][0])],'reason':'Fictional question link'} for i in h['report_task_ids']},
                'relation':{'decision':'SUPPORTED','issue_preserves_open_question':True,'case_witnesses':[witness(h['case_refs'][0])],
                    'history_witnesses':[witness(h['history_refs'][0])],'reason':'Two-sided fictional distinction'},
                'legal_applicability':{'decision':'UNRESOLVED','witnesses':[],'reason':'No legal applicability asserted'},
                'report_use':{'purpose':'MATERIAL_DISTINCTION','decision':'JUSTIFIED','reason':'Only the observed difference is described'}}
            if self.scenario=='cross_history':
                ident=next(i for i,a in claims.items() if a['source_domain']=='HISTORY')
                value['claims'][ident]['witnesses']=[{'span_id':'UNSEEN_OTHER_DOCUMENT_SPAN'}]
            for row in list(value['claims'].values())+list(value['issue_links'].values())+[value[k] for k in ('relation','legal_applicability','report_use')]:
                row.pop('reason',None);row.pop('meaning',None)
                row.update(reason_code='SOURCE_SUPPORTED' if row['decision'] not in ('UNRESOLVED','NOT_INVOKED') else 'AUTHORITY_MISSING',affected_dimensions=[])
            return done(value)
        if t in ('report','report-revision'):
            value={'items':{},'comparisons':{}}
            for tid,spec in request['schema']['properties']['items']['properties'].items():
                candidates=spec['properties']['record_ids']['items'].get('enum',[])
                name=m['tasks'][tid]['proposition']
                ids=[i for i in candidates if m['reviewed_record_catalog'][i].get('record_scope',{}).get('event')=='fixture:'+name or m['reviewed_record_catalog'][i].get('task_id')==tid]
                if name=='result':ids += [i for i in candidates if m['reviewed_record_catalog'][i].get('record_scope',{}).get('event')=='fixture:possession']
                value['items'][tid]={'record_ids':ids,'coverage':'COMPLETE' if ids else 'UNRESOLVED','omission_reason':'Fictional complete selection'}
                if self.scenario in ('all_unknown','unreviewed_questions'):value['items'][tid].update(record_ids=[],coverage='UNRESOLVED')
                if self.scenario=='prose_escape':value['items'][tid]['text']='The unverified party wins unconditionally.'
            for hid,spec in request['schema']['properties']['comparisons']['properties'].items():
                choices=spec['properties']['disposition']['enum']
                value['comparisons'][hid]={'disposition':'USED' if 'USED' in choices else 'REJECTED',
                    'report_item_id':spec['properties']['report_item_id']['enum'][0], 'reason':'Fictional relevance choice'}
            return done(value)
        value,receipt=super().call(cid,arm,tag,request,attempt)
        if t.startswith('task-review-') and self.scenario=='unreviewed_questions':
            for parts in value.values():parts['question']['decision']='UNRESOLVED'
        if t.startswith('use-review-'):
            assert 1<=len(m['subjects'])<=2 and len(m['tasks'])<=2 and len(m['scopes'])==1
            if self.scenario=='legal_use_unresolved':
                for parts in value.values():parts['use'].update(decision='UNRESOLVED',reason='Fictional legal premise remains open; source description is supported')
            if self.scenario=='missing_source_owner':
                for parts in value.values():parts['attribution'].update(observed_owner='UNDECLARED',owner_relation='MISMATCH')
        if t.startswith('scope-review-') and self.scenario=='scope_patch' and not tag.startswith('repair-'):
            for parts in value.values():parts['stage_court']['decision']='REJECT'
        if t.startswith('scope-review-') and self.scenario=='case_number_year':
            for parts in value.values():parts['time'].update(time_role='CASE_IDENTIFIER_YEAR',event_relation='MATCH')
        if t.startswith('final-review-') and self.scenario=='wrong_final_owner':
            for row in value['source_records'].values():row['observed_owner']='UNDECLARED'
        if self.scenario in ('review_repair','split_record') and t.startswith('final-review-') and not tag.startswith('repair-'):
            tid=next(i for i,x in m['exact_report']['items'].items() if any('unsupported phrase' in seg['text'] for seg in x['segments']))
            value['items'][tid].update(decision='REJECT',serious_error=True,revision_class='ALLOWED_SOURCE_ERROR',
                revision_refs=[i for i in case if src[i]['original_id']=='fixture:court'],repair_target='SOURCE_RECORDS',error_types=['UNSUPPORTED_REASON'],reason='Reassess the original statement; the fixed source record contains a fictional unsupported phrase.')
        if self.scenario=='scope_patch' and t.startswith('final-review-') and not tag.startswith('repair-'):
            tid=next(iter(value['items']))
            value['items'][tid].update(decision='REJECT',serious_error=True,revision_class='ALLOWED_SOURCE_ERROR',revision_refs=case[:1],
                repair_target='SCOPES',error_types=['PROCEDURE'],reason='The fictional declared stage needs correction from the original record.')
        if self.scenario=='registry_repair' and t.startswith('final-review-') and not tag.startswith('repair-'):
            for rid,row in value['source_records'].items():
                record=next(seg for item in m['exact_report']['items'].values() for seg in item['segments'] if seg.get('source_record_id')==rid)
                if record['record_scope']['event']=='fixture:prior':row['observed_owner']='UNDECLARED';row['decision']='REJECT'
        if self.scenario=='wrong_coverage_link' and t.startswith('final-review-'):
            record=next(seg['record_id'] for item in m['exact_report']['items'].values() for seg in item['segments'] if seg.get('record_scope',{}).get('event')=='fixture:title')
            oid=next(i for i,o in m['source_inventory']['obligations'].items() if o['question']=='prior')
            value['whole_source_coverage']['obligations'][oid]['answer_record_ids']=[record]
        if self.scenario=='scope_transfer' and t.startswith('use-review-'):
            for parts in value.values():parts['scope_bridge']['dimensions']['procedure'].update(relation='MISMATCH',reason='Fictional prior proceeding cannot serve current gate')
        if self.scenario=='missing_record' and t.startswith('final-review-') and not tag.startswith('repair-'):
            prior_ref=next(i for i in case if src[i]['original_id']=='fixture:court')
            value['whole_source_coverage']['omissions'].append({'question':'What did the prior court record about possession?', 'refs':[prior_ref],
                'importance':'IMPORTANT','finding_class':next(k for k,v in C.OMISSION_CLASSES.items() if v==('ALLOWED_SOURCE_OMISSION','ALLOWED_RECORD')),
                'basis':'Fictional allowed court record omitted','repair_target':'SOURCE_RECORDS'})
        return value,receipt


class WholeWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=read(ROOT/'protocol.json');cls.work=ROOT/'private/engineering'/str(time.time_ns());cls.work.mkdir(parents=True)
        packet=copy.deepcopy(PACKET);packet['sources'][0]['text']+=' Dana formerly owned that parcel.';packet['sources'][1]['text']+=' The Appeal Court considered the prior record.';packet['sources'][2]['text']+=' The record is complete for possession.'
        packet['sources'] += [{'source_id':'history:a','document_id':'other-a','document_role':'HISTORICAL','text':'In a separate historical possession proceeding Dana testimony was disputed.'},
            {'source_id':'history:b','document_id':'other-b','document_role':'HISTORICAL','text':'Another separate possession decision records disputed occupation and permission.'}]
        cls.snapshot=prepare_sources(packet,LIB)
    def whole(self,scenario='normal'):
        dest=self.work/scenario;provider=Provider(scenario)
        outcome=run_arm(provider,self.snapshot,self.cfg,dest,'C')
        return outcome,dest,provider
    def test_01_original_to_rules_and_report(self):
        o,d,p=self.whole();self.assertTrue(o['complete_chain'],o);self.assertTrue(o['internal_pass'],o)
        comp=read(d/'computation.json');report=read(d/'final-report.json')
        self.assertTrue(any(v['state']=='TRUE' for v in comp['computed']['rules'].values()))
        self.assertTrue(any(x['include'] for x in report['comparisons'].values()))
        self.assertTrue(any(t.startswith('history-reading-') for t in p.calls))
        self.assertTrue(all('text' not in x for x in report['selection']['items'].values()))
        self.assertEqual(read(d/'history-usage.json')['semantic_correctness'],None)
        shared=read(d/'shared.json');mutated=copy.deepcopy(report)
        next(iter(mutated['items'].values()))['text']='An unchecked legal conclusion.'
        self.assertEqual(RC.check_exact(self.snapshot,shared['proposal'],shared['reviews'],comp['accepted'],comp['computed'],mutated),['REPORT_CHANGED_OUTSIDE_REVIEWED_RECORD_SELECTION'])
    def test_02_unknown_gate_blocks_actual_remedy(self):
        o,d,p=self.whole('unknown_gate');self.assertTrue(o['complete_chain'],o)
        c=read(d/'computation.json')['computed'];self.assertTrue(all(x['outcome']=='UNRESOLVED' for x in c['requests'].values()))
        self.assertFalse(any(x['state']=='CONDITIONS_MET_IN_DECLARED_SCOPE' for x in c['paths'].values()))
        parent=read(d/'shared.json');before=digest(parent);tid=next(i for i,t in parent['proposal']['tasks'].items() if t['proposition']=='gate')
        child,_=apply_update(self.snapshot,{'kind':'HYPOTHETICAL','parent_snapshot':self.snapshot['snapshot_id'],'reason':'Fictional branch only','assumptions':{tid:'TRUE'}})
        h=run_arm(Provider(),child,self.cfg,self.work/'hypothetical','C',parent,parent_snapshot=self.snapshot)
        self.assertTrue(h['complete_chain'],h);self.assertEqual(digest(read(d/'shared.json')),before)
        self.assertIn('Hypothetical branch', (self.work/'hypothetical/final-report.txt').read_text())
    def test_03_repair_rebuilds_fixed_content_once(self):
        o,d,p=self.whole('review_repair');self.assertTrue(o['complete_chain'],o)
        self.assertTrue(o['revision_effect']['content_changed'],o)
        self.assertIn('repair-source-record-review-0',p.calls);self.assertIn('repair-use-review-0',p.calls);self.assertNotIn('repair-objects',p.calls)
        self.assertNotIn('previous_report',read(d/'revision-feedback.json'))
        self.assertFalse(any('previous_report' in json.dumps(r['material']) and 'previous_report_hash' not in json.dumps(r['material']) for r in p.requests))
        self.assertTrue((d/'reports/0.json').exists());self.assertTrue((d/'reports/repair-1.json').exists())
    def test_04_unknown_report_cannot_claim_known_content_covered(self):
        o,d,p=self.whole('all_unknown');self.assertTrue(o['complete_chain'],o);self.assertFalse(o['internal_pass'])
        check=o['check']['whole_source_coverage']['inventory_check'];self.assertFalse(check['complete'])
    def test_05_wrong_document_and_new_prose_cannot_reach_report(self):
        o,d,p=self.whole('cross_history');self.assertFalse(o['complete_chain'],o)
        self.assertTrue(o['core_chain_complete']);self.assertEqual(o['stop_reason'],'PARTIAL_REPORT_HISTORY_FAILURE')
        self.assertFalse(any(x['include'] for x in read(d/'final-report.json')['comparisons'].values()))
        events=read(d/'history-assessment.json')['events']
        self.assertTrue(any(x.get('status')=='TECHNICAL_FAILURE' for x in events))
        o,d,p=self.whole('prose_escape');self.assertFalse(o['complete_chain']);self.assertFalse((d/'final-report.json').exists())
        self.assertEqual(o['answer'],None);self.assertIn('EXTRA_FIELD',o['error'])

    def test_06_bad_law_or_identity_cannot_authorize_a_rule(self):
        for scenario in ('wrong_identity','unreviewed_law'):
            with self.subTest(scenario=scenario):
                o,d,p=self.whole(scenario);self.assertTrue(o['complete_chain'],o)
                c=read(d/'computation.json')['computed']
                self.assertFalse(any(x['outcome']=='SUPPORTED_IN_DECLARED_SCOPE' for x in c['requests'].values()))
    def test_07_duplicate_source_record_is_rendered_once(self):
        o,d,p=self.whole('duplicate_record');self.assertTrue(o['complete_chain'],o)
        text=(d/'final-report.txt').read_text()
        self.assertEqual(text.count('On 1910-01-01 inspection records Dana occupying the West parcel.'),1)
        self.assertIn('Shared material for this question:',text)
        self.assertTrue(any(x.get('also_covered_by') for x in read(d/'final-report.json')['items'].values()))
    def test_08_failure_preserved_no_rerun(self):
        o,d,p=self.whole('technical_failure');self.assertFalse(o['complete_chain']);self.assertIsNone(o['answer'])
        with self.assertRaisesRegex(ValueError,'PRESERVED'):
            run_arm(Provider(),self.snapshot,self.cfg,d,'C')

    def test_09_proof_sources_reach_report_without_becoming_outcomes(self):
        o,d,p=self.whole('proof_route');self.assertTrue(o['complete_chain'],o)
        shared=read(d/'shared.json')['proposal'];report=read(d/'final-report.json')
        proof={i for i,t in shared['tasks'].items() if t['role']=='PROOF'}
        self.assertTrue(proof)
        self.assertTrue(any(x.get('source_record_id') for item in report['items'].values() for x in item['segments']))
        self.assertFalse(any(i in report['items'] for i in proof))

    def test_10_report_records_and_rule_unknown_are_independent(self):
        o,d,p=self.whole('legal_use_unresolved');self.assertTrue(o['complete_chain'],o)
        comp=read(d/'computation.json');report=read(d/'final-report.json')
        self.assertTrue(any(x['report_eligible'] for x in comp['accepted']['uses'].values()))
        self.assertFalse(any(x['bundle_eligible'] for x in comp['accepted']['uses'].values()))
        self.assertTrue(any(item['segments'] and item['report_coverage_claim']=='COMPLETE' and item['rule_execution_state']=='UNKNOWN' and not item['unresolved_included'] for item in report['items'].values()))

    def test_11_independent_owner_and_event_mismatches_block_acceptance(self):
        for scenario in ('missing_source_owner','case_number_year','wrong_final_owner'):
            with self.subTest(scenario=scenario):
                o,d,p=self.whole(scenario);self.assertTrue(o['complete_chain'],o)
                if scenario=='wrong_final_owner':self.assertFalse(o['internal_pass'],o)
                comp=read(d/'computation.json')
                if scenario=='missing_source_owner':self.assertFalse(any(u['report_eligible'] for u in comp['accepted']['uses'].values()))
                if scenario=='case_number_year':
                    self.assertFalse(any(comp['accepted']['scopes'].values()))
                    self.assertFalse(any(x['state']=='CONDITIONS_MET_IN_DECLARED_SCOPE' for x in comp['computed']['paths'].values()))
                if scenario=='wrong_final_owner':
                    self.assertTrue(any(any(s.startswith('FINAL_SOURCE_RECORD_BINDING_NOT_CONFIRMED:') for s in x['reasons']) for x in o['check']['problems']))
                    plan=read(d/'repair-plan.json');self.assertIn('OBJECTS',plan['targets'])
                    self.assertTrue(o['revision_effect'] or any(t.startswith('repair-') for t in p.calls))

    def test_12_rejected_questions_do_not_repeat_fallback_or_pass_quality(self):
        o,d,p=self.whole('unreviewed_questions');self.assertTrue(o['complete_chain'],o);self.assertFalse(o['internal_pass'],o)
        self.assertEqual((d/'final-report.txt').read_text().count('Important content for this report obligation remains unresolved by the analysis.'),1)

    def test_13_history_off_keeps_current_computation_and_plain_baseline(self):
        import baseline
        provider=Provider();cfg={**self.cfg,'history_enabled':False};dest=self.work/'history_off'
        o=run_arm(provider,self.snapshot,cfg,dest,'C-H0');self.assertTrue(o['complete_chain'],o)
        self.assertFalse(any(t.startswith('history-') for t in provider.calls))
        h0=read(dest/'computation.json')['computed'];normal=read(self.work/'normal/computation.json')['computed']
        self.assertEqual(h0['task_states'],normal['task_states'])
        self.assertFalse(read(dest/'final-report.json')['comparisons'])
        req=baseline.request(self.snapshot,self.cfg)
        self.assertEqual(req['mechanisms'],[]);self.assertTrue(req['one_call_only'])
        self.assertNotIn('response_format',req['plain_wire'])
        self.assertTrue(all(self.snapshot['directory'][i]['domain']!='HISTORY' for i in req['source_ids']))

    def test_14c_unresolved_records_do_not_create_impossible_mode_enum(self):
        o,d,p=self.whole('source_unknown');self.assertTrue(o['complete_chain'],o);self.assertFalse(o['internal_pass'])
        comp=read(d/'computation.json');self.assertFalse(comp['accepted']['uses'])
        self.assertFalse(any(r['report_eligible'] for r in comp['accepted']['source_records'].values()))
        self.assertFalse(any('"enum": []' in json.dumps(r['schema']) for r in p.requests))

    def test_14a_empty_needs_still_search_and_review_history(self):
        o,d,p=self.whole('empty_history_needs');self.assertTrue(o['complete_chain'],o)
        ledger=read(d/'retrieval-ledger.json')
        self.assertTrue(any(n.get('origin')=='ORIGINAL_USER_QUESTION_SEARCH_NOT_SEMANTIC_NEED' for n in ledger['needs'].values()))
        self.assertTrue(any(t.startswith('history-compare-') for t in p.calls))
        self.assertTrue(any(x['include'] for x in read(d/'final-report.json')['comparisons'].values()))

    def test_14b_source_revocation_invalidates_dependents(self):
        normal=read(self.work/'normal/shared.json');rid=next(iter(normal['proposal']['source_records']))
        dest=self.work/'record_revoked'
        o=run_arm(Provider(),self.snapshot,self.cfg,dest,'C',normal,revoked=[rid])
        self.assertTrue(o['complete_chain'],o)
        comp=read(dest/'computation.json')
        self.assertFalse(comp['accepted']['source_records'][rid]['report_eligible'])
        self.assertFalse(any(u['bundle_eligible'] for uid,u in comp['accepted']['uses'].items() if rid in normal['proposal']['uses'][uid]['source_record_ids']))
        self.assertFalse(any(rid in x['support_ids'] for x in read(dest/'final-report.json')['items'].values()))

    def test_14_limited_budget_preserves_failed_draft_without_rebuilding(self):
        # Same fictional full workflow, insufficient suffix allowance. This is
        # an engineering stop scenario, not an experimental case-budget change.
        cfg={**self.cfg,'capacity_diagnostic':False,'parameters':{**self.cfg['parameters'],'max_tokens':16384},'max_input_tokens_per_arm':400000};p=Provider('review_repair');d=self.work/'budget_stop'
        o=run_arm(p,self.snapshot,cfg,d,'C');self.assertTrue(o['complete_chain'],o)
        self.assertEqual(o['stop_reason'],'REPAIR_NOT_DISPATCHED_BUDGET')
        self.assertFalse(o['internal_pass']);self.assertFalse(any(t.startswith('repair-') for t in p.calls))
        self.assertTrue((d/'final-report.json').exists());self.assertTrue((d/'reports/0.json').exists())

    def test_15_scope_transfer_does_not_erase_description_or_authorize_rule(self):
        o,d,p=self.whole('scope_transfer');self.assertTrue(o['complete_chain'],o)
        c=read(d/'computation.json')
        self.assertTrue(any(u['report_eligible'] for u in c['accepted']['uses'].values()))
        self.assertFalse(any(u['bundle_eligible'] for u in c['accepted']['uses'].values()))
        self.assertFalse(any(x['state']=='TRUE' for x in c['computed']['rules'].values()))
        self.assertIn('SOURCE_TO_TARGET_SCOPE_NOT_VERIFIED',(d/'final-report.txt').read_text())

    def test_16_rejected_unrendered_record_is_repaired_without_report_hack(self):
        o,d,p=self.whole('rejected_record');self.assertTrue(o['complete_chain'],o)
        before=read(d/'shared.json');after=read(d/'repair-shared.json')
        rejected=[i for i,r in before['reviews']['values']['source_records'].items() if r['decision']=='REJECT']
        self.assertTrue(rejected)
        first=read(d/'reports/0.json')['report'];self.assertFalse(any(set(rejected)&set(x['support_ids']) for x in first['items'].values()))
        self.assertTrue(o['revision_effect']['content_changed'],o)
        self.assertTrue(all(i not in after['proposal']['source_records'] for i in rejected))

    def test_17_missing_record_and_compound_record_have_complete_repair_routes(self):
        for scenario in ('missing_record','split_record'):
            o,d,p=self.whole(scenario);self.assertTrue(o['complete_chain'],o)
            self.assertTrue(o['revision_effect']['content_changed'],o)
            lineage=read(d/'source-record-repair-lineage.json')['records']
            if scenario=='missing_record':self.assertTrue(lineage['ADDITIONS']['new_ids'])
            else:self.assertTrue(any(len(x['new_ids'])==2 for x in lineage.values()))

    def test_18_registry_identity_is_repaired_before_source_and_use(self):
        o,d,p=self.whole('registry_repair');self.assertTrue(o['complete_chain'],o)
        self.assertTrue(o['revision_effect']['content_changed'],o)
        self.assertLess(p.calls.index('repair-objects-patch'),p.calls.index('repair-source-record-repair-0'))
        self.assertLess(p.calls.index('repair-source-record-review-0'),p.calls.index('repair-use-review-0'))
        shared=read(d/'repair-shared.json');old=read(d/'shared.json')
        added=set(shared['proposal']['objects'])-set(old['proposal']['objects']);self.assertTrue(added)
        self.assertTrue(all(i in shared['reviews']['values']['objects'] for i in added))
        self.assertIn('Appeal Court',(d/'final-report.txt').read_text())
        self.assertTrue(any(t.startswith('repair-history-review-') for t in p.calls))
        history_calls=sum(t.removeprefix('repair-').startswith('history-') for t in p.calls)
        if self.cfg.get('capacity_diagnostic'):
            # The diagnostic disables the old ten-call quota, but retains finite
            # pairs, one context expansion and one revision. No until-pass loop.
            finite=(1+self.cfg['max_report_revisions'])*(3*self.cfg['history_max_pairs']+self.cfg['history_context_expansions'])
            self.assertLessEqual(history_calls,finite)
        else:self.assertLessEqual(history_calls,self.cfg['history_max_calls'])

    def test_19_unselected_record_cannot_certify_question_coverage(self):
        o,d,p=self.whole('wrong_coverage_link');self.assertTrue(o['complete_chain'],o)
        self.assertFalse(o['internal_pass'])
        coverage=o['check']['whole_source_coverage']['inventory_check']
        self.assertTrue(any(not r['complete'] for r in coverage['obligations'].values()))

    def test_20_original_question_keeps_own_scope_and_reviewed_destinations(self):
        d=self.work/'empty_history_needs';ledger=read(d/'retrieval-ledger.json')
        base=[n for n in ledger['needs'].values() if n.get('origin')=='ORIGINAL_USER_QUESTION_SEARCH_NOT_SEMANTIC_NEED']
        self.assertTrue(base);self.assertTrue(all(n['scope_id']=='ORIGINAL_QUESTION' and n['task_id']=='ORIGINAL_QUESTION' for n in base))
        requests=[read(f) for f in (d/'requests').glob('history-compare-*.json')]
        self.assertTrue(all(r['material']['material']['scope']['kind']=='ORIGINAL_QUESTION' for r in requests))
        self.assertTrue(all(r['material']['material']['report_scopes'] for r in requests))
        for h in read(d/'shared.json')['proposal']['analogies'].values():self.assertTrue(h['report_task_ids'])

    def test_21_identical_citation_is_not_permission_to_promote_claim_role(self):
        shared=read(self.work/'normal/shared.json');p=shared['proposal']
        cfg={**self.cfg,'source_records':p['source_records']}
        schema=C.uses(self.snapshot,p['tasks'],cfg,p['objects'])
        for spec in schema['properties'].values():
            for choice in spec['properties']['uses']['items']['properties']['source_record_mode']['enum']:
                rid,mode=choice.split('|',1);self.assertEqual(C.USE_MODES[mode]['content_role'],p['source_records'][rid]['content_role'])


    def test_22_scope_patch_invalidates_old_reviews_and_all_dependent_uses(self):
        o,d,p=self.whole('scope_patch');self.assertTrue(o['complete_chain'],o)
        self.assertIn('repair-scopes-patch',p.calls)
        before=read(d/'shared.json');after=read(d/'repair-shared.json')
        self.assertNotEqual(before['proposal']['scopes'],after['proposal']['scopes'])
        self.assertNotEqual(before['reviews']['values']['scopes'],after['reviews']['values']['scopes'])
        self.assertNotIn('repair-objects-patch',p.calls)
        self.assertTrue(any(t.startswith('repair-use-review-') for t in p.calls))
        self.assertTrue(o['internal_pass'],o)


    def test_23_dedup_keeps_distinct_sourced_participant_roles(self):
        o,d,p=self.whole('distinct_roles');self.assertTrue(o['complete_chain'],o)
        text=(d/'final-report.txt').read_text()
        self.assertIn('Dana (occupant)',text);self.assertIn('Dana (former owner)',text)
        report=read(d/'final-report.json')
        roles=[seg['record_scope']['participant_roles'][0]['role'] for item in report['items'].values() for seg in item['segments'] if seg.get('record_scope',{}).get('event')=='fixture:possession']
        self.assertEqual(set(roles),{'occupant','former owner'})



if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(WholeWorkflow))
    save(WholeWorkflow.work/'acceptance.json',{'kind':'FICTIONAL_WHOLE_WORKFLOW_NOT_MODEL_QUALITY','passed':result.wasSuccessful(),
        'tests':result.testsRun,'failures':[(str(t),s) for t,s in result.failures+result.errors],
        'model_calls':0,'real_case_quality':None})
    print('ACCEPTANCE_DIRECTORY',WholeWorkflow.work)
    raise SystemExit(0 if result.wasSuccessful() else 1)
