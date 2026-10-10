#!/usr/bin/env python3
"""Lossless factorized common input encoding. No reference-selected content."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.proof_semantic_run_v13 import save
ROOT=Path('outputs/proof-semantic-interface-v13')

def build():
    texts={};plans={};source_keys=set()
    def key(value):
        text=value if isinstance(value,str) else json.dumps(value,sort_keys=True,ensure_ascii=False)
        sha=hashlib.sha256(text.encode()).hexdigest();texts[sha]=text;return sha
    inputroot=ROOT/(sys.argv[1] if len(sys.argv)>1 else 'final-model-inputs')
    paths=list(inputroot.glob('*/model-information-fullcontext.json'))
    for path in paths:
        cid=path.parent.name;x=json.loads(path.read_text());pairs={p['id']:p for p in x['ce_pairs']};nodes=[]
        for n in x['graph']['nodes']:
            if not n['id'].startswith('C:'):parts=[key(n['text'])]
            else:
                p=pairs[n['id'][2:]];right=json.loads(p['right']);legacy=right['legacy_P_material']
                parts=[key(legacy['proposed_use']),key(p['left'])]
                parts += [key(f) for f in legacy['evidence']]
                parts += [key(right['raw_relations']),key(right['relation_encoding_audit']),key(right['coverage_limits']),key(right['restored_source']['limits'])]
                for s in right['restored_source']['segments']:
                    for c in s['chunks']:
                        k=key({'id':s['id'],'document':s['source_document'],'position':s['original_position'],'original_chars':[c['start'],c['end']],'source_role':s['metadata'].get('role'),'text':c['text']});parts.append(k);source_keys.add(k)
            nodes.append({'node':n['id'],'part_sha256':list(dict.fromkeys(parts)),'aggregation':'equal mean of complete normalized part encodings; re-normalize'})
        plans[cid]={'graph':nodes,'input_file':str(path),'reference_used':False,'complete_information_scope':'graph node union and full relation records; CE reads the same union explicitly'}
    out=ROOT/(sys.argv[2] if len(sys.argv)>2 else 'encoding-final');save(out/'plan.json',plans);save(out/'texts.json',texts);save(out/'source-keys.json',sorted(source_keys))
    save(out/'specification.json',{'parts_are_lossless':True,'fields_removed':[],'source_recovery_unchanged':True,'no_model_architecture_change':True,'no_old_weights_compatibility_claim':True,'cases':len(plans),'texts':len(texts),'characters':sum(len(t) for t in texts.values()),'source_chunks':len(source_keys)})
if __name__=='__main__':build()
