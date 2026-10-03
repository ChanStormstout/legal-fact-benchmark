import unittest,json,copy,importlib.util
from legal_bench.rules_verdict_v1.repetition_v8 import StringGuard,RepetitionAbort
from legal_bench.rules_verdict_v1.intermediate_v8 import compact_checks,check_facts
from legal_bench.rules_verdict_v1.intermediate_v7 import check_facts as oldcheck
class V8Tests(unittest.TestCase):
 def test_stream_guard(self):
  fragment='abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ!!'
  raw=json.dumps({'notes':[{'point':fragment*4}]})
  g=StringGuard()
  with self.assertRaises(RepetitionAbort):
   for ch in raw:g.feed(ch)
  self.assertEqual(g.hit['field'],'point')
 def test_separate_strings_not_repetition(self):
  f='x'*64;g=StringGuard();g.feed(json.dumps({'point':f*3,'record':f*3,'case_refs':[f]*6}));self.assertIsNone(g.hit)
 def test_escaped_chunks(self):
  f='"\\\n'+('z'*61);raw=json.dumps({'reason':f*4});g=StringGuard()
  with self.assertRaises(RepetitionAbort):
   for i in range(0,len(raw),7):g.feed(raw[i:i+7])
 def test_preserve_all_checks(self):
  source={'segments':[{'id':'s','text':'T L P E R'}]};m=lambda t:{'text':t,'refs':['s']}
  base={'status':'NARRATED','uncertain':[],'refs':['s']}
  d={'tenancies':[dict(base,id='t'+str(i),tenant=m('T'),landlord=m('L'),premises=m('P'),value='YES') for i in range(3)],'transfers':[dict(base,id='x'+str(i),event=m('E'),transferor=m('T'),recipient=m('R'),premises=m('P'),mode='SUBLET') for i in range(3)],'times':[dict(base,id='d',event=m('E'),event_date=None,after_threshold='YES')],'consents':[dict(base,id='c',grantor=m('L'),target=m('E'),recipient=m('R'),premises=m('P'),form='WRITTEN',polarity='NO')],'links':[],'coverage_limits':'unresolved law'}
  before=copy.deepcopy(d);full,_=check_facts(d,source);old,_=oldcheck(d,source)
  self.assertEqual({k:full[k] for k in old},old)
  compact,trace=compact_checks(full);self.assertEqual(len(compact['combinations']),9);self.assertEqual(full['combination_counts']['complete_model_proposed'],9)
  self.assertEqual(d,before);self.assertEqual(len(compact['record_checks']),8)
  self.assertNotIn('proposal',json.dumps(compact['record_checks']))
  byid={j['id']:j for j in compact['joins']}
  for orig,jid in zip(full['all_join_trace'],trace['join_occurrences']):
   self.assertEqual({k:byid[jid][k] for k in ['left','right','result']},orig)
  d['links']=[{'left':'t0.tenant','right':'x0.transferor','relation':r,'status':'NARRATED','refs':['s']} for r in ['SAME','DIFFERENT']]
  full,_=check_facts(d,source);compact,_=compact_checks(full)
  conflicts=[j for j in compact['joins'] if j['result']['basis']=='CONFLICTING_MODEL_LINKS'];self.assertTrue(conflicts);self.assertEqual(len(conflicts[0]['result']['links']),2)
  self.assertEqual(len(compact['combinations']),9)
if __name__=='__main__':unittest.main()
