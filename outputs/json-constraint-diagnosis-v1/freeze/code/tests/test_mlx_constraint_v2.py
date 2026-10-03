import unittest
from lmformatenforcer import TokenEnforcer,TokenEnforcerTokenizerData,JsonSchemaParser
from legal_bench.mlx_json_constraint_v2 import CompositeQuoteEnforcer
TOKENS=['{','"point"',':','"','A','.\",','"assessment"','"SUPPORTED"','"REFUTED"','}',',','Z','\\"','.\"}','.\",\"bad\":','null','.\",\"assessment\":','[',']']
def data():return TokenEnforcerTokenizerData([(i,t,False) for i,t in enumerate(TOKENS)],lambda ids:''.join(TOKENS[i] for i in ids),len(TOKENS),False,len(TOKENS)+1)
SCHEMA={'type':'object','properties':{'point':{'type':'string'},'assessment':{'enum':['SUPPORTED','REFUTED']}},'required':['point','assessment'],'additionalProperties':False}
PREFIX=[0,1,2,3,4]  # {"point":"A

def walk(enforcer,ids):
 for n in range(len(ids)+1):allowed=enforcer.get_allowed_tokens(ids[:n]).allowed_tokens
 return set(allowed)
class ConstraintTests(unittest.TestCase):
 def test_reproduces_and_repairs_composite_quote(self):
  old=walk(TokenEnforcer(data(),JsonSchemaParser(SCHEMA)),PREFIX);new=walk(CompositeQuoteEnforcer(data(),JsonSchemaParser(SCHEMA)),PREFIX)
  self.assertNotIn(5,old);self.assertIn(5,new);self.assertTrue(old<=new)
  self.assertNotIn(13,new) # required assessment missing
  self.assertNotIn(14,new) # extra key forbidden
  self.assertIn(16,new) # supported combined ending + required key
 def test_valid_complete_and_eos(self):
  ids=PREFIX+[5,6,2,7,9];e=CompositeQuoteEnforcer(data(),JsonSchemaParser(SCHEMA))
  for n,t in enumerate(ids):self.assertIn(t,walk(e,ids[:n]))
  self.assertIn(len(TOKENS),walk(e,ids))
 def test_invalid_value_still_blocked(self):
  e=CompositeQuoteEnforcer(data(),JsonSchemaParser(SCHEMA));allowed=walk(e,PREFIX+[5,6,2])
  self.assertNotIn(15,allowed);self.assertNotIn(11,allowed);self.assertIn(7,allowed)
 def test_escaped_quote_does_not_end_field(self):
  e=CompositeQuoteEnforcer(data(),JsonSchemaParser(SCHEMA));allowed=walk(e,PREFIX+[12])
  self.assertIn(4,allowed);self.assertIn(5,allowed);self.assertNotIn(len(TOKENS),allowed)
if __name__=='__main__':unittest.main()
