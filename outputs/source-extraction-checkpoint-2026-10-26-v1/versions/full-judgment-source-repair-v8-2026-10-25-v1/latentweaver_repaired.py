"""Repaired local upstream adaptation; explicitly not original upstream performance.

No upstream outputs or target judgments are used. Pure upstream builders and
validators run unchanged. No upstream client, downloader or batch launcher runs.
"""
import copy
import hashlib
import importlib
import importlib.util
import json
import sys
from pathlib import Path
from common import digest, save

ROOT=Path('/Users/victor/Documents/Codex/2026-09-28/files-mentioned-by-the-user-canonicalizing/outputs/rapido-ontology-source-v25-2026-10-25-v1')
EXTERNAL=ROOT/'private/external/latentweaver/source'
COMMIT='156a0c32275682421bc0746678749e20a318debf'


def modules():
    sys.path.insert(0,str(ROOT/'private/vendor'))
    if 'lw_pinned' not in sys.modules:
        spec=importlib.util.spec_from_file_location('lw_pinned',EXTERNAL/'prompt2_v2/src/__init__.py',
            submodule_search_locations=[str(EXTERNAL/'prompt2_v2/src')])
        module=importlib.util.module_from_spec(spec);sys.modules['lw_pinned']=module
        spec.loader.exec_module(module)
    return {name:importlib.import_module('lw_pinned.'+name) for name in (
        'config','input_loader','source_spans','prompt_builder','production_guardrails',
        'json_utils','candidate_validator','canonicalizer','canonical_validator',
        'source_validator','semantic_audit','semantic_admission')}


def plain_request(messages,cfg,schema=None):
    wire=copy.deepcopy(cfg['parameters'])
    # Native upstream uses no response_format. All other model parameters and
    # output/context capacities are shared with V25; semantic outputs are not fixed.
    wire.pop('response_format',None)
    wire.update(messages=messages,max_tokens=cfg['diagnostic_output_tokens'],
                chat_template_kwargs={'enable_thinking':False})
    if schema is not None:
        wire['response_format']={'type':'json_schema','json_schema':{'name':'candidate','schema':schema}}
    return {'plain_wire':wire,'output_token_cap':cfg['diagnostic_output_tokens']}


def ask(provider,cid,tag,messages,cfg,dest,schema=None):
    req=plain_request(messages,cfg,schema);save(dest/'requests'/(tag+'.json'),req)
    for attempt in range(cfg['max_technical_retries']+1):
        try:
            text,receipt=provider.call(cid,'LW',tag,req,attempt)
            save(dest/'receipts'/(tag+'.json'),receipt)
            (dest/(tag+'.txt')).write_text(text)
            return text
        except Exception as exc:
            receipts=getattr(exc,'receipts',[])
            if (provider.dispatch_stop or not receipts or receipts[-1].get('no_retry')
                or receipts[-1].get('status') not in ['STREAM_INCOMPLETE','STREAM_PROTOCOL_ERROR','CALL_TIMEOUT','TECHNICAL_FAILURE']
                or attempt>=cfg['max_technical_retries']):raise


def case_text(snapshot):
    paragraphs=[(sid,row['text']) for sid,row in snapshot['directory'].items() if row['domain']=='CASE']
    # Paragraph IDs are available to both methods; every original character is retained.
    text='\n\n'.join('['+sid+']\n'+content for sid,content in paragraphs)
    if len(text.split())>=6000:
        raise ValueError('UPSTREAM_MULTI_CHUNK_ADAPTER_NOT_IMPLEMENTED_NO_TRUNCATION')
    return text


def first_messages(kind,text):
    ontology=(EXTERNAL/'land_dispute_pipeline/ontology/Ontology.txt').read_text()
    template=(EXTERNAL/f'land_dispute_pipeline/prompts/prompt_1{kind}.txt').read_text()
    prompt=template.replace('{ontology}',ontology).replace('{text}',text)
    prompt += '\n'+SEMANTIC_GUIDANCE
    return [{'role':'system','content':'You are a legal AI parsing engine. You output valid JSON only.'},
            {'role':'user','content':prompt}]


def loaded_case(m,cid,text,inventories,dest):
    IL=m['input_loader'];docs={}
    contents={'CASE_SOURCE':text,'PROMPT1A':json.dumps(inventories['a'],ensure_ascii=False,indent=2),
              'PROMPT1B':json.dumps(inventories['b'],ensure_ascii=False,indent=2),
              'ONTOLOGY':(EXTERNAL/'prompt2_v2/input/ontology/Ontology.txt').read_text()}
    for name,content in contents.items():
        path=dest/'inputs'/(name+'.txt');path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content)
        docs[name]=IL.LoadedDocument(name,path,content,hashlib.sha256(content.encode()).hexdigest())
    return IL.LoadedCase(cid,{'case_id':cid},docs)


