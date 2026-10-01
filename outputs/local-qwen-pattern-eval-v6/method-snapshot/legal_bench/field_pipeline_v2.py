"""Declared source-supported fields and query-dependent unknowns, version 2.

Source anchors validate provenance, not the semantic accuracy of LLM declarations.
Legacy views remain conservative unless an existing explicit projection applies.
No free-text qualifier is interpreted by keywords or case-specific rules.
"""
import copy,itertools
from .core import digest,canonical
from .fast_development import import_case,VOCABULARY
from .conditional_engine import field_value as legacy_value,iso_date,equal_value
from .typed_relations import validate_query,relation_value,EDGE_OPS

VERSION='declared-fields-v2'

def raw_value(event,field):
    value=event
    for part in field.split('.'):
        value=value.get(part) if isinstance(value,dict) else None
    return value

def import_declared(annotation,source):
    # The temporary value only runs legacy ID/source validation. It is restored
    # to UNKNOWN before computation, and never grants a known type or role.
    working=copy.deepcopy(annotation)
    originals={e['id']:e for e in annotation.get('events',[]) if isinstance(e,dict) and 'id' in e}
    for e in working.get('events',[]):
        if isinstance(e,dict) and e.get('type') in [None,'UNKNOWN']:e['type']='LEASE_PROPERTY'
    view=import_case(working,source)
    sm={s['id']:s['text'] for s in source['segments']};diagnostics=[]
    def anchored(seq):return isinstance(seq,list) and bool(seq) and all(isinstance(x,dict) and x.get('quote') and x['quote'] in sm.get(x.get('segment_id'),'') for x in seq)
    objects={o['id']:o for o in view['objects']}
    allowed=lambda f:isinstance(f,str) and (f in ['type','status','polarity','time','roles','attributes','*'] or f.startswith(('roles.','attributes.')))
    for e in view['events']:
        original=originals[e['id']];e['type']=original.get('type') or 'UNKNOWN';e['source_assertion']=copy.deepcopy(original)
        blocked=[];known={}
        def block(fields,reason,evidence=None):
            blocked.append({'affected_fields':fields,'reason':reason,'evidence':evidence or [],'kind':'DECLARED_DEPENDENCY'})
        declared=original.get('known_fields',[])
        if not isinstance(declared,list):declared=[];block(['*'],'MALFORMED_KNOWN_FIELDS')
        for d in declared:
            f=d.get('field') if isinstance(d,dict) else None
            if not allowed(f) or f in ['*','roles','attributes']:
                diagnostics.append({'event_id':e['id'],'field':f,'reason':'INVALID_KNOWN_FIELD'});continue
            if d.get('value') is None or d.get('value')!=raw_value(e,f) or not anchored(d.get('evidence')):
                block([f],'KNOWN_FIELD_VALUE_OR_QUOTE_INVALID');continue
            if f=='type' and d['value'] not in VOCABULARY:block(['type'],'UNKNOWN_TYPE_DECLARATION');continue
            if f.startswith('roles.'):
                o=objects.get(d['value'])
                if not o or o.get('identity_resolved') is not True:block([f],'UNRESOLVED_OBJECT_REFERENCE');continue
                if e['type'] in VOCABULARY and f.split('.',1)[1] not in VOCABULARY[e['type']]:block([f],'ROLE_OUTSIDE_TYPE');continue
            if f=='time' and not iso_date(d['value']):block(['time'],'NON_EXACT_DATE');continue
            if f=='status' and d['value']=='UNKNOWN' or f=='polarity' and d['value']=='UNKNOWN':block([f],'EXPLICIT_UNKNOWN');continue
            known[f]=copy.deepcopy(d)
        uncertainties=original.get('unresolved',[])
        if not isinstance(uncertainties,list):block(['*'],'MALFORMED_UNRESOLVED');uncertainties=[]
        for u in uncertainties:
            affects=u.get('affects') if isinstance(u,dict) else None
            if not isinstance(affects,list) or not affects or any(not allowed(f) for f in affects):
                block(['*'],'UNDECLARED_UNCERTAINTY_DOMAIN');continue
            if not anchored(u.get('evidence')):block(['*'],'UNLOCATED_UNCERTAINTY_DECLARATION');continue
            block(affects,u.get('reason','EXPLICIT_UNCERTAINTY'),u['evidence'])
        deps={}
        scope_deps=original.get('scope_dependencies',[])
        if not isinstance(scope_deps,list):block(['*'],'MALFORMED_SCOPE_DEPENDENCIES');scope_deps=[]
        for d in scope_deps:
            if not isinstance(d,dict):continue
            affects=d.get('affects')
            if isinstance(affects,list) and affects and all(allowed(f) for f in affects) and anchored(d.get('evidence')):
                deps[d.get('scope_key')]=d
        if e.get('scope') and not original.get('scope_parsed',False):
            for key in e['scope']:
                d=deps.get(key)
                if d:block(d['affects'],d.get('reason','UNPARSED_SCOPE'),d['evidence'])
                else:block(['*'],'UNPARSED_SCOPE_WITHOUT_FIELD_DOMAIN:'+key)
        e['field_contract']={'version':VERSION,'known_fields':known,'blocked':blocked,
                             'type_unresolved':'type' not in known or any('type' in b['affected_fields'] for b in blocked)}
    view['version']=VERSION;view['declaration_diagnostics']=diagnostics
    return view

