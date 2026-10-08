import copy
import unittest
import numpy as np
from tests.test_irac_native_v1 import fixture
from legal_bench.irac_application.graph_builder import build_graph
from legal_bench.irac_application.target_adapter import adapt_targets
from legal_bench.rules_verdict_v1.irac_native_schema_v1 import ContractError

def data_fixture():
    x=fixture();x['blind_bindings']=[];return x

class ApplicationTests(unittest.TestCase):
    def test_unsigned_no_signed_edges(self):
        g=build_graph(data_fixture());self.assertEqual(sum(e['type']=='CANDIDATE_LINK' for e in g['edges']),4)
        self.assertFalse(any('SUPPORTS_CONDITION' in e['type'] for e in g['edges']))
    def test_mask_not_input(self):
        x=data_fixture();x['facts'][0]['supervision_mask']=True
        with self.assertRaises(ContractError):build_graph(x)
    def test_mask_changes_do_not_change_graph(self):
        x=data_fixture();a=build_graph(x)['graph_hash']
        targets={'mask':True,'label':'SATISFIED'};targets.update(mask=False,label='DEFEATED')
        self.assertEqual(a,build_graph(x)['graph_hash'])
    def test_not_decided_masked(self):
        x=data_fixture();row={'condition_id':'C1','label':'UNRESOLVED','basis_kind':'NOT_DECIDED'}
        out=adapt_targets(['C1'],{'element_targets':[row]},x['provenance'])
        self.assertFalse(out[0]['supervision_mask']);self.assertIsNone(out[0]['target'])
    def test_partial_supervision_independent(self):
        x=data_fixture();ref=x['facts'][0]['source_refs'];r=dict(condition_id='C1',label='SATISFIED',basis_kind='FACT_ACCEPTED',substantive_adjudication=True,input_sufficient=True,source_review='SUPPORTED',target_refs=ref)
        out=adapt_targets(['C1','C2'],{'element_targets':[r]},x['provenance'])
        self.assertTrue(out[0]['supervision_mask']);self.assertFalse(out[1]['supervision_mask'])
    def test_no_judicial_unresolved_from_missing(self):
        x=data_fixture();r=dict(condition_id='C1',label='UNRESOLVED',basis_kind='INSUFFICIENT_RECORD',substantive_adjudication=True,input_sufficient=True,source_review='SUPPORTED',target_refs=x['facts'][0]['source_refs'])
        self.assertFalse(adapt_targets(['C1'],{'element_targets':[r]},x['provenance'])[0]['supervision_mask'])
    def test_duplicate_targets_are_masked(self):
        x=data_fixture();r=dict(condition_id='C1',label='SATISFIED',basis_kind='FACT_ACCEPTED',substantive_adjudication=True,input_sufficient=True,source_review='SUPPORTED',target_refs=x['facts'][0]['source_refs'])
        self.assertFalse(adapt_targets(['C1'],{'element_targets':[r,r]},x['provenance'])[0]['supervision_mask'])

if __name__=='__main__':unittest.main()

