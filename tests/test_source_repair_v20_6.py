"""Unified regressions for real failures and the actual repair-to-final entry."""
import copy
import json
import unittest
from pathlib import Path
from legal_bench.proof_carrying import source_repair_v20_6 as repair
from legal_bench.proof_carrying import local_pipeline_v19_8 as core
from legal_bench.proof_carrying import shared_sources_v20_3 as shared
from legal_bench.proof_carrying.repetition_v20_6 import StringGuard, RepetitionAbort, duplicates
from legal_bench.proof_carrying.schema_contract_v19_6 import validate

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT/'outputs/proof-evidence-binding-rerun-v20-5'


def read(path):
    return json.loads(path.read_text())


class RepairRegression(unittest.TestCase):
    def test_actual_cross_item_failure_is_caught(self):
        text = (OLD/'local/1954254/P02/repair/raw-response.txt')
        if not text.exists():
            text = OLD/'local/1954254/P02/raw-response.txt'
        raw = text.read_text()
        guard = StringGuard()
        with self.assertRaises(RepetitionAbort):
            for start in range(0,len(raw),31):
                guard.feed(raw[start:start+31])
        self.assertEqual(guard.hit['kind'],'EXACT_REPEATED_EXPLANATORY_ITEM')
        self.assertEqual(guard.hit['field'],'coverage_limits')

    def test_distinct_scopes_and_escaped_strings_remain_valid(self):
        note = 'A quoted "qualification" belongs to this separate legal premise. '*2
        value = {'analyses': {'A': {'gaps': [note]},'B': {'gaps':[note]}},
            'coverage_limits': ['A specific qualification about the first claim.',
                                'A different qualification about the second claim.']}
        guard = StringGuard()
        for c in json.dumps(value):
            guard.feed(c)
        self.assertIsNone(guard.hit)
        self.assertEqual(duplicates(value),[])

    def test_corrected_category_does_not_change_rule_text_or_input(self):
        fixture=read(OLD/'preparation/1187427/P01/fixture.json')
        original=copy.deepcopy(fixture['rules'])
        rules,changes=repair.corrected_rules(original)
        self.assertEqual(len(changes),1)
        self.assertEqual(original,fixture['rules'])
        before={p['id']:p['text'] for r in original for p in r['premises']}
        after={p['id']:p['text'] for r in rules for p in r['premises']}
        self.assertEqual(before,after)
        p=next(p for r in rules for p in r['premises'] if p['id']==changes[0]['premise'])
        self.assertEqual(p['variables']['statutory_term'],'LEGAL_CONCEPT')
        schema=repair.repair_task(fixture['case'],rules,
            next(t['part'] for t in read(OLD/'plan.json')['tasks'] if t['case_id']=='1187427'),
            read(OLD/'local/1187427/P01/expanded.json'))['schema']
        role=schema['properties']['analyses']['properties'][p['id']]['properties']['uses']['items']['properties']['role_objects']['properties']['statutory_term']
        self.assertTrue(role['description'].endswith('LEGAL_CONCEPT'))

    def test_real_cached_parts_enter_local_recomputation(self):
        # These injected labels check program behavior only, never semantic truth.
        plan=read(OLD/'plan.json')
        by_case={}
        for slot in plan['tasks']:
            cid,pid=slot['case_id'],slot['part']['id']
            fixture=read(OLD/'preparation'/cid/pid/'fixture.json')
            rules,_=repair.corrected_rules(fixture['rules'])
            rules=[r for r in rules if r['id'] in slot['part']['rule_ids']]
            original=read(OLD/'local'/cid/pid/'expanded.json')
            immutable_copy=copy.deepcopy(original)
            task=repair.critique_task(fixture['case'],rules,original)
            criticism={'verdicts':{k:{'label':'SUPPORTED','refs':row['refs'][:1] or ['SRC:1'],
                'reason':'Injected positive control for code behavior only.'}
                for k,row in task['claims'].items()},'coverage_limits':[]}
            binding_key=next(k for k,row in task['claims'].items() if row['kind']=='OBJECT_BINDING')
            criticism['verdicts'][binding_key]['label']='UNSUPPORTED'
            applied=repair.apply_critique(fixture['case'],rules,original,task,criticism)
            self.assertEqual(applied['independent']['status'],'OK')
            self.assertTrue(any(x['effect']=='LOCAL_BINDING_PENDING' for x in applied['application_ledger']))
            self.assertEqual(original,immutable_copy)
            # Other independently accepted declarations remain candidates.
            self.assertGreater(applied['decision_counts'].get('SUPPORTED',0),0)
            by_case.setdefault(cid,[]).append((pid,applied))
        fixture=read(OLD/'preparation/1954254/P01/fixture.json')
        full_rules,_=repair.corrected_rules(fixture['rules'])
        selected=[r for r in full_rules if r['id']!='R11']
        merged=repair.merge_applied(fixture['case'],selected,by_case['1954254'])
        final=repair.final_task(fixture['case'],full_rules,merged,by_case['1954254'])
        self.assertEqual(final['source_ids'],[s['id'] for s in fixture['case']['segments']])
        self.assertFalse(final['source_input_truncated'])
        # The final entry accepts a genuine unknown without calling it a failure.
        synthetic={'request_id':'Q1','conclusion':'Unknown in this synthetic code test.',
            'grounds':[{'point':'Synthetic code test only.','statement_status_and_stage':'UNKNOWN',
                'case_refs':final['source_ids'][:1],'rule_refs':[], 'explanation':'Not a real legal answer.'}],
            'counterarguments':[],'gaps':['Missing synthetic evidence.'],'assumptions':[],
            'connection_handling':[]}
        accepted=core.accept_final(final,json.dumps(synthetic),'OK')
        self.assertIsNotNone(accepted['answer'])

    def test_stale_review_is_rejected(self):
        fixture=read(OLD/'preparation/1954254/P02/fixture.json')
        rules,_=repair.corrected_rules(fixture['rules'])
        rules=[r for r in rules if r['id'] in ['R06','R07','R08','R09','R10']]
        raw=read(OLD/'local/1954254/P02/expanded.json')
        task=repair.critique_task(fixture['case'],rules,raw)
        changed=copy.deepcopy(raw);changed['coverage_limits'].append('New version.')
        with self.assertRaisesRegex(ValueError,'STALE_SOURCE_CRITIQUE'):
            repair.apply_critique(fixture['case'],rules,changed,task,{})


if __name__=='__main__':
    unittest.main()