def value(event,field):
    # Record identity is an importer-validated structural ID, not event identity.
    if field=='id':return event['id'],[]
    c=event['field_contract']
    if c.get('version')!=VERSION:return legacy_value(event,field)
    d=c['known_fields'].get(field)
    reasons=[b for b in c['blocked'] if any(f==field or field.startswith(f+'.') or f=='*' for f in b['affected_fields'])]
    # Independent coarse type support describes what an assertion is ABOUT;
    # whole-proposition restrictions still block occurrence and all arguments.
    if field=='type' and d and not any('type' in b['affected_fields'] for b in c['blocked']):return d['value'],[]
    if reasons:return None,reasons
    if not d:return None,[{'affected_fields':[field],'reason':'NO_DECLARED_SOURCE_SUPPORT'}]
    return d['value'],[]

def execute_declared(view,registry,query):
    err=validate_query(query)
    if err:return {'status':'UNSUPPORTED','reason':err,'witnesses':[],'uncertain_bindings':[],'rejected_bindings':[],'candidate_decisions':[]}
    pools=[];decisions=[]
    for atom in query['atoms']:
        pool=[]
        for e in view['events']:
            if e['unit_id']!=view['units'][0]['id']:continue
            if 'event_id' in atom and atom['event_id']!=e['id']:continue
            typ,why=value(e,'type')
            excluded=typ is not None and typ!=atom['type']
            decisions.append({'var':atom['var'],'event_id':e['id'],'field':'type','required':atom['type'],'known':typ,'decision':'EXCLUDE' if excluded else 'KEEP_UNKNOWN' if why else 'KEEP','reason':'KNOWN_DIFFERENT_TYPE' if excluded else 'TYPE_UNCERTAIN' if why else 'KNOWN_REQUIRED_TYPE','dependencies':why})
            if not excluded:pool.append(e)
        pools.append(pool)
    good=[];unknown=[];rejected=[];objects={o['id']:o for o in view['objects']}
    for combo in itertools.product(*pools):
        binding=dict(zip([a['var'] for a in query['atoms']],combo));missing=[];failed=[];refs=[]
        def get(e,f):
            v,r=value(e,f)
            if r:missing.append({'event_id':e['id'],'field':f,'dependencies':r})
            return v
        for atom,e in zip(query['atoms'],combo):
            for f,target in [('type',atom['type']),('status',atom.get('status','COURT_FOUND')),('polarity',atom.get('polarity','POSITIVE'))]:
                if target=='ANY':continue
                v=get(e,f)
                if v is not None and v!=target:failed.append({'event_id':e['id'],'field':f,'value':v,'required':target})
        for c in query.get('constraints',[]):
            var,f=c['left'].split('.',1);left=get(binding[var],f)
            if c['op']=='equals':right=c['value']
            else:var,f=c['right'].split('.',1);right=get(binding[var],f)
            if c['op'] in EDGE_OPS:
                st,ids,reason=relation_value(registry,objects,c['op'],left,right);refs.extend(ids)
                decision={'constraint':c,'left':left,'right':right,'reason':reason,'edge_ids':ids}
                if st=='UNKNOWN':missing.append(decision)
                elif st=='MISMATCH':failed.append(decision)
            elif left is None or right is None:continue
            elif c['op']=='before' and (not iso_date(left) or not iso_date(right)):missing.append({'constraint':c,'reason':'EXACT_TIME_REQUIRED'})
            elif not ({'same':lambda:equal_value(left,right),'equals':lambda:equal_value(left,right),'different':lambda:not equal_value(left,right),'before':lambda:left<right}[c['op']]()):failed.append({'constraint':c,'left':left,'right':right})
        w={'binding':{k:e['id'] for k,e in binding.items()},'evidence_refs':[{'case_id':view['case_id'],'event_id':e['id']} for e in combo],'relation_edge_refs':sorted(set(refs))}
        if failed:rejected.append(dict(w,failed_conditions=failed,uncertainty=missing))
        elif missing:unknown.append(dict(w,uncertainty=missing))
        else:good.append(w)
    specified=all('event_id' in a for a in query['atoms'])
    return {'status':'MATCH' if good else 'UNKNOWN' if unknown else 'MISMATCH' if specified and rejected else 'NOT_FOUND','witnesses':good,'uncertain_bindings':unknown,'rejected_bindings':rejected,'candidate_decisions':decisions,'closed_world':False,'version':VERSION}
