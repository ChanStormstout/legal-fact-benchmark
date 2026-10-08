"""Independent, reusable scoped rule templates; given-rule oracle is audited."""
import copy
from legal_bench.rules_verdict_v1.irac_native_schema_v1 import quote_errors
from .input_partition import AVAIL

def validate_template(template,sources):
    errors=[]
    for key in ('template_id','family','jurisdiction','version','scope','conditions','rule'):
        if key not in template:errors.append('MISSING:'+key)
    ids={c.get('id') for c in template.get('conditions',[])}
    for r in [template.get('rule',{})]+template.get('conditions',[]):
        errors+=quote_errors(r.get('source_refs'),sources)
        for d in r.get('dependencies',[]):
            if not isinstance(d,dict) or d.get('condition_id') not in ids or d.get('operator') not in {'AND','OR','QUALIFICATION'}:errors.append('DEPENDENCY_INVALID')
    return sorted(set(errors))

def attach(template,issue_id):
    rule=copy.deepcopy(template['rule']);rule.update(independent_source=True,governs_issue_id=issue_id)
    common=dict(statement_status='DOCUMENT_RECORDED',semantic_stage='PRE_TARGET_RECORD',court_level='NONE',prospective_availability=AVAIL)
    rule.update(common);conditions=copy.deepcopy(template['conditions'])
    for c in conditions:c.update(common,rule_id=rule['id'])
    return rule,conditions

RULE_PROMPT='''Build a REUSABLE GIVEN RULE template from the independent legal source excerpts below, NOT from any target case. No external search. Return a complete downloadable rule-FAMILY.json once. This is model-proposed rule decomposition, not an automatically induced rule or complete law library. Use at most 4-6 single-proposition conditions; identity and positive/negative direction must be unambiguous and stable across cases. Distinguish legal requirements, alternative routes, qualifications, burden triggers and evidentiary factors. Do not treat factors as necessary conditions. Exclude case-specific facts and verdicts from rule/condition wording, even if the independent precedent excerpt recites such facts. Dependencies only when directly supported; AND/OR/QUALIFICATION IDs refer to defined conditions. Do not force mechanical overall verdict logic. Scope narrowly to the ACTUAL jurisdiction/provision/version specified. Declare historical/version uncertainty and interpretation coverage; no promise of complete decisive tests.
Output {template_id,family,jurisdiction,version,scope,coverage_limits,rule:{id,text,source_refs:[{source_id,quote}]},conditions:[{id,text,kind:"NECESSARY",polarity:"POSITIVE",dependencies:[],source_refs:[{source_id,quote}]}]}. kind can NECESSARY,ALTERNATIVE,QUALIFICATION,BURDEN_TRIGGER,FACTOR, but fill ONE actual value; same for polarity POSITIVE/NEGATIVE. Exact continuous quotes independently; no concatenation or ellipses. Each condition must quote the given independent rule source. Conditions use unique stable IDs prefixed FAMILY; all references use the source IDs below. No targets, factual supports/defeats or training masks.'''
