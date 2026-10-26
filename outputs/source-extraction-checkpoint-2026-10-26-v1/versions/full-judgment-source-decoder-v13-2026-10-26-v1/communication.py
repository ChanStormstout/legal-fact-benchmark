"""Lossless transport compaction and generic revision feedback; no legal answers."""
import copy
import json
import re
from collections import Counter
from common import digest
from schema_contract import decoder_schema


def compact_schema(schema):
    """Factor repeated subschemas into JSON Schema definitions for prompt display.

    The consumer retains the original semantic schema. The decoder receives an
    equivalent self-contained form. Resolving display references reproduces the
    original schema canonically; display factoring never changes the contract.
    """
    definitions = {}
    names = {}

    def visit(value, root=False):
        # Walk schema positions, not dictionaries that merely contain a key
        # named type/enum/anyOf. Properties are literal field-name mappings.
        if not isinstance(value, dict):
            raise ValueError('SCHEMA_NODE_REQUIRED')
        key = digest(value)
        def children():
            out = copy.deepcopy(value)
            for keyword in ('properties', '$defs', 'patternProperties'):
                if keyword in out:
                    out[keyword] = {name: visit(spec) for name, spec in value[keyword].items()}
            for keyword in ('items', 'additionalProperties'):
                if isinstance(value.get(keyword), dict):
                    out[keyword] = visit(value[keyword])
            for keyword in ('anyOf', 'oneOf', 'allOf'):
                if keyword in out:
                    out[keyword] = [visit(spec) for spec in value[keyword]]
            return out
        if not root and len(json.dumps(value)) > 90:
            if key not in names:
                name = 'D' + str(len(names) + 1)
                names[key] = name
                definitions[name] = children()
            return {'$ref': '#/$defs/' + names[key]}
        return children()

    out = visit(schema, True)
    out['$defs'] = definitions
    return out


def expand_schema(display):
    definitions = display.get('$defs', {})

    def visit(value):
        if isinstance(value, list):
            return [visit(v) for v in value]
        if not isinstance(value, dict):
            return value
        if '$ref' in value:
            return visit(definitions[value['$ref'].split('/')[-1]])
        return {k: visit(v) for k, v in value.items() if k != '$defs'}
    return visit(display)


def retrieval_for_report(retrieval):
    """Keep the audit ledger on disk; send only each unique source ID once."""
    return {k: copy.deepcopy(retrieval[k]) for k in
            ('method', 'selected_ids', 'history_selected_ids', 'history_context_budget_chars', 'collections', 'snapshot_id',
             'rank_is_not_semantic_acceptance', 'external_network', 'coverage_complete')
            if k in retrieval}


def visible_schema(schema, all_ids, visible_ids):
    """Remove unseen source choices before decoding; never fix generated values."""
    def visit(x):
        if isinstance(x,list):return [visit(v) for v in x]
        if not isinstance(x,dict):return x
        out={k:visit(v) for k,v in x.items()}
        if 'enum' in out:
            out['enum']=[v for v in out['enum'] if v not in all_ids or v in visible_ids]
            if not out['enum']:raise ValueError('NO_VISIBLE_SOURCE_FOR_REQUIRED_ENUM')
        if out.get('type')=='array' and 'enum' in out.get('items',{}):
            out['maxItems']=min(out.get('maxItems',len(out['items']['enum'])),len(out['items']['enum']))
            if out.get('minItems',0)>out['maxItems']:raise ValueError('INSUFFICIENT_VISIBLE_SOURCES')
        return out
    return visit(schema)


