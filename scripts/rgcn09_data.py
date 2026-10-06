"""V09 source-first expansion. No training, label inference, or verdict selection.

Existing database fields are locators only: even `facts` can contain the target
court's final reasoning. Never copy them into model task inputs automatically.
"""
import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path('outputs/rgcn-data-expansion-09')
MECHANISMS = {
    'family_occupation': r'\b(?:son|sons|daughter|wife|husband|brother|father|family)\b',
    'control_exclusive_possession': r'exclusive|legal possession|control|divest|right to possess',
    'partnership_company': r'partner|partnership|company|corporat|firm',
    'amalgamation': r'amalgamat|merger|merged',
    'statutory_succession': r'statutory succession|vesting|nationalis|nationaliz|take.over|acquisition|undertaking',
    'licence_sublease': r'licen[cs]e|sub.?lett|sub.?leas',
    'written_consent': r'written consent|consent in writing|rent note|rent deed|permission',
    'temporal_applicability': r'1952|1958|commencement|retrospect|amendment|before|after',
}


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if read(path) == value:
            return
        raise ValueError('Preserve existing output; use a new filename: ' + str(path))
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve_renderer_markers(document):
    """Recognise equivalent renderer delimiters only; keep original segment bytes.

    Web windows may use either U+3010 or the internal citation-start delimiters,
    even for the same unfinished citation at a line boundary. No case words,
    whitespace, citation number or address are changed. Real conflicts remain.
    """
    import copy
    d = copy.deepcopy(document)
    conflicts, equivalents = [], []
    def canonical(text):
        return text.replace('\ue200cite\ue202', '【').replace('\ue201', '】')
    for row in d['conflicts']:
        (equivalents if canonical(row['existing']) == canonical(row['alternative']) else conflicts).append(row)
    d['conflicts'] = conflicts
    d['equivalent_renderer_variants'] = equivalents
    if equivalents and not conflicts and not d['unparsed'] and len(d['totals']) == 1:
        d['status'] = 'INCOMPLETE' if d['missing_lines'] else 'COMPLETE_RENDERING'
    return d


def index():
    protocol = read(ROOT / 'data-protocol.json')
    train = {str(x['case_id']) for x in protocol['existing_train']}
    dev = set(protocol['development_ids'])
    prior = read('outputs/legal-rule-support-study-02/candidate-order.json')
    exposed = set(prior['known_exposed_ids']) | train | dev
    # Only fact/issue/party text proposes mechanism coverage. Analysis is used
    # solely as a wider locator, not for mechanism selection or model features.
    db = Path('outputs/benchmark-pilot/data/cases.sqlite')
    conn = sqlite3.connect('file:' + str(db) + '?mode=ro', uri=True)
    out = []
    for cid, rank, title, url, record_hash, raw in conn.execute(
            'select doc_id,line_number,title,url,record_sha256,raw_json from cases order by line_number'):
        record = json.loads(raw)
        fact_issue = '\n'.join(str(record.get(k, '')) for k in
                               ('facts', 'issues', 'petitioners_arguments', 'respondents_arguments'))
        locator = fact_issue + '\n' + str(record.get('analysis_of_the_law', ''))
        if not re.search(r'delhi\s+(?:and\s+ajmer\s+)?rent\s+(?:control|act)', locator, re.I):
            continue
        if not re.search(r'14.{0,15}1.{0,8}b|sub.?lett|sub.?leas|part(?:ed|ing)?\s+with\s+possession', locator, re.I):
            continue
        marks = {}
        for mechanism, pattern in MECHANISMS.items():
            hit = re.search(pattern, fact_issue, re.I)
            if hit:
                marks[mechanism] = {'locator_excerpt': fact_issue[max(0, hit.start()-70):hit.end()+90],
                                    'status': 'METADATA_SCREEN_NOT_SOURCE_VERIFIED'}
        role = 'TRAIN_EXISTING' if cid in train else 'DEVELOPMENT_ONLY' if cid in dev else 'PRIOR_EXPOSED' if cid in exposed else 'NEW_CANDIDATE'
        out.append(dict(case_id=cid, title=title, url=url, saved_rank=rank,
                        database_record_hash=record_hash, prior_role=role,
                        mechanism_hits=marks, eligibility='FULL_ORIGINAL_AND_ACTUAL_ISSUE_CHECK_REQUIRED',
                        model_input_allowed=False))
    save(ROOT / 'candidate-index.json', {'database': str(db), 'database_sha256': sha(db),
        'database_records': conn.execute('select count(*) from cases').fetchone()[0],
        'selection_fields': ['facts', 'issues', 'petitioners_arguments', 'respondents_arguments'],
        'wider_locator_only': ['analysis_of_the_law'],
        'not_used': ['conclusion', 'courts_reasoning', 'precedent_analysis', 'model results'],
        'rows': out, 'caution': 'Metadata can mix final analysis; hits do not establish legal scope, source completeness or non-exposure.'})
    print('Indexed', len(out), 'candidate records;', sum(x['prior_role']=='NEW_CANDIDATE' for x in out), 'not listed as prior targets.')


def verify_v08():
    old = read(ROOT / 'v08-preservation.json')
    errors = [p for p, h in {**old['hashes'], **old['code_hashes']}.items()
              if not Path(p).exists() or sha(p) != h]
    if errors:
        raise ValueError('V08 preservation failed: ' + str(errors))
    print('V08 preserved:', len(old['hashes']), 'files and', len(old['code_hashes']), 'current source files')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['index', 'verify-v08'])
    args = parser.parse_args()
    {'index': index, 'verify-v08': verify_v08}[args.command]()


if __name__ == '__main__':
    main()
