"""One whole-document interface replay from preserved model outputs, not a trial.

No synthetic legal snippets, inserted corrections, model verdicts or paid calls.
Old records are mechanically projected and kept UNRESOLVED throughout. This checks
the actual full-document call chain, not the quality of a hypothetical new model.
"""
import copy
import json
from pathlib import Path
import environment as env
import source_v10 as s
import source_v9
import latentweaver_v10 as lw
from prepare import load, wire, sha
from inspection import measure
from communication import compact_schema, expand_schema


def project(old, catalog):
    source_to_unit={sid:uid for uid,u in catalog['units'].items() for sid in u['source_ids']}
    out=[]
    for item in old['records'].values():
        r=item['record']; ids=list(dict.fromkeys(r['source_ids']+
            [sid for q in r['qualifications'] for sid in q['source_ids']]))
        owner=source_to_unit[r['source_ids'][0]]
        def w(v):return {'value':v,'source_ids':ids if v is not None else []}
        a=r['attribution'];p=r['proposition']
        mode={'ALLEGATION':'ALLEGATION','DENIAL':'DENIAL','COURT_FINDING':'FINDING',
              'LEGAL_ARGUMENT':'LEGAL_ARGUMENT','OPEN_QUESTION':'QUESTION',
              'DOCUMENT_TERM':'DOCUMENT_TERM','UNRESOLVED':'UNRESOLVED'}.get(r['kind'],'NARRATION')
        kind='SOURCE_METADATA' if r['kind']=='SOURCE_METADATA' else {
            'LEGAL_EFFECT':'LEGAL_EFFECT','OCCURRENCE':'EVENT','PROCEDURE':'PROCEDURE'}.get(p['layer'],'OTHER')
        out.append({'owner_unit_id':owner,
            'primary_source_ids':[sid for sid in r['source_ids'] if source_to_unit[sid]==owner],
            'source_ids':ids,'content_kind':kind,'statement_mode':mode,
            'attribution':{'speaker':w(a['speaker']),'forum':w(a['forum']),
                           'case_context':'UNKNOWN','case_reference':w(None)},
            'proposition':{'text':' '.join(str(p[k]) for k in ['subject','relation','object'] if p[k] is not None),
                           'polarity':'UNKNOWN','negation_scope':None},
            'participants':[{'role':role,'mention':w(p[field]),'referent':w(None)}
                            for role,field in [('SUBJECT','subject'),('OBJECT','object')] if p[field] is not None],
            'scope':{'property':w(None),'event_time':w(p['event_time']),
                     'statement_time':w(a['time']),'proceeding':w(a['stage'])},
            'qualifications':[{'type':q['type'],'content':{'value':q['text'],'source_ids':q['source_ids']}}
                              for q in r['qualifications']],
            'uncertainties':r['uncertainties']+['Mechanical old-output projection; no new semantic assessment.']})
    return out


def unresolved_coverage(catalog, focus):
    return {uid:{'state':'UNRESOLVED','source_ids':catalog['units'][uid]['source_ids'],
                 'explanation':'Offline interface replay does not assess source coverage.',
                 'missing_relationships':['Reference annotation and live model evaluation remain pending.']}
            for uid in focus}


def expand_view(req,value):
    if isinstance(value,dict):
        if set(value)=={'witness_id'}:
            w=req['witness_table'][value['witness_id']]
            return {'value':w['value'],'source_ids':expand_view(req,w['references'])}
        if set(value)=={'source_set_id'}:return req['source_sets'][value['source_set_id']]
        return {k:expand_view(req,v) for k,v in value.items()}
    if isinstance(value,list):return [expand_view(req,v) for v in value]
    return value


