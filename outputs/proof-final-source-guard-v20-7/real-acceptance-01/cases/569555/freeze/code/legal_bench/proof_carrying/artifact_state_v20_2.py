"""Immutable composition snapshots, execution pause, and local code closure.

This module performs filesystem/AST work only. It never loads a neural model.
"""
import ast
import hashlib
import json
from pathlib import Path


def byte_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def immutable(path, value):
    path = Path(path)
    body = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() != body:
        raise ValueError('IMMUTABLE_SNAPSHOT_CHANGED:' + str(path))
    if not path.exists():
        path.write_text(body)
    return value


def paused(root):
    return (Path(root) / 'PAUSE_REQUESTED.json').exists()


def local_closure(root, entries):
    """Include relative and function-local imports plus explicit child entries."""
    root = Path(root)
    found, pending = set(), list(entries)

    def module_path(module):
        p = root.joinpath(*module.split('.'))
        for candidate in (p.with_suffix('.py'), p / '__init__.py'):
            if candidate.is_file():
                return candidate.relative_to(root).as_posix()
        return None

    while pending:
        name = pending.pop()
        if name in found:
            continue
        path = root / name
        if not path.is_file():
            raise ValueError('LOCAL_DEPENDENCY_MISSING:' + name)
        found.add(name)
        module = name[:-3].replace('/', '.').removesuffix('.__init__')
        package = module.split('.') if path.name == '__init__.py' else module.split('.')[:-1]
        for node in ast.walk(ast.parse(path.read_text(), filename=name)):
            imports = []
            if isinstance(node, ast.Import):
                imports = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ''
                if node.level:
                    base = '.'.join(package[:len(package)-node.level+1] + ([base] if base else []))
                imports = [base] + [base + '.' + a.name for a in node.names if a.name != '*']
            for target in imports:
                rel = module_path(target)
                if rel and rel not in found:
                    pending.append(rel)
    return sorted(found)


def freeze_files(root, out, entries, prepared, configurations=()):
    root, out = Path(root), Path(out)
    code = local_closure(root, entries)
    hashes = {p: byte_hash(root / p) for p in code}
    for rel in code:
        dest = out / 'freeze/code' / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        content = (root / rel).read_bytes()
        if dest.exists() and dest.read_bytes() != content:
            raise ValueError('FROZEN_COPY_CHANGED:' + rel)
        if not dest.exists():
            dest.write_bytes(content)
    return {
        'code_hashes': hashes,
        'prepared_hashes': {p: byte_hash(root / p) for p in sorted(prepared)},
        'configuration_hashes': {p: byte_hash(root / p) for p in sorted(configurations)},
        'explicit_entries': list(entries),
        'closure_policy': 'AST_LOCAL_IMPORTS_INCLUDING_FUNCTION_IMPORTS_AND_EXPLICIT_CHILD_ENTRIES',
    }


def verify_files(root, manifest):
    for field in ('code_hashes', 'prepared_hashes', 'configuration_hashes'):
        for rel, expected in manifest.get(field, {}).items():
            if byte_hash(Path(root) / rel) != expected:
                raise ValueError('FROZEN_DEPENDENCY_CHANGED:' + rel)
    return True


def composition(root, out, cid, role, slots, fixture, merge):
    """Changing parts produce a new content-addressed snapshot, never a stale hit."""
    root, out = Path(root), Path(out)
    parts, identities = [], []
    for slot in slots:
        if slot['case_id'] != cid or slot['role'] != role:
            continue
        dest = out / slot['dest']
        run = json.loads((dest / 'run.json').read_text()) if (dest / 'run.json').exists() else None
        formal = json.loads((dest / 'formal-answer.json').read_text()) if (dest / 'formal-answer.json').exists() else None
        status = run.get('run_status') if run else 'SUBMITTED_UNCERTAIN' if (dest / 'start.json').exists() else 'NOT_STARTED'
        ready = formal is not None and formal.get('answer') is not None and status == 'OK'
        ids = {r['id'] for r in fixture['rules'] if r['id'] in slot['part'].get('rule_ids', [])}
        identities.append({
            'part': slot['part']['id'], 'rule_ids': sorted(ids),
            'premise_ids': [p['id'] for r in fixture['rules'] if r['id'] in ids for p in r['premises']],
            'run_status': status, 'state': 'COMPLETED' if ready else 'NOT_STARTED' if status == 'NOT_STARTED' else 'UNAVAILABLE',
            'run_sha256': byte_hash(dest / 'run.json') if run is not None else None,
            'formal_sha256': byte_hash(dest / 'formal-answer.json') if formal is not None else None,
            'readable': ready,
        })
        if ready:
            parts.append((slot, formal['answer']))
    identity = {'case_id': cid, 'role': role, 'parts': identities, 'fixture_sha256': digest(fixture)}
    key = digest(identity)
    path = out / 'assembled' / cid / role / (key + '.json')
    if path.exists():
        result = json.loads(path.read_text())
        if result['composition'] != identity:
            raise ValueError('SNAPSHOT_IDENTITY_MISMATCH')
        return result
    result = {
        'answer': merge(fixture, parts, role) if parts else None,
        'status': 'ALL_PARTS_READABLE' if parts and len(parts) == len(identities) else 'PARTIAL' if parts else 'NO_READABLE_PART',
        'parts': identities, 'composition': identity, 'snapshot_sha256': key,
    }
    return immutable(path, result)


def execution_context(p, q):
    return {role: {k: wrapper[k] for k in ('status', 'parts', 'snapshot_sha256')}
            for role, wrapper in (('P', p), ('Q', q))}


def terminal_parts(out, slots, role):
    """An uncertain submission or unstarted slot is not a terminal result."""
    missing = []
    for slot in slots:
        if slot['role'] == role and not (Path(out) / slot['dest'] / 'run.json').is_file():
            missing.append(slot['dest'])
    if missing:
        raise ValueError('STAGE_DEPENDENCY_NOT_TERMINAL:' + role + ':' + str(len(missing)))

