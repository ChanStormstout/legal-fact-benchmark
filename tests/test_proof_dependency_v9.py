import copy,json,tempfile,unittest,subprocess,sys
from pathlib import Path
from legal_bench.proof_carrying.grounding_v9 import source_match
from legal_bench.proof_carrying.dependency_v9 import role_contracts,rebind,compile_routes,select_closed
from legal_bench.proof_carrying.composite_v9 import prepare,validate_record
from legal_bench.proof_carrying.contracts import content_hash
from scripts import proof_dependency_v9 as app

class Repair(unittest.TestCase):
 def test_source_boundaries(self):
  s={'a':{'text':'He did not','document':'d','original_line':1},'b':{'text':'transfer possession.','document':'d','original_line':2},'c':{'text':'Other conclusion.','document':'d','original_line':5}}
  f=lambda q,rr:source_match({'quote':q,'refs':rr},s)
  self.assertIsNone(f('He did not transfer possession.',['b','a'])['error'])
  self.assertIsNotNone(f('He did transfer possession.',['a','b'])['error'])
  self.assertIsNotNone(f('possession. Other conclusion.',['b','c'])['error'])
  self.assertEqual(f('transfer possession.\nOther conclusion.',['b','c'])['mode'],'EXPLICIT_SEPARATE_EXCERPTS')
  s['c']['document']='wrong';self.assertEqual(f('transfer possession.\nOther conclusion.',['b','c'])['error'],'MULTI_DOCUMENT_QUOTE')
 def test_rules_only_connect_declared_variables(self):
  data=app.prepare_case('840688');rules,facts,src,vc,_,_,cs,_=data
  raw=json.load(open(app.BASE/'candidates/840688.json'));fi={p['id']:p for p in facts['premises']}
  c=next(c for c in raw if c['rule_ref']=='R1@2' and [x['id'] for x in c['inputs']]==['P01','P02','P19'])
  fixed=rebind(c,rules[c['rule_ref']],fi,vc[c['rule_ref']]);self.assertEqual(fixed['v9_binding_issues'],[])
  bad=copy.deepcopy(fi);bad['P02']['bindings'][2]['entity']='WRONG_PROPERTY';self.assertIn('VARIABLE_CONFLICT:property',rebind(c,rules[c['rule_ref']],bad,vc[c['rule_ref']])['v9_binding_issues'])
 def test_alternatives_budget_and_cycle(self):
  bind=[{'role':'subject','entity':'x'}]
  def c(k,r,ins):return {'id':k,'rule_ref':r,'inputs':ins,'bindings':bind,'time_scope':None,'simple_features':{'opposition':0,'conflict':0}}
  cs=[c('bad','r1',[]),c('good','r1',[]),c('end','r2',[{'slot':'p','kind':'RULE_DEPENDENCY','id':'r1'}])]
  rr={'r1':{'conclusion_predicate':'p'},'r2':{'conclusion_predicate':'q'}};qs=[{'id':'Q','predicate':'q','text':'q'}];vc={'r1':{'slot_variables':{}},'r2':{'slot_variables':{'p':{'subject':'subject'}}}}
  d,_,_=compile_routes(cs,['bad','good','end'],rr,qs,{},vc);self.assertEqual(len(d['requests']),2)
  selected=select_closed(cs,['end','bad','good'],rr,qs,budget=2);self.assertIn('end',selected['selected']);self.assertEqual(len(selected['selected']),2)
  cs[0]['inputs']=[{'slot':'p','kind':'RULE_DEPENDENCY','id':'r2'}];cs=cs[:1]+cs[2:];self.assertFalse(select_closed(cs,['bad','end'],rr,qs,2)['selected'])
 def test_request_alternative_failure_does_not_hide_success(self):
  qs=[{'id':'Q'}];ck={'requests':[{'id':'q1','answer':None,'errors':['bad']},{'id':'q2','answer':'TRUE','errors':[]}]}
  a=app.aggregate(qs,ck,{'q1':'Q','q2':'Q'})[0];self.assertEqual(a['answer'],'TRUE');self.assertEqual(len(a['alternatives']),2)
  ck['requests'].append({'id':'q3','answer':'CONFLICTED','errors':[]});self.assertEqual(app.aggregate(qs,ck,{'q1':'Q','q2':'Q','q3':'Q'})[0]['answer'],'CONFLICTED')
 def test_composite_full_coverage(self):
  rules,facts,src,vc,made,_,_,_=app.prepare_case('74028');self.assertTrue(made)
  item=made[0];parts={p['id']:p for p in facts['premises']};snap={'rules':rules,'premises':parts,'sources':src,'reviews':{'premises':{k:{'decision':'ACCEPT_RESEARCH','subject_hash':content_hash(p)} for k,p in parts.items()}}}
  bad=copy.deepcopy(item);bad['components']=bad['components'][:-1];self.assertIn('COMPOSITE_INCOMPLETE',validate_record(bad,snap))
  bad=copy.deepcopy(snap);p=bad['premises'][item['components'][0]];p['bindings'][0]['entity']='wrong';self.assertIn('COMPOSITE_OBJECT_MISMATCH',validate_record(item,bad))
 def test_real_entry_and_snapshot(self):
  old=app.OUT
  with tempfile.TemporaryDirectory() as t:
   app.OUT=Path(t)
   try:
    r=app.run_case('840688','interface',app.prepare_case('840688'));self.assertEqual(r['requests'],2)
    dest=app.OUT/'results/interface/840688';self.assertEqual(json.load(open(dest/'invocation.json'))['returncode'],0)
    checked=json.load(open(dest/'checked.json'));self.assertTrue(checked['requests'])
    snap=json.load(open(dest/'snapshot.json'));der=json.load(open(dest/'derivation.json'))
    from legal_bench.proof_carrying.contracts_v9 import propose
    from legal_bench.proof_carrying.checker_v9 import check_payload
    bad=copy.deepcopy(der)
    for st in bad['steps']:
     for b in st['bindings']:
      if b['role']=='property':b['entity']='BAD_PROPERTY'
    result=check_payload(propose(snap,bad),snap);self.assertTrue(all(q['answer'] is None for q in result['requests']))
   finally:app.OUT=old
if __name__=='__main__':unittest.main()
