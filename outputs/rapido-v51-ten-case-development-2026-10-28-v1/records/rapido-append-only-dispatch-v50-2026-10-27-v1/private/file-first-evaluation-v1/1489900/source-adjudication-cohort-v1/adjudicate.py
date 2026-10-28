"""Append-only source adjudication; no model calls or report/reference edits."""
import copy
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
CASE = HERE.parent
OLD = CASE.parent.parent
ROOT = OLD.parent.parent
SRC = OLD / 'atomic-reference-evaluation-v2/1489900'
PROV = OLD / 'provisional-reference-evaluation-v1/1489900'
FIRST = CASE / 'atomic-coverage-first-pass-v1'
V51 = ROOT / 'rapido-source-plan-direct-edit-v51-2026-10-28-v1/private'
PREV = V51 / 'anonymous-final-evaluation-v1/1489900/source-adjudication-v2'
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
view = read(SRC / 'source-view.json')
packet = read(SRC / 'packet.json')
oldpacket = read(PROV / 'packet.json')
assert (SRC / 'source-view.json').read_bytes() == (PROV / 'source-view.json').read_bytes()
paired = read(PREV / 'packet-paired.json')
packet['reports'].append(copy.deepcopy(next(r for r in paired['reports'] if r['blind_id'] == 'WFQ')))
reports = {r['blind_id']: r for r in packet['reports']}
log, units, provenance, excluded = [], [], [], []

def decision(obj, axis, key, after, reason, **extra):
    field = 'status' if axis == 'coverage' else 'label'
    idfield = 'item_id' if axis == 'coverage' else 'id'
    row = next(x for x in obj[axis] if x[idfield] == key)
    before = copy.deepcopy(row)
    row[field] = after
    row['reason'] = reason
    row.update(extra)
    log.append(dict(blind_id=obj['blind_id'], axis=axis, id=key, before=before, after=copy.deepcopy(row)))

def align(obj, key, proposition):
    row = next(x for x in obj['assertions'] if x['id'] == key)
    units.append(dict(blind_id=obj['blind_id'], id=key, before=row['proposition'], after=proposition,
                      reason='Align inventory to actual words; do not import omitted details from source.'))
    row['proposition'] = proposition

base = read(PREV / 'labels-source-adjudicated-shared-units.json')
pf = {r['blind_id']: copy.deepcopy(r) for r in base['reports']}
out = [copy.deepcopy(read(CASE / 'source-adjudication-A0-v1/labels-source-adjudicated.json')['reports'][0])]

