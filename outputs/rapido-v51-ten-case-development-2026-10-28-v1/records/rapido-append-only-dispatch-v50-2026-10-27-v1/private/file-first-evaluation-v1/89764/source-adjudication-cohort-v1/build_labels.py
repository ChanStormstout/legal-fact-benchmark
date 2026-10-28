"""Source adjudication of existing final outputs. No experimental model calls."""
import copy
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
RAW = HERE.parent
OLD = RAW.parent.parent
SRC = OLD / 'atomic-reference-evaluation-v2/89764'
PREV = OLD / 'provisional-reference-evaluation-v1/89764'
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
packet = read(SRC / 'packet.json')
view = read(SRC / 'source-view.json')
texts = {r['blind_id']: r['text'] for r in packet['reports']}
decisions = []
labels = {}

def write(name, value):
    p = HERE / name
    if p.exists():
        raise ValueError('Preserve old output: ' + str(p))
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def change(row, field, value, blind, reason):
    old = row.get(field)
    if old != value:
        decisions.append(dict(blind_id=blind, id=row.get('item_id', row.get('id')), field=field,
                              before=old, after=value, reason=reason))
        row[field] = value

provenance = []
for blind in texts:
    covpath = RAW / f'{blind}-coverage-first-pass-raw.json'
    cov = read(covpath)
    assert cov['reference_sha256'] == packet['reference_sha256']
    assert cov['source_view_sha256'] == packet['source_view_sha256']
    assert cov['report_sha256'] == hashlib.sha256(texts[blind].encode()).hexdigest()
    apath = PREV / f'{blind}-assertions-original.json'
    if apath.exists():
        a = read(apath)
        assert a['report_sha256'] == cov['report_sha256']
        # Old assertions saw a different reference HASH, never its items. The
        # byte-identical report, question and allowed source are the reuse basis.
        provenance.append(dict(blind_id=blind, original_file=str(apath), sha256=sha(apath),
            original_reference_hash=a['reference_sha256'], current_reference_hash=packet['reference_sha256'],
            assertion_judge_saw_new_reference_items=False, new_annotation_claimed=False,
            reuse_basis='Same actual report bytes, question, and allowed source text; assertions axis did not receive reference items.'))
        a['reference_sha256'] = packet['reference_sha256']
        a['source_view_sha256'] = packet['source_view_sha256']
    else:
        a = {k:cov[k] for k in ['case_id','source_view_sha256','reference_sha256','blind_id','report_sha256']}
        a.update(reading_complete=cov['reading_complete'], assertion_inventory_complete=False,
                 assertions=[], serious_error_inventory_complete=False, serious_errors=[])
        provenance.append(dict(blind_id=blind, assertion_annotation_missing=True,
                               P_H_serious_total_must_remain_null=True))
    a['coverage'] = cov['coverage']
    a['main_answer'] = 'PARTIAL'
    a['annotation_status'] = 'SOURCE_ADJUDICATED_MODEL_REFERENCE_NOT_HUMAN_GOLD'
    labels[blind] = a

for blind in texts:
    c = {x['item_id']: x for x in labels[blind]['coverage']}
    # Equivalent report phrases receive the same interpretation. Generic women
    # possessing jewels is not the specific widow-possession relation required.
    if blind in ['8DI','SZS','THB']:
        change(c['A17'], 'status', 'NOT_SATISFIED', blind,
               'All three summarize women or females possessing their jewels but omit the particular assertion that this widow retained hers. Apply the same literal relation criterion to the near-identical passages.')
        c['A17']['reason'] = 'Generic women-possession assertion does not convey the specific widow-possession relation, although the general assertion itself has a source.'
    # The comparative statement is explicitly introduced as Defendant 1's
    # account of this widow's provision. Context need not repeat "third wife".
    change(c['A18'], 'status', 'CORRECT', blind,
           'Whole-report context identifies the plaintiff as the recipient compared with the second wife. Do not require a memorized role phrase while accepting equivalent contextual attribution in other reports.')
    c['A18']['reason'] = 'The attributed maintenance comparison, read with the immediately identified widow and Defendant 1 statement, preserves the recipient and second-wife comparison.'
    change(c['A19'], 'status', 'NOT_SATISFIED', blind,
           'Each report states the directive and/or earlier request, but none states the arbitrator acknowledged actual receipt of pleadings with the order. A requested transmission is not the separate recorded acknowledgment.')
    c['A19']['reason'] = 'Directive and transmission request are reported, but the arbitrator acknowledgment of actual receipt with the order is omitted.'
    if blind in ['8DI','KEA']:
        change(c['A31'], 'status', 'ANNOTATION_UNRESOLVED', blind,
               'No target disposition is invented, but the trial court is assigned a specific misconduct finding whose reasons are absent. The combined reference boundary is therefore not unqualifiedly satisfied. Use the same rule in both reports.')
        c['A31']['reason'] = 'Known dispositions and further appeal are distinguished, but specific prior misconduct findings are inferred from a disposition without the missing reasons; the combined boundary criterion is unresolved.'
    if blind in ['8DI','SZS']:
        change(c['A27'], 'status', 'ANNOTATION_UNRESOLVED', blind,
               'The report tentatively suggests evidence beyond pleadings but does not explicitly retain uncertainty about the complete pleading/record comparison. Whether the hedge sufficiently conveys the required evidentiary limit remains ambiguous in both identical analyses.')
        c['A27']['reason'] = 'Substantive material and the no-new-facts position are juxtaposed; a hedge about extra-pleading evidence is present, but the unavailable-record comparison is not identified as unresolved.'

