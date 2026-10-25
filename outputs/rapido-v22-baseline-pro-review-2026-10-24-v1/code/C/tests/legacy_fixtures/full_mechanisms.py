"""Synthetic whole-case transitions, not real model output or research micro checks."""
import copy,json,tempfile,sys,unittest,hashlib
from pathlib import Path
from whole_case_acceptance import FixtureProvider,PACKET,LIB,ROOT,REPO,C,E,fixture_wire,task_names
from common import read,save,prepare_sources,digest
from runner import run_arm
from retrieval import Index,load_corpus
from updates import apply_update

class CompleteFixture(FixtureProvider):
    def definitions(self,tag):
        rows=super().definitions(tag)+[('record_complete','FACT','PROOF')]
        if self.scenario=='duplicates':rows.append(('occupancy','FACT','GROUND'))
        if self.scenario=='predicates_from_rule':rows=[r for r in rows if r[0] not in ('possession','gate')]
        if self.scenario=='repair' and tag.startswith('repair-'):rows.append(('independent omitted finding','FACT','GROUND'))
        return rows
    def call(self,cid,arm,tag,request,attempt=0):
        rawtag=tag;tag=tag.removeprefix('repair-');m=request['material']['material'];src=request['material']['sources'];refs=list(src)
        law=[i for i in src if src[i]['domain']=='LAW'];case=[i for i in src if src[i]['domain']=='CASE' and src[i]['original_id'].startswith('fixture:')]
        def d():return {'decision':'ACCEPT','reason':'Fictional source-reviewed mapping, engineering only','refs':case+law}
        if tag=='burdens':
            by=task_names(m['tasks'])
            value={'burdens':[{'scope_id':next(iter(m['scopes'])),'task_id':by['possession'],
                'holder':next(i for i,x in m['objects'].items() if x['name']=='Dana'),
                'shifted_holder':next((i for i,x in m['objects'].items() if x['name']=='Morgan'),'NONE') if self.scenario=='shift' else 'NONE',
                'shifted_task_id':by['title'] if self.scenario=='shift' else 'NONE','trigger_tasks':[], 'shift_trigger_tasks':[by['gate']] if self.scenario=='shift' else [],
                'record_complete_task':by['record_complete'],'failure_effect':'REQUEST_NOT_ESTABLISHED',
                'authority_refs':law,'standard':'Fictional complete-record test','reason':'Fictional law explicitly assigns this task'}]}
        elif tag=='requests':
            by=task_names(m['tasks'])
            value={'requests':[{'scope_id':next(iter(m['scopes'])),'conclusion_task':by['result'],'level':'REMEDY',
                'name':'Fictional limited remedy','grounds':([{'all_paths':[pid],'reason':'Independent alternative'} for pid in m['paths']] if self.scenario=='independent' else [{'all_paths':list(m['paths']),'reason':'Joint test'}]),
                'gates':[by['gate']],'blockers':[by['exclusion']],'exceptions':[],'burden_ids':list(m['burdens']),
                'authority_refs':law,'coverage_complete':True,'missing_grounds':[],'reason':'Fictional scope complete'}]}
        elif tag.startswith(('burden-review','request-review')):
            value={i:{k:d() for k in ('scope','law','coverage')} for i in m['subjects']}
            if self.scenario=='unreviewed_law':
                for v in value.values():v['law']['decision']='UNRESOLVED'
        elif tag.startswith('analogies-'):
            hist=[i for i in src if src[i]['domain']=='HISTORY']
            tid=next(i for i,t in m['tasks'].items() if t['proposition']=='prior')
            value={'analogies':{cid:{'task_id':tid,'history_refs':row['history_refs'],'case_refs':case,'similarities':'Fictional possession issue','differences':'Different dispute and proof','limited_use':'Contrast only','authority_refs':law,'orientation':'OPPOSITION','law_status':'NOT_INVOKED','scope_comparison':{k:{'assessment':'DIFFERENT','reason':'Fictional distinct scope'} for k in ('actors','property','time','procedure','request')}} for cid,row in m['candidates'].items()}}
        elif tag.startswith('analogy-review'):
            value={i:{'history':{'decision':'ACCEPT','reason':'Fictional history only','refs':h['history_refs']},'current':{'decision':'ACCEPT','reason':'Fictional current only','refs':h['case_refs']},'comparison':{'decision':'ACCEPT','reason':'Fictional contrast, no law invoked','refs':h['history_refs']+h['case_refs']},'law':{'decision':'UNRESOLVED','reason':'Not invoked','refs':[]}} for i,h in m['subjects'].items()}
        elif tag=='task-equivalence':
            by={x['proposition']:i for i,x in m['tasks'].items()}
            value={'groups':[{'canonical':by['possession'],'duplicates':[by['occupancy']],'reason':'Same fictional proposition'}]} if 'occupancy' in by else {'groups':[]}
        elif tag.startswith('merge-review'):value={i:d() for i in m['subjects']}
        elif tag.startswith('coverage-final'):
            value={'read_ids':list(src),'omissions':[]}
        elif tag.startswith('coverage-'):
            value={'read_ids':list(src),'issues':[],'unresolved':[]}
        else:
            value,receipt=super().call(cid,arm,rawtag,request,attempt)
            if tag in ('objects','direct-objects') and self.scenario=='shift':
                value['objects'].append({'name':'Morgan','kind':'PARTY','description':'Fictional other party','refs':case[:1]})
            if tag=='paths' and self.scenario=='independent':
                by={t['proposition']:i for i,t in m['tasks'].items()}
                value['paths'].append({**copy.deepcopy(value['paths'][0]),'name':'Independent unresolved path','supports':[by['title']]})
            if tag.startswith('uses'):
                for tid,row in value.items():
                    if m['tasks'][tid]['proposition']=='possession' and self.scenario in ('unmet','incomplete_record'):
                        for u in row['uses']:u['state']='UNKNOWN'
                    if m['tasks'][tid]['proposition']=='record_complete' and self.scenario=='incomplete_record':
                        for u in row['uses']:u['state']='UNKNOWN'
            if tag.startswith('bundles'):
                for tid,row in value.items():
                    if m['tasks'][tid]['proposition']=='possession' and self.scenario in ('unmet','incomplete_record'):
                        for b in row['bundles']:b['proof_status']='NOT_SATISFIED'
            if tag.startswith('bundles') and self.scenario=='alternative_bundle':
                tid=next(i for i,t in m['tasks'].items() if t['proposition']=='possession')
                alternate=copy.deepcopy(value[tid]['bundles'][0]);alternate.update(state='UNKNOWN',proof_status='UNRESOLVED',complete=False,missing=['Alternative incomplete'],reason='Fictional alternative does not displace sufficient bundle')
                value[tid]['bundles'].append(alternate)
            if tag in ('report','report-revision') and arm=='C':
                comp=m['fallible_analysis'].get('compact_computation',{})
                for rid,cert in comp.get('requests',{}).items():
                    item=value['items'][cert['task_id']];item.update(consequence_scope='REMEDY',outcome=cert['outcome'],support_ids=[rid],
                        kind='CONDITIONAL' if cert['conditional'] or cert['outcome']=='UNRESOLVED' else 'DERIVED',
                        text=('If the stated assumptions hold: ' if cert['conditional'] else '')+'Fictional remedy '+cert['outcome'])
                for tid in comp.get('assumptions',{}):
                    if tid in value['items']:value['items'][tid].update(kind='CONDITIONAL',text='Assume the fictional condition, not actual evidence')
            if tag.startswith('final-review') and self.scenario=='repair' and not rawtag.startswith('repair-'):
                value['whole_source_coverage']={'reason':'Fictional omission','omissions':[{'question':'independent omitted finding','refs':case,'importance':'IMPORTANT','classification':'ALLOWED_SOURCE_OMISSION','information_target':'ALLOWED_RECORD','basis':'Positive fictional source','repair_target':'TASKS'}]}
            value=fixture_wire(tag,value,request);C.validate(value,request['schema']);return value,receipt
        self.calls.append(rawtag);value=fixture_wire(tag,value,request);C.validate(value,request['schema'])
        return value,{'synthetic':True,'status':'OK','usage':{'prompt_tokens':0,'completion_tokens':0},'elapsed_seconds':0,'pipeline_request_hash':digest(request)}

