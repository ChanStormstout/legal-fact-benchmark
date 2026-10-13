"""Cache/tokenizer acceptance only; never invokes a model."""
import copy,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import proof_local_compact_v19 as entry
from tests.test_compact_proposals_v19 import fixture
from legal_bench.proof_carrying import local_pipeline_v19_compact as pipe

def run():
    from legal_bench.mlx_json_constraint import tokenizer_data
    from legal_bench.mlx_json_constraint_v2 import SchemaMask
    from legal_bench.proof_carrying.repetition_v19_compact import ExpansionGuard
    from legal_bench.rules_verdict_v1.repetition_v9 import RepetitionAbort
    start=time.perf_counter();tok=entry.tokenizer();eos=tok.eos_token_id;data=tokenizer_data(tok,eos)
    c,r,x=fixture();sc=pipe.schema(r,c)
    receipts=[]
    for name,value,legal in [('complete',x,True),('wrong_namespace',None,False)]:
        if value is None:value=copy.deepcopy(x);value['analyses'][0]['uses'][0]['records']=['SRC:1']
        ids=tok.encode(json.dumps(value,separators=(',',':')),add_special_tokens=False);m=SchemaMask(data,sc);prefix=[];blocked=None
        for i,t in enumerate(ids):
            if t not in m.enforcer.get_allowed_tokens(prefix).allowed_tokens:blocked=i;break
            prefix.append(t)
        ending=blocked is None and eos in m.enforcer.get_allowed_tokens(prefix).allowed_tokens
        assert ending==legal,(name,blocked)
        receipts.append({'name':name,'complete_and_EOS':ending,'blocked_at':blocked,'tokens':len(ids)})
    cached=[];parent=entry.HISTORY/'continuation-03'
    for cid,part in [('1954254','P01'),('1187427','P02')]:
        d=parent/'local'/cid/part;raw=(d/'raw-response.txt').read_text();ids=entry.read(d/'token-ids.json');schema=entry.read(d/'schema.json')
        # Exact cached token prefixes at the middle of a string/list, not a
        # freshly generated sample. Replay the original frozen schema.
        target=9500 if cid=='1954254' else raw.index('32,32')+5 if '32,32' in raw else 1100
        m=SchemaMask(data,schema);prefix=[];position=0
        for i,t in enumerate(ids):
            allowed=m.enforcer.get_allowed_tokens(prefix).allowed_tokens
            if t not in allowed:raise ValueError('CACHED_TOKEN_MASK_MISMATCH:'+cid+':'+str(i))
            prefix.append(t);position=len(tok.decode(prefix))
            if position>=target:break
        allowed=m.enforcer.get_allowed_tokens(prefix).allowed_tokens
        closers=['"','",','"}'] if cid=='1954254' else [']','],']
        candidates=[]
        for text in closers:
            ts=tok.encode(text,add_special_tokens=False)
            pp=list(prefix);ok=True
            for t in ts:
                if t not in m.enforcer.get_allowed_tokens(pp).allowed_tokens:ok=False;break
                pp.append(t)
            candidates.append({'text':text,'tokens':ts,'allowed':ok})
        assert any(v['allowed'] for v in candidates),(cid,candidates,tok.decode(prefix[-30:]))
        g=ExpansionGuard();trigger=None
        try:
            for j in range(0,len(raw),79):g.feed(raw[j:j+79])
        except RepetitionAbort:trigger=g.hit
        cached.append({'slot':cid+'/'+part,'original_raw_sha256':entry.sha(d/'raw-response.txt'),
                       'prefix_tokens_replayed':len(prefix),'prefix_characters':position,'tail':tok.decode(prefix[-24:]),
                       'closure_candidates':candidates,'new_scoped_guard_hit':trigger,
                       'old_status':entry.read(d/'run.json')['run_status'],'no_regenerated_or_repaired_output':True})
    plan=entry.capacity()
    entry.save(entry.OUT/'engineering/tokenizer-replay.json',{'status':'PASS','receipts':receipts,'cached':cached,
               'elapsed_seconds':time.perf_counter()-start,'model_calls':0,'actual_pinned_tokenizer':True,'constraint':'CompositeQuoteEnforcer'})
    print(json.dumps({'status':'PASS','cached_closures':[(x['slot'],x['closure_candidates']) for x in cached],
                      'remaining_capacity_issues':len(plan['issues']),'max_required_tokens':max(x['required_total_tokens'] for x in plan['P_slots'])},indent=2),flush=True)

if __name__=='__main__':run()
