import hashlib
import json
from legal_bench.proof_carrying.semantic_sources_v12 import resolve_record,trace_sources
from legal_bench.proof_carrying.grounding_v9 import source_match

def test_exact_alias_preserves_content_and_deduplicates_location(tmp_path):
    t=tmp_path/'task';t.write_text('[IK-123:L1]\nHe did not transfer possession.')
    c={'case_id':'123','source_sha256':'frozen','segments':[{'id':'IK-123:L1','source_document':'123','text':'He did not transfer possession.','original_line':1}]}
    raw={'refs':['turn0file0:IK-123:L1','IK-123:L1'],'quote':'He did not transfer possession.','label':'UNUSABLE'}
    before=json.dumps(raw);resolved,a=resolve_record(raw,c,t)
    assert json.dumps(raw)==before and resolved['quote']==raw['quote'] and resolved['label']=='UNUSABLE'
    assert len(a['mappings'])==1
    sources={s['id']:{**s,'document':'123'} for s in c['segments']}
    assert source_match(resolved,sources)['error'] is None
    resolved['quote']='He did transfer possession.'
    assert source_match(resolved,sources)['error']=='QUOTE_NOT_LOCATED'
    foreign={'refs':['turn0file0:IK-456:L1','turn0file0:IK-123:L2','turn0file0']}
    assert resolve_record(foreign,c,t)[0]==foreign
    mixed={'refs':['turn0file0','IK-123:L1'],'quote':raw['quote']}
    clean,log=resolve_record(mixed,c,t)
    assert clean['refs']==['IK-123:L1'] and log['mappings'][0]['kind']=='ATTACHMENT_DOCUMENT_POINTER'
    assert source_match(clean,sources)['error'] is None
    assert resolve_record({'refs':['turn0file0']},c,t)[0]['refs']==['turn0file0']

def test_original_response_hash_and_span(tmp_path):
    p=tmp_path/'raw';p.write_text('Title\nsource text\nEnd')
    c={'case_id':'123','segments':[{'id':'IK-123:L1','text':'source text','provenance':[{'raw_path':str(p),'raw_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'document_id':'123','raw_char_range':[6,17]}]}]}
    assert trace_sources(c)['all_traceable']
    p.write_text('changed')
    assert not trace_sources(c)['all_traceable']
