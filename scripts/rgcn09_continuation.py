"""V09 continuation: immutable source/split assembly; never fits a model.

Qualification and allowed ranges are explicit source-review decisions. Allocation
only sees mechanism/stage and original candidate rank, not labels or verdicts.
"""
import copy
import hashlib
import json
import sys
from collections import defaultdict, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_identity_v2 import validate_view

ROOT = Path('outputs/rgcn-data-expansion-09/continuation-01')
MECHANISMS = ['family_occupation', 'control_exclusive_possession',
              'partnership_company', 'amalgamation', 'statutory_succession',
              'licence_sublease', 'written_consent', 'temporal_applicability']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    text = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    if path.exists():
        if path.read_text() != text:
            raise ValueError('IMMUTABLE_OUTPUT_EXISTS: ' + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def allowed_view(document, ranges, case_metadata):
    """Copy exact source substrings; no summarization or inferred missing text."""
    segments = []
    for source in document['segments']:
        for interval in ranges:
            first, last = interval[:2]
            if not first <= source['original_line'] <= last:
                continue
            s = copy.deepcopy(source)
            s['source_segment_id'] = source['id']
            s['start'] = 0
            s['end'] = len(s['text'])
            if len(interval) == 3:
                # Explicit reviewed character boundary, never a keyword guess.
                s['end'] = interval[2]
                s['text'] = s['text'][:s['end']]
            if s['text'].strip():
                segments.append(s)
    view = dict(case_metadata, case_id=document['document_id'], segments=segments)
    mapping = validate_view(view, document)
    return view, mapping


def allocate(qualified, existing_groups=None):
    """Round-robin strata and TRAIN/TRAIN/SEALED, pre-annotation.

    Sorted stage order is the deterministic refinement of the frozen stage
    round-robin rule. Unknown associations remain unknown, not independence.
    """
    groups = dict(existing_groups or {})
    queues = defaultdict(deque)
    for row in sorted(qualified, key=lambda r:(r['rank'], int(r['case_id']))):
        if row['decision'] != 'QUALIFIED_MAIN':
            continue
        queues[(row['mechanism'], row['stage'])].append(row)
    keys = sorted(queues, key=lambda k:(MECHANISMS.index(k[0]), k[1]))
    order = []
    while any(queues.values()):
        for key in keys:
            if queues[key]:
                order.append(queues[key].popleft())
    output = []
    cycle = ['TRAIN', 'TRAIN', 'SEALED_TEST']
    index = 0
    for row in order:
        row = copy.deepcopy(row)
        group = row['group_id']
        if group in groups:
            row['split'] = groups[group]
            row['allocation_reason'] = 'Known dispute retained in its existing split'
        else:
            row['split'] = cycle[index % 3]
            groups[group] = row['split']
            row['allocation_reason'] = 'Frozen mechanism/stage round-robin and TRAIN/TRAIN/SEALED cycle'
            index += 1
        row['allocation_index'] = len(output)
        output.append(row)
    return output


def no_training_factory(kind, unit_ids):
    """Use existing S/B/C architecture, explicit current pool dimensionality.

    Construction is a numerical-interface check, never a trained result.
    Frozen V08 source and its default-14 fit entry remain untouched.
    """
    from legal_bench.rules_verdict_v1.rgcn_use_v1 import UseModel
    if len(unit_ids) != len(set(unit_ids)) or not unit_ids:
        raise ValueError('INVALID_POOL')
    return UseModel(kind, units=len(unit_ids))


def assemble_sources():
    from legal_bench.rules_verdict_v1.source_identity_v2 import parse_responses, merge_windows
    spec = json.loads((ROOT/'source-range-decisions.json').read_text())
    candidate_order = json.loads((ROOT/'public-candidate-order.json').read_text())
    ranks = {r['case_id']:100+r['saved_rank'] for r in candidate_order}
    missing_rank = sorted(r['case_id'] for r in spec['cases'] if r['case_id'] not in ranks)
    rows, documents, views, mappings = [], {}, {}, {}
    for row in spec['cases']:
        cid = row['case_id']
        if cid == '186379114':
            raw = ROOT/'open-186379114-80.txt'
            document = merge_windows(parse_responses(raw.read_text(), raw))[cid]
        elif cid in ('183917167', '12668753'):
            responses = []
            paths = list(ROOT.glob('open-'+cid+'-*.txt'))
            if cid == '183917167': paths.append(ROOT/'open-initial-extra.txt')
            for raw in sorted(paths): responses.extend(parse_responses(raw.read_text(),raw))
            document = merge_windows(responses)[cid]
        else:
            document = json.loads((ROOT/'documents'/(cid+'.json')).read_text())
        metadata = {'split':'UNALLOCATED',
            'input_scope':spec['general_scope'],
            'coverage_limits':['Retrospective source-conditioned retrieval, not pre-litigation prediction.',
                               'Eligibility review is not complete semantic annotation.',
                               'Broader dispute association is unconfirmed.']}
        view, mapping = allowed_view(document,row['allowed_ranges'],metadata)
        documents[cid], views[cid], mappings[cid] = document, view, mapping
        rows.append(dict(row, group_id='NEW-'+cid, decision='QUALIFIED_MAIN',
            rank=ranks[cid] if cid in ranks else 50+missing_rank.index(cid),
            qualification_reason='Current proceedings directly concern Delhi1958s14(1)(b); not mere precedent citation.',
            qualification_refs=[s['id'] for s in view['segments'] if '14(1)' in s['text'] or '14 (1)' in s['text']][:4] or [view['segments'][0]['id']],
            prior_role='QUALIFICATION_ONLY_NO_METHOD_USE',
            association='NO_KNOWN_CROSS_SPLIT_LINK_FOUND; broader links unconfirmed',
            source_title=document['titles'][0],url=document['url']))
    base=ROOT.parent
    for cid,mechanism in [('84124','licence_sublease'),('190527224','control_exclusive_possession')]:
        inherited=base/'target-source-screen/allowed'/(cid+'.json')
        views[cid]=json.loads(inherited.read_text())
        rows.append({'case_id':cid,'group_id':'NEW-'+cid,'decision':'QUALIFIED_MAIN',
            'mechanism':mechanism,'stage':'SC_APPEAL','rank':int(cid),
            'qualification_reason':'Explicit restored qualification decision, no prior method use.',
            'qualification_refs':[views[cid]['segments'][0]['id']],
            'prior_role':'QUALIFICATION_ONLY_NO_METHOD_USE',
            'association':'NO_KNOWN_CROSS_SPLIT_LINK_FOUND; broader links unconfirmed',
            'url':'https://indiankanoon.org/doc/'+cid+'/', 'inherited_view':str(inherited)})
    old=json.loads((base/'split-manifest.json').read_text())['cases']
    old=[r for r in old if r['split'] in ('TRAIN','DEVELOPMENT')]
    allocated=allocate(rows,{r['group_id']:r['split'] for r in old})
    for row in allocated:
        cid=row['case_id']; branch=ROOT/'sealed' if row['split']=='SEALED_TEST' else ROOT/'freeze'
        view=copy.deepcopy(views[cid]); view['split']=row['split']
        save(branch/'allowed'/(cid+'.json'),view)
        if cid in documents:
            save(ROOT/'freeze/full'/(cid+'.json'),documents[cid])
            save(branch/'mappings'/(cid+'.json'),mappings[cid])
            row['full_source']=str(ROOT/'freeze/full'/(cid+'.json'))
            row['full_source_sha256']=digest(row['full_source'])
        row['allowed_source']=str(branch/'allowed'/(cid+'.json'))
        row['allowed_sha256']=digest(row['allowed_source'])
        row['data_ready']=('SOURCE_READY; graph/label pending' if row['split']=='TRAIN'
                           else 'RESERVED_SOURCE_ONLY; no labels/features/development feedback')
    save(ROOT/'qualified-candidates.json',rows)
    save(ROOT/'split-manifest.json',{'cases':old+allocated,'seed':20261004,
        'allocation_before_labels':True,'method':'Frozen mechanism/stage round-robin; TRAIN/TRAIN/SEALED',
        'independence':'Known linked disputes excluded; broader associations unconfirmed',
        'historical_manifest_preserved':True})
    return allocated


def prepare_tasks():
    from scripts.rgcn09_labels import model_material, INSTRUCTIONS
    pool=json.loads((ROOT.parent/'authority-pool/laws.json').read_text())
    old_conditions=json.loads(Path('outputs/rgcn-ranking-diagnostic-07/pilot/source-reviewed-law-proposals.json').read_text())
    new_conditions=json.loads((ROOT/'web/LAW-NEW16.download.json').read_text())['units']
    by_unit={u['id']:u for u in pool}
    for proposal in new_conditions:
        if proposal['unit_id'] not in by_unit: raise ValueError('UNKNOWN_LAW')
        for condition in proposal['conditions']:
            if condition['quote'] not in by_unit[proposal['unit_id']]['text']:
                raise ValueError('NONEXACT_LAW_QUOTE')
    conditions=old_conditions+new_conditions
    if len({u['unit_id'] for u in conditions})!=30: raise ValueError('POOL_CONDITION_COUNT')
    save(ROOT/'freeze/source-condition-proposals.json',conditions)
    prefix=Path('outputs/rgcn-ranking-development-06/tasks/GRAPH01.txt').read_text().split('MATERIAL')[0]
    prefix=prefix.replace('TASK GRAPH01','TASK V09-GRAPH').replace('all14','all30').replace('All14','All30')
    ledger=[]
    split=json.loads((ROOT/'split-manifest.json').read_text())['cases']
    for row in split:
        cid=row['case_id']
        if row['split']!='TRAIN':continue
        if cid in {r['case_id'] for r in split if r.get('status','').startswith('EXISTING')}:
            # Find frozen old graph by content ID; never modify its assertions.
            proposals=Path('outputs/rgcn-ranking-diagnostic-07/pilot/parsed')
            graph=next(json.loads(f.read_text()) for f in proposals.glob('GRAPH*.json') if str(json.loads(f.read_text())['case_id'])==cid)
            case=json.loads((Path('outputs/rgcn-ranking-diagnostic-07/pilot/sources')/(cid+'.json')).read_text())
            fixed={k:graph[k] for k in ('case_id','needs','objects','facts','relations')}
            view,laws=model_material(case,pool)
            instructions=prefix+'\nSUPPLEMENT ONLY: reuse supplied fixed needs/objects/facts/relations, without re-extraction or edits. Return only case_id, alignments, coverage_limits, using the same alignment interface above. Provide exactly the16 annotation_target_ids; the old14 alignments are preserved and joined offline. Do not include use labels, relevance scores or verdicts. Missing connections remain UNKNOWN.\n'
            material={'case_id':cid,'fixed_graph_input':fixed,'case':view,'authority_candidates':laws,'source_condition_proposals':conditions,'annotation_target_ids':[u['id'] for u in pool if u['id'].startswith('LAW:V09:')]}
            tid='ALIGN-'+cid
            text=instructions+'\nMATERIAL\n'+json.dumps(material,ensure_ascii=False)+'\nEND_OF_INPUT '+tid+'\n'
            path=ROOT/'tasks'/(tid+'.txt');path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists() and path.read_text()!=text:raise ValueError('TASK_CHANGED')
            path.write_text(text);ledger.append({'task_id':tid,'case_id':cid,'role':'INPUT_ALIGNMENT_NO_LABELS','path':str(path),'sha256':digest(path),'status':'PREPARED'})
            continue
        case=json.loads(Path(row['allowed_source']).read_text());view,laws=model_material(case,pool)
        question='Which supplied authorities help analyze the live Delhi DRC1958s14(1)(b) issue shown by this allowed record, respecting the target procedural stage, rival assertions and scope limits? Do not predict the withheld target verdict.'
        common={'case_id':cid,'question':question,'case':view,'authority_candidates':laws}
        label=dict(common,annotation_target_ids=[u['id'] for u in pool])
        graph=dict(common,source_condition_proposals=conditions)
        for role,material,instructions in [('LABEL',label,INSTRUCTIONS),('GRAPH',graph,prefix)]:
            tid=role+'-'+cid;text=instructions+'\nMATERIAL\n'+json.dumps(material,ensure_ascii=False)+'\nEND_OF_INPUT '+tid+'\n'
            path=ROOT/'tasks'/(tid+'.txt');path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists() and path.read_text()!=text:raise ValueError('TASK_CHANGED')
            path.write_text(text);ledger.append({'task_id':tid,'case_id':cid,'role':'SUPERVISION' if role=='LABEL' else 'INPUT_NO_LABELS','path':str(path),'sha256':digest(path),'status':'PREPARED'})
    save(ROOT/'prepared-task-ledger.json',ledger)
    return ledger


if __name__ == '__main__':
    if sys.argv[1:] == ['assemble-sources']:
        from collections import Counter
        rows=assemble_sources()
        print(dict(Counter(r['split'] for r in rows)), 'new cases')
    elif sys.argv[1:] == ['prepare-tasks']:
        print(len(prepare_tasks()), 'tasks; SEALED omitted; no training')
    else:
        raise SystemExit('Use assemble-sources; no training entry exists in this stage.')
