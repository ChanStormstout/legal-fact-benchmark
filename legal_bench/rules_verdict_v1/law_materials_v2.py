"""Historical judgment authority units; no claim of consolidated statute coverage."""
import datetime
from .authority_index import build, search
from .source_views import digest


def units_from_judgment(source, decided_on):
    datetime.date.fromisoformat(decided_on)
    return [{'id':source['case_id']+':'+s['id'], 'text':s['text'],
             'source':{'case_id':source['case_id'],'segment_id':s['id'],'url':source['url'],'text_sha256':source.get('text_sha256')},
             'decided_on':decided_on,'version_status':'JUDGMENT_AS_RECORDED_NOT_VERIFIED_CONSOLIDATED_STATUTE',
             'source_kind':'JUDGMENT_PASSAGE_ROLE_NOT_AUTOMATICALLY_ADOPTED_RULE',
             'dependencies':[], 'dependency_coverage':'NOT_YET_REVIEWED', 'segment_hash':digest(s['text'].encode())}
            for s in source['segments']]


def eligible_units(units, target_case_id, target_date):
    date=datetime.date.fromisoformat(target_date)
    included,excluded=[],[]
    for u in units:
        reason='SAME_CASE_TARGET_LEAKAGE' if u['source']['case_id']==target_case_id else 'FUTURE_AUTHORITY' if datetime.date.fromisoformat(u['decided_on'])>=date else None
        if reason:excluded.append({'unit_id':u['id'],'reason':reason})
        else:included.append(u)
    return included,excluded


def citation_checks(payload, sources):
    """Quote localization only; no entailment/adoption/condition-validity claim."""
    lookup={(c,s['id']):s['text'] for c,source in sources.items() for s in source['segments']}
    findings=[]
    def visit(v,path):
        if isinstance(v,dict):
            if {'case_id','segment_id','quote'} <= set(v):
                text=lookup.get((str(v['case_id']),v['segment_id']))
                findings.append({'path':path,'case_id':str(v['case_id']),'segment_id':v['segment_id'],
                                 'status':'EXACT_QUOTE' if text is not None and isinstance(v['quote'],str) and v['quote'] and v['quote'] in text else 'NOT_EXACTLY_LOCATED',
                                 'quote':v['quote']})
            for k,x in v.items():visit(x,path+'.'+k)
        elif isinstance(v,list):
            for i,x in enumerate(v):visit(x,path+'[%d]'%i)
    visit(payload,'$')
    return {'references':findings,'exact':sum(x['status']=='EXACT_QUOTE' for x in findings),
            'not_located':sum(x['status']!='EXACT_QUOTE' for x in findings),'semantic_support_established':False}
