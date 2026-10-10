import copy
import json
import tempfile
import unittest
from pathlib import Path
from scripts import irac_web_v9 as v


class WebV9Tests(unittest.TestCase):
    def test_old_two_regression(self):
        for c in ('112400','188721101'):
            for s in ('A','P'):
                text,sc,a=v.assemble(c,s)
                old=Path('outputs/irac-semantic-interface-v6/runs')/c/s
                self.assertEqual(text,(old/'prompt.txt').read_text())
                self.assertEqual(sc,v.read(old/'schema.json'))
                self.assertTrue(a['passed'])

    def test_four_materials_and_B_exact_delta(self):
        raw={'records':[],'arrangements':[],'conditions':[],'limitations':[],'coverage_limits':['Synthetic assembly check only.']}
        for c in v.CASES:
            a,sc,ad=v.assemble(c,'A');p,_,pd=v.assemble(c,'P');b,bs,bd=v.assemble(c,'B',raw)
            self.assertEqual(sc,bs)
            self.assertEqual(ad['source_map'],pd['source_map'])
            self.assertEqual(ad['source_map'],bd['source_map'])
            self.assertEqual(ad['law_sha256'],pd['law_sha256'])
            before,rest=b.split(v.MARK,1);inter,after=rest.split(v.END,1)
            self.assertEqual(json.loads(inter),{'proposal':raw})
            self.assertEqual(before+v.MARK+'{}'+v.END+after,a)

    def test_actual_web_import_local_error_preserves_raw(self):
        c='1114159';m,t,l,sm=v.inputs(c)
        sid=next(iter(m['sources']))
        from legal_bench.irac_application.semantic_v6 import catalogue
        condition=next(iter(catalogue(t)))
        p={'records':[{'text':'Synthetic retained record','statement_status':'PARTY_CLAIM','refs':[sid]}],
           'arrangements':[{'description':'Synthetic arrangement','refs':[sid]}],
           'conditions':[{'arrangement':1,'condition':condition,'assessment':'UNRESOLVED',
                          'evidence':[{'record':12,'role':'SUPPORT','connection':'Invalid local reference'}],
                          'law_refs':[],'explanation':'Synthetic pending judgment','gaps':[]}],
           'limitations':[],'coverage_limits':[]}
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);(out/'raw-response.txt').write_text(json.dumps(p))
            result=v.accept(c,'P',out)
            self.assertEqual(result['answer'],p)
            imp=v.read(out/'import.json')
            self.assertEqual(len(imp['records']),1)
            self.assertTrue(imp['quarantine'])
            b,_,_=v.assemble(c,'B',p)
            self.assertEqual(json.loads(b.split(v.MARK)[1].split(v.END)[0])['proposal'],p)

    def test_actual_web_final_completion_and_failure(self):
        c='112400';old=v.read('outputs/irac-semantic-interface-v6/runs/112400/A/result.json')['prediction']
        wrong=copy.deepcopy(old);wrong['answers'][0]['claim_id']='MISSING_REQUEST'
        for value,ok in [(old,True),({'answers':[]},False),({'answers':old['answers']*2},False),(wrong,False)]:
            with tempfile.TemporaryDirectory() as td:
                out=Path(td);raw=json.dumps(value);(out/'raw-response.txt').write_text(raw)
                r=v.accept(c,'A',out)
                self.assertEqual(r['answer'] is not None,ok)
                self.assertEqual((out/'raw-response.txt').read_text(),raw)


if __name__=='__main__':unittest.main()
