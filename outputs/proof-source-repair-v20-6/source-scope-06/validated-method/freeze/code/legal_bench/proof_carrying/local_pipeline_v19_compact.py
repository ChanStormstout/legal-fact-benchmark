"""V19_5: model propositions and code-restored source remain separate."""
import copy
from .local_pipeline_v19_refs import *
from . import local_pipeline_v19_refs as parent
from .reference_addresses_v19 import convert as typed_convert

VERSION = 'V19_5'

def schema(rules, case=None):
    result = parent.schema(rules, case)
    spec = result['properties']['analyses']['items']['properties']['records']['items']
    spec['properties']['proposition'] = spec['properties'].pop('text')
    spec['required'] = ['proposition' if x == 'text' else x for x in spec['required']]
    # No size cap on substantive interpretation. Repeated addresses have no new
    # evidentiary content; the incremental guard also checks this at runtime.
    def walk(v):
        if isinstance(v, dict):
            if 'refs' in v.get('properties', {}):v['properties']['refs']['uniqueItems'] = True
            for value in v.values():walk(value)
        elif isinstance(v, list):
            for value in v:walk(value)
    walk(result)
    return result

# One revision of the existing contract and synthetic example, not a growing
# collection of outcome-specific instructions. No target facts are used here.
INSTRUCTION = parent.INSTRUCTION.replace('Each record attributes speaker, court/stage and the exact source.',
    'Each record contains a proposition: your specific interpretation of a source assertion, not a transcription of its paragraph. Keep attribution, negation and substantive qualifications in that proposition. Code separately restores the selected original fragments from refs. Do not accumulate earlier records into a later record. Distinct propositions, courts or stages remain distinct; the same record can be linked to multiple uses. Each record attributes speaker, court/stage and the exact source.').replace('"text":', '"proposition":')

def proposal_prompt(case, rules, part):
    selected = [r for r in rules if r['id'] in part['rule_ids']]
    view = {**case, 'segments':[s for s in case['segments'] if s['id'] in part['source_ids']]}
    notice = '\nV19_5 ADDRESS DIRECTORY:\n' + compact_json([s['address'] for s in source_directory(view)])
    notice += '\nArray position n selects SRC:n. EV:n, OBJ:n and USE:n are one-based positions local to this analysis. Each refs list contains each selected address once; reuse it freely in different records/uses. Dynamic existence is checked on import. necessary_limits kinds NOTE/STAGE_SCOPE do not block; BLOCK_SCOPE identifies a specific missing prerequisite, UNMAPPED leaves its scope pending. component is WHOLE_JUDGMENT or COMP:n.\n'
    return (INSTRUCTION + notice + '\nFIXED REQUEST:\n' + compact_json(next(q for q in case['targets'] if q['id']=='Q1'))
            + '\nPART BOUNDARY:\n' + compact_json(part) + '\nUNCHANGED RULES AND PREMISE WORK DIRECTORY:\n' + compact_json(directory(selected))
            + '\nROLE ADDRESSES (TYPE IS NOT IDENTITY):\n' + compact_json(role_directory(selected))
            + '\nALLOWED SOURCE (original, not generated evidence):\n' + source_text(view)
            + '\nOUTPUT SCHEMA:\n' + compact_json(schema(selected, view)))

def convert(raw, case, production_version):
    transport = copy.deepcopy(raw)
    ledger = []
    if production_version == VERSION:
        src = {row['choice']:row['address'] for row in source_directory(case)}
        originals = {s['id']:s for s in case['segments']}
        for n, unit in enumerate(transport['analyses']):
            for i, rec in enumerate(unit['records']):
                rec['text'] = rec.pop('proposition')
                rec['text_origin'] = 'MODEL_INTERPRETATION_NOT_VERBATIM_SOURCE'
                rec['restored_source'] = [{'address':src[ref], 'text':originals[src[ref]]['text'],
                    'source_document':originals[src[ref]]['source_document'],
                    'original_line':originals[src[ref]].get('original_line'), 'origin':'PROGRAM_RESTORED_ORIGINAL'}
                    for ref in rec['refs'] if ref in src]
                ledger.append({'unit':n+1, 'record':i+1, 'conversion':'PROPOSITION_TO_LEGACY_TEXT_ROLE',
                               'semantics_changed':False, 'source_is_not_interpretation':True})
        version = 'V19_4'
    else:version = production_version
    converted, addresses = typed_convert(transport, case, version)
    return converted, addresses + ledger

def independent_import(raw, converted, case, version):
    from .local_checker_v19_refs import check_import
    if version != VERSION:return check_import(raw, converted, case, version)
    # Recompute interpretation/source separation directly; don't trust import
    # flags or call the production conversion routine.
    canonical = copy.deepcopy(raw); errors=[]
    source_map={'SRC:'+str(i):s for i,s in enumerate(case['segments'],1)}
    for a,b in zip(canonical['analyses'],converted['analyses']):
        for x,y in zip(a['records'],b['records']):
            x['text']=x.pop('proposition')
            expected=[{'address':source_map[r]['id'],'text':source_map[r]['text'],
                       'source_document':source_map[r]['source_document'],
                       'original_line':source_map[r].get('original_line'),'origin':'PROGRAM_RESTORED_ORIGINAL'}
                      for r in x['refs'] if r in source_map]
            if y.get('text')!=x['text'] or y.get('restored_source')!=expected:errors.append('INTERPRETATION_OR_SOURCE_CHANGED')
    result=check_import(canonical,converted,case,'V19_4')
    result['errors']+=errors;result['status']='REJECTED' if result['errors'] else 'OK'
    return result
