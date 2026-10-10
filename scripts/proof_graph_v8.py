"""One resumable V8 entry: prepare / ingest / build / encode / train / deliver."""
import argparse,copy,hashlib,json,shutil,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.contracts import read_json,content_hash,byte_hash
from legal_bench.proof_carrying.workflow_v7 import write_once,text_once,contract
from legal_bench.proof_carrying.workflow_v8 import fixed_requests,source_roles,verify_history,reverse_index,revision_impact
from legal_bench.proof_carrying.candidates_v8 import catalogue,layout,generate,graph,mapping_candidates,simple_score,select
from legal_bench.proof_carrying.tasks_v8 import prompt

ROOT=Path('outputs/proof-carrying-graph-integration-v8')
OLD=Path('outputs/proof-carrying-pipeline-v7')
CASES=('789051','1418721','1841885','840688','161859415','74028','522414','1144022')

def prepare():
    protocol={'version':'V8','case_order':list(CASES),'task':'EXPOSED_JUDGMENT_RECONSTRUCTION_DEVELOPMENT',
        'maximum_web_calls':24,'planned_proposals':8,'planned_references':8,'model':'VISIBLE_ORDINARY_HIGH_TO_BE_RECORDED','web_retries':0,
        'candidate_generation':'Rule slot exact model predicates plus fixed E5 top2; up to12 applications per rule; lexical stable product; retain unknown and mismatches',
        'candidate_budget':6,'dependency_policy':'No label-guided expansion; shared selected applications only; unresolved dependency explicit',
        'encoder':{'model':'intfloat/e5-small-v2','revision':'ffb93f3bd4047442299a41ebb6fa998a38507c52'},
        'model':{'hidden':64,'layers':2,'bases':4,'dropout':.1},'optimizer':{'name':'AdamW','learning_rate':.001,'weight_decay':.0001},
        'epochs':100,'selection':'Fixed final epoch; heldout not used for model selection','seeds':[20261001,20261002,20261003],
        'folds':[list(CASES[::2]),list(CASES[1::2])],'group_basis':'Distinct named disputes in existing eight-case inventory; not newly proven exhaustive linkage independence',
        'gate':'at least4 usable disputes; each training fold has independently reviewed USABLE and UNUSABLE; unlabelled/UNRESOLVED masked',
        'training_max_fits':12,'source_review':'one concentrated review after batch, not human gold',
        'freeze_policy':'code+tasks frozen before first web generation; independent graph saved before labels; append data/split manifest before fitting',
        'no_new_targets':True,'sealed_access':False,'no_push':True,
        'acceptance_policy':'Existing hash-pinned rule/scope research decisions; raw premises and candidate court evaluations only by separate reference review, address validation and concentrated source review; never legal approval',
        'stop':'one collection, one training batch, one concentrated review; no semantic retries or parameter search'}
    write_once(ROOT/'protocol.json',protocol)
    for cid in CASES:
        dest=ROOT/'inputs'/cid;spec=read_json(OLD/'inputs'/cid/'spec.json');sources=read_json(OLD/'inputs'/cid/'sources.json')
        restored,docs=source_roles(cid,sources,spec['documents'])
        rules=read_json(OLD/'inputs'/cid/'rules.json')['rules'];der=read_json(OLD/'inputs'/cid/'derivation.json')
        inventory=fixed_requests(der)
        for name,data in [('spec',spec),('sources',restored),('documents',docs),('rules',rules),('requests',inventory),('catalogue',catalogue(rules)),('rule-layout',layout(rules))]:write_once(dest/(name+'.json'),data)
        from legal_bench.rules_verdict_v1.retrieve import expand
        law_ids=list(dict.fromkeys(ref for r in rules for ref in r['source_refs']))
        units=[{'id':ref,'text':restored[ref]['text'],'document':restored[ref]['document'],'role':restored[ref]['document_role'],'dependencies':[]} for ref in law_ids]
        package=expand([{'id':ref} for ref in law_ids],units,initial=max(1,len(units)),max_units=max(1,len(units)),rounds=1) if units else {'units':[],'selected_ids':[]}
        write_once(dest/'shared-law-package.json',{'selection':'EXISTING_RULE_SOURCE_POINTERS_NOT_NEW_RETRIEVAL_EXPERIMENT','package':package,'all_methods_identical':True,
            'precedent_originals':'No new originals fetched. Target reports retained as reports; independent precedent verification unresolved.'})
        write_once(dest/'historical-integrity.json',verify_history(OLD/'cases'/cid))
        task=prompt(spec,restored,rules,inventory,'proposal');text_once(ROOT/'tasks'/cid/'proposal.txt',task)
        write_once(ROOT/'tasks'/cid/'proposal-manifest.json',{'sha256':hashlib.sha256(task.encode()).hexdigest(),'stage':'READY_NOT_SUBMITTED','source_hash':content_hash(restored),
            'source_map':[{'id':r,'character_offset':task.index('['+r+']'),'text_hash':content_hash(s['text'])} for r,s in restored.items()],
            'old_facts_or_answers_attached':False})
    print('prepared',len(CASES))