def run_case(provider,cid,snapshot,cfg,dest):
    m=modules();text=case_text(snapshot);inventories={};stages=[]
    save(dest/'adaptation.json',{'upstream_commit':COMMIT,'native_model':'qwen3-235b-a22b-instruct-2507',
         'tested_model':cfg['api_model'],'same_model_adaptation':True,'not_native_performance':True,
         'primary_input_hash':digest(text),'native_semantic_repair_enabled':False,'label':'REPAIRED_LOCAL_ADAPTATION_V8_NOT_UPSTREAM',
         'prompt_changes':['generic attribution, event/effect and condition guidance','native candidate schema enforced during generation'],
         'transport_changes':['Together endpoint and authorized credential','Qwen 9B shared parameters',
          'shared 65536 output capacity','one identical technical retry maximum','serial execution',
          'existing SSE and no-progress guards'],
         'source_changes':['same full rendered judgment supplied to both Prompt 1A and Prompt 1B, including disposition',
                           'source IDs retained; one authorized case below 6000 words'],
         'auxiliary_ontology':'native upstream classification ontology, not executable law',
         'not_a_single_call_A0_baseline':True})
    try:
        from json_repair import loads as repair_loads
        for kind in ('a','b'):
            raw=ask(provider,cid,'prompt1'+kind,first_messages(kind,text),cfg,dest)
            try:strict=json.loads(raw);strict_valid=isinstance(strict,dict)
            except ValueError:strict_valid=False
            # This is the upstream Prompt-1 parser policy; report repairs separately.
            cleaned=raw.strip()
            if cleaned.startswith('```'):cleaned='\n'.join(cleaned.splitlines()[1:])
            if cleaned.rstrip().endswith('```'):cleaned=cleaned.rstrip()[:-3]
            parsed=repair_loads(cleaned)
            if not isinstance(parsed,dict):raise ValueError('UPSTREAM_PROMPT1_NOT_OBJECT')
            inventories[kind]=parsed;save(dest/('prompt1'+kind+'.json'),parsed)
            save(dest/('prompt1'+kind+'-parse.json'),{'strict_json_object':strict_valid,
                  'repair_parser':'json-repair 0.54.2 as native Prompt 1 policy','raw_preserved':True})
            stages.append('prompt1'+kind)
        loaded=loaded_case(m,cid,text,inventories,dest)
        config=m['config'].load_config(EXTERNAL/'prompt2_v2/config.yaml')
        spans=m['source_spans'].build_source_span_index(loaded)
        save(dest/'source-spans.json',m['source_spans'].source_span_index_to_dict(spans))
        messages=m['production_guardrails'].apply_primary_guardrails(
            m['prompt_builder'].build_messages(loaded,config,span_index=spans))
        schema=candidate_wire_schema(cid,list(spans))
        save(dest/'candidate-wire-schema.json',schema)
        messages[-1]['content']+='\n'+SEMANTIC_GUIDANCE
        raw=ask(provider,cid,'prompt2',messages,cfg,dest,schema=schema)
        candidate=m['json_utils'].parse_model_json(raw)
        save(dest/'model-candidate.json',candidate);stages.append('prompt2')
        from schema_contract import validate
        validate(candidate,schema)
        gate=m['candidate_validator'].validate_llm_candidate(candidate,
            canonical_schema_path=config.schema_path,expected_case_id=cid,allowed_source_span_ids=set(spans))
        save(dest/'candidate-validation.json',gate.to_dict())
        if not gate.valid:raise ValueError('UPSTREAM_CANDIDATE_CONTRACT_INVALID')
        canonical,changes=m['canonicalizer'].canonicalize_candidate(candidate,loaded,config.schema_path,span_index=spans)
        save(dest/'canonical.json',canonical);save(dest/'canonicalization.json',changes.to_dict())
        structural=m['canonical_validator'].validate_canonical(canonical,config.schema_path,cid)
        grounding=m['source_validator'].validate_source_refs(canonical,loaded,span_index=spans)
        audit=m['semantic_audit'].audit_semantics(canonical)
        save(dest/'validation.json',{'structural':structural.to_dict(),'grounding':grounding.to_dict(),
            'semantic_audit':audit.to_dict(),'hard_validation_valid':bool(structural.valid and grounding.valid),
            'semantic_review_is_diagnostic_not_native_gate':True})
        if not (structural.valid and grounding.valid):raise ValueError('UPSTREAM_CANONICAL_OR_SOURCE_VALIDATION_FAILED')
        SA=m['semantic_admission'];items=SA.build_semantic_admission_items(candidate,spans)
        save(dest/'semantic-items.json',items)
        if items:
            raw=ask(provider,cid,'semantic-admission',SA.build_semantic_admission_messages(case_id=cid,items=items),cfg,dest)
            review=m['json_utils'].parse_model_json(raw)
            admission=SA.validate_semantic_admission_response(case_id=cid,items=items,response=review)
        else:admission=SA.make_empty_semantic_admission_result()
        save(dest/'semantic-admission.json',admission.to_dict());stages.append('semantic-admission')
        outcome={'case_id':cid,'technical_complete':True,'completed_stages':stages,
                 'hard_validation_valid':True,'content_quality':None,'not_native_performance':True}
    except Exception as exc:
        outcome={'case_id':cid,'technical_complete':False,'completed_stages':stages,
                 'error':type(exc).__name__+':'+str(exc),'content_quality':None,
                 'raw_extractions_remain_evaluable':bool(inventories),'not_native_performance':True}
    save(dest/'outcome.json',outcome);return outcome

