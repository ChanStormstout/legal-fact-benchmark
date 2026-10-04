"""One development-only candidate reorder; no inference of legal applicability.

Uses an existing scope field as an explicit-law prefix feature, then original rank.
Inspired by field-aware retrieval, not an implementation of BM25F or a trained ranker.
"""
import re

def normalized_law_name(text):
    text=re.sub(r'[,\s]+(?:18|19|20)\d{2}\b','',text.casefold())
    return ' '.join(re.findall(r'[a-z0-9]+',text))

def scope_match(scope, explicit_act_names):
    s=normalized_law_name(scope)
    return any((s==n or s.startswith(n+' ')) for n in map(normalized_law_name,explicit_act_names) if n)

def rerank(ranking,units,explicit_act_names):
    table={u['id']:u for u in units}
    if len(table)!=len(units) or len({x['id'] for x in ranking})!=len(ranking):
        raise ValueError('Duplicate unit or candidate')
    records=[]
    for pos,item in enumerate(ranking,1):
        u=table[item['id']]
        records.append({**item,'baseline_rank':pos,'scope_prefix_match':scope_match(u.get('scope',''),explicit_act_names)})
    records.sort(key=lambda r:(not r['scope_prefix_match'],r['baseline_rank']))
    for pos,item in enumerate(records,1):item['rank']=pos
    return records
