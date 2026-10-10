"""Unified, resumable research workflow. No model transport or legal approval is implicit.

Input proposals, research acceptance decisions and independent checks remain
separate. Cached runs and external web responses use the same persisted stages.
"""
import copy
import datetime
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .contracts import byte_hash, content_hash, read_json, write_once as _write_once
from .realcase_contracts import schemas, validate, unique
from .realcase_tasks_v2_2 import COMMON, INSTRUCTIONS, EXAMPLE
from .realcase_engine import propose
from .reconstruction_view_v4 import view
from .review_priority_v2 import order

VERSION = 'PROOF_WORKFLOW_V7'
ROOT = Path(__file__).resolve().parents[2]
KINDS = ('rules', 'rule_review', 'facts', 'reference', 'derivation')
DEPENDENCIES = {'rules': (), 'rule_review': ('rules',), 'facts': ('rules',),
                'reference': (), 'derivation': ('rules', 'facts')}
POLICY_FIELDS = ('reviews', 'scope_reviews', 'court_assessments', 'role_mappings',
                 'role_views', 'formal_approval', 'policy_version')


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def write_once(path, value):
    path = Path(path)
    if path.exists():
        if read_json(path) != value:
            raise FileExistsError('IMMUTABLE_RECORD_DIFFERS:' + str(path))
        return
    _write_once(path, value)


