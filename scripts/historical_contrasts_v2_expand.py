"""Pre-training source-based expansion. Keep initial protocol and split immutable."""
from scripts.historical_contrasts_v2_prepare import ROOT, OUT, QUESTION, LABEL_INSTRUCTION, task, save, sha
from legal_bench.historical_contrasts_v1.contracts import read_json, digest

def expand():
    sources=read_json(OUT/'private/source-cases.json');inputs=read_json(OUT/'source-input-hashes.json');added=[]
    for p in sorted((ROOT/'outputs/rules-verdict-v20-four-case-pairs/sources').glob('*.json')):
        x=read_json(p);added.append({'case_id':p.stem,'group_id':p.stem,'question':QUESTION,
            'input_scope':x['scope'],'segments':x['segments'],'path':str(p.relative_to(ROOT)),
            'prior_role':'OLD_EXPOSED_RETROSPECTIVE_DEVELOPMENT','split':'TRAIN'})
        inputs[str(p.relative_to(ROOT))]=sha(p)
    manifest_path=ROOT/'outputs/gnn-irac-application-development-01/construction-manifest.json'
    manifest=read_json(manifest_path);inputs[str(manifest_path.relative_to(ROOT))]=sha(manifest_path)
    for cid in ['114533','1870868']:
        m=next(x for x in manifest if x['case_id']==cid)
        if m['family']!='DRC_SUBLETTING':raise ValueError('do not pad with unrelated grounds')
        original=read_json(ROOT/m['source_path']);by_id={s['id']:s['text'] for s in original['segments']};segments=[];lineage=[]
        for i,r in enumerate(m['screen']['allowed_spans']):
            if r['semantic_stage'] not in ('PRE_TARGET_RECORD','PRIOR_COURT_FINDING','TARGET_STAGE_PARTY_ARGUMENT'):raise ValueError('unsafe stage')
            raw=by_id[r['source_id']];q=r['quote']
            if q not in raw:raise ValueError('source quote changed')
            sid=r['source_id']+':PRETARGETSPAN'+str(i+1);segments.append({'id':sid,'text':q})
            a=raw.index(q);lineage.append({'id':sid,'original_id':r['source_id'],'char_span':[a,a+len(q)],
                'original_text_sha256':digest(raw),'semantic_stage':r['semantic_stage']})
        inputs[m['source_path']]=sha(ROOT/m['source_path'])
        added.append({'case_id':cid,'group_id':cid,'question':QUESTION,
            'input_scope':'Complete individually admitted pre-target spans; incomplete whole judgment; lower findings keep attribution.',
            'segments':segments,'path':m['source_path'],'prior_role':'OLD_EXPOSED_RETROSPECTIVE_DEVELOPMENT',
            'split':'TRAIN','lineage':lineage})
    ids={q['case_id'] for q in sources['queries']}|{r['case_id'] for r in sources['references']}
    if ids&{q['case_id'] for q in added}:raise ValueError('duplicate case')
    expanded={**sources,'queries':sources['queries']+added}
    save('private/source-cases-expanded.json',expanded);save('source-input-hashes-expanded.json',inputs)
    protocol=read_json(OUT/'protocol.json')
    protocol['query_cases']=len(expanded['queries']);protocol['split_manifest'].update({q['case_id']:'TRAIN' for q in added})
    protocol['training']['seeds']=[13,37,71,101,137]
    protocol['learning_curve_sizes']=[5,11,17]
    protocol['expansion']={'initial_queries':22,'additional_training_queries':len(added),
        'reason':'User requested data adequacy; add independently existing same-ground pretarget sources before any training/performance inspection',
        'no_scope_padding':True,'no_old_sealed_body_read':True,'adequacy_claim':'Still small; measure seed and query-group variability, not a definitive sample size'}
    save('protocol-expanded.json',protocol)
    refs=[{'case_id':r['case_id'],'input_scope':r['input_scope'],'segments':r['allowed_input']} for r in sources['references']]
    ledger=[]
    for i in range(0,len(added),3):
        q=[{k:x[k] for k in ('case_id','question','input_scope','segments')} for x in added[i:i+3]]
        ledger.append(task('LABELS-'+str(7+i//3),LABEL_INSTRUCTION+'\nReturn machine-readable JSON in a single fenced ```json code block. Escape internal quotation marks and literal backslashes.',{'references':refs,'queries':q}))
    save('private/prepared-expansion-tasks.json',ledger)
    save('data-expansion-before-training.json',{'added_queries':[q['case_id'] for q in added],
        'train':17,'validation':3,'development_holdout':8,'initial_protocol_preserved':True,'new_labels_required':True,
        'known_dispute_association_beyond_checked_titles_unconfirmed':True,'training_started':False,'tasks':ledger})
    print(ledger)

if __name__=='__main__':expand()