class WholeMechanisms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=read(ROOT/'protocol.json');cls.work=ROOT/'private/full-engineering'/str(__import__('time').time_ns());cls.work.mkdir(parents=True)
        packet=copy.deepcopy(PACKET);packet['sources'][2]['text']+=' The record is complete for possession. Morgan is the other party.'
        lib=copy.deepcopy(LIB);lib['authority_clips'][0]['text']+=' FICTIONAL: Dana must prove possession on the complete record; if not satisfied the request is not established. Admission shifts the duty to Morgan only in the explicitly mapped shift scenario.'
        cls.snapshot=prepare_sources(packet,lib)
    def run_full(self,name,scenario='normal',snapshot=None,cfg=None):
        provider=CompleteFixture(scenario);dest=self.work/name
        result=run_arm(provider,snapshot or self.snapshot,cfg or self.cfg,dest,'C')
        self.assertTrue(result['complete_chain'],result)
        return result,dest,provider
    def test_supported_remedy_full_report(self):
        result,dest,p=self.run_full('supported','predicates_from_rule')
        c=read(dest/'computation.json')['computed'];self.assertEqual(next(iter(c['requests'].values()))['outcome'],'SUPPORTED_IN_DECLARED_SCOPE')
        self.assertTrue(result['internal_pass'],result);self.assertIn('requests',p.calls);self.assertIn('burdens',p.calls)
        questions=read(dest/'tasks-rule-questions.json')
        self.assertEqual(len(questions['created_questions']),2)
        self.assertFalse(questions['case_answers_supplied'])
        self.assertTrue(c['rules'])
    def test_independent_sufficient_path_survives_other_unknown_ground(self):
        result,dest,_=self.run_full('independent','independent');c=read(dest/'computation.json')['computed']
        cert=next(iter(c['requests'].values()));self.assertIn('UNKNOWN',cert['ground_states']);self.assertIn('TRUE',cert['ground_states'])
        self.assertEqual(cert['outcome'],'SUPPORTED_IN_DECLARED_SCOPE');self.assertTrue(result['internal_pass'],result)
    def test_sufficient_bundle_survives_incomplete_alternative(self):
        result,dest,_=self.run_full('alternative-bundle','alternative_bundle');c=read(dest/'computation.json')['computed']
        self.assertEqual(next(iter(c['burdens'].values()))['effect'],'SATISFIED')
        self.assertEqual(next(iter(c['requests'].values()))['outcome'],'SUPPORTED_IN_DECLARED_SCOPE')
        self.assertTrue(result['internal_pass'],result)
    def test_unmet_burden_not_false(self):
        result,dest,_=self.run_full('unmet','unmet');c=read(dest/'computation.json')['computed'];b=next(iter(c['burdens'].values()))
        self.assertEqual(b['effect'],'REQUEST_NOT_ESTABLISHED');self.assertEqual(c['task_states'][b['task_id']],'UNKNOWN')
        self.assertEqual(next(iter(c['requests'].values()))['outcome'],'NOT_ESTABLISHED');self.assertTrue(result['internal_pass'],result)
    def test_incomplete_record_no_adverse_inference(self):
        _,dest,_=self.run_full('incomplete','incomplete_record');c=read(dest/'computation.json')['computed']
        self.assertEqual(next(iter(c['burdens'].values()))['effect'],'UNRESOLVED');self.assertEqual(next(iter(c['requests'].values()))['outcome'],'UNRESOLVED')
    def test_unresolved_gate_blocks_remedy(self):
        _,dest,_=self.run_full('unknown-gate','unknown_gate');c=read(dest/'computation.json')['computed']
        self.assertEqual(next(iter(c['requests'].values()))['outcome'],'UNRESOLVED')
    def test_unreviewed_law_does_not_authorize(self):
        _,dest,_=self.run_full('law','unreviewed_law');c=read(dest/'computation.json')['computed']
        self.assertIn('UNACCEPTED_LAW',next(iter(c['requests'].values()))['reasons'])
    def test_shift_changes_holder_not_fact(self):
        _,dest,_=self.run_full('shift','shift');c=read(dest/'computation.json')['computed'];p=read(dest/'shared.json')['proposal'];b=next(iter(c['burdens'].values()))
        self.assertEqual(p['objects'][b['holder']]['name'],'Morgan');self.assertEqual(b['shift'],'TRUE')
    def test_omission_rebuilds_then_reports_once(self):
        result,dest,provider=self.run_full('repair','repair');self.assertTrue(result['internal_pass'],result)
        self.assertNotIn('repair-objects',provider.calls);self.assertNotIn('repair-scopes',provider.calls);self.assertIn('repair-use-review-0',provider.calls)
        self.assertEqual(read(dest/'repair-reuse.json')['reused_stages'],['OBJECTS','SCOPES'])
        repaired=read(dest/'repair-shared.json');self.assertTrue(any(t['proposition']=='independent omitted finding' for t in repaired['proposal']['tasks'].values()))
        self.assertTrue((dest/'reports/0.json').exists());self.assertTrue((dest/'reports/repair-1.json').exists())
        feedback=read(dest/'revision-feedback.json')
        old=read(dest/'reports/0.json')
        self.assertEqual(feedback['previous_report'],old['report'])
        self.assertEqual(feedback['program_problems'],old['check']['problems'])
        self.assertNotIn('program_check',feedback)
        self.assertFalse((dest/'requests/repair-scopes.json').exists())
        self.assertFalse(read(dest/'revision-effect.json')['not_independent_quality_improvement'] is False)
    def test_equivalent_tasks_merge_before_all_use_computation(self):
        result,dest,_=self.run_full('duplicates','duplicates');p=read(dest/'shared.json')['proposal']
        self.assertEqual(len(p['task_aliases']),1);self.assertNotIn('occupancy',[t['proposition'] for t in p['tasks'].values()]);self.assertTrue(result['internal_pass'])
    def test_hypothesis_recomputes_and_renders_conditional(self):
        _,dest,_=self.run_full('hyp-parent','unknown_gate');shared=read(dest/'shared.json');tid=next(i for i,t in shared['proposal']['tasks'].items() if t['proposition']=='gate')
        before=digest(shared);event={'kind':'HYPOTHETICAL','parent_snapshot':self.snapshot['snapshot_id'],'reason':'Engineering conditional analysis','assumptions':{tid:'TRUE'}}
        child,_=apply_update(self.snapshot,event);out=self.work/'hyp-child'
        result=run_arm(CompleteFixture(),child,self.cfg,out,'C',shared,parent_snapshot=self.snapshot)
        self.assertTrue(result['complete_chain'],result);self.assertTrue(result['internal_pass'],result)
        c=read(out/'hypothetical-computation.json')['computed'];self.assertTrue(c['conditional_not_actual']);self.assertEqual(next(iter(c['requests'].values()))['outcome'],'SUPPORTED_IN_DECLARED_SCOPE')
        self.assertEqual(digest(read(dest/'shared.json')),before);self.assertIn('If the stated assumptions', (out/'final-report.txt').read_text())
    def test_corpus_and_long_original_coverage_enter_whole_chain(self):
        packet=copy.deepcopy(PACKET)
        packet['sources'] += [{'source_id':'irrelevant:'+str(n),'text':'Unrelated background '+('neutral words '*60),'document_id':'background-'+str(n)} for n in range(8)]
        packet['sources'].append({'source_id':'analog:1','text':'Separate historical dispute: possession was disputed, not established.','document_role':'HISTORICAL'})
        snapshot=prepare_sources(packet,LIB);cfg={**self.cfg,'source_window_chars':2500,'source_scan_chars':1800}
        # Every fixture claim cites the compact actual record, not irrelevant chunks.
        result,dest,provider=self.run_full('long',snapshot=snapshot,cfg=cfg)
        self.assertTrue((dest/'coverage-ledger.json').exists());self.assertTrue(any(x.startswith('coverage-final') for x in provider.calls))
        retrieval=read(dest/'shared.json')['retrieval'];self.assertEqual(retrieval['collections']['HISTORY'],1)
        self.assertTrue(any(t['SUPPORT']['HISTORY']['hits'] for t in retrieval['tasks'].values()))
        accepted=read(dest/'computation.json')['accepted'];self.assertTrue(any(x['report_eligible'] for x in accepted['analogies'].values()))
        final=read(dest/'final-report.json')
        self.assertTrue(any(x['include'] for x in final['comparisons'].values()))
        self.assertIn('HISTORICAL COMPARISON', (dest/'final-report.txt').read_text())
        self.assertTrue(read(dest/'history-usage.json')['final_history_items'])
        index=Index(snapshot);hist=[i for i,s in snapshot['directory'].items() if s['domain']=='HISTORY'][0]
        p=read(dest/'shared.json')['proposal'];self.assertTrue(all(hist not in u['refs'] for u in p['uses'].values()))
    def test_frozen_corpus_loader_rejects_related_dispute(self):
        corpus=self.work/'corpus.json';save(corpus,{'sources':[{'source_id':'s','text':'Other case source, no labels'}]})
        item={'id':'history','path':'corpus.json','sha256':hashlib.sha256(corpus.read_bytes()).hexdigest(),'allowed_cases':['T'],'visibility':'ALLOWED','domain':'HISTORY','dispute_group':'other'}
        manifest=self.work/'manifest.json';save(manifest,{'documents':[item],'target_dispute_groups':{'T':['target']}})
        rows,h=load_corpus(manifest,'T');self.assertEqual(rows[0]['document_role'],'HISTORICAL')
        bad=self.work/'bad-manifest.json';save(bad,{'documents':[item],'target_dispute_groups':{'T':['other']}})
        with self.assertRaisesRegex(ValueError,'LEAKAGE'):load_corpus(bad,'T')

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(WholeMechanisms))
    save(WholeMechanisms.work/'acceptance.json',{'kind':'SYNTHETIC_END_TO_END_ENGINEERING_NOT_MODEL_QUALITY','tests':result.testsRun,'passed':result.wasSuccessful(),
        'failures':[(str(t),s) for t,s in result.failures+result.errors],'new_model_calls':0,'real_case_quality':None})
    raise SystemExit(0 if result.wasSuccessful() else 1)
