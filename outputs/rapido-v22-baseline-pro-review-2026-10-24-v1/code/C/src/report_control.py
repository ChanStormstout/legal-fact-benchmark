"""Selection and exact rendering of reviewed records; never supplies legal answers.

The Qwen report call chooses existing records. A prose conclusion cannot bypass
its dependencies by calling itself UNKNOWN or CONDITIONAL. All selected source
interpretations still come from the counted experimental model and may be wrong.
"""
import copy
from common import digest, task_review_ok, refs_valid


def catalog(snapshot, p, accepted, computed):
    rows = {}
    for rid, result in accepted.get('source_records',{}).items():
        if not result['report_eligible']:continue
        rec=p['source_records'][rid]
        # Preserve the record's own event/procedure; never rewrite it into task scope.
        parties='; '.join(p['objects'][r['object_id']]['name']+' ('+r['role']+')' for r in rec['participant_roles']) or 'not specified in this record'
        properties='; '.join(p['objects'][i]['name'] for i in rec['properties']) or 'not specified in this record'
        court=p['objects'].get(rec['court'],{}).get('name','unresolved')
        text=(rec['owner_label']+' ['+rec['status']+']: '+rec['text']+
              '\nRecorded scope: '+rec['event']+'; '+rec['time']+' ['+rec['date_role']+']; '+rec['procedure']+'. Court: '+court+'. Participants: '+parties+'. Property: '+properties+'.')
        rows[rid]={'task_id':None,'source_use_id':rid,'source_record_id':rid,'text':text,
            'refs':list(rec['refs']),'origin':'REVIEWED_SOURCE_RECORD','source_owner':rec['source_owner'],
            'status':rec['status'],'state':'UNKNOWN','content_role':rec['content_role'],
            'source_record_hash':digest(rec),'record_scope':{k:rec[k] for k in ('actors','properties','participant_roles','event','time','date_role','procedure','court','court_position')}}
    for pid, result in computed['paths'].items():
        path = p['paths'][pid]
        refs = list(path['authority_refs'])
        for tid in path['supports'] + path['gates'] + path['blockers']:
            refs += [r for uid, u in p['uses'].items() if u['task_id'] == tid
                     and accepted['uses'][uid]['bundle_eligible'] for r in u['refs']]
        deps=result['dependencies']
        descriptions=[p['tasks'][i]['proposition']+' = '+computed['task_states'].get(i,'UNKNOWN') for i in deps]
        text=('Declared argument question: '+p['tasks'][result['task_id']]['proposition']+
              '\nFrozen calculation: '+result['state']+'. Conditions: '+'; '.join(descriptions)+
              '. Controlling gate: '+result['gate_state']+'; countercondition: '+result['blocker_state']+'.'+
              (' Qualification failures: '+', '.join(result['reasons'])+'.' if result['reasons'] else '')+
              ' This describes only the declared argument calculation, not the entire case or independent legal approval.')
        rows[pid] = {'task_id': result['task_id'], 'text': text,
                    'refs': list(dict.fromkeys(refs)), 'origin': 'COMPUTED_LOCAL_PATH',
                    'source_owner': 'NONE', 'certificate_hash': digest(result)}
    for rid, result in computed.get('requests', {}).items():
        # Include actual computed blockers/unknowns without inventing a favorable
        # result; the exact state, namespace and dependencies remain attached.
        request = p['requests'][rid]
        refs = list(request['authority_refs'])
        for tid in request['gates'] + request['blockers']:
            refs += p['tasks'][tid]['question_basis_refs']
        conditional = computed.get('conditional_not_actual') or result.get('conditional')
        rows[rid] = {'task_id': result['task_id'], 'text':
            ('Hypothetical branch, not actual evidence. ' if conditional else '') +
            'Frozen-rule calculation for declared request '+request['name']+' ['+rid+']: ' + result['outcome'] +
            '. This result applies only to the declared request, premises and rules; it is not the entire case outcome.',
            'refs': list(dict.fromkeys(refs)), 'origin': 'COMPUTED_REQUEST', 'source_owner': 'NONE',
            'certificate_hash': digest(result)}
    for tid,t in p['tasks'].items():
        state=computed['task_states'].get(tid,'UNKNOWN')
        if state not in ('UNKNOWN','CONFLICTED'):continue
        rejected=[{'use_id':uid,'reasons':u['report_reasons']+u['premise_reasons']} for uid,u in accepted['uses'].items() if u['task_id']==tid and not u['bundle_eligible']]
        rule=computed['rules'].get(tid,{})
        detail='; '.join(sorted({reason for u in rejected for reason in u['reasons']}|set(rule.get('reasons',[]))))
        rows['GAP:'+tid]={'task_id':tid,'text':'Open analysis question: '+t['proposition']+'\nComputed state: '+state+
            ('. Blocked dependencies: '+detail if detail else '. No qualified complete premise or rule result is available')+
            '. This is an analysis limitation, not a claim that the original source or judgment is absent.',
            'refs':list(t['question_basis_refs']),'origin':'COMPUTED_GAP','source_owner':'NONE',
            'certificate_hash':digest({'state':state,'rejected':rejected,'rule':rule}), 'state':state}
    for ident,row in rows.items():row['record_id']=ident
    return rows