def text_once(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text() != value: raise FileExistsError('IMMUTABLE_RECORD_DIFFERS:' + str(path))
        return
    with path.open('x', encoding='utf-8') as f:
        f.write(value)


def event(root, action, **data):
    folder = root / 'events'
    folder.mkdir(exist_ok=True)
    i = len(list(folder.glob('*.json'))) + 1
    write_once(folder / f'{i:05}.json', {'at': now(), 'action': action, **data})


def schema(kind):
    s = copy.deepcopy(schemas(kind))
    # Registry versions are preserved, not rewritten to fit the original v1 enum.
    if kind == 'rules':
        s['properties']['rules']['items']['properties']['version'] = {'type': 'integer', 'minimum': 1}
    # New ingestion is record based. A 31st intact row does not erase 30 rows.
    # This does not change historical contract failures into historical successes.
    for value in s['properties'].values() if kind == 'reference' else []:
        if value.get('type') == 'array':
            value.pop('maxItems', None)
    return s


def contract(kind, value):
    """Isolate malformed top-level records, retaining raw input and every issue."""
    s = schema(kind)
    if not isinstance(value, dict):
        raise ValueError('TOP_LEVEL_OBJECT_REQUIRED')
    expected = s['properties']
    if set(value) != set(expected):
        raise ValueError('TOP_LEVEL_FIELDS_MISMATCH')
    usable, isolated = {}, []
    for key, contract_ in expected.items():
        if contract_.get('type') != 'array':
            validate(value[key], contract_)
            usable[key] = value[key]
            continue
        if not isinstance(value[key], list):
            raise ValueError('ARRAY_REQUIRED:' + key)
        usable[key] = []
        for i, row in enumerate(value[key]):
            try:
                validate(row, contract_['items'])
                usable[key].append(row)
            except (ValueError, KeyError, TypeError) as exc:
                isolated.append({'field': key, 'index': i, 'reason': str(exc), 'original': row})
    # Ambiguous IDs must never silently select one record.
    for key in ('entities', 'premises', 'rules', 'steps', 'requests'):
        if key in usable:
            rows = usable[key]
            duplicate = {x['id'] for x in rows if sum(y['id'] == x['id'] for y in rows) > 1}
            for row in rows:
                if row['id'] in duplicate:
                    isolated.append({'field': key, 'id': row['id'], 'reason': 'DUPLICATE_ID', 'original': row})
            usable[key] = [x for x in rows if x['id'] not in duplicate]
    return usable, isolated


def resolve(base, path):
    p = Path(path)
    return p.resolve() if p.is_absolute() else (base / p).resolve()


def code_paths():
    paths = list((ROOT / 'legal_bench/proof_carrying').glob('*.py'))
    paths += [ROOT / p for p in ('scripts/proof_pipeline_v7.py', 'scripts/check_realcase_certificate_v4.py',
                                'legal_bench/rules_verdict_v1/contracts.py',
                                'legal_bench/irac_application/contract_v5.py',
                                'legal_bench/irac_application/aligned_v2_runtime.py')]
    return sorted(paths)


def initialize(spec_path, destination):
    spec_path, dest = Path(spec_path).resolve(), Path(destination).resolve()
    if dest.exists():
        raise FileExistsError('NEW_WORKSPACE_REQUIRED:' + str(dest))
    spec = read_json(spec_path)
    for key in ('case_id', 'name', 'stage', 'question', 'sources', 'documents'):
        if key not in spec:
            raise ValueError('SPEC_FIELD_MISSING:' + key)
    base = spec_path.parent
    sources = read_json(resolve(base, spec['sources']))
    if not isinstance(sources, dict) or not sources:
        raise ValueError('INDEXED_SOURCES_REQUIRED')
    for ref, s in sources.items():
        if not isinstance(s.get('text'), str) or not s.get('document') or not s.get('url'):
            raise ValueError('SOURCE_PROVENANCE_MISSING:' + ref)
        if str(s['document']) != str(spec['case_id']):
            raise ValueError('TARGET_DOCUMENT_IDENTITY_CONFLICT:' + ref)
        if not (isinstance(s.get('original_line'), int) or isinstance(s.get('start'), int)):
            raise ValueError('SOURCE_POSITION_REQUIRED:' + ref)
    # Resolve and verify every original before creating the workspace.
    originals = []
    for doc in spec['documents']:
        path = resolve(base, doc['path'])
        if byte_hash(path) != doc['sha256']:
            raise ValueError('ORIGINAL_SOURCE_HASH_MISMATCH:' + str(path))
        originals.append(path)
    if not originals:
        raise ValueError('ORIGINAL_SOURCE_REQUIRED')
    indexed = {}
    for original in originals:
        document = read_json(original)
        if str(document.get('document_id')) != str(spec['case_id']):
            raise ValueError('ORIGINAL_DOCUMENT_IDENTITY_CONFLICT')
        for segment in document.get('segments', []):
            ref = segment['id']
            if ref in indexed and indexed[ref]['text'] != segment['text']:
                raise ValueError('ORIGINAL_WINDOW_CONFLICT:' + ref)
            indexed[ref] = segment
    mapping = []
    for ref, source in sources.items():
        original = indexed.get(ref)
        if not original or original['text'] != source['text'] or original['original_line'] != source.get('original_line'):
            raise ValueError('SOURCE_INDEX_DOES_NOT_RESTORE_ORIGINAL:' + ref)
        mapping.append({'id': ref, 'line': original['original_line'],
                        'provenance': original.get('provenance', []), 'text_sha256': content_hash(source['text'])})
    dest.mkdir(parents=True)
    write_once(dest / 'source-map.json', mapping)
    shutil.copyfile(spec_path, dest / 'spec.json')
    write_once(dest / 'sources.json', sources)
    docs = []
    for i, original in enumerate(originals):
        path = dest / 'originals' / f'{i:03}{original.suffix}'
        path.parent.mkdir(exist_ok=True)
        shutil.copyfile(original, path)
        docs.append({'path': str(path.relative_to(dest)), 'sha256': byte_hash(path),
                     'origin': str(original)})
    write_once(dest / 'source-manifest.json', {'documents': docs,
        'source_index_hash': byte_hash(dest / 'sources.json'),
        'identity_basis': spec.get('identity_basis', 'Upstream supplied document identity; semantic verification not automatic'),
        'scope': spec.get('source_scope', 'Supplied complete reconstruction source'),
        'entries': len(sources), 'text_addresses_are_not_semantic_approval': True})
    provenance = {}
    for kind, entry in spec.get('cached', {}).items():
        if kind not in (*KINDS, 'policy'):
            raise ValueError('UNSUPPORTED_CACHE_STAGE:' + kind)
        source = resolve(base, entry['path'])
        folder = dest / 'stages' / kind
        folder.mkdir(parents=True)
        target = folder / 'raw.json'
        shutil.copyfile(source, target)
        meta = {**entry, 'path': str(source), 'sha256': byte_hash(source),
                'transport': 'EXISTING_SAVED_ARTIFACT', 'new_model_call': False}
        write_once(folder / 'provenance.json', meta)
        provenance[kind] = meta
        _import(folder, kind)
    material = {str(p.relative_to(dest)): byte_hash(p) for p in dest.rglob('*') if p.is_file()}
    code = {}
    for p in code_paths():
        rel = p.relative_to(ROOT)
        target = dest / 'freeze/code' / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
        code[str(rel)] = byte_hash(p)
    write_once(dest / 'freeze/config.json', {'version': VERSION, 'created': now(),
        'code_hashes': code, 'initial_material_hashes': material,
        'research_only': True, 'model_policy': 'Existing saved outputs or externally recorded ordinary High; no implicit model call',
        'semantic_repairs': False, 'evaluation_experiment': False,
        'policy_missing': 'Keep available graph and local request results; never auto approve',
        'graph_changes_truth': False, 'parent': spec.get('parent'),
        'approval': 'Separate append-only record; this checker cannot issue formal legal approval'})
    event(dest, 'INITIALIZED', cached=provenance, new_model_calls=0)
    return advance(dest)


def _import(folder, kind):
    raw = (folder / 'raw.json').read_text()
    text = raw.strip()
    operations = []
    if text.startswith('```') and text.endswith('```'):
        text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        operations.append('REMOVE_OUTER_MARKDOWN_FENCE')
    result = {'status': 'FORMAT_ERROR', 'answer': None, 'format_operations': operations,
              'raw_sha256': byte_hash(folder / 'raw.json'), 'semantic_verified': False}
    try:
        value = json.loads(text)
        write_once(folder / 'content.json', value)
        if kind == 'policy':
            if not isinstance(value, dict) or not isinstance(value.get('reviews'), dict):
                raise ValueError('EXPLICIT_RESEARCH_POLICY_REQUIRED')
            usable, isolated = value, []
        else:
            usable, isolated = contract(kind, value)
        write_once(folder / 'usable.json', usable)
        write_once(folder / 'isolated.json', isolated)
        result.update(status='PARTIAL' if isolated else 'IMPORTED', answer='usable.json',
                      isolated_count=len(isolated))
    except (ValueError, TypeError, KeyError) as exc:
        result['error'] = str(exc)
    result['saved_hashes'] = {p.name: byte_hash(p) for p in folder.iterdir() if p.is_file() and p.name != 'import.json'}
    write_once(folder / 'import.json', result)
    return result


def verify(root):
    root = Path(root)
    freeze = read_json(root / 'freeze/config.json')
    for path, h in freeze['code_hashes'].items():
        if byte_hash(ROOT / path) != h or byte_hash(root / 'freeze/code' / path) != h:
            raise ValueError('FROZEN_CODE_CHANGED:' + path)
    for path, h in freeze['initial_material_hashes'].items():
        if byte_hash(root / path) != h:
            raise ValueError('FROZEN_INPUT_CHANGED:' + path)
    for p in (root / 'stages').glob('*/import.json') if (root / 'stages').exists() else []:
        record = read_json(p)
        for name, expected in record['saved_hashes'].items():
            if byte_hash(p.parent / name) != expected:
                raise ValueError('IMPORTED_STAGE_CHANGED:' + str(p.parent / name))
    for p in (root / 'stages').glob('*/task-manifest.json') if (root / 'stages').exists() else []:
        if read_json(p)['prompt_sha256'] != byte_hash(p.parent / 'task.txt'):
            raise ValueError('TASK_CHANGED:' + str(p))
    if (root / 'artifacts.json').exists():
        for path, h in read_json(root / 'artifacts.json')['hashes'].items():
            if byte_hash(root / path) != h:
                raise ValueError('DELIVERED_ARTIFACT_CHANGED:' + path)
    return {'status': 'VERIFIED', 'case_id': read_json(root / 'spec.json')['case_id']}


def load_stage(root, kind):
    p = root / 'stages' / kind / 'import.json'
    if not p.exists():
        return None
    result = read_json(p)
    return read_json(p.parent / result['answer']) if result['answer'] else None


def task(root, kind):
    spec = read_json(root / 'spec.json')
    attachments = {k: load_stage(root, k) for k in DEPENDENCIES[kind]}
    if any(v is None for v in attachments.values()):
        return False
    folder = root / 'stages' / kind
    if (folder / 'task.txt').exists():
        return True
    sources = read_json(root / 'sources.json')
    ordered = sorted(sources.items(), key=lambda x: (x[1]['document'], x[1].get('original_line', x[1].get('start', 0)), x[0]))
    prompt = COMMON + '\nTASK: ' + kind + '\n' + INSTRUCTIONS[kind] + '\n\n' + EXAMPLE
    prompt += '\nCASE: ' + str(spec['case_id']) + ' | ' + spec['name']
    prompt += '\nSTAGE: ' + spec['stage'] + '\nQUESTION: ' + spec['question']
    prompt += '\nTASK ATTACHMENTS:\n' + json.dumps(attachments, ensure_ascii=False, indent=2)
    prompt += '\nCOMPLETE ALLOWED SOURCE:\n' + '\n'.join('[' + ref + '] ' + s['text'] for ref, s in ordered)
    prompt += '\nOUTPUT SCHEMA:\n' + json.dumps(schema(kind), indent=2)
    prompt += '\nEND_OF_TASK\n'
    text_once(folder / 'task.txt', prompt)
    write_once(folder / 'schema.json', schema(kind))
    write_once(folder / 'task-manifest.json', {'prompt_sha256': byte_hash(folder / 'task.txt'),
        'attachment_hash': content_hash(attachments), 'source_index_hash': byte_hash(root / 'sources.json'),
        'source_map': [{'id': ref, 'text_hash': content_hash(s['text']),
                        'task_character_start': prompt.index('[' + ref + '] ' + s['text']),
                        'characters': len('[' + ref + '] ' + s['text'])} for ref, s in ordered],
        'reference_isolation': kind != 'reference' or not attachments,
        'status': 'READY_NOT_SUBMITTED', 'visible_model': None})
    return True


def ingest(root, kind, response, metadata):
    root = Path(root).resolve()
    verify(root)
    if (root / 'complete.json').exists():
        raise ValueError('COMPLETED_WORKSPACE_IMMUTABLE_USE_REVISION')
    folder = root / 'stages' / kind
    if (folder / 'raw.json').exists():
        raise FileExistsError('RESPONSE_EXISTS_NO_RETRY')
    if kind != 'policy' and not (folder / 'task-manifest.json').exists():
        raise ValueError('TASK_NOT_READY')
    meta = read_json(metadata)
    if kind != 'policy' and meta.get('submitted_task_sha256') != byte_hash(folder / 'task.txt'):
        raise ValueError('SUBMISSION_IDENTITY_MISMATCH')
    if not meta.get('origin'):
        raise ValueError('RESPONSE_ORIGIN_REQUIRED')
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(response, folder / 'raw.json')
    write_once(folder / 'provenance.json', meta)
    result = _import(folder, kind)
    event(root, 'INGESTED', stage=kind, status=result['status'])
    return advance(root)


def graph(snapshot, facts, derivation):
    """Typed graph retains all records; only declared signed premise edges are spectral."""
    nodes, edges = {}, []
    def node(kind, key, record):
        nid = kind + ':' + key
        nodes[nid] = {'id': nid, 'kind': kind, 'record_id': key, 'record': record}
        return nid
    def edge(a, b, relation, origin, **extra):
        edges.append({'from': a, 'to': b, 'relation': relation, 'origin': origin, **extra})
    for ref, source in snapshot['sources'].items(): node('SOURCE', ref, source)
    for eid, e in snapshot['entities'].items(): node('ENTITY', eid, e)
    for pid, p in snapshot['premises'].items():
        a = node('PREMISE', pid, p)
        for ref in p['refs']: edge('SOURCE:' + ref, a, 'CITED_AS_BASIS', 'PROPOSAL_NOT_VERIFIED')
        for b in p['bindings']: edge(a, 'ENTITY:' + b['entity'], b['role'], 'PROPOSAL_NOT_VERIFIED')
    for rid, r in snapshot['rules'].items():
        a = node('RULE', rid, r)
        for ref in r['source_refs']: edge('SOURCE:' + ref, a, 'RULE_TRANSLATION_SOURCE', 'RESEARCH_TRANSLATION')
    signed = []
    for e in facts.get('relations', []):
        status = 'ADDRESS_VALID_NOT_SEMANTICALLY_VERIFIED' if (e['from'] in snapshot['premises'] and e['to'] in snapshot['premises'] and e['refs'] and all(r in snapshot['sources'] for r in e['refs'])) else 'UNRESOLVED_ADDRESS'
        edge('PREMISE:' + e['from'], 'PREMISE:' + e['to'], e['sign'], 'INPUT_PROPOSAL', refs=e['refs'], reason=e['reason'], status=status)
        if status.startswith('ADDRESS_VALID'): signed.append(e)
    for s in derivation.get('steps', []):
        a = node('STEP', s['id'], s)
        edge('RULE:' + s['rule_ref'], a, 'APPLIES_RULE', 'PROPOSED_DEPENDENCY')
        for inp in s['inputs']: edge(inp['kind'] + ':' + inp['id'], a, 'CONSUMES_SLOT', 'PROPOSED_DEPENDENCY', slot=inp['slot'])
    for q in derivation.get('requests', []):
        a = node('REQUEST', q['id'], q)
        edge('STEP:' + q['step_id'], a, 'REQUESTS_CONCLUSION', 'PROPOSAL_NOT_VERIFIED')
    dangling = [e for e in edges if e['from'] not in nodes or e['to'] not in nodes]
    priority = order({'premises': list(snapshot['premises'].values()), 'relations': signed})
    priority['scope'] = 'OPERATIONAL_REVIEW_QUEUE_NO_BENEFIT_CLAIM'
    priority['excluded_relations'] = [e for e in facts.get('relations', []) if e not in signed]
    return {'nodes': list(nodes.values()), 'edges': edges, 'dangling': dangling,
            'signed_projection': 'Only source-addressable declared premise relations. Logical dependencies are not votes.',
            'legal_truth_from_graph': False}, priority


def assemble(root, facts, rules, policy):
    spec = read_json(root / 'spec.json')
    rules_by_id = {r['id'] + '@' + str(r['version']): r for r in rules['rules']}
    if len(rules_by_id) != len(rules['rules']):
        raise ValueError('DUPLICATE_RULE_VERSION')
    snap = {'snapshot_id': str(spec['case_id']) + '-' + content_hash({'spec': spec, 'facts': facts, 'rules': rules, 'policy': policy})[:16],
            'case_id': str(spec['case_id']), 'stage': spec['stage'],
            'jurisdiction': spec.get('jurisdiction', 'SOURCE_RECONSTRUCTION'),
            'sources': read_json(root / 'sources.json'),
            'documents': [{k: d[k] for k in ('path', 'sha256')} for d in read_json(root / 'source-manifest.json')['documents']],
            'entities': unique(facts['entities']), 'premises': unique(facts['premises']), 'rules': rules_by_id,
            'reviews': {'premises': {}, 'rules': {}}, 'scope_reviews': {}, 'court_assessments': {},
            'formal_approval': None, 'policy_version': 'MISSING_ACCEPTANCE_POLICY'}
    if policy:
        for k, v in policy.items():
            if k in ('entities', 'premises', 'rules', 'sources', 'case_id', 'stage', 'snapshot_id', 'documents'):
                raise ValueError('POLICY_MUST_NOT_REWRITE_INPUT:' + k)
            snap[k] = copy.deepcopy(v)
    return snap


def advance(root):
    root = Path(root).resolve()
    verify(root)
    if (root / 'complete.json').exists():
        return read_json(root / 'complete.json')
    stage_status = {}
    for kind in KINDS:
        p = root / 'stages' / kind / 'import.json'
        if p.exists(): stage_status[kind] = read_json(p)['status']
        else: stage_status[kind] = 'READY_NOT_SUBMITTED' if task(root, kind) else 'WAITING_DEPENDENCY'
    facts, rules = load_stage(root, 'facts'), load_stage(root, 'rules')
    policy = load_stage(root, 'policy')
    derivation = load_stage(root, 'derivation')
    stage_status['policy'] = 'IMPORTED' if policy else 'REVIEW_PENDING'
    state = {'version': VERSION, 'stages': stage_status, 'new_model_calls_by_runner': 0,
             'case_id': read_json(root / 'spec.json')['case_id']}
    if facts is None or rules is None:
        state['status'] = 'WAITING_INPUT'
        event(root, 'WAITING', **state)
        return state
    # Graph and policy packet can be delivered before a derivation or approval.
    snap = assemble(root, facts, rules, policy)
    rev = len(list((root / 'events').glob('*.json')))
    pending = root / 'previews' / f'{rev:05}'
    g, priority = graph(snap, facts, derivation or {})
    write_once(pending / 'graph.json', g)
    write_once(pending / 'review-queue.json', priority)
    if derivation is None:
        write_once(pending / 'review-packet.json', {'premises': snap['premises'], 'rules': snap['rules'],
            'sources': snap['sources'], 'existing_policy': policy, 'legal_approval': 'PENDING',
            'template': {'reviews': {'premises': {}, 'rules': {}}, 'scope_reviews': {},
                         'formal_approval': None, 'policy_version': 'REVIEWER_MUST_SET'},
            'instruction': 'Supply attributed research decisions keyed by content hashes. Never auto approve from source address validity.'})
        state['status'] = 'WAITING_DERIVATION'
        event(root, 'WAITING', **state)
        return state
    write_once(root / 'snapshot.json', snap)
    write_once(root / 'graph.json', g)
    write_once(root / 'review-queue.json', priority)
    write_once(root / 'review-packet.json', {'premises': snap['premises'], 'rules': snap['rules'],
        'sources': snap['sources'], 'research_policy': policy, 'qualified_legal_approval': 'PENDING',
        'instruction': 'Review decisions are inputs, not a result of graph scores or this orchestrator.'})
    write_once(root / 'manifest.json', {'snapshots': {snap['snapshot_id']: {
        'path': 'snapshot.json', 'sha256': byte_hash(root / 'snapshot.json')}}})
    try:
        certificate = propose(snap, derivation)
        write_once(root / 'certificate.json', certificate)
        argv = [sys.executable, str(ROOT / 'scripts/check_realcase_certificate_v4.py'),
                str(root / 'certificate.json'), '--manifest', str(root / 'manifest.json')]
        if (root / 'invocation.json').exists():
            invocation = read_json(root / 'invocation.json')
            checked = json.loads((root / 'checker-stdout.txt').read_text())
            if invocation['returncode']: raise ValueError('CHECKER_PROCESS_FAILED')
        else:
            started = now()
            result = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, timeout=120)
            text_once(root / 'checker-stdout.txt', result.stdout)
            text_once(root / 'checker-stderr.txt', result.stderr)
            write_once(root / 'invocation.json', {'argv': argv, 'returncode': result.returncode,
                       'started': started, 'finished': now(), 'independent_process': True})
            checked = json.loads(result.stdout)
            if result.returncode: raise ValueError('CHECKER_PROCESS_FAILED')
        output = view(snap, certificate, checked) if checked['status'] == 'COMPLETED' else {'requests': []}
    except (ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        checked = {'status': 'TECHNICAL_OR_CONTRACT_FAILURE', 'answer': None, 'reason': str(exc)}
        output = {'requests': []}
    write_once(root / 'checker-result.json', checked)
    write_once(root / 'analysis.json', output)
    render(root, snap, derivation, checked, output, g, priority)
    state.update(status='DELIVERED' if checked['status'] == 'COMPLETED' else 'DELIVERED_WITH_FAILURE',
                 checker_status=checked['status'], request_count=len(checked.get('requests', [])),
                 legal_approval=False, origin=read_json(root / 'spec.json').get('proposal_origin', 'EXTERNAL_UNTRUSTED_PROPOSAL'),
                 conditional_count=sum(q['draft_status'] == 'CONDITIONAL_RECONSTRUCTION' for q in checked.get('requests', [])),
                 open_text_uncomputed=sum(bool(q.get('uncomputed')) for q in checked.get('requests', [])))
    write_once(root / 'complete.json', state)
    event(root, 'DELIVERED', **state)
    write_once(root / 'artifacts.json', {'hashes': {str(p.relative_to(root)): byte_hash(p)
        for p in root.rglob('*') if p.is_file()}})
    return state


def render(root, snap, proposal, checked, output, g, priority):
    esc = lambda x: html.escape(str(x))
    def dump(x): return '<pre>' + esc(json.dumps(x, ensure_ascii=False, indent=2)) + '</pre>'
    def detail(title, content, opened=False):
        return '<details' + (' open' if opened else '') + '><summary>' + esc(title) + '</summary>' + content + '</details>'
    def refs(ids):
        return ' '.join('<a href="#src-' + esc(r) + '">' + esc(r) + '</a>' for r in ids if r in snap['sources'])
    body = '<h1>Judgment reconstruction · ' + esc(snap['case_id']) + '</h1>'
    body += '<p class="notice">Research draft. Source review, formal dependency checks and legal approval are separate. Formal legal approval pending. Open legal evaluations are not independently computed.</p>'
    body += '<nav><a href="#answers">Analysis</a> · <a href="#chain">Dependency chain</a> · <a href="#graph">Graph</a> · <a href="#review">Review queue</a> · <a href="#sources">Sources</a></nav>'
    body += '<p><a href="certificate.json">Certificate</a> · <a href="checker-result.json">Independent check</a> · <a href="review-packet.json">Review packet</a> · <a href="freeze/config.json">Frozen version</a></p>'
    body += '<h2 id="answers">Bounded analysis</h2>'
    for row in output['requests']:
        body += '<article><h3>' + esc(row['id']) + ' · ' + esc(row['status']) + '</h3>'
        body += '<p>' + esc(row['published_conditional_statement'] or 'No computed conclusion for this request.') + '</p>'
        body += refs(row['source_refs']) + dump({k: v for k, v in row.items() if k not in ('source_refs',)}) + '</article>'
    if not output['requests']: body += dump(checked)
    body += detail('Decisive counterarguments and gaps retained verbatim', dump({'counterarguments': proposal['counterarguments'], 'gaps': proposal['gaps']}), True)
    body += '<h2 id="chain">Explicit dependency chain</h2>'
    for s in proposal['steps']:
        inputs = []
        for inp in s['inputs']:
            target = ('premise-' if inp['kind'] == 'PREMISE' else 'step-') + inp['id']
            inputs.append('<li>' + esc(inp['slot']) + ' ← <a href="#' + esc(target) + '">' + esc(inp['id']) + '</a></li>')
        result = checked.get('steps', {}).get(s['id'], {})
        body += '<article id="step-' + esc(s['id']) + '"><h3>' + esc(s['id']) + '</h3><a href="#rule-' + esc(s['rule_ref']) + '">' + esc(s['rule_ref']) + '</a><ul>' + ''.join(inputs) + '</ul>' + detail('Step, bindings and independent result', dump({'proposal': s, 'checked': result})) + '</article>'
    body += '<h2>Premises and rule registry</h2>'
    for pid, p in snap['premises'].items():
        body += '<article id="premise-' + esc(pid) + '"><h3>' + esc(pid) + ' · ' + esc(p['statement_status']) + '</h3><p>' + esc(p['text']) + '</p>' + refs(p['refs']) + detail('Attribution, bindings, limitations and review', dump({'record': p, 'review': snap['reviews']['premises'].get(pid)})) + '</article>'
    for rid, r in snap['rules'].items():
        body += '<article id="rule-' + esc(rid) + '"><h3>' + esc(rid) + ' · ' + esc(r['operator']) + '</h3><p>' + esc(r['conclusion_text']) + '</p>' + refs(r['source_refs']) + detail('Inputs, exceptions, scope and review', dump({'rule': r, 'review': snap['reviews']['rules'].get(rid)})) + '</article>'
    body += '<h2 id="graph">Typed graph and signed relations</h2><p>Arrow direction records the proposed dependency. Green/red links only denote proposed support/opposition, never legal truth.</p>'
    # Layered native SVG: all non-source nodes; source edges remain in graph.json and hyperlinks.
    layers = ('ENTITY', 'PREMISE', 'RULE', 'STEP', 'REQUEST')
    positions = {}
    for x, kind in enumerate(layers):
        for y, n in enumerate(n for n in g['nodes'] if n['kind'] == kind):
            positions[n['id']] = (35 + x * 195, 40 + y * 48)
    height = max([100] + [xy[1] + 50 for xy in positions.values()])
    svg = '<svg role="img" aria-label="Typed dependency graph" viewBox="0 0 1040 ' + str(height) + '">'
    for e in g['edges']:
        if e['from'] not in positions or e['to'] not in positions: continue
        x, y = positions[e['from']]; xx, yy = positions[e['to']]
        color = '#167d46' if e['relation'] == 'SUPPORT' else '#b33232' if e['relation'] == 'OPPOSE' else '#87939e'
        svg += f'<path d="M {x+80} {y} L {xx+80} {yy}" stroke="{color}" fill="none"><title>{esc(e["relation"])}</title></path>'
    for nid, (x, y) in positions.items():
        svg += f'<g><rect x="{x}" y="{y-13}" width="167" height="28" rx="5" fill="#e9f0f5" stroke="#87939e"/><text x="{x+4}" y="{y+5}" font-size="10">{esc(nid)}</text></g>'
    body += '<div class="graph">' + svg + '</svg></div>' + detail('All graph edges including source links', dump(g))
    body += '<h2 id="review">Review queue (does not change truth or approval)</h2>' + dump({k: priority[k] for k in ('source_order', 'simple_order', 'graph_budget_5', 'graph_budget_10')})
    body += '<h2 id="sources">Original source locations</h2>'
    for ref, s in sorted(snap['sources'].items(), key=lambda x: (x[1]['document'], x[1].get('original_line', x[1].get('start', 0)), x[0])):
        body += '<article id="src-' + esc(ref) + '"><h3>' + esc(ref) + ' · ' + esc(s['role']) + '</h3><p>' + esc(s['text']) + '</p><a href="' + esc(s['url']) + '">Original document</a></article>'
    css = 'body{font:16px/1.6 system-ui;max-width:1180px;margin:40px auto;padding:0 24px;color:#192733;background:#fafbfc}a{color:#075d9c}article,details{padding:12px 18px;margin:12px 0;border:1px solid #d5dce1;border-radius:8px;background:white}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}summary{cursor:pointer}nav,.notice{padding:14px;background:#e9f0f5}.graph{overflow:auto}svg{min-width:900px;width:100%}h2{margin-top:35px}article:target{outline:3px solid #d59025}'
    text_once(root / 'index.html', '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Proof-carrying reconstruction</title><style>' + css + '</style><body>' + body + '</body></html>')
    lines = ['# ' + snap['case_id'] + ' — research reconstruction',
             'Formal approval pending. This is not automatic legal certification.',
             '[Complete source-to-conclusion interface](index.html)',
             '[Independent result](checker-result.json) · [Graph](graph.json) · [Review queue](review-queue.json)']
    for row in output['requests']:
        lines += ['\n## ' + row['id'] + ' · ' + row['status'], str(row['published_conditional_statement']),
                  'Errors: ' + ', '.join(row['errors']), 'Gaps: ' + ', '.join(row['gaps'])]
    lines += ['\n## Counterarguments'] + proposal['counterarguments'] + ['\n## Remaining gaps'] + proposal['gaps']
    text_once(root / 'report.md', '\n\n'.join(lines) + '\n')


def revise(parent, spec_path, destination, reason):
    parent = Path(parent).resolve()
    verify(parent)
    if not reason.strip(): raise ValueError('REVISION_REASON_REQUIRED')
    old = read_json(parent / 'spec.json')
    new = read_json(spec_path)
    if str(old['case_id']) != str(new['case_id']): raise ValueError('REVISION_CASE_MISMATCH')
    result = initialize(spec_path, destination)
    dest = Path(destination)
    # Separate from completed artifacts: immutable revision ledger plus hashes.
    changes = []
    for component in ('sources.json', 'snapshot.json', 'certificate.json', 'analysis.json', 'graph.json'):
        a, b = parent / component, dest / component
        changes.append({'component': component, 'old_hash': byte_hash(a) if a.exists() else None,
                        'new_hash': byte_hash(b) if b.exists() else None,
                        'changed': not a.exists() or not b.exists() or byte_hash(a) != byte_hash(b)})
    write_once(dest / 'revision.json', {'parent': str(parent), 'parent_manifest_hash': byte_hash(parent / 'artifacts.json'),
        'reason': reason, 'changes': changes, 'old_records_rewritten': False})
    return result