def ingest(cid,kind,path,metadata):
    dest=ROOT/'runs'/cid/kind
    if (dest/'raw.txt').exists():raise ValueError('NO_DUPLICATE_OR_RETRY')
    task=ROOT/'tasks'/cid/(kind+'.txt');meta=read_json(metadata)
    if meta.get('submitted_sha256')!=byte_hash(task):raise ValueError('SUBMISSION_HASH_MISMATCH')
    raw=Path(path).read_text();text_once(dest/'raw.txt',raw);write_once(dest/'transport.json',meta)
    text=raw.strip();ops=[]
    if text.startswith('```') and text.endswith('```'):text=text.split('\n',1)[1].rsplit('```',1)[0].strip();ops=['REMOVE_OUTER_FENCE']
    try:
        value=json.loads(text);write_once(dest/'parsed.json',value)
        if kind=='proposal':usable,isolated=contract('facts',value)
        else:
            if not isinstance(value,dict) or not isinstance(value.get('candidate_reviews'),list):raise ValueError('REFERENCE_INTERFACE')
            usable,isolated=value,[]
        write_once(dest/'usable.json',usable);write_once(dest/'isolated.json',isolated)
        status={'technical_status':'PARTIAL' if isolated else 'OK','answer':'usable.json','operations':ops}
    except (ValueError,TypeError,KeyError) as e:status={'technical_status':'FORMAT_ERROR','answer':None,'reason':str(e),'operations':ops}
    write_once(dest/'status.json',status);print(json.dumps(status))

def texts():
    out={}
    for cid in CASES:
        p=ROOT/'runs'/cid/'proposal/usable.json'
        if not p.exists():continue
        facts=read_json(p);rules=read_json(ROOT/'inputs'/cid/'rules.json')
        for text in [p['text'] for p in facts['premises']]+[s['description'] for r in rules for s in r['slots']]+[c['meaning'] for c in catalogue(rules)]:out[hashlib.sha256(text.encode()).hexdigest()]=text
    for p in (ROOT/('model-graphs' if (ROOT/'model-graphs').exists() else 'graphs')).glob('*.json') if (ROOT/'graphs').exists() else []:
        for n in read_json(p)['nodes']:
            text=n['text']+'\nMETADATA: '+json.dumps(n['metadata'],sort_keys=True,ensure_ascii=False);out[hashlib.sha256(text.encode()).hexdigest()]=text
    write_once(ROOT/('model-graph-texts.json' if (ROOT/'model-graphs').exists() else 'graph-texts.json' if (ROOT/'graphs').exists() else 'candidate-texts.json'),out)
    return out

def encode():
    import numpy as np,torch
    from transformers import AutoTokenizer,AutoModel
    from legal_bench.irac_application.text_cache import chunk_ranges
    torch.set_num_threads(4);values=texts();cfg=read_json(Path('outputs/gnn-irac-aligned-v2/text-cache/encoder.json'))
    stage='model-graph' if (ROOT/'model-graphs').exists() else 'graph' if (ROOT/'graphs').exists() else 'candidate';out=ROOT/'encoding'/stage;out.mkdir(parents=True,exist_ok=True)
    if (out/'complete.json').exists():print('reuse',out);return
    tok=AutoTokenizer.from_pretrained(cfg['path'],local_files_only=True);model=AutoModel.from_pretrained(cfg['path'],local_files_only=True).eval()
    prefix=tok.encode(cfg['prefix'],add_special_tokens=False);capacity=512-len(prefix)-tok.num_special_tokens_to_add(pair=False);vectors={};audit=[];start=time.perf_counter()
    with torch.no_grad():
        for key,text in values.items():
            e=tok(text,add_special_tokens=False,truncation=False,return_offsets_mapping=True);ids=e['input_ids'];ranges=chunk_ranges(ids,e['offset_mapping'],text,capacity);vs=[]
            for a,b in ranges:
                x=torch.tensor([tok.build_inputs_with_special_tokens(prefix+ids[a:b])]);h=model(input_ids=x,attention_mask=torch.ones_like(x)).last_hidden_state
                vs.append(torch.nn.functional.normalize(h.mean(dim=1),p=2,dim=1)[0].numpy())
            v=np.mean(vs,axis=0);v/=max(np.linalg.norm(v),1e-12);vectors[key]=v;audit.append({'hash':key,'tokens':len(ids),'ranges':ranges,'truncated':False})
    np.savez(out/'vectors.npz',**vectors);write_once(out/'complete.json',{'encoder':cfg,'count':len(values),'seconds':time.perf_counter()-start,'audit':audit})
    print('encoded',stage,len(values))

