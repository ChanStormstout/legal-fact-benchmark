import unittest,copy
from legal_bench.rules_verdict_v1.family_overlay_v11 import FAMILY,label_overlay,graph_overlay
class TestOverlay(unittest.TestCase):
 def setUp(self):
  self.src={'case_id':'1','segments':[{'id':'s','text':'tenant raises consent'}]};self.units=[{'id':u,'text':'previous consent in writing'} for u in FAMILY]+[{'id':'OUTSIDE','text':'unchanged'}];self.old={'slots':{u['id']:{'state':'KNOWN','canonical_category':'BACKGROUND','record':{'unit_id':u['id'],'category':'BACKGROUND','reason':'old','case_refs':['s'],'law_quote':'consent'}} for u in self.units}}
 def test_unknown_and_missing_never_enter_loss_and_outside_unchanged(self):
  r={FAMILY[0]:{'case_id':'1','unit_id':FAMILY[0],'action':'UNKNOWN','category':'UNKNOWN','reason':'use unclear','case_refs':['s'],'law_quote':'consent'}}
  x,t,_=label_overlay(self.old,r,self.src,self.units);self.assertEqual(x['slots'][FAMILY[0]]['state'],'UNKNOWN');self.assertEqual(x['slots'][FAMILY[1]]['state'],'REVIEW_NOT_COMPLETED');self.assertEqual(x['slots']['OUTSIDE'],self.old['slots']['OUTSIDE'])
 def test_keep_cannot_silently_recover_isolated(self):
  self.old['slots'][FAMILY[0]]['state']='ISOLATED';r={FAMILY[0]:{'case_id':'1','unit_id':FAMILY[0],'action':'KEEP','category':'BACKGROUND','reason':'old','case_refs':['s'],'law_quote':'consent'}};x,_,_=label_overlay(self.old,r,self.src,self.units);self.assertEqual(x['slots'][FAMILY[0]]['state'],'ISOLATED')
 def test_graph_masks_scoped_without_label_argument(self):
  a={'unit_id':FAMILY[0],'scope':'DIRECT','state':'CANDIDATE','reason':'old','links':[{'state':'CANDIDATE','need_id':'n'}]};p={'case_id':'1','needs':[{'id':'n','text':'branch'}],'alignments':[a,{'unit_id':'OUTSIDE','links':[]}]};r={FAMILY[0]:{'case_id':'1','unit_id':FAMILY[0],'scope':'INCOMPATIBLE','state':'NONE','reason':'unrelated branch','case_refs':['s'],'link_reviews':[{'index':0,'action':'ISOLATE','reason':'no bridge','case_refs':['s']}]}};q,m,t,_=graph_overlay(p,r,self.src,[]);self.assertEqual(q['needs'],p['needs']);self.assertEqual(q['alignments'][1],p['alignments'][1]);self.assertEqual(m,[FAMILY[0]+'::alignment0']);self.assertEqual(p['alignments'][0]['scope'],'DIRECT')
if __name__=='__main__':unittest.main()