SEMANTIC_GUIDANCE = """Source fidelity checks, without supplied case answers:
Distinguish current parties and appellate roles from earlier litigants, creditors, judges,
counsel and persons merely mentioned. A payment recipient is not necessarily the claimant.
Attribute each allegation to its actual speaker, using preceding original context. Do not
invent testimony, immediate threats, evidence, or missing facts to complete a template.
Separate execution of an instrument from whether it binds another person: rejecting its
legal effect is not rejecting the occurrence of execution. A considered claim is not an
adopted holding. Keep lower-court findings, current holdings, editorial headnotes and quoted
precedents separate. Extract the final outcome when explicitly present, without labelling a
resolved issue unadjudicated. Preserve conditions, exceptions, scope, negation and burdens
in the relevant descriptions, not merely the bottom-line outcome. References to precedents
must identify whether followed, limited, distinguished or rejected. Use only the native
candidate relation types and their permitted endpoint types; program-owned metadata edges
are not model-authored relations. Unknown or unresolved content stays explicit."""

def candidate_wire_schema(cid,source_ids):
    """Compile the pinned finite candidate contract, retaining its native validator.

    oneOf alternatives have disjoint status discriminators. The sole conditional
    separates Conclusion from every other node type. No model data is rewritten.
    """
    root=json.loads((EXTERNAL/'prompt2_v2/schemas/llm_candidate_schema.json').read_text())
    defs=root['$defs']
    defs['source_ref']['properties']['source_span_id']={'type':'string','enum':source_ids}
    root['properties']['case_id']={'type':'string','enum':[cid]}
    def visit(n):
        if isinstance(n,list): return [visit(x) for x in n]
        if not isinstance(n,dict): return n
        if '$ref' in n:
            assert set(n)=={'$ref'} and n['$ref'].startswith('#/$defs/')
            return visit(copy.deepcopy(defs[n['$ref'][8:]]))
        if 'allOf' in n:
            assert len(n['allOf'])==1 and n['allOf'][0].get('x-purpose')=='conclusion-kind'
            base={k:copy.deepcopy(v) for k,v in n.items() if k!='allOf'}
            yes=copy.deepcopy(base);no=copy.deepcopy(base)
            yes['properties']['node_type']={'type':'string','enum':['Conclusion']}
            yes['properties']['conclusion_kind']={'type':'string','enum':['HOLDING','DISPOSITION']}
            yes['required']=list(dict.fromkeys(yes['required']+['conclusion_kind']))
            no['properties']['node_type']['enum'].remove('Conclusion')
            no['properties']['conclusion_kind']={'type':'null'}
            return {'anyOf':[visit(yes),visit(no)]}
        if 'oneOf' in n:
            assert set(n)=={'oneOf'}
            return {'anyOf':[visit(x) for x in n['oneOf']]}
        out={k:visit(v) for k,v in n.items() if k not in ('$defs','$schema','$id','title') and not k.startswith('x-')}
        if 'const' in out: out['enum']=[out.pop('const')]
        if isinstance(out.get('type'),list):
            types=out.pop('type');branches=[]
            for typ in types:
                b=copy.deepcopy(out);b['type']=typ
                if 'enum' in b:
                    b['enum']=[v for v in b['enum'] if (v is None if typ=='null' else isinstance(v,str))]
                    if not b['enum']:continue
                branches.append(b)
            return {'anyOf':branches}
        return out
    from schema_contract import decoder_schema
    return decoder_schema(visit(root))
