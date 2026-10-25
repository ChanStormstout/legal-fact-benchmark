"""Consolidated whole-chain engineering acceptance; no model or semantic scoring.

Real V20 caches are read unchanged only to reproduce dependency addresses.
All simulated repaired meanings live exclusively in this fictional provider.
"""
import copy
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'src')]
from whole_workflow import Provider,PACKET,LIB
from common import read,save,digest,prepare_sources
from runner import run_arm,retain_evidence
import contracts as C
import engine as E


class RecoveryProvider(Provider):
    def __init__(self,mode):
        super().__init__();self.mode=mode;self.original_fixture_records=[]
    def call(self,cid,arm,tag,request,attempt=0):
        t=tag.removeprefix('repair-');m=request['material']['material']
        def done(value):
            self.requests.append(copy.deepcopy(request));self.calls.append(tag)
            C.validate(value,request['schema'])
            return value,{'synthetic':True,'status':'OK','usage':{'prompt_tokens':0,'completion_tokens':0},
                'elapsed_seconds':0,'pipeline_request_hash':digest(request)}
        if t.startswith('uses-') and not m['source_records']:
            return done({i:{'uses':[]} for i in m['tasks']})
        if t.startswith('bundles-') and not m['uses']:
            return done({i:{'bundles':[]} for i in m['tasks']})
        if t=='source-record-additions':
            return done({'additions':self.original_fixture_records if self.mode=='empty_recovery' else [],'limitations':[]})
        if t.startswith('source-record-repair-') and self.mode=='withdrawal':
            return done({i:{'replacements':[],'reason':'Fictional withdrawal without replacement'} for i in m['subjects']})
        value,receipt=super().call(cid,arm,tag,request,attempt)
        if t=='source-records' and self.mode=='empty_recovery':
            self.original_fixture_records=copy.deepcopy(value['records'])
            value={'records':[],'limitations':['Fictional initial extractor incorrectly confuses hidden outcome with visible contents.']}
        if t=='source-record-coverage' and self.mode=='withdrawal' and not tag.startswith('repair-'):
            for row in value.values():row.update(status='PARTIAL',reason='Fictional record version needs source correction')
        if t=='tasks' and self.mode=='task_churn' and tag.startswith('repair-'):
            for row in value['tasks'].values():row['why_required']+=' Revised fictional question formulation.'
        if t.startswith('final-review-') and not tag.startswith('repair-'):
            if self.mode=='task_churn':
                row=next(iter(value['items'].values()))
                row.update(decision='REJECT',serious_error=True,revision_class='ALLOWED_SOURCE_ERROR',
                    revision_refs=[i for i,v in request['material']['sources'].items() if v['domain']=='CASE'],
                    repair_target='TASKS',error_types=['UNSUPPORTED_REASON'],reason='Fictional task framing requires repair')
            elif self.mode=='empty_recovery':
                # Even an erroneous no-allowed-repair verdict cannot suppress the
                # separately observed source-description gap.
                for row in value['whole_source_coverage']['obligations'].values():
                    row['repair_target']='NO_ALLOWED_REPAIR'
        C.validate(value,request['schema'])
        return value,receipt


