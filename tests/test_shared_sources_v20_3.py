import copy
import json
import unittest
from legal_bench.proof_carrying import shared_sources_v20_3 as shared
from legal_bench.mlx_json_constraint_v20_3 import SharedSourceParser
from legal_bench.proof_carrying.schema_contract_v19_6 import validate


def original_schema():
    ref={'type':'string','enum':['SRC:1','SRC:2','SRC:3']}
    return {'type':'object','properties':{
        'records':{'type':'array','items':{'type':'object','properties':{
            'text':{'type':'string'},'refs':{'type':'array','items':ref,'uniqueItems':True,'minItems':1,'maxItems':3}},
            'required':['text','refs'],'additionalProperties':False}},
        'uses':{'type':'array','items':{'type':'object','properties':{
            'witnesses':{'type':'array','items':{'type':'object','properties':{
                'source':ref,'necessity':{'type':'string','enum':['REQUIRED','OPTIONAL']}},
                'required':['source','necessity'],'additionalProperties':False}}},'required':['witnesses'],'additionalProperties':False}},
        'limits':{'type':'array','items':{'type':'object','properties':{'refs':{'type':'array','items':ref,'minItems':0,'maxItems':3}},'required':['refs'],'additionalProperties':False}}},
        'required':['records','uses','limits'],'additionalProperties':False,'$defs':{'source_choice':ref}}


def example():
    return {'records':[{'text':'Literal legal claim preserved.','refs':['SRC:2','SRC:1']}],
            'uses':[{'witnesses':[{'source':'SRC:2','necessity':'REQUIRED'},
                                  {'source':'SRC:1','necessity':'REQUIRED'},
                                  {'source':'SRC:3','necessity':'OPTIONAL'}]}],
            'limits':[{'refs':[]},{'refs':['SRC:2','SRC:1']}]}


def parse(schema,text):
    p=SharedSourceParser(schema)
    for c in text:p=p.add_character(c)
    return p


class SharedSources(unittest.TestCase):
    def test_roundtrip_preserves_source_order_claims_and_witness_attributes(self):
        raw=example(); before=copy.deepcopy(raw); compact=shared.pack(raw)
        self.assertEqual(compact['source_sets'],[['SRC:2','SRC:1'],['SRC:3']])
        self.assertEqual(compact['records'][0]['ref_set'],compact['uses'][0]['witnesses'][0]['source_set'])
        self.assertEqual(shared.expand(compact),before); self.assertEqual(raw,before)
        self.assertEqual(shared.check_expansion(compact,before,original_schema())['status'],'OK')

    def test_independent_check_rejects_source_or_necessity_corruption(self):
        compact=shared.pack(example()); raw=shared.expand(compact)
        raw['uses'][0]['witnesses'][0]['necessity']='OPTIONAL'
        with self.assertRaisesRegex(ValueError,'MISMATCH'):shared.check_expansion(compact,raw,original_schema())

    def test_undefined_empty_and_duplicate_groups_fail_closed(self):
        c=shared.pack(example());c['records'][0]['ref_set']='C999'
        with self.assertRaisesRegex(ValueError,'UNDEFINED'):shared.expand(c)
        c=shared.pack(example());c['source_sets'].append(c['source_sets'][0])
        with self.assertRaisesRegex(ValueError,'DUPLICATE'):shared.expand(c)
        c=shared.pack(example());c['uses'][0]['witnesses'][0]['source_set']='C0'
        with self.assertRaisesRegex(ValueError,'EMPTY_WITNESS'):shared.expand(c)

    def test_shared_membership_does_not_merge_distinct_claims(self):
        r=example();r['records'].append({'text':'Opposing claim remains distinct.','refs':['SRC:2','SRC:1']})
        c=shared.pack(r);self.assertEqual(len(c['source_sets']),2);self.assertEqual(len(shared.expand(c)['records']),2)

    def test_alternating_necessity_and_order_are_retained(self):
        r=example();r['uses'][0]['witnesses']=[{'source':'SRC:2','necessity':'OPTIONAL'},{'source':'SRC:1','necessity':'REQUIRED'},{'source':'SRC:3','necessity':'OPTIONAL'}]
        self.assertEqual(shared.expand(shared.pack(r)),r)

    def test_source_table_must_be_first_and_forward_reference_cannot_enter(self):
        s=shared.schema(original_schema());p=parse(s,'{"')
        self.assertIn('s',p.get_allowed_characters());self.assertNotIn('r',p.get_allowed_characters())
        p=parse(s,'{"source_sets":[],"records":[{"text":"x","ref_set":')
        self.assertNotIn('"',p.get_allowed_characters())

    def test_actual_defined_identifier_only_and_optional_empty(self):
        s=shared.schema(original_schema());prefix='{"source_sets":[["SRC:1"]],"records":[{"text":"x","ref_set":"C'
        p=parse(s,prefix);self.assertIn('1',p.get_allowed_characters());self.assertNotIn('2',p.get_allowed_characters());self.assertNotIn('0',p.get_allowed_characters())
        c=shared.pack(example());self.assertTrue(parse(s,json.dumps(c)).can_end());validate(c,s)

    def test_source_unique_prefix_and_duplicate_definition_are_guarded(self):
        s=shared.schema(original_schema());p=parse(s,'{"source_sets":[["SRC:1","SRC:')
        self.assertNotIn('1',p.get_allowed_characters());self.assertIn('2',p.get_allowed_characters())
        p=parse(s,'{"source_sets":[["SRC:1"],["SRC:1"')
        self.assertNotIn(']',p.get_allowed_characters());self.assertIn(',',p.get_allowed_characters())

    def test_strings_with_json_punctuation_and_escaped_quotes_are_preserved(self):
        r=example();r['records'][0]['text']='Literal ["SRC:1"] and {"ref_set":"C7"} in prose.'
        c=shared.pack(r);self.assertTrue(parse(shared.schema(original_schema()),json.dumps(c)).can_end());self.assertEqual(shared.expand(c),r)


if __name__=='__main__':unittest.main()