def revision_feedback(report, review, check, proposal):
    """Keep failed judgments once; no full checker or successful-review dump."""
    return {
        'previous_report_hash': digest(report),
        'previous_selection': copy.deepcopy(report.get('selection',{})),
        'exact_report_items':copy.deepcopy(report.get('items',{})),
        'statement_reviews': {i:copy.deepcopy(v) for i,v in review['items'].items()
            if v['decision']!='ACCEPT' or v.get('serious_error') or not v.get('important_content_complete') or v.get('error_types')},
        'comparison_reviews':{i:copy.deepcopy(v) for i,v in review.get('comparisons',{}).items()
            if v['decision']!='ACCEPT' or v.get('serious_error') or v.get('error_types')},
        'source_disagreements': copy.deepcopy(review.get('source_disagreements', [])),
        'source_record_reviews': copy.deepcopy(review.get('source_records',{})),
        'source_record_candidates': copy.deepcopy(proposal.get('source_records',{})),
        'coverage_review': copy.deepcopy(review['whole_source_coverage']),
        'program_problems': copy.deepcopy(check['problems']),
        'previous_obligations': {i:{k:t[k] for k in ('section','scope_id','importance','question_basis_refs','proposition')} for i,t in proposal['tasks'].items() if t.get('role','REPORT')=='REPORT'},
        'instruction': (
            'Re-read originals for every flagged statement, missing section and '
            'source-linked omission. Preserve supported opposing positions and '
            'important prior obligations; do not blindly trust either report or '
            'review. Correct source attribution/bindings if warranted. A well '
            'supported unresolved or conditional answer is valid. Do not replace '
            'this task with another catalogue of every supplied statute.'),
    }


def feedback_for_stage(feedback,target):
    """Upstream reassessment receives questions and original refs, not old answers."""
    if not feedback:return None
    items=[]
    for group in ('statement_reviews','comparison_reviews'):
        for ident,v in feedback.get(group,{}).items():
            if (v.get('repair_target')==target or target=='USES' and v.get('repair_target')=='REPORT') and v.get('revision_class')=='ALLOWED_SOURCE_ERROR':
                items.append({'reported_item':ident,'question':v['reason'],'refs':v['revision_refs']})
            elif target=='REPORT' and v.get('decision')=='REJECT' and v.get('revision_class')=='NO_CORRECTION_REQUIRED':
                items.append({'reported_item':ident,'question':'Resolve the disagreement between rejection and no requested correction. Reread the cited record; unsupported material may remain unresolved. Reviewer reason: '+v['reason'],'refs':v.get('refs',[]),'contradictory_review_not_assumed_correct':True})
    if target in ('SOURCE_RECORDS','OBJECTS'):
        evidence=list(feedback.get('initial_source_record_reviews',{}).items())+list(feedback.get('source_record_reviews',{}).items())
        for ident,row in evidence:
            if target=='OBJECTS' and not any(f['field'] in ('source_owner','owner_label','participant_roles','actors','court') for f in row.get('field_findings',[])):continue
            if row.get('decision')!='ACCEPT' or row.get('field_findings') or any(v!='AGREES' for v in row.get('reading_alignment',{}).values()):
                candidate=feedback.get('source_record_candidates',{}).get(ident,{})
                items.append({'reported_record':ident,'question':row['reason'],'refs':row.get('refs',[]),
                    'field_findings':row.get('field_findings',[]),'reading_alignment':row.get('reading_alignment'),
                    'candidate_values':{f['field']:candidate.get(f['field']) for f in row.get('field_findings',[])},
                    'review_is_fallible_not_replacement_truth':True})
    if target in ('SOURCE_RECORDS','OBJECTS','SCOPES'):
        for ident,row in feedback.get('statement_reviews',{}).items():
            if row.get('repair_target')==target:
                for rid in row.get('affected_record_ids',[]):
                    items.append({'reported_record':rid,'reported_item':ident,'question':row['reason'],
                                  'refs':row.get('revision_refs',[]),'not_a_corrected_answer':True})
    for row in feedback.get('coverage_review',{}).get('omissions',[]):
        if row.get('repair_target')==target and row.get('information_target')=='ALLOWED_RECORD':
            items.append({k:row[k] for k in ('question','refs','basis')})
    for row in feedback.get('mechanical_source_questions',[]):
        if row.get('repair_target')==target:items.append({k:row[k] for k in ('question','refs','basis')})
    return {'source_linked_questions':items,'not_corrected_answers':True} if items else None


