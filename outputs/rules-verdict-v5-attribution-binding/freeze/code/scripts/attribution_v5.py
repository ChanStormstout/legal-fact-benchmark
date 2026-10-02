"""One frozen source-bound attribution diagnostic; three serial calls, no integration."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.attribution_v5 import schema,prompt,check
from legal_bench.rules_verdict_v1.source_views import digest,write_new
from legal_bench.rules_verdict_v1.runtime import SETTINGS
ROOT=Path('outputs/rules-verdict-v5-attribution-binding');OLD=Path('outputs/rules-verdict-v4-attribution');CASES=['661475','69305','1134266']
def read(p):return json.loads(Path(p).read_text())
def prepare():
    for cid in CASES:
        s=read(OLD/'sources'/(cid+'.json'));t=read(OLD/'prepared'/cid/'targets.json')
        write_new(ROOT/'sources'/(cid+'.json'),s);write_new(ROOT/'prepared'/cid/'targets.json',t);write_new(ROOT/'prepared'/cid/'schema.json',schema(s,t))
        p=ROOT/'prepared'/cid/'prompt.txt';v=prompt(s,t)
        if p.exists() and p.read_text()!=v:raise ValueError('Changed prompt')
        p.write_text(v)
    write_new(ROOT/'references.json',read(OLD/'references.json'))
    names=['scripts/attribution_v5.py','legal_bench/rules_verdict_v1/attribution_v5.py','legal_bench/rules_verdict_v1/runtime.py','legal_bench/rules_verdict_v1/contracts.py','legal_bench/mlx_json_constraint.py','legal_bench/model_output.py','tests/test_attribution_v5.py']
    for name in names:
        p=ROOT/'freeze/code'/name;p.parent.mkdir(parents=True,exist_ok=True);raw=Path(name).read_bytes()
        if p.exists() and p.read_bytes()!=raw:raise ValueError('Frozen code changed')
        p.write_bytes(raw)
    paths=[p for p in ROOT.rglob('*') if p.is_file() and p.name!='config.json']
    write_new(ROOT/'freeze/config.json',{'settings':SETTINGS,'max_output_tokens':2200,'max_calls':3,'scope':'SAME_SIX_EXPOSED_TARGETS_NOT_END_TO_END','files':{str(p):digest(p.read_bytes()) for p in paths},'scoring':'Separate status, finding level, structural checks and local semantic review. No integration or condition replay.'})
def run(cid):
    from legal_bench.rules_verdict_v1.runtime import Runner
    f=read(ROOT/'freeze/config.json')
    for p,h in f['files'].items():
        if digest(Path(p).read_bytes())!=h:raise ValueError('Frozen input changed '+p)
    r=Runner(Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),f['settings'])
    r.run((ROOT/'prepared'/cid/'prompt.txt').read_text(),read(ROOT/'prepared'/cid/'schema.json'),ROOT/'runs'/cid,f['max_output_tokens'])
def collect():
    rows=[];runs=[]
    for cid in CASES:
        meta=read(ROOT/'runs'/cid/'run.json');runs.append(meta);data=read(ROOT/'runs'/cid/'parsed.json') if meta['run_status']=='OK' else {}
        s=read(ROOT/'sources'/(cid+'.json'))
        for ref in read(ROOT/'references.json')['rows']:
            if ref['case_id']!=cid:continue
            r=data.get(ref['id']);rows.append({'reference':ref,'run_status':meta['run_status'],'result':r,'status_agreement':None if r is None else r['status']==ref['status'],'finding_level_agreement':None if r is None else r['finding_level']==ref['adoption'],'check':None if r is None else check(r,s)})
    write_new(ROOT/'results.json',{'rows':rows,'local_calls':3,'web_calls':0,'seconds':sum(r.get('elapsed_seconds',0) for r in runs),'peak_memory_gb':max(r.get('peak_mlx_memory_gb',0) for r in runs)})
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run','collect']);p.add_argument('--case',choices=CASES);a=p.parse_args()
    if a.action=='prepare':prepare()
    elif a.action=='run':run(a.case)
    else:collect()
