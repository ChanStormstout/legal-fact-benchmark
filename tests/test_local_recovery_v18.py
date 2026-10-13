import json,unittest
from legal_bench.proof_carrying import local_pipeline_v18_recovery as pipe
from legal_bench.proof_carrying.local_annotation_v18_recovery import label_admissibility

class RecoveryContract(unittest.TestCase):
 def label(self):return {'connection_id':'K001','label':'UNSUPPORTED','basis':'Clear attribution mismatch.','refs':['visible','supplement'],'quote':'text','mandatory_basis_refs':['visible'],'dispute':False,'input_coverage_limited':False,'outside_packet_dependencies':[]}
 def test_negative_and_supplement_are_not_disputes_or_input_gaps(self):
  row=self.label();self.assertTrue(label_admissibility(row,{'visible'},{})['supervised']);self.assertFalse(row['dispute'])
 def test_actual_gap_and_dispute_retained(self):
  row=self.label();row['mandatory_basis_refs']=['supplement'];self.assertFalse(label_admissibility(row,{'visible'},{})['supervised'])
  row=self.label();row['dispute']=True;self.assertEqual(label_admissibility(row,{'visible'},{})['reason'],'GENUINE_REFERENCE_DISPUTE_RETAINED');self.assertTrue(row['dispute'])
 def test_legacy_flag_never_guessed(self):
  row=self.label();del row['mandatory_basis_refs'];self.assertEqual(label_admissibility(row,{'visible'},{})['reason'],'REFERENCE_CONTRACT_AMBIGUOUS_OR_LEGACY')
 def test_compact_preserves_semantics(self):
  v={'negative':'not admitted','refs':['L1','L8'],'items':[{'evidence':'counterargument\nretained'}]};self.assertEqual(json.loads(pipe.compact_json(v)),v);self.assertNotIn('\n ',pipe.compact_json(v))
if __name__=='__main__':unittest.main()
