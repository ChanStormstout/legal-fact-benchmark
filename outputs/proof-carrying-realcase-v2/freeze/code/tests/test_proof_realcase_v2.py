import copy, json, subprocess, sys, tempfile, unittest
from pathlib import Path
from legal_bench.proof_carrying.contracts import content_hash,write_once,byte_hash
from legal_bench.proof_carrying.realcase_engine import propose
from legal_bench.proof_carrying.realcase_tasks import prompt
from legal_bench.proof_carrying.realcase_checker import check_payload
from legal_bench.proof_carrying.review_priority_v2 import order

ROOT=Path(__file__).resolve().parents[1]
def fixture():
    b=[{'role':'subject','entity':'Mira'},{'role':'property','entity':'Z'}]
    p={'id':'F1','predicate':'OCCUPATION_RECORDED','text':'Recorded occupation.', 'bindings':b,'time_scope':'Monday',
       'statement_status':'LOWER_COURT_FINDING','speaker':'court','court_level':'trial','stage':'trial','state':'TRUE',
       'refs':['S1'],'quote':'Mira occupied Z.','limitations':['Title not determined; not a blocker to the record.']}
    r={'id':'R1','version':1,'description':'Synthetic record rule','conclusion_predicate':'RECORD_AVAILABLE',
        'conclusion_text':'An occupation record is available; no title consequence.','jurisdiction':'Synthetic','stage':'APPEAL',
        'origin':'RESEARCH_TRANSLATION','source_refs':['R0'],'source_quote':'An occupation record is available.',
        'operator':'ALL','slots':[{'name':'record','predicate':'OCCUPATION_RECORDED','description':'record',
            'expected':'TRUE','allowed_statuses':['LOWER_COURT_FINDING'],'required_roles':['subject','property'],'time_required':True}],
        'exception_slots':[],'scope_limits':['Synthetic'],'burden_policy':'NOT_COVERED','unimplemented':[]}
    r2=copy.deepcopy(r);r2.update(id='R2',conclusion_predicate='RECORD_CHAIN');r2['slots'][0]['predicate']='RECORD_AVAILABLE'
    snap={'snapshot_id':'S1','case_id':'SYNTHETIC','stage':'APPEAL','jurisdiction':'Synthetic','entities':{'Mira':{},'Z':{},'Q':{}},
        'sources':{'S1':{'text':'Mira occupied Z.','role':'JUDGMENT_TEXT','url':'synthetic://source'},
                   'R0':{'text':'An occupation record is available.','role':'JUDGMENT_TEXT','url':'synthetic://rule'}},
        'documents':[],'premises':{'F1':p},'rules':{'R1@1':r,'R2@1':r2},'reviews':{'premises':{},'rules':{}}}
    refresh(snap)
    steps=[{'id':'T1','rule_ref':'R1@1','bindings':b,'time_scope':'Monday','inputs':[{'slot':'record','kind':'PREMISE','id':'F1'}],
       'proposed_state':'TRUE','explanation':'narrow record chain'},
       {'id':'T2','rule_ref':'R2@1','bindings':b,'time_scope':'Monday','inputs':[{'slot':'record','kind':'STEP','id':'T1'}],
       'proposed_state':'TRUE','explanation':'consume prior typed result'}]
    deriv={'steps':steps,'requests':[{'id':'Q1','step_id':'T2','predicate':'RECORD_CHAIN','text':'Record chain available.',
       'proposed_state':'TRUE'}],'counterarguments':['No title determination.'],'gaps':['Legal approval pending.']}
    return snap,deriv

def refresh(s):
    for category in ('premises','rules'):
        s['reviews'][category]={k:{'subject_hash':content_hash(v),'decision':'ACCEPT_RESEARCH','qualified_legal_approval':False} for k,v in s[category].items()}