def build():
    import numpy as np
    v=np.load(ROOT/'encoding/candidate/vectors.npz')
    def sim(a,b):return float(v[hashlib.sha256(a.encode()).hexdigest()]@v[hashlib.sha256(b.encode()).hexdigest()])
    for cid in CASES:
        p=ROOT/'runs'/cid/'proposal/usable.json'
        if not p.exists():continue
        inp=ROOT/'inputs'/cid;facts=read_json(p);rules=read_json(inp/'rules.json');sources=read_json(inp/'sources.json')
        cs=generate(facts,rules,sources,sim);mappings=mapping_candidates(facts,catalogue(rules),sim);g=graph(facts,rules,sources,cs,read_json(inp/'requests.json'))
        write_once(ROOT/'candidates'/(cid+'.json'),cs);write_once(ROOT/'mappings'/(cid+'.json'),mappings);write_once(ROOT/'graphs'/(cid+'.json'),g)
        task=prompt(read_json(inp/'spec.json'),sources,rules,read_json(inp/'requests.json'),'reference',facts,cs,mappings)
        text_once(ROOT/'tasks'/cid/'reference.txt',task);write_once(ROOT/'tasks'/cid/'reference-manifest.json',{'sha256':hashlib.sha256(task.encode()).hexdigest(),
            'input_graph_sha256':content_hash(g),'candidates_sha256':content_hash(cs),'contains_scores_or_checker_results':False})
        print(cid,len(cs))

def freeze():
    paths=list(Path('legal_bench/proof_carrying').glob('*.py'))+[Path('scripts/proof_graph_v8.py'),Path('scripts/check_realcase_certificate_v4.py')]
    hashes={}
    for p in paths:
        dest=ROOT/'freeze/code'/p;dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():shutil.copyfile(p,dest)
        if byte_hash(p)!=byte_hash(dest):raise ValueError('FROZEN_SOURCE_CHANGED:'+str(p))
        hashes[str(p)]=byte_hash(p)
    write_once(ROOT/'freeze.json',{'method_hashes':hashes,'protocol_hash':byte_hash(ROOT/'protocol.json'),
        'task_hashes':{str(p):byte_hash(p) for p in (ROOT/'tasks').glob('*/proposal.txt')},'reference_template_hash':byte_hash(Path('legal_bench/proof_carrying/tasks_v8.py'))})
    print('frozen')

def gate():
    labels={};audit=[]
    for cid in CASES:
        p=ROOT/'runs'/cid/'reference/usable.json'
        if not p.exists():continue
        candidates={c['id'] for c in read_json(ROOT/'candidates'/(cid+'.json'))};rows=read_json(p)['candidate_reviews'];counts={}
        for r in rows:counts[r.get('id')]=counts.get(r.get('id'),0)+1
        labels[cid]={}
        sources=read_json(ROOT/'inputs'/cid/'sources.json')
        for r in rows:
            key=r.get('id');refs=r.get('refs',[]);quote=r.get('quote','')
            ok=key in candidates and counts[key]==1 and refs and all(x in sources for x in refs) and bool(quote) and any(quote in sources[x]['text'] for x in refs)
            label={'USABLE':1,'UNUSABLE':0}.get(r.get('label')) if ok else None
            labels[cid][key]=label;audit.append({'case':cid,'id':key,'label':label,'address_quote_ok':bool(ok),'not_semantic_approval':True})
    folds=read_json(ROOT/'protocol.json')['folds'];coverage=[]
    for f in folds:
        counts={k:sum(v==k for c in f for v in labels.get(c,{}).values()) for k in (0,1)};coverage.append(counts)
    ready=sum(any(x is not None for x in l.values()) for l in labels.values())>=4 and all(c[0]>0 and c[1]>0 for c in coverage)
    write_once(ROOT/'supervision/labels.json',labels);write_once(ROOT/'supervision/audit.json',audit)
    result={'ready':ready,'folds':folds,'coverage':coverage,'reference':'MODEL_GENERATED_SOURCE_REVIEW_REQUIRED_NOT_HUMAN_GOLD'}
    write_once(ROOT/'supervision/gate.json',result);print(json.dumps(result));return result

