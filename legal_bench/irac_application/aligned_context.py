"""Optional context interfaces; neither oracle laws nor candidates are learned rules."""
import hashlib,itertools

def normalization_candidates(records, embeddings, max_candidates=1000):
    """E5 only proposes semantic neighbors; never merges facts or identities."""
    import numpy as np
    pairs=[]
    for a,b in itertools.combinations(records,2):
        ka=hashlib.sha256(a['text'].encode()).hexdigest();kb=hashlib.sha256(b['text'].encode()).hexdigest()
        if ka not in embeddings or kb not in embeddings:continue
        va=np.asarray(embeddings[ka]);vb=np.asarray(embeddings[kb]);score=float(va@vb/max(float(np.linalg.norm(va)*np.linalg.norm(vb)),1e-12))
        pairs.append(dict(left=a['id'],right=b['id'],similarity=score,equivalence='NOT_DETERMINED',identity='NOT_INFERRED'))
    pairs.sort(key=lambda x:(-x['similarity'],x['left'],x['right']))
    return dict(candidates=pairs[:max_candidates],total_candidates=len(pairs),truncated=len(pairs)>max_candidates,merge_performed=False)

def given_rule_package(family,templates,sources):
    """Explicit given-rule condition, separate from retrieval or learned selection."""
    if family not in templates:return dict(status='NOT_COVERED',template=None,sources=[])
    return dict(status='GIVEN_RULE_CONDITION',template=templates[family],sources=sources[family],selection_origin='RESEARCHER_SUPPLIED_NOT_AUTOMATIC_RETRIEVAL',scope_compatibility='MUST_BE_EVALUATED_PER_CASE')

def mine_existing_interface(records,miner,max_candidates=1000,min_groups=2):
    """Delegate only typed legacy-compatible facts; do not invent event types."""
    compatible=[r for r in records if r.get('event_type') and r.get('group_id')]
    if not compatible:return dict(status='NO_COMPATIBLE_TYPED_FACTS',patterns=[],reason='Free-text native assertions are not silently converted to old event types.',candidate_budget=max_candidates,min_dispute_groups=min_groups)
    return miner(compatible,max_candidates=max_candidates,min_groups=min_groups)