def report_content(report):
    """Surface content used to detect ineffective revisions, excluding meta verdicts."""
    return {group:sorted([{k:v[k] for k in ('include','text','refs')} for v in report.get(group,{}).values()],key=lambda x:json.dumps(x,sort_keys=True))
            for group in ('items','comparisons')}


def canonical_id_sets(value, schema):
    """Only repeated identical IDs in declared set fields; preserve a change ledger.

    No text correction, ID replacement, truncation, JSON completion, or verdict
    change. Array ordering is retained at first occurrence. Every raw item must
    already be a member of the declared enum, so unknown IDs cannot disappear.
    """
    changes=[]
    def visit(v,s,path):
        if 'anyOf' in s:
            from schema_contract import violations
            matches=[]
            for branch in s['anyOf']:
                start=len(changes)
                candidate=visit(v,branch,path)
                delta=changes[start:];del changes[start:]
                if not violations(candidate,branch):matches.append((candidate,delta))
            if len(matches)==1:
                candidate,delta=matches[0];changes.extend(delta);return candidate
            # Ambiguous or invalid unions retain the raw value for validation.
            return v
        if isinstance(v,dict) and s.get('type')=='object':
            return {k:visit(x,s.get('properties',{}).get(k,{}),path+'/'+k) for k,x in v.items()}
        if isinstance(v,list) and s.get('type')=='array':
            item=s.get('items',{});out=[visit(x,item,path+'/'+str(i)) for i,x in enumerate(v)]
            if s.get('uniqueItems') and item.get('type')=='string' and 'enum' in item and all(isinstance(x,str) and x in item['enum'] for x in out):
                unique=list(dict.fromkeys(out))
                if len(unique)!=len(out):changes.append({'path':path,'raw_ids':out,'canonical_ids':unique})
                return unique
            return out
        return v
    return visit(value,schema,'$'),changes


class BlankNoProgress(RuntimeError):
    pass


class RepeatedTextNoProgress(RuntimeError):
    pass