def train():
    import numpy as np
    from legal_bench.proof_carrying.ranker_v8 import tensors,fit
    status=read_json(ROOT/'supervision/gate.json')
    if not status['ready']:raise ValueError('SUPERVISION_GATE_CLOSED')
    labels=read_json(ROOT/'supervision/labels.json');vec=np.load(ROOT/'encoding/model-graph/vectors.npz');data={cid:tensors(read_json(ROOT/'model-graphs'/(cid+'.json')),vec) for cid in CASES if (ROOT/'graphs'/(cid+'.json')).exists()};cfg=read_json(ROOT/'protocol.json')
    write_once(ROOT/'freeze/data-training.json',{'files':{str(p):byte_hash(p) for folder in ('graphs','model-graphs','candidates','supervision') for p in (ROOT/folder).glob('*.json')},'folds':cfg['folds'],'seeds':cfg['seeds'],'config':cfg})
    for i,held in enumerate(cfg['folds']):
        training={c:d for c,d in data.items() if c not in held};test={c:d for c,d in data.items() if c in held}
        for seed in cfg['seeds']:
            for kind in ('Flat','RGCN'):
                out=ROOT/'fits'/f'fold{i}-{kind}-{seed}'
                if (out/'reload.json').exists():continue
                fit(kind,seed,training,test,labels,out,epochs=cfg['epochs']);print(out,flush=True)

def deliver():
    import numpy as np
    from legal_bench.proof_carrying.ranker_v8 import tensors,Ranker,predict
    from legal_bench.proof_carrying.delivery_v8 import run_case
    cfg=read_json(ROOT/'protocol.json');labels=read_json(ROOT/'supervision/labels.json')
    vec=np.load(ROOT/'encoding/model-graph/vectors.npz');summary=[]
    data={cid:tensors(read_json(ROOT/'model-graphs'/(cid+'.json')),vec) for cid in CASES if (ROOT/'graphs'/(cid+'.json')).exists()}
    def record(cid,name,scores,weight=None):
        out=ROOT/'results'/name/cid
        if out.exists():result=read_json(out/'analysis.json')
        else:result=run_case(ROOT,cid,name,scores)
        selected=read_json(out/'ranking.json')['selected'];known=labels.get(cid,{})
        summary.append({'case':cid,'method':name,'selected':selected,'known_usable_selected':sum(known.get(k)==1 for k in selected),
            'known_unusable_selected':sum(known.get(k)==0 for k in selected),'known_usable_total':sum(v==1 for v in known.values()),
            'unlabelled_selected':sum(known.get(k) is None for k in selected),'weights':weight,
            'requests':[{k:r.get(k) for k in ('id','technical_status','answer','failure_stage')} for r in result['requests']],
            'source_checked_semantics_not_guaranteed':True})
    for cid in data:
        cs=read_json(ROOT/'candidates'/(cid+'.json'));record(cid,'Simple',{c['id']:simple_score(c) for c in cs})
        held=next(f for f in cfg['folds'] if cid in f);training=[x for x in data if x not in held]
        counts={};all_values=[]
        for t in training:
            rules={r['id']+'@'+str(r['version']):r for r in read_json(ROOT/'inputs'/t/'rules.json')}
            for c in read_json(ROOT/'candidates'/(t+'.json')):
                y=labels.get(t,{}).get(c['id'])
                if y is not None:counts.setdefault(rules[c['rule_ref']]['conclusion_predicate'],[]).append(y);all_values.append(y)
        rr={r['id']+'@'+str(r['version']):r for r in read_json(ROOT/'inputs'/cid/'rules.json')}
        def prior(c):
            values=counts.get(rr[c['rule_ref']]['conclusion_predicate'],all_values)
            return (sum(values)+1)/(len(values)+2)
        record(cid,'RulePrior',{c['id']:prior(c) for c in cs})
    for i,held in enumerate(cfg['folds']):
        test={c:d for c,d in data.items() if c in held}
        for seed in cfg['seeds']:
            for kind in ('Flat','RGCN'):
                fitdir=ROOT/'fits'/f'fold{i}-{kind}-{seed}'
                if not (fitdir/'reload.json').exists():continue
                model=Ranker(kind,next(iter(test.values()))['x'].shape[1]);model.load_weights(str(fitdir/'weights.safetensors'))
                scores=predict(model,test);old=read_json(fitdir/'predictions.json')
                delta=max(abs(scores[c][k]-old[c][k]) for c in scores for k in scores[c])
                if delta>1e-7:raise ValueError('DELIVERY_CHECKPOINT_MISMATCH')
                write_once(fitdir/'delivery-load.json',{'checkpoint':str(fitdir/'weights.safetensors'),'sha256':byte_hash(fitdir/'weights.safetensors'),'parity':delta,'actual_use':'scores passed to run_case candidate selection'})
                for cid,ss in scores.items():record(cid,kind+'-'+str(seed),ss,str(fitdir/'weights.safetensors'))
    write_once(ROOT/'comparison.json',summary);print('delivered',len(summary))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','ingest','encode','build','freeze','gate','train','deliver']);p.add_argument('--case');p.add_argument('--kind');p.add_argument('--response');p.add_argument('--metadata');a=p.parse_args()
    if a.action=='ingest':ingest(a.case,a.kind,a.response,a.metadata)
    else:globals()[a.action]()