def main():
    dest=env.HERE/'private/offline-whole-document-review'
    if dest.exists():raise ValueError('EXISTING_REVIEW_NOT_OVERWRITTEN')
    cfg=load(env.HERE/'protocol.json');cohort=load(env.HERE/'private/preparation/cohort.json')
    previews=[]
    for row in cohort['selected']:
        cid=row['case_id'];sources=load(env.HERE/'private/preparation/inputs'/f'{cid}.json')['sources']
        cat=s.prepare_units(sources)
        assert [sid for u in cat['units'].values() for sid in u['source_ids']]==list(sources)
        for i,focus in enumerate(cat['groups']):
            for role,ind in [('primary',False),('independent',True)]:
                req=s.reading_request(sources,cat,focus,ind);actual=wire(req,cfg)
                assert json.loads(actual['messages'][1]['content'])['sources']==sources
                assert not {'candidates','primary_records','independent_observations'} & set(req)
                assert expand_schema(compact_schema(req['schema']))==req['schema']
                previews.append({'case_id':cid,'stage':f'{role}-{i:03d}',**measure(actual)})
        snap={'directory':{sid:{'domain':'CASE','text':v} for sid,v in sources.items()}}
        text=lw.case_text(snap)
        assert all('['+sid+']\n'+v in text for sid,v in sources.items())
        for kind in ('a','b'):
            messages=lw.first_messages(kind,text)
            assert text in messages[1]['content']
            previews.append({'case_id':cid,'stage':'LW-prompt1'+kind,**measure(lw.plain_request(messages,cfg)['plain_wire'])})
        # V9 request construction is retained, not repaired inside the comparator.
        for i,focus in enumerate(source_v9.plan(sources)):
            req=source_v9.reading_request(sources,focus);actual=wire(req,cfg)
            assert json.loads(actual['messages'][1]['content'])['sources']==sources
            previews.append({'case_id':cid,'stage':f'V9-reading-{i:03d}',**measure(actual)})
    sources=load(env.HERE/'private/preparation/inputs/1251841.json')['sources'];catalog=s.prepare_units(sources)
    old_path=env.V9/'private/run-v1/cases/1251841/ROLE/source-records.json'
    projected=project(load(old_path),catalog);measurements=[]
    def ask(tag,req):
        assert req['sources']==sources
        actual=wire(req,cfg)
        assert json.loads(actual['messages'][1]['content'])['sources']==sources
        assert expand_schema(compact_schema(req['schema']))==req['schema']
        measurements.append({'stage':tag,**measure(actual)})
        if tag.startswith(('reading-','independent-')):
            focus=req['owner_unit_ids']
            return {'records':[copy.deepcopy(r) for r in projected if r['owner_unit_id'] in focus],
                    'coverage':unresolved_coverage(catalog,focus)}
        if tag.startswith('whole-document-reconcile-'):
            return {'decisions':[{'target_id':k,'action':'UNRESOLVED',
                'issues':[{'aspect':'provenance','explanation':'Old output replay supplies no independent semantic judgment.'}],
                'source_ids':expand_view(req,v)['source_ids'],'source_basis':'Offline replay of the existing record; not a source endorsement.',
                'new_records':[]} for k,v in req['primary_records'].items()],
                'additions':[],'coverage':unresolved_coverage(catalog,req['owner_unit_ids'])}
        assert tag.startswith('whole-document-final-review-')
        assert not {'events','coverage_proposal','final_review'} & set(req)
        return {'reviews':[{'target_id':k,'verdict':'UNRESOLVED',
                 'source_ids':expand_view(req,v)['source_ids'],'source_basis':'Offline replay requires live source review before any semantic conclusion.',
                 'issues':[{'aspect':'provenance','explanation':'No independent new model review was performed.'}]}
                for k,v in req['records'].items()],
                'coverage':unresolved_coverage(catalog,req['owner_unit_ids'])}
    result=s.run(sources,ask,dest/'chain')
    assert result['technical_complete'] and result['record_states']=={'UNRESOLVED':result['records']}
    capacity_warnings=[r['stage'] for r in measurements if r['message_content_tokens_local']+
                       cfg['parameters']['max_tokens']>=cfg['context_length']]
    for p in env.HERE.glob('*.py'):compile(p.read_text(),str(p),'exec')
    before=load(env.HERE/'private/preservation-before.json')
    files=before.get('files',before)
    if isinstance(files,list):raise ValueError('UNEXPECTED_PROTECTION_MANIFEST')
    changed=[str(p) for p,h in files.items() if sha(p)!=h]
    assert not changed,changed
    s.save(dest/'request-measurements.json',{'planned_first_readings':previews,'complete_cached_record_replay':measurements})
    s.save(dest/'report.json',{'status':'PASS_OFFLINE_WHOLE_DOCUMENT_INTERFACE_ONLY',
        'full_sources_preserved_for_all_six':True,'arbitrary_lw_word_limit_removed':True,
        'projected_from':str(old_path),'projected_source_sha256':sha(old_path),
        'independent_reading_simulated_from_same_old_records':True,
        'new_model_calls':0,'synthetic_legal_snippets':0,'model_semantic_acceptances_inserted':0,
        'semantic_quality':None,'full_document_model_experiment_completed':False,
        'replay_context_warnings':capacity_warnings,
        'old_files_checked':len(files),'old_files_changed':changed,'chain':result})
    print(json.dumps({'status':'PASS_OFFLINE_ONLY','replay_records':result['records'],
        'protected_files':len(files),'request_previews':len(previews),'new_model_calls':0}))


if __name__=='__main__':main()
