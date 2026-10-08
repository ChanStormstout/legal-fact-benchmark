import unittest,json,copy,tempfile
from pathlib import Path
from unittest.mock import patch
from tests.test_irac_hybrid_v3 import fixture,HybridTests
from legal_bench.irac_application.pipeline_v4 import process,catalogue,display,compact,expand_compact
from legal_bench.irac_application.pipeline_v4_tasks import schema,prompt
from scripts import irac_pipeline_v4 as entry
R=entry.R;V=entry.V
class Repairs(unittest.TestCase):
 def load(self,c):
  m,t,l=entry.inputs(c);s=dict(m['sources']);s.update({x['source_id']:x for x in l});return m,t,l,s
 def old(self,c):return json.loads((V/'runs'/c/'proposal/raw-response.txt').read_text())
 def test_real_111_partial(self):
  m,t,l,s=self.load('1114159');i,c=process(self.old('1114159'),t,s,'1114159');self.assertTrue(i['usable']);self.assertTrue(i['projection']['evidence']);self.assertTrue(any(x['test_id']=='DRC_BONA_FIDE-C04' for x in i['missing']))
 def test_real_553_other_binding_not_gate(self):
  m,t,l,s=self.load('55384096');i,c=process(self.old('55384096'),t,s,'55384096');self.assertTrue(i['usable']);self.assertTrue(any(x['binding_id']=='b1' for x in i['projection']['evidence']));self.assertTrue(any(x['binding_id']=='b2' for x in i['missing']))
 def test_real_188_bad_uses_records_survive(self):
  m,t,l,s=self.load('188721101');i,c=process(self.old('188721101'),t,s,'188721101');self.assertTrue(i['usable']);self.assertEqual(len(i['projection']['evidence']),4);self.assertEqual(sum(len(e['uses']) for e in i['projection']['evidence']),0);self.assertEqual(sum(x['kind']=='use' for x in i['quarantine']),10)
 def test_catalogue_all_layers(self):
  for cid in ['112400','188721101']:
   m,t,l,s=self.load(cid);cat=catalogue(t);sc=schema('proposal',m,t,l);choices=sc['properties']['evidence']['items']['properties']['uses']['items']['properties']['branch_id']['enum'];self.assertEqual(set(choices),{x for bs in cat.values() for x in bs});self.assertIn(json.dumps(cat),prompt('proposal',m,t,l));self.assertNotIn('prediction',sc['properties']['conditions']['items']['properties'])
   for tid,bs in cat.items():
    for branch in bs:
     p,_,_=fixture();sid=next(iter(m['sources']));p['bindings'][0].update(refs=[sid],claim_ids=[t['claims'][0]['id']]);p['evidence']=p['evidence'][:1];p['evidence'][0].update(refs=[sid]);p['evidence'][0]['uses'][0].update(test_id=tid,branch_id=branch);p['limitations']=[];i,c=process(p,t,s,cid);self.assertFalse(i['quarantine']);self.assertEqual(c['evidence_use_checks'][0]['use_status'],'USABLE_AS_MODEL_PROPOSED')
 def test_bad_source_local_and_no_label_fabrication(self):
  p,t,s=fixture();p['evidence'][0]['refs']=['missing'];i,c=process(p,t,s,'c');self.assertTrue(i['usable']);self.assertEqual(c['conditions'][0]['program_assessment']['status'],'REFUTED');self.assertEqual(c['conditions'][0]['model_output_status'],'NOT_PRODUCED')
 def test_bad_limit_not_release(self):
  p,t,s=fixture();p['limitations'][0]['refs']=['missing'];i,c=process(p,t,s,'c');self.assertEqual(c['evidence_use_checks'][0]['use_status'],'UNRESOLVED_MAPPING')
 def test_conflict_no_vote_and_crossbinding(self):
  p,t,s=fixture();p['limitations']=[];p['evidence'].append(dict(p['evidence'][0],id='e3'));i,c=process(p,t,s,'c');self.assertTrue(c['conditions'][0]['program_assessment']['conflict']);p['bindings'].append(dict(p['bindings'][0],id='b2',event='other event'));p['evidence'][1]['binding_id']='b2';i,c=process(p,t,s,'c');self.assertEqual(c['bindings'][0]['tests']['T']['status'],'SUPPORTED');self.assertEqual(c['bindings'][1]['tests']['T']['status'],'REFUTED')
 def test_or_actual_process(self):
  m,t,l,s=self.load('112400');p,_,_=fixture();sid='IK-112400:L124:restored-v2';tid='DRC_BONA_FIDE-C03';p['bindings'][0].update(refs=[sid],claim_ids=[t['claims'][0]['id']]);p['evidence']=p['evidence'][:1];p['evidence'][0]['refs']=[sid];p['evidence'][0]['uses'][0].update(test_id=tid,branch_id=tid+'/SELF');p['limitations']=[];i,c=process(p,t,s,'112400');self.assertEqual(c['bindings'][0]['tests'][tid]['status'],'SUPPORTED');self.assertEqual(c['bindings'][0]['claims'][0]['result']['status'],'UNRESOLVED')
 def test_reversible_display(self):
  for cid in entry.ALL:
   m,t,l,s=self.load(cid);v,mp=display(m);by={x['source_id']:x for x in v['records']}
   for sid,a in mp.items():self.assertEqual(by[a['display_id']]['text'][slice(*a['char_range'])],m['sources'][sid]['text'])
   for row in v['records']:self.assertIn(json.dumps(row['text'],ensure_ascii=False),prompt('final',m,t,l))
 def test_compact_lossless_except_declared_duplicate_fields(self):
  p,t,s=fixture();i,c=process(p,t,s,'c');f=copy.deepcopy(c);v=compact(c);self.assertEqual(c,f);expected={k:copy.deepcopy(x) for k,x in c.items() if k not in ['source_recovery','coverage_limits','burdens','scope']}
  for x in expected['evidence_use_checks']:x.pop('record_retained')
  self.assertEqual(expand_compact(v),expected)
 def test_actual_attempt_local_partial_and_failure(self):
  m,t,l,s=self.load('1114159');value=self.old('1114159')
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'raw-response.txt').write_text(json.dumps(value));r=entry.finish_attempt({'run_status':'OK','schema_mask_calls':1},p,'P',m,t,l);self.assertEqual(r['run_status'],'OK');self.assertTrue((p/'checks-full.json').exists())
  for cid in ['52547606','68065690']:
   with tempfile.TemporaryDirectory() as d:
    p=Path(d);raw=(V/'runs'/cid/'proposal/raw-response.txt').read_text();(p/'raw-response.txt').write_text(raw);r=entry.finish_attempt({'run_status':'OUTPUT_TRUNCATED'},p,'P',*entry.inputs(cid));self.assertIsNone(r['prediction']);self.assertEqual((p/'raw-response.txt').read_text(),raw)
 def test_actual_complete_slot_saves_exact_input(self):
  class Tok:
   def encode(self,t):return list(t.encode())
  class Fake:
   tokenizer=Tok()
   def render(self,t):return 'CHAT:'+t
   def run(self,text,sc,out,**kwargs):
    (out/'prompt.txt').write_text(text);(out/'rendered.txt').write_text(self.render(text));(out/'raw-response.txt').write_text('{');return {'run_status':'OUTPUT_TRUNCATED'}
  m,t,l,s=self.load('112400');txt=prompt('final',m,t,l)
  with tempfile.TemporaryDirectory() as d:
   r,_=entry.complete_slot(Fake(),'112400','A',txt,schema('final',m,t,l),1,Path(d));self.assertIsNone(r['prediction']);self.assertTrue(json.loads((Path(d)/'input-delivery.json').read_text())['rendered_matches'])
if __name__=='__main__':unittest.main()
