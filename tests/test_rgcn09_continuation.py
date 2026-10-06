import copy
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from scripts.rgcn09_continuation import allocate, save, ROOT
from scripts.rgcn09_import import join_old_graph, inspect_labels, payload

class ContinuationTests(unittest.TestCase):
    def test_allocation_before_labels_keeps_known_disputes_together(self):
        rows=[dict(case_id=str(i),group_id='g' if i<2 else str(i),decision='QUALIFIED_MAIN',mechanism='family_occupation',stage='ARC_TRIAL',rank=i) for i in range(5)]
        result=allocate(rows,{'g':'DEVELOPMENT'})
        self.assertEqual([x['split'] for x in result[:2]],['DEVELOPMENT']*2)
        self.assertEqual([x['split'] for x in result[2:]],['TRAIN','TRAIN','SEALED_TEST'])
        self.assertEqual(result,allocate(list(reversed(rows)),{'g':'DEVELOPMENT'}))

    def test_old_facts_preserved_and_no_labels_joined_into_graph(self):
        old=dict(case_id='1',needs=[{'id':'n1'}],objects=[{'id':'o1'}],facts=[{'id':'f1','status':'CLAIMED'}],relations=[],alignments=[{'unit_id':'OLD'}],coverage_limits=['old'])
        sup=dict(case_id='1',alignments=[{'unit_id':'NEW','scope':'UNKNOWN'}],coverage_limits=['new'])
        combined=join_old_graph(old,sup,['NEW'])
        self.assertEqual(combined['facts'],old['facts']);self.assertEqual(old['coverage_limits'],['old'])
        sup['uses']=[]
        with self.assertRaisesRegex(ValueError,'INTERFACE'):join_old_graph(old,sup,['NEW'])

    def test_bad_label_row_isolated_unknown_not_negative(self):
        case={'case_id':'1','split':'TRAIN','segments':[{'id':'s1','text':'record'}]}
        units=[{'id':'a','text':'control rule'},{'id':'b','text':'other'}]
        p={'case_id':'1','uses':[{'unit_id':'a','category':'CORE','reason':'control','case_refs':['s1'],'law_quote':'invented'}, {'unit_id':'b','category':'UNKNOWN','reason':'not determined','case_refs':[],'law_quote':''}],'unresolved':[]}
        result=inspect_labels(p,case,units,['a','b'])
        self.assertEqual(len(result['isolated']),1);self.assertEqual(result['known'],[]);self.assertEqual(len(result['unknown']),1)

    def test_tasks_never_include_sealed_and_immutable_save(self):
        manifest=json.loads((ROOT/'split-manifest.json').read_text());roles={r['case_id']:r['split'] for r in manifest['cases']}
        for task in json.loads((ROOT/'prepared-task-ledger.json').read_text()):self.assertEqual(roles[task['case_id']],'TRAIN')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.json';save(p,{'v':1});original=p.read_bytes();save(p,{'v':1})
            with self.assertRaisesRegex(ValueError,'IMMUTABLE'):save(p,{'v':2})
            self.assertEqual(p.read_bytes(),original)

    def test_wrapper_removal_preserves_one_complete_payload(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'web').mkdir()
            p={'case_id':'1','uses':[],'unresolved':[]}
            (root/'web/LABEL-1.response.txt').write_text('Reply\n```json\n'+json.dumps(p)+'\n```\nEnd')
            with patch('scripts.rgcn09_import.ROOT',root):
                restored,_,_=payload('LABEL-1')
            self.assertEqual(restored,p)

    def test_ambiguous_or_incomplete_json_is_not_repaired(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'web').mkdir();raw=root/'web/LABEL-1.response.txt'
            for text in ('{"case_id":"1","uses":[',
                         '{"case_id":"1","uses":[]}\n{"case_id":"1","uses":[],"unresolved":[]}'):
                raw.write_text(text)
                with patch('scripts.rgcn09_import.ROOT',root):
                    with self.assertRaisesRegex(ValueError,'NO_COMPLETE_JSON'):payload('LABEL-1')

if __name__=='__main__':unittest.main()
