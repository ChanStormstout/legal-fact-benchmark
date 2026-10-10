import copy,unittest
from pathlib import Path
from legal_bench.proof_carrying.contracts import read_json,content_hash
from legal_bench.proof_carrying.realcase_engine import propose
from legal_bench.proof_carrying.realcase_checker_v4 import check_payload
from legal_bench.proof_carrying.realcase_grounding_v4 import step_semantic_hash
from scripts.proof_checker_patch_v4 import migrate

ROOT=Path(__file__).resolve().parents[1]/'outputs/proof-carrying-checker-evaluation-v4/natural/789051'

class AddressTests(unittest.TestCase):
    def base(self):
        s=read_json(ROOT/'snapshot.json');p=read_json(ROOT/'certificate.json')['proposal']
        return migrate(s,p)[0],p

    def test_equivalent_order_prose_and_binding_order(self):
        for operation in ('inputs','bindings','explanation'):
            s,p=self.base();t=p['steps'][1];h=step_semantic_hash(t)
            if operation=='explanation':t['explanation']='Different prose, same named inputs.'
            else:t[operation]=list(reversed(t[operation]))
            self.assertEqual(h,step_semantic_hash(t))
            r=check_payload(propose(s,p),s);self.assertEqual(r['requests'][0]['answer'],'TRUE')

    def test_material_fields_still_pinned_and_invalid(self):
        for field,value in [('time_scope','Different time'),('rule_ref','R2@999'),('proposed_state','FALSE')]:
            s,p=self.base();t=p['steps'][1];h=step_semantic_hash(t);t[field]=value
            self.assertNotEqual(h,step_semantic_hash(t));self.assertIsNone(check_payload(propose(s,p),s)['requests'][0]['answer'])
        s,p=self.base();p['steps'][1]['inputs'][0]['id']='F12'
        self.assertIsNone(check_payload(propose(s,p),s)['requests'][0]['answer'])
        s,p=self.base();p['steps'][1]['bindings'][0]['entity']='E2'
        self.assertIsNone(check_payload(propose(s,p),s)['requests'][0]['answer'])

    def test_duplicate_slots_still_rejected(self):
        s,p=self.base();p['steps'][1]['inputs'].append(copy.deepcopy(p['steps'][1]['inputs'][0]))
        self.assertIsNone(check_payload(propose(s,p),s)['requests'][0]['answer'])

    def test_prose_preserved_but_not_displayed_as_checked(self):
        s,p=self.base();bad='The plaintiff owns the suit land.';p['requests'][0]['text']=bad
        q=check_payload(propose(s,p),s)['requests'][0]
        self.assertEqual(q['submitted_text'],bad);self.assertNotEqual(q['text'],bad)
        self.assertFalse(q['submitted_text_semantically_checked'])

if __name__=='__main__':unittest.main()