def report_dependencies(p):
    """Declared question dependencies, not evidence or truth certificates.

    An internal predicate may inform a report about its selected rule. Paths and
    requests contribute their explicit edges. Cross-scope edges are excluded.
    No lexical matching or whole-case expansion supplies missing relationships.
    """
    tasks=p['tasks'];graph={tid:set() for tid in tasks}
    def edge(parent,child):
        if parent in tasks and child in tasks and tasks[parent]['scope_id']==tasks[child]['scope_id']:
            graph[parent].add(child)
    for tid,t in tasks.items():
        for cid,c in tasks.items():
            if t.get('role','REPORT')=='REPORT' and set(t.get('obligation_ids',[])) & set(c.get('informs_obligation_ids',[])):
                edge(tid,cid)
        if t['kind']=='DERIVED' and t['rule_id']!='NONE':
            for cid,c in tasks.items():
                if c.get('role')=='PROOF' and c.get('rule_condition','NONE').startswith(t['rule_id']+':'):
                    edge(tid,cid)
    for path in p.get('paths',{}).values():
        for key in ('supports','alternatives','gates','blockers'):
            for cid in path[key]:edge(path['conclusion_task'],cid)
        for ex in path['exceptions']:
            edge(path['conclusion_task'],ex['blocker_task']);edge(path['conclusion_task'],ex['exception_task'])
    for request in p.get('requests',{}).values():
        tid=request['conclusion_task']
        for key in ('gates','blockers'):
            for cid in request[key]:edge(tid,cid)
        for pid in [pid for g in request['grounds'] for pid in g['all_paths']]:
            if pid in p.get('paths',{}):edge(tid,p['paths'][pid]['conclusion_task'])
        for ex in request['exceptions']:
            edge(tid,ex['blocker_task']);edge(tid,ex['exception_task'])
    result={}
    for tid,t in tasks.items():
        if t.get('role','REPORT')!='REPORT':continue
        seen={tid};pending=[tid]
        while pending:
            for cid in sorted(graph[pending.pop()]):
                if cid not in seen:seen.add(cid);pending.append(cid)
        result[tid]=sorted(seen)
    return result


def eligible_records(p,records):
    routes={}
    for tid,deps in report_dependencies(p).items():
        # Selection is allowed to examine all descriptions to recover unallocated
        # important records. That is a candidate set, NOT a coverage certificate.
        routes[tid]=[i for i,r in records.items() if r['origin']=='REVIEWED_SOURCE_RECORD' or r['task_id'] in deps]
    return routes


def comparison_routes(p,h):
    return [tid for tid in h.get('report_task_ids',[]) if tid in report_dependencies(p)]


def comparison_choices(h,accepted,routes):
    # Reasons requiring a source/applicability failure are only offered when
    # that failure actually occurred. Relevance/redundancy remains model judged.
    choices=['NO_MATERIAL_RELEVANCE','REDUNDANT']
    if accepted['report_eligible'] and routes:choices.insert(0,'USED')
    if not accepted.get('source_fidelity_verified',False):choices.append('UNRESOLVED_SOURCE')
    if any('APPLICABILITY' in r or 'LEGAL_EFFECT' in r for r in accepted['reasons']):choices.append('UNRESOLVED_APPLICABILITY')
    if not accepted['report_eligible'] or not routes:choices.append('REJECTED')
    return choices


def selection_schema(snapshot, p, accepted, computed):
    import contracts as C
    records=catalog(snapshot,p,accepted,computed);routed=eligible_records(p,records)
    def comparison(hid):
        h=p['analogies'][hid];routes=comparison_routes(p,h)
        return C.obj({'disposition':C.enum(comparison_choices(h,accepted['analogies'][hid],routes)),
            'report_item_id':C.enum(routes+['NONE']),'reason':C.text(220)})
    return C.obj({'items':C.keyed(C.report_tasks(p['tasks']),lambda tid:C.obj({
        'record_ids':C.picks(routed[tid],12),
        'coverage':C.enum((['COMPLETE'] if routed[tid] else [])+['PARTIAL','UNRESOLVED']),
        'omission_reason':C.text(220)})),
        'comparisons':C.keyed(p.get('analogies',{}),comparison)})


