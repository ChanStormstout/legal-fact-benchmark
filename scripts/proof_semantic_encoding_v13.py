#!/usr/bin/env python3
"""Shared complete-token encoding plan. Frozen encoder, no generative model calls."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
ROOT=Path('outputs/proof-semantic-interface-v13')
def build():
 texts={};plans={};source_keys=set()
 def key(text):
  k=hashlib.sha256(text.encode()).hexdigest();texts[k]=text;return k
 for d in (ROOT/'inputs-v13-02').iterdir():
  x=json.loads((d/'model-information.json').read_text());pairs={p['id']:p for p in x['ce_pairs']};nodes=[]
  for n in x['graph']['nodes']:
   parts=[]
   if n['id'].startswith('C:'):
    p=pairs[n['id'][2:]];right=json.loads(p['right']);parts.append(key(json.dumps({'left':json.loads(p['left']),'P':right['legacy_P_material'],'relations':right['raw_relations'],'relation_encoding':right['relation_encoding_audit'],'limits':right['coverage_limits']},sort_keys=True,ensure_ascii=False)))
    for s in right['restored_source']['segments']:
     # A complete source is represented by reversible chunks; no reference selects these.
     for c in s['chunks']:
      k=key(json.dumps({'id':s['id'],'document':s['source_document'],'position':s['original_position'],'original_chars':[c['start'],c['end']],'source_role':s['metadata'].get('role'),'text':c['text']},sort_keys=True,ensure_ascii=False));parts.append(k);source_keys.add(k)
    parts.append(key(json.dumps(right['restored_source']['limits'])))
   else:parts.append(key(n['text']))
   nodes.append({'node':n['id'],'part_sha256':list(dict.fromkeys(parts)),'aggregation':'equal mean of complete normalized part encodings; re-normalize','encoded':False})
  plans[d.name]={'graph':nodes,'CE':{'pairs_file':str(d/'model-information.json'),'full_pair_sources_saved':True,'segmentation':'Use same reversible restored segments; every token chunk must be scored before aggregate; no length truncation','encoded':False},'reference_used':False}
 out=ROOT/'encoding';out.mkdir(exist_ok=True);(out/'texts.json').write_text(json.dumps(texts,ensure_ascii=False));(out/'plan.json').write_text(json.dumps(plans,indent=2));(out/'source-keys.json').write_text(json.dumps(sorted(source_keys)));print(json.dumps({'unique_texts':len(texts),'source_chunks':len(source_keys),'characters':sum(map(len,texts.values()))}))
if __name__=='__main__':build()
