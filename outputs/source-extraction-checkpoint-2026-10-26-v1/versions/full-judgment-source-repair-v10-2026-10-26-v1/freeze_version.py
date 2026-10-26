"""Freeze prepared source/code dependencies without enabling execution."""
import json
import sys
from pathlib import Path
import environment as env
import latentweaver_v10 as lw
from source_v8 import save, digest
from prepare import sha, load
from inspection import TOKENIZER


def main():
    if (env.HERE/'freeze.json').exists():raise ValueError('VERSION_ALREADY_FROZEN')
    import execute_cohort
    readiness=execute_cohort.preflight()
    cfg=load(env.HERE/'protocol.json')
    assert cfg['execution_enabled'] is False and cfg['paid_api_enabled'] is False
    files=set(env.HERE.glob('*.py'))|set(env.HERE.glob('*.md'))|{env.HERE/'protocol.json',env.HERE/'COST_ESTIMATE.json',TOKENIZER}
    files.update((env.HERE/'private/preparation').rglob('*.json'))
    files.update((env.HERE/'private/offline-whole-document-review').rglob('*.json'))
    files.add(env.HERE/'private/preservation-before.json')
    for root in [env.V8,env.V9,env.V25/'src']:
        files.update(root.glob('*.py'))
    files.add(env.V7/'role_api_provider.py')
    files.add(env.REPO/'scripts/proof_together_diagnostic.py')
    for root in [lw.EXTERNAL/'land_dispute_pipeline/prompts',lw.EXTERNAL/'land_dispute_pipeline/ontology',
                 lw.EXTERNAL/'prompt2_v2/src',lw.EXTERNAL/'prompt2_v2/prompts',lw.EXTERNAL/'prompt2_v2/schemas',
                 lw.EXTERNAL/'prompt2_v2/input/ontology',env.V25/'private/vendor']:
        files.update(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts
                     and p.suffix in {'.py','.json','.yaml','.txt','.md','.so'})
    files.add(lw.EXTERNAL/'prompt2_v2/config.yaml')
    files.add(lw.EXTERNAL/'land_dispute_pipeline/Python/new_pipeline.py')
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            p=Path(name)
            if p.is_file() and str(p).startswith(str(env.REPO)) and p.suffix in {'.py','.so'}:files.add(p)
    cohort=load(env.HERE/'private/preparation/cohort.json')
    files.add(Path(cohort['identity_path']));files.add(Path(cohort['prior_cohort_path']))
    files.update(Path(r['source_path']) for r in cohort['selected'])
    manifest={'version':cfg['version'],'files':{str(p):sha(p) for p in sorted(files)},
        'python_version':sys.version,'python_executable':sys.executable,
        'paid_execution_enabled':False,'scoped_authorization_required':True,
        'model_weight_revision_verified':False,'review':readiness}
    save(env.HERE/'freeze.json',manifest)
    print(json.dumps({'frozen_files':len(files),'freeze_hash':digest(manifest),'new_model_calls':0}))


if __name__=='__main__':main()