def compile_report(snapshot, p, reviews, accepted, computed, selection):
    """Exact projection of model-selected records, not another source assessment."""
    import contracts as C
    C.validate(selection, selection_schema(snapshot, p, accepted, computed))
    records = catalog(snapshot, p, accepted, computed)
    items = {};seen_records={};seen_notes={}
    def record_key(tid,record):
        return digest({'scope':record.get('record_scope',p['tasks'][tid]['scope_id']),**{k:record.get(k) for k in ('text','refs','origin','source_owner','state','status','content_role','source_record_hash','certificate_hash')}})
    # Prefer the source's own report obligation over a consuming summary. A
    # broad summary must not steal all sections' records and leave empty links.
    owners={}
    for direct_only in (True,False):
        for tid,row in selection['items'].items():
            for ident in row['record_ids']:
                record=records[ident]
                if direct_only and record['task_id']!=tid:continue
                owners.setdefault(record_key(tid,record),tid)
    for tid, row in selection['items'].items():
        task = p['tasks'][tid]; selected=[records[i] for i in row['record_ids']];picked=[];also_covered_by=[]
        for record in selected:
            key=record_key(tid,record)
            if owners[key]!=tid:
                also_covered_by.append(owners[key]);continue
            if key in seen_records:
                also_covered_by.append(seen_records[key]);continue
            seen_records[key]=tid;picked.append(record)
        also_covered_by=list(dict.fromkeys(also_covered_by))
        body = [x['text'] for x in picked]
        refs = list(dict.fromkeys(r for x in selected for r in x['refs']))
        if row['coverage']=='COMPLETE' and not selected:
            raise ValueError('COMPLETE_REPORT_OBLIGATION_WITHOUT_SELECTED_RECORD')
        note=None
        if row['coverage']!='COMPLETE':
            note='Important content for this report obligation remains unresolved by the analysis. This is not evidence that the original proceedings or a judgment do not exist.'
            if note in seen_notes:also_covered_by.append(seen_notes[note])
            else:seen_notes[note]=tid;body.append(note)
            refs = list(dict.fromkeys(refs + task['question_basis_refs']))
        also_covered_by=list(dict.fromkeys(also_covered_by))
        # A reference-only item is not substantive text and is never sent as a
        # duplicate filler paragraph. The exact records and destinations remain
        # addressable through also_covered_by for source/coverage review.
        items[tid] = {'include': bool(body), 'section': task['section'],
            'text': '\n\n'.join(body) if body else 'OMITTED',
            'kind': 'CONTROLLED_RECORDS' if selected else 'UNKNOWN',
            'attributed_to': 'MULTIPLE_SOURCE_RECORDS' if len(picked) > 1 else picked[0]['source_owner'] if picked else 'NONE',
            'consequence_scope': 'MIXED_CONTROLLED_RECORDS' if any(x['origin'].startswith('COMPUTED_') for x in selected) else 'DESCRIPTION', 'outcome': 'DESCRIPTION' if picked else 'UNRESOLVED',
            'refs': refs, 'support_ids': list(row['record_ids']),
            'segments': copy.deepcopy(picked), 'also_covered_by':also_covered_by,'unresolved_included': note is not None,
            'report_coverage_claim':row['coverage'],'rule_execution_state':computed['task_states'].get(tid,'UNKNOWN'),
            'obligation_ids':list(task.get('obligation_ids',[])),
            'omission_reason': row['omission_reason']}
    comparisons={}
    rendered_current={seg['source_record_id'] for item in items.values() for seg in item['segments'] if 'source_record_id' in seg}
    for hid,row in selection['comparisons'].items():
        h=p['analogies'][hid];used=row['disposition']=='USED';target=row['report_item_id']
        if used and target not in comparison_routes(p,h):raise ValueError('COMPARISON_WITHOUT_REPORT_DESTINATION')
        descriptions=[]
        for aid,a in h['current_assertions'].items():
            rid=a['source_record_id']
            if rid in rendered_current:descriptions.append('See current source record '+rid+' ('+a['speaker']+')')
            else:
                descriptions.append(rid+': '+a['speaker']+' ['+a['attribution']+']: '+a['content'])
                if used:rendered_current.add(rid)
        current='; '.join(descriptions)
        historical='; '.join(a['speaker']+' ['+a['attribution']+']: '+a['content'] for a in h['history_assertions'].values())
        text=('Current record: '+current+'\nHistorical record ('+h['document_id']+'): '+historical+
            '\nMaterial comparison: '+h['similarities']+' Differences: '+h['differences']+
            '\nWarrant: '+h['warrant']+'\nUse ('+h['proposed_use']+'): '+h['limited_use']+
            '\nLimits: '+h['limitations']+'\nApplicability: '+h['law_status']+
            '. Historical facts are not current-case premises.') if used else 'OMITTED'
        comparisons[hid]={**row,'include':used,'text':text,'document_id':h['document_id'],
            'need_id':h['need_id'],'selected_claims':list(h['current_assertions'])+list(h['history_assertions']),
            'permitted_use':accepted['analogies'][hid].get('permitted_use'),
            'assessed_historical_position':h['history_reading']['recorded_position'],
            'eligibility_reasons':accepted['analogies'][hid]['reasons'],
            'refs':list(dict.fromkeys(h['history_refs']+h['case_refs']+h['authority_refs'])) if used else []}
    return {'items': items, 'comparisons': comparisons, 'selection': copy.deepcopy(selection),
            'render_contract': 'V18_RECORD_SCOPE_AND_OBLIGATION_COVERAGE', 'catalog_hash': digest(records),
            'report_dependencies':report_dependencies(p),
            'snapshot_id': snapshot['snapshot_id'], 'namespace': snapshot['namespace']}


