import copy, json, subprocess, sys, tempfile, unittest
from pathlib import Path
from tests.test_proof_realcase_v2 import fixture, refresh
from legal_bench.proof_carrying.contracts import content_hash, byte_hash
from legal_bench.proof_carrying.realcase_engine import propose
from legal_bench.proof_carrying.realcase_checker_v3 import check_payload
from legal_bench.proof_carrying.realcase_grounding_v3 import source_match
from scripts.proof_realcase_repair_v3 import review, assessment

ROOT=Path(__file__).resolve().parents[1]

def scoped():
    s,d=fixture()
    for src in s['sources'].values():src['document']=s['case_id']
    s['scope_reviews']={k:{'subject_hash':content_hash(r),'jurisdiction_compatible':True,'stage_compatible':True} for k,r in s['rules'].items()}
    return s,d

def run(s,d):return check_payload(propose(s,d),s)

def open_fixture():
    s,d=scoped();s['rules']['R1@1']['operator']='OPEN_TEXT';refresh(s)
    s['scope_reviews']['R1@1']['subject_hash']=content_hash(s['rules']['R1@1'])
    s['sources']['IK-SYNTHETIC:L1']={'text':'The court expressly found this record available.',
        'document':s['case_id'],'role':'JUDGMENT_TEXT'}
    assessment(s,d,'T1',[1],'Synthetic attributed assessment; not a merits evaluator.')
    return s,d