# The same attributed "negating any prejudice or misconduct" clause appears
# in all reports. Treat the prejudice part as an interpretive summary of the
# defense, not an independently verified absence of prejudice.
ka = {x['id']: x for x in labels['KEA']['assertions']}
change(ka['A012'], 'label', 'SUPPORTED', 'KEA',
       'As in the identical clause in 8DI, this is explicitly the defense position derived from its no-new-facts argument, not a finding of actual harmlessness. Full-context attribution is the same across reports.')
ka['A012']['reason'] = 'Fair attributed paraphrase of the no-new-facts/no-misconduct defense; no independent absence of prejudice is endorsed.'

ta = {x['id']: x for x in labels['THB']['assertions']}
change(ta['A06'], 'label', 'ANNOTATION_UNRESOLVED', 'THB',
       'The allowed source establishes further certified appeal but does not spell out Supreme Court. Preserve the same proper-court-name uncertainty used for other cases rather than complete it from case memory.')
ta['A06']['reason'] = 'Certified further appeal is supported; the specific court name is not independently supplied by these allowed excerpts.'
# Question-framing and an explicit final admission that opportunity is not
# confirmed mitigate this candidate's severity; the unsupported premises remain
# unsupported, while material serious-error status remains unresolved.
e = labels['THB']['serious_errors'][0]
change(e, 'severity_status', 'UNRESOLVED', 'THB',
       'Earlier question embeds an unproved failure, but the same paragraph explicitly says the record does not confirm denial. Whether this inconsistency materially determines the assessment is unresolved, unlike the unqualified final no-opportunity assertion in 8DI.')
e['materiality'] = 'Question framing embeds unproved failure/reliance, graded unsupported in the assertion axis; the same paragraph explicitly retains uncertainty about any denial of response. Material effect remains unresolved.'

# Source-grounded conditional implications can be supported without proving an
# actual outcome. This does not repair the distinct unqualified assertion of
# no opportunity or the unknown novelty/causal weight of the settlement.
a = next(x for x in labels['8DI']['assertions'] if x['id']=='A53')
change(a, 'label', 'SUPPORTED', '8DI',
       'Potential prejudice from the described alleged lack of opportunity is a bounded analytical possibility, not an assertion of actual prejudice; the frozen task permits conditional reasoning.')
a['reason'] = 'Bounded possibility raised by the recorded response objection, not proof that actual prejudice occurred.'

literal = []
for blind, r in labels.items():
    for axis in ['coverage','assertions','serious_errors']:
        for x in r[axis]:
            qs = [x['report_quote']] if axis=='assertions' else x.get('report_quotes',[])
            for q in qs:
                if q not in texts[blind]:
                    literal.append(dict(blind_id=blind, axis=axis, id=x.get('item_id',x.get('id')), type='REPORT_WITNESS_REVIEW', quote=q))
            for field in ['evidence','source_evidence']:
                for ev in x.get(field,[]):
                    if ev['source_id']=='SCOPE': ev['source_id']='scope'
                    original = view['scope'] if ev['source_id']=='scope' else view['sources'][ev['source_id']]['text']
                    if ev['quote'] not in original:
                        at = original.casefold().find(ev['quote'].casefold())
                        if at>=0:
                            old = ev['quote']; ev['quote']=original[at:at+len(old)]
                            literal.append(dict(blind_id=blind,type='CASE_ONLY_SOURCE_WITNESS',before=old,after=ev['quote']))
                        else:
                            literal.append(dict(blind_id=blind,axis=axis,id=x.get('item_id',x.get('id')),type='SOURCE_WITNESS_REVIEW',evidence=ev))

write('labels-source-adjudicated.json', {k:packet[k] for k in ['case_id','source_view_sha256','reference_sha256']} | {'reports':list(labels.values())})
write('source-adjudication-log.json', dict(at=datetime.now(timezone.utc).isoformat(), decisions=decisions,
    reading='All23CASE excerpts, relevant ARB21/ARB30 and EA50 originals,31frozen source-only reference criteria and uncertainties, all4final reports,4coverage and3available original assertion files. Other LAW bytes already read in preceding cases; no outside facts added.',
    provisional_reference='Parent atomic provisional31criteria; no independent design audit. Not human gold.',
    assertion_provenance=provenance, missing_assertion='SZS', method_map_opened=False,
    parent_perfect_blinding_claimed=False, model_reference_not_human_gold=True, intervals_not_statistical_CI=True))
write('literal-witness-review.json', literal)
write('pre-unmask-available-axes-freeze.json', dict(at=datetime.now(timezone.utc).isoformat(), method_map_opened=False,
    files={p.name:sha(p) for p in HERE.glob('*.json')}, full_axes=['8DI','THB','KEA'],missing_assertions=['SZS']))
print(json.dumps(dict(assertion_counts={b:len(r['assertions']) for b,r in labels.items()},literal_review=literal),ensure_ascii=False,indent=2))
