"""One complete cached-document interface replay; no new legal judgments or calls."""
import ast
import copy
import json
import sys
from pathlib import Path
import environment as env
import source_v11 as s
from experiment import load,sha,wire,OLD
from source_v8 import save
from communication import compact_schema,expand_schema
from schema_contract import validate,decoder_schema,ContractError

def main():
    sys.path.insert(0,str(env.HERE/'private/schema-validation-vendor'))
    from jsonschema import Draft202012Validator
    from tokenizers import Tokenizer
    cfg=load(env.HERE/'protocol.json');sources=load(env.HERE/'private/input.json')['sources']
    cat=s.prepare_units(sources);dest=env.HERE/'private/offline'
    if dest.exists():raise ValueError('OFFLINE_REPLAY_ALREADY_EXISTS')
    tokenizer_path=env.REPO/'.runtime/qwen35-v1/model-cache/models--mlx-community--Qwen3.5-9B-4bit/snapshots/8b2b98c00a6b4d291155e4890773ca8f769aee53/tokenizer.json'
    tokenizer=Tokenizer.from_file(str(tokenizer_path))
    # Use exactly the predecessor's mechanical conversion of full old output,
    # without running its driver or inserting correct interpretations.
    tree=ast.parse((OLD/'review_offline.py').read_text())
    project_node=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='project')
    scope={};exec(compile(ast.Module(body=[project_node],type_ignores=[]),str(OLD/'review_offline.py'),'exec'),scope)
    old=load(OLD/'private/experiment-v1/cases/1251841/V9/source-records.json')
    projected=scope['project'](old,cat);measurements=[];display_errors=[]
    for f in sorted((OLD/'private/experiment-v1/cases/1251841/V10/requests').glob('*.json')):
        req=load(f); display=compact_schema(req['schema'])
        Draft202012Validator.check_schema(display)
        assert expand_schema(display)==req['schema']
        # Validate the ORIGINAL displayed schema separately: reversible rewriting
        # alone did not establish that its properties maps were valid schemas.
        transport=next((OLD/'private/experiment-v1/transport/1251841/V10/calls').glob('*-'+f.stem+'-attempt0'),None)
        if transport:
            system=load(transport/'request.json')['messages'][0]['content']
            displayed=json.loads(system.split('Return one complete JSON object using this schema:\n',1)[1])
            try:Draft202012Validator.check_schema(displayed)
            except Exception as exc:display_errors.append({'stage':f.stem,'error':str(exc).splitlines()[0]})
    def inspect(tag,req):
        actual=wire(req,cfg);j=json.loads(actual['messages'][1]['content'])
        restored={r['source_id']:r['text'] for rows in j['source_units'].values() for r in rows}
        assert restored==sources and list(restored)==list(sources)
        assert 'sources' not in j
        display=compact_schema(req['schema']);Draft202012Validator.check_schema(display)
        Draft202012Validator.check_schema(actual['response_format']['json_schema']['schema'])
        assert expand_schema(display)==req['schema']
        tokens=sum(len(tokenizer.encode(m['content'],add_special_tokens=False).ids) for m in actual['messages'])
        if tokens+cfg['parameters']['max_tokens']>=cfg['context_length']:raise ValueError('REPLAY_CONTEXT_OVERFLOW')
        measurements.append({'stage':tag,'local_message_tokens':tokens,'wire_bytes':len(json.dumps(actual)),
                             'hosted_template_equivalence_verified':False})
        save(dest/'wires'/(tag+'.json'),actual)
        return actual
    def cov(focus):return {u:{'state':'UNRESOLVED','source_ids':cat['units'][u]['source_ids'],
                       'explanation':'Offline replay supplies no independent semantic judgment.',
                       'missing_relationships':['Live whole-document assessment remains pending.']} for u in focus}
    def ask(tag,req):
        inspect(tag,req)
        if tag.startswith(('reading-','independent-')):
            units={}
            for uid in req['owner_unit_ids']:
                records=[]
                for original in projected:
                    if original['owner_unit_id']!=uid:continue
                    r=copy.deepcopy(original);r.pop('owner_unit_id');r.pop('source_ids')
                    r['assertion_source_ids']=r.pop('primary_source_ids');records.append(r)
                units[uid]={'state':'UNRESOLVED','records':records,'note':'Old model output projected without semantic correction.',
                            'missing_relationships':['Live evaluation required.']}
            result={'units':units}
        elif tag.startswith('whole-document-reconcile-'):
            result={'decisions':{k:{'action':'UNRESOLVED','issues':[{'aspect':'provenance','explanation':'No new source assessment.'}],
                 'source_ids':v['primary_source_ids'],'source_basis':'Preserved old model interpretation; no endorsement.',
                 'new_records':[]} for k,v in req['primary_records'].items()},'additions':[],'coverage':cov(req['owner_unit_ids'])}
        else:
            result={'reviews':{k:{'verdict':'UNRESOLVED','source_ids':v['primary_source_ids'],
                 'source_basis':'Offline chain replay has not established semantic support.',
                 'issues':[{'aspect':'provenance','explanation':'No independent model review.'}]} for k,v in req['records'].items()},
                 'coverage':cov(req['owner_unit_ids'])}
        validate(result,req['schema']);validate(result,decoder_schema(req['schema']))
        Draft202012Validator(compact_schema(req['schema'])).validate(result)
        return result
    result=s.run(sources,ask,dest/'chain')
    assert result['record_states']=={'UNRESOLVED':result['records']}
    # Replay all completed old reading packets into the keyed contract without
    # changing model statuses or records. Count structural failures, not accuracy.
    old_failures=[]
    for f in sorted((OLD/'private/experiment-v1/cases/1251841/V10/responses').glob('*.json')):
        if not f.stem.startswith(('reading-','independent-')):continue
        value=load(f);i=int(f.stem.split('-')[-1]);focus=cat['groups'][i];mapped={'units':{}}
        for uid in focus:
            row=value['coverage'][uid];records=[]
            for original in value['records']:
                if original['owner_unit_id']!=uid:continue
                r=copy.deepcopy(original);r.pop('owner_unit_id');r.pop('source_ids')
                r['assertion_source_ids']=r.pop('primary_source_ids');records.append(r)
            mapped['units'][uid]={'state':row['state'],'records':records,'note':row['explanation'],
                                  'missing_relationships':row['missing_relationships']}
        try:validate(mapped,s.unit_reading_schema(sources,cat,focus))
        except ContractError as exc:old_failures.append({'stage':f.stem,'reason':'OLD_VALUE_REJECTED_BY_NEW_ADDRESS_OR_NONEMPTY_CONTRACT'})
    protected=load(env.HERE/'private/preservation-before.json')['files']
    changed=[p for p,h in protected.items() if sha(p)!=h];assert not changed
    for f in env.HERE.glob('*.py'):compile(f.read_text(),str(f),'exec')
    save(dest/'report.json',{'status':'PASS_OFFLINE_INTERFACES_ONLY','new_model_calls':0,
         'old_invalid_display_schemas':display_errors,'old_reading_packets_rejected':old_failures,
         'whole_document_chain':result,'largest_local_message_tokens':max(x['local_message_tokens'] for x in measurements),
         'all_full_sources_unchanged':True,'model_semantic_acceptances_inserted':0,'protected_files':len(protected),
         'source_quality':None,'independent_reading_offline_replay_is_same_old_output':True,
         'predecessor_comparators_not_modified':True})
    save(dest/'measurements.json',measurements)
    print(json.dumps({'offline_pass':True,'records':result['records'],'old_invalid_schema_count':len(display_errors),
          'old_reading_packet_contract_rejections':len(old_failures),'max_message_tokens':max(x['local_message_tokens'] for x in measurements)}))

if __name__=='__main__':main()