class PartitionTests(unittest.TestCase):
 def test_subspan_keeps_original_positions(self):
  from legal_bench.irac_application.input_partition import partition
  doc={'document_id':'x','url':'u','segments':[{'id':'p','text':'Tenant denies transfer. The target court finds transfer.'}]}
  sources,a=partition(doc,[dict(source_id='p',quote='Tenant denies transfer.',semantic_stage='PRE_TARGET_RECORD')])
  self.assertEqual(sources['p:span1']['text'],'Tenant denies transfer.');self.assertEqual(a[0]['original_char_range'],[0,23])
 def test_ambiguous_quote_not_guessed(self):
  from legal_bench.irac_application.input_partition import partition
  doc={'document_id':'x','url':'u','segments':[{'id':'p','text':'same same'}]}
  sources,a=partition(doc,[dict(source_id='p',quote='same',semantic_stage='PRE_TARGET_RECORD')]);self.assertFalse(sources)
 def test_grouped_splits_have_no_cross_dispute(self):
  from legal_bench.irac_application.train_eval import grouped_split
  packages=[{'group_id':str(i//2)} for i in range(12)]
  for s in grouped_split(packages):
   self.assertFalse(set(s['fit_groups'])&set(s['test_groups']));self.assertFalse(set(s['validation_groups'])&set(s['test_groups']));self.assertFalse(set(s['fit_groups'])&set(s['validation_groups']))
 def test_permutation_and_id_changes_preserve_logits(self):
  import numpy as np,mlx.core as mx
  from legal_bench.irac_application.application_models import tensorize,ApplicationModel
  from legal_bench.irac_application.graph_builder import build_graph
  from tests.test_irac_native_v1 import fixture
  x=fixture();x['blind_bindings']=[];g=build_graph(x)
  vectors={n['id']:np.random.default_rng(i).normal(size=384).astype('float32') for i,n in enumerate(g['nodes'])}
  renamed=copy.deepcopy(g);mapping={n['id']:'renamed-'+str(100-i) for i,n in enumerate(g['nodes'])}
  for n in renamed['nodes']:n['id']=mapping[n['id']]
  for e in renamed['edges']:e.update(source=mapping[e['source']],target=mapping[e['target']])
  aa=tensorize(g,vectors);bb=tensorize(renamed,{mapping[k]:v for k,v in vectors.items()})
  for kind in ['Flat','Graph']:
   mx.random.seed(1);m=ApplicationModel(kind,aa['x'].shape[1]);m.eval()
   a=np.array(m(aa));b=np.array(m(bb));idx={c:i for i,c in enumerate(bb['condition_ids'])}
   reordered=np.array([b[idx[mapping[c]]] for c in aa['condition_ids']]);np.testing.assert_allclose(a,reordered,rtol=1e-5,atol=1e-6)

class ArtifactTests(unittest.TestCase):
 def test_literal_reader_never_executes(self):
  from legal_bench.irac_application.artifact_reader import recover
  x,a=recover(["import os\nos.system('false')\ndata={'cases':[{'case_id':'x'}]}\n"])
  self.assertEqual(x['cases'][0]['case_id'],'x');self.assertEqual(len(a),1)
 def test_displayed_literal_mutations_preserved(self):
  from legal_bench.irac_application.artifact_reader import recover
  original={'cases':[{'case_id':'x','allowed_spans':[{'source_id':'p','quote':'old'}]}]}
  code="c=next(x for x in d['cases'] if x['case_id']=='x')\nfor sp in c['allowed_spans']:\n if sp['source_id']=='p':sp['quote']='new'\n"
  x,a=recover([code],initial_payload=original)
  self.assertEqual(x['cases'][0]['allowed_spans'][0]['quote'],'new');self.assertEqual(original['cases'][0]['allowed_spans'][0]['quote'],'old')
 def test_address_requires_located_quote(self):
  from legal_bench.irac_application.artifact_reader import recover,Unsupported
  with self.assertRaises(Unsupported):recover(["cases=[]\ncases.append({'source_refs':[ref('p','invented')]})\ndata={'cases':cases}"],{'p':'actual'})
 def test_hierarchical_metrics(self):
  from legal_bench.irac_application.train_eval import metrics
  rows=[dict(group_id='g',package_id='long',label=0,probabilities=[1,0,0],supervision_mask=True) for _ in range(6)]
  rows+=[dict(group_id='g',package_id='short',label=0,probabilities=[0,1,0],supervision_mask=True)]
  self.assertEqual(metrics(rows)['dispute_mean_correct'],.5)

class DeclaredReferenceTests(unittest.TestCase):
 def test_declared_entity_reference_preserved_without_relation_row(self):
  x=data_fixture();x['relations']=[];f=x['facts'][0];entity=copy.deepcopy(f);entity.pop('entity_ids',None);entity.update(id='ENTITY-Z',text='Tenant');x['entities']=[entity];f['entity_ids']=['ENTITY-Z']
  g=build_graph(x)
  self.assertTrue(any(e['source']==f['id'] and e['target']==x['entities'][0]['id'] and e['type']=='FACT_RELATES_TO_ENTITY' and e['origin']=='DECLARED_MODEL_INPUT_REFERENCE_NOT_INFERRED' for e in g['edges']))

class TextChunkTests(unittest.TestCase):
 def test_sentence_chunks_cover_every_token(self):
  from legal_bench.irac_application.text_cache import chunk_ranges
  text='one. two. three.';offsets=[(0,3),(3,4),(5,8),(8,9),(10,15),(15,16)]
  ranges=chunk_ranges(list(range(6)),offsets,text,3)
  self.assertEqual(ranges,[[0,2],[2,4],[4,6]]);self.assertEqual([i for a,b in ranges for i in range(a,b)],list(range(6)))

class RenderedQuoteTests(unittest.TestCase):
 def test_cite_wrapper_retains_every_legal_character_and_original_offsets(self):
  from legal_bench.irac_application.rendered_quotes import check_refs
  raw='Under \ue200cite\ue2029†section 14\ue201 the tenant must retain control.'
  errors,a=check_refs([dict(source_id='p',quote='Under section 14 the tenant must retain control.')],{'p':{'text':raw}})
  self.assertEqual(errors,[]);self.assertEqual(a[0]['original_char_range'],[0,len(raw)]);self.assertFalse(a[0]['legal_text_modified'])
 def test_page_text_is_never_silently_removed(self):
  from legal_bench.irac_application.rendered_quotes import check_refs
  errors,a=check_refs([dict(source_id='p',quote='Tenant retains possession.')],{'p':{'text':'Tenant retains Page 4 of 5 possession.'}})
  self.assertTrue(errors);self.assertFalse(a)