class ProgressWriter:
    """Save raw chunks; abort a long repeated block in one unclosed string.

    A detector is an abnormal-stop policy, not a semantic correction. It neither
    edits JSON nor treats the prefix as a usable answer. Reusing a source across
    separate arrays is legal. Repeating one source eight times inside a single
    array is stalled enumeration and aborts with the raw prefix preserved.
    """
    def __init__(self,out,limit,repetition_min_chars=2048,repetition_min_repeats=8,repetition_window_chars=32768):
        self.out=out;self.limit=limit;self.run=0;self.longest=0
        self.in_string=False;self.escaped=False;self.characters=0
        self.string_raw='';self.last_string_length=None;self.completed_strings=0
        self.string_length=0;self.repetition=None
        self.repeat_min=repetition_min_chars;self.repeat_count=repetition_min_repeats
        self.repeat_window=repetition_window_chars
        self.json_containers=[]
    def check_repetition(self):
        tail=self.string_raw[-self.repeat_window:]
        # Sentence repetitions detect V19's failure even across wire chunks.
        sentences=re.findall(r'[^.!?\n]{80,}[.!?](?:\s|$)',tail)
        counts=Counter(' '.join(s.split()) for s in sentences)
        for sentence,count in counts.items():
            if count>=self.repeat_count and len(sentence)*count>=self.repeat_min:
                self.repetition={'kind':'REPEATED_SENTENCE','count':count,
                    'block_characters':len(sentence),'block_hash':digest(sentence)}
                raise RepeatedTextNoProgress('REPEATED_PROSE_IN_UNCLOSED_JSON_STRING')
        # Covers repeated paragraphs with no sentence terminator. Compare exact
        # contiguous periods; do not infer semantic repetition from vocabulary.
        if len(tail)<self.repeat_min:return
        anchor=tail[-128:];end=len(tail)-128;at=tail.rfind(anchor,0,end)
        while at>=max(0,end-4096):
            period=end-at
            if period>=80 and period*self.repeat_count>=self.repeat_min and len(tail)>=period*self.repeat_count:
                block=tail[-period:]
                if tail[-period*self.repeat_count:]==block*self.repeat_count:
                    self.repetition={'kind':'PERIODIC_BLOCK','count':self.repeat_count,
                        'block_characters':period,'block_hash':digest(block)}
                    raise RepeatedTextNoProgress('REPEATED_PROSE_IN_UNCLOSED_JSON_STRING')
            if at==0:break
            at=tail.rfind(anchor,0,at)
    def write(self,text):
        result=self.out.write(text);self.out.flush()
        for char in text:
            self.characters+=1
            if self.in_string:
                self.run=0
                self.string_length+=1
                if self.escaped:self.escaped=False;self.string_raw+=char
                elif char=='\\':self.escaped=True;self.string_raw+=char
                elif char=='"':
                    self.in_string=False;self.completed_strings+=1
                    try:
                        completed=json.loads('"'+self.string_raw+'"')
                        self.last_string_length=len(completed)
                        if (self.json_containers and self.json_containers[-1]['kind']=='array'
                            and re.fullmatch(r'IKWEB-[0-9]+:L[0-9]+',completed)):
                            counts=self.json_containers[-1]['source_counts']
                            counts[completed]+=1
                            if counts[completed]>=self.repeat_count:
                                self.repetition={'kind':'SOURCE_ID_REPEATED_IN_ONE_ARRAY',
                                    'source_id':completed,'count':counts[completed]}
                                raise RepeatedTextNoProgress('SOURCE_ID_REPEATED_IN_ONE_ARRAY')
                    except ValueError:self.last_string_length=None
                    self.string_raw=''
                else:self.string_raw+=char
                if self.in_string and self.string_length%256==0:
                    self.check_repetition()
            elif char=='"':self.in_string=True;self.run=0;self.string_raw='';self.string_length=0
            elif char in '[{':
                self.run=0
                self.json_containers.append({'kind':'array' if char=='[' else 'object','source_counts':Counter()})
            elif char in ']}':
                self.run=0
                if self.json_containers:self.json_containers.pop()
            elif char in ' \t\r\n':
                self.run+=1;self.longest=max(self.longest,self.run)
                if self.run>=self.limit:raise BlankNoProgress('OUTSIDE_STRING_WHITESPACE_WITHOUT_CONTENT_PROGRESS')
            else:self.run=0
        return result
    def flush(self):self.out.flush()
    def diagnostic(self):
        return {'characters_examined':self.characters,'outside_string_whitespace_run':self.run,
            'longest_whitespace_run':self.longest,'in_string':self.in_string,
            'completed_strings':self.completed_strings,'last_completed_string_characters':self.last_string_length,
            'repetition':self.repetition,'repetition_is_not_semantic_validation':True,
            'provider_internals_known':False,'raw_content_preserved':True}


def hosted_decoder_schema(schema):
    """Omit only redundant set cardinality from hosted grammar compilation.

    For N distinct allowed strings, uniqueItems implies at most N elements.
    Prompt and local semantic validation retain the explicit bound. Existing
    streaming loop detection remains active. No model values are repaired here.
    """
    compiled = decoder_schema(schema)
    def visit(node):
        if isinstance(node, list):
            return [visit(x) for x in node]
        if not isinstance(node, dict):
            return node
        out = {k: visit(v) for k, v in node.items()}
        item = out.get('items', {})
        choices = item.get('enum') if isinstance(item, dict) else None
        if (out.get('type') == 'array' and out.get('uniqueItems') is True
            and isinstance(choices, list) and all(isinstance(x, str) for x in choices)
            and len(set(choices)) == len(choices)
            and out.get('maxItems') == len(choices)):
            del out['maxItems']
        return out
    return visit(compiled)