for bid in ['F2O', 'M40', 'FDU']:
    raw_a = read(PROV / (bid + '-assertions-original.json'))
    raw_c = read(FIRST / (bid + '-coverage-first-pass-raw.json'))
    assert all(raw_c[k] == packet[k] for k in ['case_id', 'source_view_sha256', 'reference_sha256'])
    oldr = next(r for r in oldpacket['reports'] if r['blind_id'] == bid)
    assert oldr['text'] == reports[bid]['text']
    assert raw_a['report_sha256'] == raw_c['report_sha256'] == reports[bid]['report_sha256']
    assert hashlib.sha256(reports[bid]['text'].encode()).hexdigest() == raw_c['report_sha256']
    provenance.append(dict(blind_id=bid, original_assertions=str(PROV / (bid + '-assertions-original.json')),
        original_assertions_sha256=sha(PROV / (bid + '-assertions-original.json')),
        old_reference_sha256=raw_a['reference_sha256'], current_reference_sha256=packet['reference_sha256'],
        assertion_grader_saw_reference_items=False, old_new_source_bytes_identical=True,
        old_new_question_and_report_identical=True, new_coverage_first_pass=True,
        new_coverage=str(FIRST / (bid + '-coverage-first-pass-raw.json'))))
    if bid == 'F2O':
        obj = pf[bid]
    else:
        # Actual reports differ only in one partition sentence. Use the same 80
        # relation units from the original FDU inventory, not unequal 71/80 units.
        obj = copy.deepcopy(read(PROV / 'FDU-assertions-original.json'))
        obj['blind_id'] = bid
        obj['report_sha256'] = reports[bid]['report_sha256']
        obj['serious_errors'] = copy.deepcopy(raw_a['serious_errors'])
        units.append(dict(blind_id=bid, raw_inventory_count=len(raw_a['assertions']), common_inventory_count=80,
            common_inventory_source=str(PROV / 'FDU-assertions-original.json'),
            reason='Same unchanged text uses the same actual relations; only Panchayat sentence changes.'))
    obj['reference_sha256'] = packet['reference_sha256']
    obj['coverage'] = copy.deepcopy(raw_c['coverage'])
    obj['main_answer'] = 'PARTIAL'
    obj['annotation_status'] = 'SOURCE_ADJUDICATED_NEW51_COVERAGE_COMMON_UNITS_REUSED_HASH_ONLY_ASSERTIONS'
    # All three use the same compressed profit/loss pair as the already judged A0.
    decision(obj, 'coverage', 'P12', 'ANNOTATION_UNRESOLVED',
        'The fiscal pair is recognizable, but bore/liable for profit and loss does not unambiguously express entitlement to profits. Apply the same semantic uncertainty as MA9, without demanding verbatim wording.')
    decision(obj, 'coverage', 'P21', 'ANNOTATION_UNRESOLVED',
        'The family-based revenue relation is stated. Its later-settlement attribution is not secure: the allowed excerpts do not explicitly date paragraphs5/7, and the report groups them under an early arrangement or specifically1877. Same documentary-binding uncertainty as MA9; underlying relation is not false.')
    if bid == 'F2O':
        # The new independent coverage contradicts three old parent inferences:
        # naming generic trial court, reversal, and proprietor status does not
        # supply Assistant Collector, dismissal, or the High Court four-fifths award.
        align(obj, 'A06', 'The plaintiffs claimed full ownership of819Bighas19Biswas; the report separately names aligned pro-forma defendants but does not clearly include them in this declaration.')
        align(obj, 'A22', 'The High Court relied on the June15,1893ChiefCourt judgment concerning the temporary partition restriction.')
        align(obj, 'A39', "The1903-08clause reserved initiation of partition to Dalmir's descendants; the report omits the specified division into five equal shares.")
        for key, prop in [('A32', 'The settlement history described Amir and Sharif joining the proprietary arrangement.'),
                          ('A33', 'That historical account asserted continuing joint ownership and no partition.'),
                          ('A35', "Paragraph5 assigned Dalmir's sons government revenue for all branches because of kinship."),
                          ('A36', 'Paragraph7 prohibited individual banjar reclamation without all proprietors consent.'),
                          ('A50', 'The withheld appellate assessment leaves the interaction of proprietary partition rights and settlement restrictions unresolved.')]:
            align(obj, key, prop)
        decision(obj, 'assertions', 'A31', 'ANNOTATION_UNRESOLVED',
            'The joint-possession history is in the allowed record, but that excerpt is not explicitly dated1877. Its1877 binding cannot be confirmed from adjacent source order alone. No external case completion.')
        decision(obj, 'assertions', 'A48', 'ANNOTATION_UNRESOLVED',
            'The final disposition is withheld; SupremeCourt proper-name identification is not explicit in the allowed record. Same named-court uncertainty as MA9/M40/FDU; not a confirmed wrong court.')
        obj['serious_errors'].append(dict(id='E03', type='DOCUMENT_DATE_BINDING_UNCERTAINTY',
            report_quotes=['The 1877 Wajib-ul-arz recorded joint possession since Sambat 1880'],
            source_evidence=[dict(source_id='Sde2ad06bee15', quote=view['sources']['Sde2ad06bee15']['text'])],
            materiality='Joint possession is documented, but the exact record year is not explicit in the permitted excerpt. Its chronological force could matter; severe distortion is unresolved.', severity_status='UNRESOLVED'))
    else:
        if bid == 'M40':
            a26 = next(x for x in obj['assertions'] if x['id'] == 'A26')
            a26['report_quote'] = 'they would do so themselves in accordance with their shares shown in the Khewat papers or through the village Patwari'
            decision(obj, 'assertions', 'A27', 'SUPPORTED',
                'The unchanged source requires Panchayat presence. This report correctly says presence, unlike FDU consent.',
                proposition='Paragraph2 provides partition through the Patwari in the presence of the Panchayat.',
                report_quote='in the presence of the Panchayat of the brotherhood')
        else:
            decision(obj, 'coverage', 'P05', 'CORRECT',
                'Exactly the same words as M40 identify opposing four-fifths against five equal branch shares. The separate omission of pro-forma17-19 is already reflected in P01/P02; it does not erase this fractional opposition.')
        decision(obj, 'assertions', 'A02', 'SUPPORTED',
            'The source itself describes descendants ofAlif opposite the Dalmir branch, and the report identifies Alif as Amir son. This is a supported branch shorthand, not a proved substitution of a different founder.')
        decision(obj, 'assertions', 'A31', 'ANNOTATION_UNRESOLVED',
            'The five equal recorded shares are real. The allowed excerpts do not expressly date this Khewat/Khatauni passage1877, so the claim that the report certainly moved it from1877 to1863 exceeds this view. Temporal binding remains uncertain.')
        decision(obj, 'assertions', 'A33', 'ANNOTATION_UNRESOLVED',
            'The joint-possession narrative is supported, but its explicit1877 record-year assignment is not established in the allowed paragraph. The separate ChiefCourt paragraph8 does explicitly name1877; it does not date every preceding document.')
        align(obj, 'A38', 'The historical village account asserted continuing joint ownership up to that day; the report does not expressly state never partitioned.')
        decision(obj, 'assertions', 'A72', 'ANNOTATION_UNRESOLVED',
            'An appellate proceeding is explicit, but the permitted heading does not name SupremeCourt. Same proper-name policy as MA9/F2O/WFQ.')
        decision(obj, 'assertions', 'A74', 'ANNOTATION_UNRESOLVED',
            'The documented defence and HighCourt reasoning support the position, but this appellate-section phrasing could be synthesis or an unrecorded attribution to respondents on the current appeal. Preserve stage ambiguity.')
        # Common treatment of informal precedent vs inter-partes preclusion;
        # original M40 prose-inventory had overstated binding-on-parties.
        decision(obj, 'assertions', 'A76', 'ANNOTATION_UNRESOLVED',
            'The source says binding upon the parties; binding precedent may be loose wording or broader authority. It does not clearly resolve inter-partes preclusion.')
        serious = []
        for z in obj['serious_errors']:
            if 'FAMILY_BRANCH' in z['type']:
                excluded.append(dict(blind_id=bid, raw_error=z, reason='Alif-son-of-Amir is supported family-branch shorthand in the actual source; no additional serious error established.'))
                continue
            if 'TEMPORAL' in z['type'] or 'CHRONOLOGY' in z['type']:
                z['severity_status'] = 'UNRESOLVED'
                z['materiality'] = 'The report documentary dates are uncertain, but the allowed passages do not expressly establish the1877dating assumed by the raw annotator. Preserve underlying joint/fiscal facts and a possible temporal error without confirming it from outside knowledge.'
            serious.append(z)
        # The original FDU inventory omitted the same appellate-stage warning
        # flagged for M40, although their words are identical.
        if bid == 'FDU':
            z = copy.deepcopy(read(PROV / 'M40-assertions-original.json')['serious_errors'][-1])
            z['id'] = 'E06'
            serious.append(z)
        obj['serious_errors'] = serious
    out.append(obj)