class RepairTests(unittest.TestCase):
    def test_reversible_quote_and_no_semantic_cleanup(self):
        src={'X':{'text':"In cite21†Londa 's case, the Act . No title was proved."}}
        m=source_match({'refs':['X'],'quote':"Londa's case, the Act."},src)
        self.assertIsNone(m['error']);self.assertEqual(m['mode'],'RENDERER_WHITESPACE_OR_CITATION')
        for span in m['original_spans']:
            self.assertEqual(span['original'],src[span['ref']]['text'][span['start']:span['end']])
        self.assertEqual(source_match({'refs':['X'],'quote':'Title was proved.'},src)['error'],'QUOTE_NOT_LOCATED')
        self.assertEqual(source_match({'refs':['X'],'quote':'No title was disproved.'},src)['error'],'QUOTE_NOT_LOCATED')

    def test_unsupported_not_refutation_or_fact_unknown(self):
        s,d=open_fixture();s.pop('court_assessments')
        r=run(s,d);self.assertEqual(r['requests'][0]['draft_status'],'INCOMPLETE_EXECUTION')
        self.assertIsNone(r['requests'][0]['answer']);self.assertEqual(r['requests'][0]['errors'],[])
        self.assertEqual(s['premises']['F1']['state'],'TRUE')
        self.assertIn('T1',r['requests'][0]['uncomputed'])

    def test_attributed_assessment_propagates_not_legal_approval(self):
        s,d=open_fixture();r=run(s,d)
        self.assertEqual(r['requests'][0]['draft_status'],'CONDITIONAL_RECONSTRUCTION')
        self.assertEqual(r['requests'][0]['answer'],'TRUE')
        self.assertEqual(r['requests'][0]['semantic_assumptions'],['CA-SYNTHETIC-T1'])
        self.assertFalse(r['legal_approval'])

    def test_bad_assessment_cannot_launder_proposal(self):
        for field,value in [('state','FALSE'),('statement_status','PARTY_CLAIM'),('predicate','OWNERSHIP'),
                            ('case_id','OTHER'),('stage','OTHER'),('rule_hash','bad'),('quote','Missing words')]:
            with self.subTest(field=field):
                s,d=open_fixture();a=s['court_assessments']['T1'];a.pop('review');a[field]=value;review(a)
                self.assertIn('COURT_ASSESSMENT_UNVERIFIED',run(s,d)['steps']['T1']['errors'])
        s,d=open_fixture();s['sources']['IK-SYNTHETIC:L1']['role']='DISPOSITION_ONLY'
        self.assertIn('COURT_ASSESSMENT_SOURCE_ROLE',run(s,d)['steps']['T1']['errors'])

    def test_unknown_or_opposed_premise_not_overridden_by_assessment(self):
        for state in ('UNKNOWN','CONFLICTED','FALSE'):
            s,d=open_fixture();s['premises']['F1']['state']=state;refresh(s)
            self.assertIsNone(run(s,d)['requests'][0]['answer'])
        s,d=open_fixture();s['premises']['F1']['statement_status']='PARTY_CLAIM';refresh(s)
        self.assertTrue(any('STATEMENT_STATUS_UPGRADE' in x for x in run(s,d)['steps']['T1']['errors']))

    def test_mapping_explicit_and_slot_local(self):
        s,d=scoped();p=s['premises']['F1'];p['bindings']=copy.deepcopy(p['bindings']);p['bindings'][0]['entity']='Q';refresh(s)
        self.assertIn('CROSS_OBJECT_JOIN:record',run(s,d)['steps']['T1']['errors'])
        # Invalid reviewed mapping cannot replace identities.
        r=s['rules']['R1@1'];s['role_mappings']={'T1:record':review({'id':'MAP',
            'case_id':s['case_id'],'stage':s['stage'],'rule_ref':'R1@1','rule_hash':content_hash(r),
            'premise_id':'F1','premise_hash':content_hash(p),'slot':'record',
            'roles':{'subject':'Q','property':'property'},'refs':p['refs'],'quote':p['quote']})}
        self.assertIn('ROLE_MAPPING_NOT_PERMUTATION:record',run(s,d)['steps']['T1']['errors'])

    def test_real_slot_mapping_preserves_original_and_other_bindings(self):
        base=ROOT/'outputs/proof-carrying-realcase-v2/cases/1841885/snapshots/S1.json'
        s=json.loads(base.read_text());d=json.loads((ROOT/'outputs/proof-carrying-realcase-v2/runs/1841885/derivation/parsed.json').read_text())
        original=copy.deepcopy(s['premises']['F8']);p=s['premises']['F8'];r=s['rules']['R5@1']
        s['role_mappings']={'S5:trust_denial_recorded':review({'id':'MAP','case_id':s['case_id'],
            'stage':s['stage'],'rule_ref':'R5@1','rule_hash':content_hash(r),'premise_id':'F8','premise_hash':content_hash(p),
            'slot':'trust_denial_recorded','roles':{'subject':'opponent','opponent':'subject','property':'property','transaction':'transaction'},
            'refs':['IK-1841885:L138'],'quote':s['sources']['IK-1841885:L138']['text']})}
        self.assertEqual(run(s,d)['steps']['S5']['status'],'CONDITIONAL_RECONSTRUCTION')
        self.assertEqual(s['premises']['F8'],original)
        s['role_mappings']['unrelated']=s['role_mappings'].pop('S5:trust_denial_recorded')
        self.assertIn('CROSS_OBJECT_JOIN:trust_denial_recorded',run(s,d)['steps']['S5']['errors'])

    def test_actual_cli_entry_and_source_tamper(self):
        s,d=open_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.txt';source.write_text('original')
            s['documents']=[{'path':'source.txt','sha256':byte_hash(source)}]
            snap=root/'snapshot.json';snap.write_text(json.dumps(s))
            cert=root/'cert.json';cert.write_text(json.dumps(propose(s,d)))
            manifest=root/'manifest.json';manifest.write_text(json.dumps({'snapshots':{s['snapshot_id']:{'path':'snapshot.json','sha256':byte_hash(snap)}}}))
            cmd=[sys.executable,str(ROOT/'scripts/check_realcase_certificate_v3.py'),str(cert),'--manifest',str(manifest)]
            p=subprocess.run(cmd,text=True,capture_output=True,cwd=ROOT);result=json.loads(p.stdout)
            self.assertEqual(result['requests'][0]['draft_status'],'CONDITIONAL_RECONSTRUCTION')
            source.write_text('changed');result=json.loads(subprocess.run(cmd,text=True,capture_output=True,cwd=ROOT).stdout)
            self.assertEqual(result['status'],'TECHNICAL_OR_CONTRACT_FAILURE');self.assertIsNone(result['answer'])

    def test_reviewed_rule_version_preserves_old_unknown_merits(self):
        from scripts.proof_realcase_repair_v3 import revise_sopan
        s=json.loads((ROOT/'outputs/proof-carrying-realcase-v2/cases/1841885/snapshots/S1.json').read_text())
        d=json.loads((ROOT/'outputs/proof-carrying-realcase-v2/runs/1841885/derivation/parsed.json').read_text())
        old=copy.deepcopy(s['rules']['R6@1']);f=copy.deepcopy(s['premises']['F11'])
        revise_sopan(s,d)
        self.assertEqual(s['rules']['R6@1'],old);self.assertEqual(s['premises']['F11'],f)
        self.assertEqual(s['reviews']['rules']['R6@1']['decision'],'SUSPEND')
        self.assertEqual(s['premises']['F15-REVIEWED']['state'],'TRUE')
        self.assertEqual(s['premises']['F11']['state'],'UNKNOWN')

    def test_new_checker_keeps_structural_rejections_and_local_branch(self):
        mutations=[
            lambda s,d:d['steps'][0].update(time_scope='Tuesday'),
            lambda s,d:d['steps'][0].update(rule_ref='R1@999'),
            lambda s,d:d['steps'][0]['inputs'][0].update(kind='STEP',id='T2'),
            lambda s,d:d['requests'][0].update(predicate='OWNERSHIP'),
        ]
        for mutate in mutations:
            s,d=scoped();mutate(s,d)
            self.assertEqual(run(s,d)['requests'][0]['draft_status'],'INVALID')
        s,d=scoped();d['requests'].append({**d['requests'][0],'id':'GOOD','step_id':'T1',
            'predicate':s['rules']['R1@1']['conclusion_predicate']})
        d['steps'][1]['inputs'][0]['id']='MISSING'
        results=run(s,d)['requests']
        self.assertEqual(results[0]['draft_status'],'INVALID')
        self.assertEqual(results[1]['answer'],'TRUE')

    def test_new_checker_any_exception_and_false_nonproof(self):
        s,d=scoped();r=s['rules']['R1@1']
        r['operator']='ANY';r['slots'].append({**r['slots'][0],'name':'absent'})
        refresh(s);s['scope_reviews']['R1@1']['subject_hash']=content_hash(r)
        self.assertEqual(run(s,d)['requests'][0]['answer'],'TRUE')
        r['exception_slots']=['absent'];refresh(s);s['scope_reviews']['R1@1']['subject_hash']=content_hash(r)
        self.assertEqual(run(s,d)['requests'][0]['answer'],'UNKNOWN')
        self.assertEqual(run(s,d)['requests'][0]['errors'],[])
        s,d=scoped();s['premises']['F1']['state']='FALSE';refresh(s)
        self.assertEqual(run(s,d)['requests'][0]['answer'],'UNKNOWN')
        self.assertEqual(run(s,d)['requests'][0]['errors'],[])

if __name__=='__main__':unittest.main()
