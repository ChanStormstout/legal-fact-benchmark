"""Whole-chain interface replay; never semantic or model-quality acceptance."""
import sys,json,hashlib,copy
from pathlib import Path
sys.dont_write_bytecode=True
import run as runner
m=runner.method
H=runner.HERE
OLD=H.parent/'full-judgment-source-atomic-v15-2026-10-26-v1'
sources=runner.load(runner.BASE/'private/input.json')['sources']
cat=m.prepare_units(sources);cfg=runner.load(H/'protocol.json')
seen=[]
def ask(tag,req):
    assert req['sources']==sources
    transport=runner.transport_request(req,cfg)
    wire=runner.wire(req,cfg)
    assert transport['material']['source_units']==req['source_units']
    if not seen:
        m.save(H/'private/expected-first-wire.json',wire)
    seen.append(tag)
    if tag.split('-')[0] in m.ROLE_TASKS:
        role=tag.split('-')[0];idx=int(tag.split('-')[-1])
        assert req['reader_role']==role
        assert not any(k in req for k in ['primary_records','records','independent_observations'])
        value=runner.load(OLD/f'private/offline/chain/responses/reading-{idx:03d}.json')
        # Existing cached statements, not specialist results. No corrections/acceptances.
        return value
    cov={uid:{'state':'UNRESOLVED','source_ids':cat['units'][uid]['source_ids'],
              'explanation':'Offline interface replay only; no semantic assessment.',
              'missing_relationships':['No new model assessment in this replay.']} for uid in req['owner_unit_ids']}
    if 'primary_records' in req:
        return {'decisions':{key:{'action':'UNRESOLVED','granularity':'UNCERTAIN',
                   'issues':[{'aspect':'granularity','explanation':'Offline replay does not assess content.'}],
                   'source_ids':r['primary_source_ids'],'source_basis':'Offline cached input; no acceptance.',
                   'new_records':[]} for key,r in req['primary_records'].items()},'additions':[],'coverage':cov}
    return {'reviews':{key:{'verdict':'UNRESOLVED','granularity':'UNCERTAIN',
                'issues':[{'aspect':'granularity','explanation':'Offline replay does not assess content.'}],
                'source_ids':r['primary_source_ids'],'source_basis':'Offline cached input; no acceptance.'}
             for key,r in req['records'].items()},'coverage':cov}
result=m.run(sources,ask,H/'private/offline/chain')
assert len(seen)==41
assert result['record_states'].get('MODEL_SOURCE_SUPPORTED',0)==0
# Role coverage is explicit and never relabeled as globally non-substantive.
u=cat['groups'][0][0]
req=m.role_request(sources,cat,[u],'facts')
m.validate({'units':{u:{'state':'OUTSIDE_ROLE','records':[], 'note':'Substantive material assigned to another role.','missing_relationships':[]}}},req['schema'])
# Verify code dependency preservation before freezing the new files.
inherited=runner.load(OLD/'freeze.json')['files']
assert all(runner.sha(Path(p))==h for p,h in inherited.items())
m.save(H/'private/preflight.json',{'status':'PASS_OFFLINE_INTERFACES_ONLY','stages':len(seen),
 'source_hash':m.digest(sources),'all_roles_blind_to_peer_outputs':True,
 'all_role_candidates_are_reconciliation_targets':True,'schema_supports_outside_role':True,
 'semantic_acceptances_inserted':0,'quality_claim':None,'outcome':result})
print(json.dumps({'stages':len(seen),'outcome':result}))
