"""Real MLX optimization on explicitly synthetic graphs; not legal evaluation."""
import copy
import json
import hashlib
from pathlib import Path
import numpy as np
import mlx.core as mx
from tests.test_irac_application import data_fixture
from legal_bench.irac_application.graph_builder import build_graph
from legal_bench.irac_application.application_models import tensorize,masked_group_loss
from legal_bench.irac_application.train_eval import fit

ROOT=Path('outputs/gnn-irac-application-development-01')

def main():
    out=ROOT/'engineering';out.mkdir(exist_ok=True)
    if (out/'optimizer-runs.json').exists():raise FileExistsError('Preserve prior smoke; do not rerun automatically')
    packages=[]
    for i in range(3):
        x=data_fixture();x['case_id']='SYNTHETIC-'+str(i)
        g=build_graph(x);rng=np.random.default_rng(i)
        emb={n['id']:rng.normal(size=384).astype(np.float32) for n in g['nodes']}
        packages.append(dict(package_id='SMOKE-'+str(i),group_id='SYNTHETIC-GROUP-'+str(i),
            tensors=tensorize(g,emb),graph=g,labels=[i,999],mask=[True,False],
            template_condition_ids=['SYNTHETIC:C1','SYNTHETIC:C2']))
        (out/(str(i)+'-graph.json')).write_text(json.dumps(g,indent=2)+'\n')
    runs=[]
    for kind in ('Flat','Graph'):
        model,run=fit(kind,packages,[],20261006,epochs=3)
        assert run['first_gradient_norm']>0 and run['pre_checkpoint_parameter_delta']>0
        base=float(masked_group_loss(model,packages).item())
        altered=[dict(p,labels=[p['labels'][0],-12345]) for p in packages]
        assert base==float(masked_group_loss(model,altered).item())
        # Independent forward calls cannot mix graph messages between packages.
        p=packages[0];one=np.array(model(p['tensors']));model(packages[1]['tensors'])
        assert np.allclose(one,np.array(model(p['tensors'])))
        runs.append(dict(run,mask_placeholder_invariance=True,independent_graph_forward=True,
                         final_loss=base,engineering_only=True,legal_accuracy=None))
        mx.savez(str(out/(kind+'-weights.npz')),**dict(__import__('mlx.utils',fromlist=['tree_flatten']).tree_flatten(model.parameters())))
    (out/'optimizer-runs.json').write_text(json.dumps({'synthetic':True,'models':runs,
        'real_legal_training':False,'optimizer':'AdamW','dropout':.1,'legal_accuracy':None},indent=2)+'\n')
    print(json.dumps(runs,indent=2))

if __name__=='__main__':main()