def main():
    cfg=read(ROOT/'protocol.json');old=REPO/cfg['source_method'];work=ROOT/'private/recovery-acceptance'/str(time.time_ns())
    work.mkdir(parents=True);evidence={};checks=[]
    def check(name,condition):
        if not condition:raise AssertionError(name)
        checks.append(name)
    raw=read(old/'private/run/cases/1251841/C/repair-shared.json')
    proposal=raw['proposal'];before=digest(raw)
    orphan_uses=[i for i,u in proposal['uses'].items() if u['task_id'] not in proposal['tasks']]
    orphan_bundles=[i for i,b in proposal['bundles'].items() if b['task_id'] not in proposal['tasks']]
    check('real V20 cache reproduces dangling task references',len(orphan_uses)==14 and len(orphan_bundles)==14)
    try:E.validate_dependencies(proposal)
    except ValueError as exc:check('stale dependency fails explicitly before inference',str(exc).startswith('STALE_DEPENDENCY_REFERENCES:'))
    else:raise AssertionError('Stale proposal incorrectly accepted')
    uses,bundles=retain_evidence(proposal,proposal['tasks'],proposal['source_records'],set())
    check('retention never treats removed task ids as unaffected',not set(orphan_uses)&set(uses) and not set(orphan_bundles)&set(bundles)
        and all(u['task_id'] in proposal['tasks'] for u in uses.values())
        and all(b['task_id'] in proposal['tasks'] for b in bundles.values()))
    check('real cache remains byte-content unchanged',digest(read(old/'private/run/cases/1251841/C/repair-shared.json'))==before)
    evidence['real_cache']={'orphan_uses':orphan_uses,'orphan_bundles':orphan_bundles,
        'cache_hash':before,'semantic_inputs_replaced':False,'method_quality_score':None}
    packet=copy.deepcopy(PACKET);packet['sources'][2]['text']+=' The record is complete for possession.'
    snapshot=prepare_sources(packet,LIB)
    for mode in ('empty_recovery','withdrawal','task_churn'):
        dest=work/mode;provider=RecoveryProvider(mode)
        outcome=run_arm(provider,snapshot,cfg,dest,'C')
        check(mode+' completes fictional whole chain',outcome['complete_chain'])
        oldshared=read(dest/'shared.json');newshared=read(dest/'repair-shared.json')
        E.validate_dependencies(newshared['proposal'])
        check(mode+' retains one repair pass',sum(t=='repair-report' for t in provider.calls)==1)
        source_calls=[t for t in provider.calls if t.startswith('source-original-read-')]
        check(mode+' original reading occurs before extraction',provider.calls.index(source_calls[0])<provider.calls.index('objects')<provider.calls.index('source-records'))
        check(mode+' does not repeat original reading during repair',not any(t.startswith('repair-source-original-read-') for t in provider.calls))
        for req in provider.requests:
            if req['task'].startswith('Read the supplied original CASE passages') or req.get('policy','').startswith('Describe and check the supplied original record'):
                check(mode+' source stage excludes target legal question '+digest(req)[:8],
                    'question' not in req['material'] and 'question_scope' not in req['material'] and 'frozen_law' not in req['material']
                    and all(x['domain']=='CASE' for x in req['material']['sources'].values()))
        if mode=='empty_recovery':
            check('empty extraction still has original reading',not oldshared['proposal']['source_records'] and bool(oldshared['proposal']['source_original_reading']['observations']))
            check('empty extraction becomes actionable source omissions',bool(read(dest/'repair-plan.json')['source_omissions']))
            check('fictional source recovery reviews new records before uses',provider.calls.index('repair-source-record-additions')<provider.calls.index('repair-source-record-review-0')<provider.calls.index('repair-use-review-0'))
            check('fictional recovered source reaches final report',bool(newshared['proposal']['source_records']) and outcome['internal_pass'])
        elif mode=='withdrawal':
            check('withdrawal without replacement remains incomplete',not newshared['proposal']['source_records'] and not outcome['internal_pass'])
            check('withdrawal preserves missing source evidence',bool(newshared['proposal']['source_record_coverage']['gaps']))
        else:
            invalidation=read(dest/'repair-evidence-invalidation.json')
            check('task replacement invalidates old evidence',bool(invalidation['removed_task_ids']) and not invalidation['retained_use_ids'] and not invalidation['retained_bundle_ids'])
            check('task replacement requires actual fresh fictional review calls','repair-use-review-0' in provider.calls)
            check('new task references reach final computation',bool(newshared['proposal']['uses']) and outcome['internal_pass'])
        evidence[mode]={'outcome':outcome,'calls':provider.calls,'old_proposal_hash':digest(oldshared['proposal']),
            'new_proposal_hash':digest(newshared['proposal']),'directory':str(dest.relative_to(ROOT)),'quality_score':None}
    # Baseline, rule knowledge, corpus membership and evaluation are unchanged.
    for name in ('baseline.py','evaluation.py','rule-library.json','law-coverage.json','corpus-manifest.json','corpus-summary.json'):
        check(name+' identical to V20',(ROOT/name).read_bytes()==(old/name).read_bytes())
    summary={'status':'PASS','checks':checks,'evidence':evidence,'model_calls':0,'engineering_only':True,
        'real_semantic_answers_injected':False,'independent_quality':None,'one_consolidated_acceptance':True}
    save(work/'summary.json',summary)
    print(json.dumps({'status':'PASS','directory':str(work),'checks':len(checks),'model_calls':0}))


if __name__=='__main__':main()