# Fixed F keeps its seven actual extra relations, and its own changed A12/A15/
# A23/A38. Synchronize only unchanged P/F statements; never create an ideal edit.
f = pf['WFQ']
p = next(r for r in out if r['blind_id'] == 'F2O')
changed_assertions = {'A12', 'A15', 'A23', 'A38'}
for i, row in enumerate(f['assertions'][:52]):
    if row['id'] not in changed_assertions:
        assert row['report_quote'] == p['assertions'][i]['report_quote']
        f['assertions'][i] = copy.deepcopy(p['assertions'][i])
for c in f['coverage']:
    key = c['item_id']
    if key not in {'P23', 'P35', 'P36', 'P37'}:
        c.update(copy.deepcopy(next(x for x in p['coverage'] if x['item_id'] == key)))
f['serious_errors'] = copy.deepcopy(p['serious_errors'])
f['annotation_status'] = 'FIXED_F_SAME_UNCHANGED_P_RELATIONS_SYNCHRONIZED_NEW51_COHORT_NO_NEW_WEB_GRADE'
out.append(f)

# Restore exact source witnesses for mechanical arithmetic; raw witness strings
# are preserved separately. Full source passages are used only where a raw
# quotation was paraphrased; this operation supplies no new truth label.
literal = []
for obj in out:
    text = reports[obj['blind_id']]['text']
    for axis in ['coverage', 'assertions', 'serious_errors']:
        for z in obj[axis]:
            for field in ['evidence', 'source_evidence']:
                for ev in z.get(field, []):
                    sid = ev['source_id']
                    if sid in ['Scope', 'SCOPE']:
                        ev['source_id'] = sid = 'scope'
                    original = view['scope'] if sid == 'scope' else view['sources'][sid]['text']
                    if ev['quote'] not in original:
                        old = ev['quote']
                        idx = original.casefold().find(old.casefold())
                        ev['quote'] = original[idx:idx + len(old)] if idx >= 0 else original
                        literal.append(dict(blind_id=obj['blind_id'], axis=axis, id=z.get('item_id', z.get('id')),
                            type='EXACT_SOURCE_WITNESS', source_id=sid, before=old, after=ev['quote']))
            qs = [z['report_quote']] if axis == 'assertions' else z.get('report_quotes', [])
            for q in qs:
                if q not in text:
                    literal.append(dict(blind_id=obj['blind_id'], axis=axis, id=z.get('item_id', z.get('id')),
                        type='REPORT_WITNESS_REQUIRES_REVIEW', quote=q))

labels = {k: packet[k] for k in ['case_id', 'source_view_sha256', 'reference_sha256']} | {'reports': out}
def write(name, data):
    with (HERE / name).open('x') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
write('packet-cohort.json', packet)
write('labels-source-adjudicated.json', labels)
write('source-adjudication-log.json', dict(at=datetime.now(timezone.utc).isoformat(), decisions=log,
    unit_alignment=units, excluded_raw_serious_flags=excluded, original_assertion_provenance=provenance,
    reference_unchanged=True, raw51coverage_and_old17_preserved=True,
    parent_not_method_blind=True, model_reference_not_human_gold=True,
    report_texts_unchanged=True, no_model_calls=True,
    temporal_reference_limitation='Allowed excerpts do not explicitly date every village-history/fiscal paragraph1877. Freeze preserved; uncertainty carried in labels, not completed from outside.' ))
write('literal-witness-review.json', literal)
print(json.dumps([x for x in literal if x['type']=='REPORT_WITNESS_REQUIRES_REVIEW'], ensure_ascii=False, indent=2))