class RealcaseTests(unittest.TestCase):
    def run_cli(self,s,d,current=None,corrupt_source=False):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);s=copy.deepcopy(s)
            (p/'source.txt').write_text('Synthetic source bytes')
            s['documents']=[{'path':'source.txt','sha256':byte_hash(p/'source.txt')}]
            write_once(p/'snapshot.json',s)
            write_once(p/'manifest.json',{'snapshots':{s['snapshot_id']:{'path':'snapshot.json','sha256':byte_hash(p/'snapshot.json')}}})
            write_once(p/'cert.json',propose(s,d))
            if corrupt_source:(p/'source.txt').write_text('changed')
            cmd=[sys.executable,str(ROOT/'scripts/check_realcase_certificate.py'),str(p/'cert.json'),'--manifest',str(p/'manifest.json')]
            if current:cmd+=['--current',current]
            r=subprocess.run(cmd,text=True,capture_output=True,cwd=ROOT);self.assertEqual(r.returncode,0,r.stderr)
            return json.loads(r.stdout)
    def test_real_entry_chain_pending_approval_not_unknown(self):
        s,d=fixture();r=self.run_cli(s,d)
        self.assertEqual(r['requests'][0]['answer'],'TRUE');self.assertFalse(r['legal_approval'])
        self.assertEqual(r['requests'][0]['formal_status'],'APPROVAL_PENDING')
        self.assertIn('T1',r['steps']);self.assertEqual(r['steps']['T2']['dependencies'][0]['kind'],'STEP')
    def test_local_branch_missing_does_not_block_other_request(self):
        s,d=fixture();d['steps'][1]['inputs']=[];d['steps'][1]['proposed_state']='UNKNOWN';d['requests'][0]['proposed_state']='UNKNOWN'
        d['requests'].append({'id':'Q2','step_id':'T1','predicate':'RECORD_AVAILABLE','text':'Record','proposed_state':'TRUE'})
        r=self.run_cli(s,d);self.assertEqual([q['answer'] for q in r['requests']],['UNKNOWN','TRUE'])
    def test_binding_and_time_errors(self):
        for field,value,code in [('bindings',[{'role':'subject','entity':'Mira'},{'role':'property','entity':'Q'}],'CROSS_OBJECT_JOIN'),('time_scope','Tuesday','TIME_SCOPE_MISMATCH')]:
            s,d=fixture();d['steps'][0][field]=value;r=self.run_cli(s,d)
            self.assertTrue(any(code in e for e in r['steps']['T1']['errors']))
    def test_party_and_disposition_no_upgrade(self):
        for status,code in [('PARTY_CLAIM','STATEMENT_STATUS_UPGRADE'),('TARGET_DISPOSITION','DISPOSITION_OR_RULE_AS_FACT')]:
            s,d=fixture();s['premises']['F1']['statement_status']=status;refresh(s);r=self.run_cli(s,d)
            self.assertTrue(any(code in e for e in r['steps']['T1']['errors']))
    def test_cycle_dangling_version_and_type_upgrade(self):
        for change in ('cycle','dangling','version','type'):
            s,d=fixture()
            if change=='cycle':d['steps'][0]['inputs']=[{'slot':'record','kind':'STEP','id':'T2'}]
            if change=='dangling':d['steps'][1]['inputs'][0]['id']='NONE'
            if change=='version':d['steps'][1]['rule_ref']='R2@99'
            if change=='type':d['requests'][0]['predicate']='OWNER_CONFIRMED'
            self.assertIsNone(self.run_cli(s,d)['requests'][0]['answer'])
    def test_nonproof_is_not_false_and_notes_not_blanket_blocker(self):
        s,d=fixture();s['premises']['F1']['state']='UNKNOWN';refresh(s)
        for x in d['steps']:x['proposed_state']='UNKNOWN'
        d['requests'][0]['proposed_state']='UNKNOWN';r=self.run_cli(s,d)
        self.assertEqual(r['requests'][0]['answer'],'UNKNOWN')
    def test_any_and_exception_preserve_unknown(self):
        s,d=fixture();r=s['rules']['R1@1'];r['operator']='ANY'
        optional=copy.deepcopy(r['slots'][0]);optional['name']='other';r['slots'].append(optional)
        refresh(s);self.assertEqual(self.run_cli(s,d)['requests'][0]['answer'],'TRUE')
        ex=copy.deepcopy(optional);ex.update(name='exception',predicate='EXCEPTION');r['slots'].append(ex);r['exception_slots']=['exception'];refresh(s)
        for x in d['steps']:x['proposed_state']='UNKNOWN'
        d['requests'][0]['proposed_state']='UNKNOWN'
        result=self.run_cli(s,d);self.assertEqual(result['requests'][0]['answer'],'UNKNOWN')
    def test_false_antecedent_not_negative_conclusion(self):
        s,d=fixture();s['premises']['F1']['state']='FALSE';refresh(s)
        for x in d['steps']:x['proposed_state']='UNKNOWN'
        d['requests'][0]['proposed_state']='UNKNOWN'
        r=self.run_cli(s,d);self.assertEqual(r['requests'][0]['answer'],'UNKNOWN')
        self.assertIn('SUFFICIENT_RULE_NOT_APPLICABLE_NO_NEGATIVE_INFERENCE',r['steps']['T1']['gaps'])
    def test_source_and_old_snapshot(self):
        s,d=fixture();self.assertEqual(self.run_cli(s,d,current='S2')['reason'],'STALE_CURRENT_SNAPSHOT')
        self.assertEqual(self.run_cli(s,d,corrupt_source=True)['reason'],'SOURCE_BYTES_CHANGED')
        self.assertEqual(self.run_cli(s,d,current='S1')['requests'][0]['answer'],'TRUE')
    def test_empty_or_duplicate_requests(self):
        s,d=fixture();d['requests']=[];self.assertIn('EMPTY_REQUESTS',self.run_cli(s,d)['reason'])
        s,d=fixture();d['requests']*=2;self.assertIn('DUPLICATE',self.run_cli(s,d)['reason'])
    def test_reference_isolation(self):
        with self.assertRaisesRegex(ValueError,'ISOLATION'):
            prompt('789051','reference',{'segments':[]},{'rules':{},'facts':{}})
    def test_graph_conflict_and_isolate(self):
        s,d=fixture();p=s['premises']['F1'];p2=copy.deepcopy(p);p2['id']='F2';p3=copy.deepcopy(p);p3['id']='F3'
        g=order({'premises':[p,p2,p3],'relations':[{'from':'F1','to':'F2','sign':x,'refs':['S1'],'reason':'synthetic'} for x in ('SUPPORT','OPPOSE')]})
        self.assertEqual(g['signed_graph']['conflicting_pairs'],[[0,1]]);self.assertEqual(g['signed_graph']['isolates'],[2])
        self.assertFalse(g['truth_or_approval_changed']);self.assertEqual(len(g['graph_budget_5']),3)
    def test_immutable_write(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x.json';write_once(p,{'a':1})
            with self.assertRaises(FileExistsError):write_once(p,{'a':2})
            self.assertEqual(json.loads(p.read_text()),{'a':1})
    def test_checker_not_import_engine(self):
        src=(ROOT/'legal_bench/proof_carrying/realcase_checker.py').read_text()
        self.assertNotIn('import realcase_engine',src);self.assertNotIn('from .realcase_engine',src)

if __name__=='__main__':unittest.main()
