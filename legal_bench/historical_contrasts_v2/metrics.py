"""Judged-only metrics: uncertainty is not an irrelevant candidate."""
import math, random
import numpy as np

def evaluate(scores,judged,outcomes=None):
    ordered=sorted(scores,key=lambda c:(-scores[c],c));known=[c for c in ordered if c in judged]
    positive={c for c,y in judged.items() if y==1}
    if not positive:return {'evaluable':False,'reason':'NO_REVIEWED_POSITIVE','known_candidates':len(judged)}
    def recall(k):return len(set(known[:k])&positive)/len(positive)
    def ndcg(k):
        actual=sum(judged[c]/math.log2(i+2) for i,c in enumerate(known[:k]))
        ideal=sum(1/math.log2(i+2) for i in range(min(k,len(positive))))
        return actual/ideal if ideal else None
    contrast=None;eligible=0
    if outcomes:
        pairs=[(a,b) for a in positive for b in positive if a<b and {outcomes.get(a),outcomes.get(b)}=={'SUPPORT_GROUND','OPPOSE_GROUND'}]
        eligible=len(pairs)
        if pairs:contrast=sum(a in ordered[:3] and b in ordered[:3] for a,b in pairs)/len(pairs)
    return {'evaluable':True,'NDCG@3':ndcg(3),'Recall@3':recall(3),
        'Precision@3':sum(judged[c] for c in known[:3])/min(3,len(known)),
        'MRR':1/(next(i for i,c in enumerate(known) if judged[c])+1),
        'Recall@5':recall(5),'contrast_pair_coverage@3':contrast,'eligible_contrast_pairs':eligible,
        'unknown_in_original_top3':sum(c not in judged for c in ordered[:3]),
        'known_candidates':len(judged),'positive_candidates':len(positive),
        'discriminative':0 in judged.values(),
        'metric_policy':'Filter UNKNOWN/DISPUTED/rejected candidates only for judged ranking metrics; contrast coverage uses actual top3'}

def aggregate(rows):
    ok=[r for r in rows if r['metrics']['evaluable']]
    keys=['NDCG@3','Recall@3','Precision@3','MRR','Recall@5','contrast_pair_coverage@3']
    informative=[r for r in ok if r['metrics']['discriminative']]
    return {'query_count':len(rows),'evaluable_queries':len(ok),
        'discriminative_queries':sum(r['metrics']['discriminative'] for r in ok),
        'discriminative_mean':{k:float(np.mean([r['metrics'][k] for r in informative if r['metrics'][k] is not None]))
           if any(r['metrics'][k] is not None for r in informative) else None for k in keys},
        **{k:float(np.mean([r['metrics'][k] for r in ok if r['metrics'][k] is not None]))
           if any(r['metrics'][k] is not None for r in ok) else None for k in keys}}

def paired_bootstrap(differences,seed=20261013,repeats=5000):
    if not differences:return None
    rng=random.Random(seed);n=len(differences)
    values=[sum(rng.choices(differences,k=n))/n for _ in range(repeats)]
    return {'mean_difference':sum(differences)/n,'ci95':[float(np.quantile(values,.025)),float(np.quantile(values,.975))],
            'groups':n,'bootstrap_repeats':repeats,'resampling_unit':'query dispute group',
            'small_exposed_development_sample_not_final_inference':True}