def check_exact(snapshot, p, reviews, accepted, computed, report):
    try:
        expected = compile_report(snapshot, p, reviews, accepted, computed, report['selection'])
    except (KeyError, ValueError, TypeError) as exc:
        return ['INVALID_REPORT_SELECTION:' + type(exc).__name__]
    return [] if report == expected else ['REPORT_CHANGED_OUTSIDE_REVIEWED_RECORD_SELECTION']


def coverage_status(coverage, report, inventory, snapshot):
    """Aggregate explicit model coverage assessments, with traceable addresses.

    Passing is not semantic completeness. Missing/unknown decisions cannot become
    complete merely because an optional omissions array was empty.
    """
    results = {}
    for oid, obligation in inventory.get('obligations', {}).items():
        if obligation['importance'] != 'IMPORTANT':
            continue
        row = coverage.get('obligations', {}).get(oid, {})
        ids = row.get('report_item_ids', [])
        included = [report['items'][i] for i in ids if i in report['items'] and (report['items'][i]['include'] or report['items'][i].get('also_covered_by'))
                    and oid in report['items'][i].get('obligation_ids',[])]
        record_ids=set(row.get('answer_record_ids',[]))
        selected_ids={rid for item in included for rid in item.get('support_ids',[])}
        records={segment['record_id']:segment for item in report['items'].values() for segment in item.get('segments',[])}
        # Every referenced record must really be selected for this obligation;
        # semantic correspondence is separately judged by the model, not inferred
        # from overlapping source paragraphs or broad report-section coverage.
        ok=(row.get('status')=='COMPLETE' and bool(included) and bool(record_ids) and
            record_ids<=selected_ids and row.get('answer_relation')!='DOES_NOT_ANSWER' and
            bool(row.get('reason','').strip()) and refs_valid(row.get('refs',[]),snapshot,'CASE'))
        if obligation['answerability']=='KNOWN_RECORD':
            ok=ok and row.get('answer_relation')=='DIRECT_RECORD' and any(
                records.get(rid,{}).get('origin')=='REVIEWED_SOURCE_RECORD' and
                records[rid].get('status') not in ('LIMITATION','HYPOTHETICAL','UNRESOLVED') and
                set(records[rid].get('refs',[])) & set(obligation['refs']) for rid in record_ids)
        results[oid] = {'complete': ok, 'model_status': row.get('status', 'MISSING'),
                        'source_refs': obligation['refs'], 'report_item_ids': ids,'answer_record_ids':sorted(record_ids),'answer_relation':row.get('answer_relation')}
    important_sources = [ref for ref, row in inventory.get('source_dispositions', {}).items()
                         if row['relevance'] == 'IMPORTANT']
    represented = {ref for o in inventory.get('obligations', {}).values() for ref in o['refs']}
    missing = sorted(set(important_sources) - represented)
    return {'obligations': results, 'important_sources_without_obligation': missing,
            'complete': bool(results) and all(x['complete'] for x in results.values()) and not missing,
            'not_independent_semantic_verification': True}
