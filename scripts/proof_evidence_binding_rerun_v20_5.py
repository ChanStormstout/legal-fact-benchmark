"""Four explicitly authorized reruns; independent review follows saved generation."""
import json
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from legal_bench.proof_carrying.local_runtime_v20_5 import Runner
from legal_bench.proof_carrying import evidence_binding_gate_v20_5 as gate
from legal_bench.proof_carrying import shared_sources_v20_3 as shared
from legal_bench.proof_carrying.artifact_state_v20_2 import immutable,verify_files,byte_hash
OUT = ROOT/'outputs/proof-evidence-binding-rerun-v20-5'


def read(p): return json.loads(Path(p).read_text())


def main():
    plan = read(OUT/'plan.json'); verify_files(ROOT, read(OUT/'freeze/protocol.json'))
    runner = Runner((ROOT/'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip())
    beginning = time.monotonic()
    for slot in plan['tasks']:
        cid, part = slot['case_id'], slot['part']['id']
        if (OUT/'PAUSE_REQUESTED.json').exists(): print('OWN_RERUN_PAUSED',flush=True); return
        source = OUT/'preparation'/cid/part; dest = OUT/'local'/cid/part
        remain = plan['total_generation_seconds']-(time.monotonic()-beginning)
        if remain <= 0: print('BOUNDED_TIME_USED',flush=True); return
        print('TASK',cid,part,flush=True)
        meta = runner.run((source/'prompt.txt').read_text(),read(source/'schema.json'),dest,
                          plan['max_output_tokens'],min(plan['per_call_seconds'],remain),'FIXED')
        if meta['run_status']=='OK':
            compact = read(dest/'parsed.json'); f=read(source/'fixture.json')
            expanded=shared.expand(compact); immutable(dest/'expanded.json',expanded)
            audit=gate.audit(compact,read(source/'original-schema.json'),f['case'],f['rules'])
            immutable(dest/'unreviewed-gate.json',audit)
            summary={'run_status':'OK','output_tokens':meta['output_tokens'],
                'finish_reason':meta['finish_reason'],'gate_before_source_review':audit['status'],
                'hard_errors':audit['errors'],'pending_bindings':audit['pending_bindings'],
                'analysis':{pid:u['analysis_status'] for pid,u in expanded['analyses'].items()},
                'semantic_approval':False}
        else:
            summary={'run_status':meta['run_status'],'output_tokens':meta.get('output_tokens'),
                     'finish_reason':meta.get('finish_reason'),'formal_answer':None,'semantic_approval':False}
        immutable(dest/'rerun-summary.json',summary)
        print('SAVED',cid,part,json.dumps(summary,ensure_ascii=False)[:1000],flush=True)
        if meta['run_status'] in ('OUT_OF_MEMORY','UNSUPPORTED','INTERRUPTED_BY_USER_PAUSE'): return
    print('FOUR_REAL_RERUNS_FINISHED',flush=True)


if __name__=='__main__':main()
