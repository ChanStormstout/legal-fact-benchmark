"""Rebuildable local text index. Sources are immutable and no relevance label is inferred."""
import json
import re
import sqlite3
from pathlib import Path
from .source_views import digest, write_new


def build(units, destination):
    destination = Path(destination)
    ids = [u['id'] for u in units]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate authority IDs')
    for unit in units:
        if not unit.get('text') or not unit.get('source') or 'version_status' not in unit:
            raise ValueError('Authority requires exact text, provenance and explicit version status')
    fingerprint = digest(units)
    manifest = destination.with_suffix('.manifest.json')
    if destination.exists():
        if not manifest.exists() or json.loads(manifest.read_text())['units_hash'] != fingerprint:
            raise FileExistsError('Index differs; use a new version')
        return json.loads(manifest.read_text())
    destination.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(destination))
    try:
        connection.execute('CREATE VIRTUAL TABLE authority_fts USING fts5(id UNINDEXED, text)')
        connection.execute('CREATE TABLE metadata (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        for unit in units:
            connection.execute('INSERT INTO authority_fts(id,text) VALUES (?,?)', (unit['id'], unit['text']))
            connection.execute('INSERT INTO metadata VALUES (?,?)', (unit['id'], json.dumps(unit, ensure_ascii=False)))
        connection.commit()
    finally:
        connection.close()
    result = {'index_kind': 'SQLITE_FTS5_BM25_ONLY', 'units': len(units), 'units_hash': fingerprint,
              'sqlite_version': sqlite3.sqlite_version, 'db_sha256': digest(destination.read_bytes()),
              'no_dense_or_reranker_claim': True}
    write_new(manifest, result)
    return result


def search(destination, query, limit=50):
    if not isinstance(limit, int) or not 1 <= limit <= 200:
        raise ValueError('Invalid candidate budget')
    terms = sorted(set(re.findall(r'\w+', query.lower(), re.UNICODE)))
    if not terms:
        return []
    # User/model text is data; no raw FTS syntax or SQL interpolation.
    expression = ' OR '.join('"' + t.replace('"', '""') + '"' for t in terms)
    connection = sqlite3.connect(Path(destination).resolve().as_uri() + '?mode=ro', uri=True)
    try:
        rows = connection.execute('SELECT id,bm25(authority_fts) FROM authority_fts WHERE authority_fts MATCH ? ORDER BY bm25(authority_fts),id LIMIT ?', (expression, limit)).fetchall()
    finally:
        connection.close()
    return [{'id': key, 'rank': i + 1, 'bm25_distance': score} for i, (key, score) in enumerate(rows)]