def request_wire(request,cfg,attempt=0):
    """Keep prompt/source bytes; compile an equivalent hosted decoding contract."""
    system=request['policy']+'\n'+request['task']
    system+='\nReturn one complete JSON object using this schema:\n'+json.dumps(compact_schema(request['schema']),ensure_ascii=False,separators=(',',':'))
    # Retry identity is a transport property. Do not change the model's prompt.
    wire={**cfg['parameters'],'max_tokens':request.get('output_token_cap',cfg['parameters']['max_tokens']),'messages':[{'role':'system','content':system},
        {'role':'user','content':json.dumps(request['material'],ensure_ascii=False,separators=(',',':'))}],
        'response_format':{'type':'json_schema','json_schema':{'name':'legal_stage','schema':hosted_decoder_schema(request['schema'])}},
        'chat_template_kwargs':{'enable_thinking':False}}
    if cfg.get('capacity_diagnostic'):
        capacity=cfg['diagnostic_output_tokens']
        if cfg.get('omit_max_tokens') or type(capacity) is not int or not 2048<capacity<cfg['context_length']:
            raise ValueError('EXPLICIT_DIAGNOSTIC_OUTPUT_CAPACITY_REQUIRED')
        if wire['max_tokens']!=capacity:raise ValueError('STAGE_OUTPUT_CAPACITY_MISMATCH')
        if wire.get('context_length_exceeded_behavior')!='error':raise ValueError('SOURCE_TRUNCATION_NOT_ALLOWED')
    return wire


def bind_review_addresses(tag,value,subjects,snapshot):
    """Deterministic addresses of the MODEL-CHOSEN witnesses and exact subjects.

    Never changes decision, reason, evidence selection, body meaning or any legal
    proposition. The original provider value and this mapping are saved separately.
    """
    from common import resolve_witnesses, SCOPE_FIELDS
    from contracts import OMISSION_CLASSES, USE_MODES
    result=copy.deepcopy(value);changes=[];tag=tag.removeprefix('repair-')
    fields=SCOPE_FIELDS
    def refs(rec,key):
        return list(dict.fromkeys(w['ref'] for w in resolve_witnesses(rec.get(key,[]),snapshot) if w))
    def omissions(coverage):
        for i,row in enumerate(coverage.get('omissions',[])):
            cls,target=OMISSION_CLASSES[row['finding_class']]
            row.update(classification=cls,information_target=target)
            changes.append({'operation':'EXPAND_SELECTED_ENUM','index':i,'selection':row['finding_class'],'classification':cls,'information_target':target})
    if tag.startswith('source-record-review-'):
        for ident,row in result.items():
            row['refs']=list(dict.fromkeys(row.get('refs',[])+refs(row,'witnesses')))
            changes.append({'operation':'RESOLVE_SOURCE_RECORD_REVIEW_WITNESSES','subject':ident,'refs':row['refs']})
    elif tag in ('scopes','scopes-patch','direct-scopes'):
        from common import time_registry
        choices=time_registry(snapshot)
        scope_rows=list(result['replacements'].values())+result['additions'] if tag=='scopes-patch' else result['scopes']
        for row in scope_rows:
            choice=row.pop('time_choice')
            value=choices.get(choice,{'time':'UNKNOWN','time_precision':'UNKNOWN','time_witnesses':[]})
            row.update({k:copy.deepcopy(value[k]) for k in ('time','time_precision','time_witnesses')})
            row['time_choice']=choice
            if choice!='UNKNOWN':row['refs']=list(dict.fromkeys(row['refs']+[value['ref']]))
            changes.append({'operation':'BIND_MODEL_SELECTED_LITERAL_DATE','choice':choice,'not_event_acceptance':True})
    elif tag in ('tasks','direct-report-outline'):
        for ident,row in result['tasks'].items():
            kind,rule=row.pop('kind_rule').split(':',1)
            row.update(kind=kind,rule_id=rule)
            changes.append({'operation':'EXPAND_SELECTED_TASK_MODE','subject':ident,'kind':kind,'rule_id':rule})
    elif tag.startswith('uses-'):
        for tid,part in result.items():
            for n,row in enumerate(part['uses']):
                rid,mode=row.pop('source_record_mode').split('|',1);row['source_record_id']=rid;row.update(USE_MODES[mode])
                changes.append({'operation':'EXPAND_MODEL_SELECTED_USE_MODE','subject':tid,'index':n,'selection':mode})
    elif tag in ('report','report-revision') and any('text' in r for r in result.get('comparisons',{}).values()):
        for hid,row in result.get('comparisons',{}).items():
            h=subjects[hid];row['include']=row['disposition']=='USED'
            row['refs']=list(dict.fromkeys(h['history_refs']+h['case_refs']+h.get('authority_refs',[]))) if row['include'] else []
            changes.append({'operation':'BIND_COMPARISON_DISPOSITION_AND_EXISTING_SOURCE_PACKET','subject':hid,'include':row['include'],'refs':row['refs'],'model_text_unchanged':True})
    elif tag.startswith(('use-review-','analogy-review-','task-review-')):
        for ident,parts in result.items():
            for part,row in parts.items():
                if 'witnesses' in row:
                    row['refs']=list(dict.fromkeys(row.get('refs',[])+refs(row,'witnesses')))
                    changes.append({'operation':'RESOLVE_SELECTED_SOURCE_WITNESSES','subject':ident,'part':part,'refs':row['refs']})
    elif tag.startswith('identity-'):
        for ident,row in result.items():
            row['refs']=refs(row,'identity_witnesses')
            changes.append({'operation':'RESOLVE_SELECTED_WITNESS_SOURCE_IDS','subject':ident,'refs':row['refs']})
    elif tag.startswith('scope-review-'):
        for ident,parts in result.items():
            for part,row in parts.items():
                row['refs']=refs(row,'witnesses')
                row['assessed']={k:copy.deepcopy(subjects[ident][k]) for k in fields[part]}
                row['binding_origin']='EXACT_IMMUTABLE_REQUEST_SUBJECT_NOT_MODEL_COPY'
                changes.append({'operation':'BIND_EXACT_REQUEST_SUBJECT_AND_SELECTED_WITNESSES','subject':ident,'part':part,'refs':row['refs'],'assessed':row['assessed']})
    elif tag.startswith('final-review-'):
        for ident,row in result.get('source_records',{}).items():
            row['refs']=list(dict.fromkeys(row.get('refs',[])+refs(row,'witnesses')))
            changes.append({'operation':'RESOLVE_FINAL_SOURCE_RECORD_WITNESSES','subject':ident,'refs':row['refs']})
        for group in ('items','comparisons'):
            for ident,row in result.get(group,{}).items():
                row['refs']=list(dict.fromkeys(row['reviewed_refs']+refs(row,'witnesses')))
                if group=='comparisons':
                    row['refs']=list(dict.fromkeys(row['refs']+refs(row,'history_witnesses')+refs(row,'case_witnesses')))
                    decisions={'OMISSION_JUSTIFIED':'ACCEPT','OMISSION_UNJUSTIFIED':'REJECT','OMISSION_UNRESOLVED':'UNRESOLVED'}
                    if row['decision'] in decisions:
                        row['omission_assessment']=row['decision'];row['decision']=decisions[row['decision']]
                changes.append({'operation':'RESOLVE_REVIEWED_AND_SELECTED_WITNESS_SOURCE_IDS','subject':ident,'group':group,'refs':row['refs']})
        if 'whole_source_coverage' in result:omissions(result['whole_source_coverage'])
    elif tag.startswith('coverage-final-'):
        omissions(result)
    return result,changes
