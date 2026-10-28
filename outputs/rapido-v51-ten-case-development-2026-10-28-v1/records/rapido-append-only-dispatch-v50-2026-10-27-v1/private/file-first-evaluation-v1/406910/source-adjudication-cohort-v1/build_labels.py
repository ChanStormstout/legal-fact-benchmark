"""Adjudicate only received existing annotation axes against permitted originals."""
import copy
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
RAW = HERE.parent
OLD = RAW.parent.parent
SRC = OLD / 'atomic-reference-evaluation-v2/406910'
read = lambda p: json.loads(p.read_text())
packet = read(SRC / 'packet.json')
view = read(SRC / 'source-view.json')
texts = {r['blind_id']:r['text'] for r in packet['reports']}
decisions = []

def write(name, obj):
    with (HERE/name).open('x') as f:
        json.dump(obj,f,ensure_ascii=False,indent=2)
        f.write('\n')

def change(row, field, value, blind, reason):
    before = row.get(field)
    if before != value:
        decisions.append(dict(blind_id=blind,id=row.get('item_id',row.get('id')),
                              field=field,before=before,after=value,reason=reason))
        row[field]=value

covpaths = {'2VJ':RAW/'2VJ-coverage-delayed-original.json',
            '07S':RAW/'07S-coverage-delayed-original.json',
            'Z5D':SRC/'Z5D-coverage-original.json'}
apaths = {'2VJ':RAW/'2VJ-assertions-delayed-original.json',
          '07S':SRC/'07S-assertions-original.json',
          'ECJ':RAW/'ECJ-assertions-delayed-original.json'}
labels = {}
for b in texts:
    seed = read(apaths[b]) if b in apaths else read(covpaths[b])
    assert all(seed[k]==packet[k] for k in ['case_id','source_view_sha256','reference_sha256'])
    assert seed['report_sha256']==hashlib.sha256(texts[b].encode()).hexdigest()
    if b not in apaths:
        seed.update(assertions=[],assertion_inventory_complete=False,
                    serious_errors=[],serious_error_inventory_complete=False)
    seed['coverage'] = read(covpaths[b])['coverage'] if b in covpaths else []
    seed['main_answer']='PARTIAL'
    seed['annotation_status']='SOURCE_ADJUDICATED_EXISTING_AVAILABLE_AXES_NOT_HUMAN_GOLD'
    labels[b]=seed

# Combined reference conditions are interpreted consistently. Both reports
# locate the earlier cess test but leave the group-wide 1939 finding implicit.
for b in ['2VJ','07S']:
    c = {x['item_id']:x for x in labels[b]['coverage']}
    change(c['P14'],'status','ANNOTATION_UNRESOLVED',b,
        'Both explicitly report Sita Ram and the earlier interest reduction, but not the separate all-other-mortgagors finding. Whether the collective decree context suffices for the combined criterion is ambiguous; do not label equivalent implicit context oppositely.')
    c['P14']['reason']='The 1939/1934-Act Sita Ram cess test is explicit; group-wide entitlement is only implicit in the decree context. Preserve the same combined-item ambiguity.'
c = {x['item_id']:x for x in labels['2VJ']['coverage']}
change(c['P32'],'status','ANNOTATION_UNRESOLVED','2VJ',
    'The report first accurately states non-contestation, then calls it conceded. That could mean tacit non-opposition or stronger affirmative admission. Apply the same ambiguity already recorded in the assertion axis, rather than definite coverage failure.')
c['P32']['reason']='Accurate non-contestation is followed by ambiguous concession language; historical silence versus affirmative agreement is not consistently distinguished.'

# Close 07S/ECJ reports are compared using a common actual-assertion inventory,
# rather than rewarding the different granularity of separate Web passes.
common = copy.deepcopy(labels['ECJ']['assertions'])
removed = {'A01','A02','A03','A04','A52','A54'}
for b in ['ECJ','07S']:
    rows=[]
    for original in common:
        aid=original['id']
        if aid in removed:
            decisions.append(dict(blind_id=b,id=aid,operation='SEMANTIC_DEDUPLICATION',
                reason='Generic introductory issue/history repeats the later transaction, objection, appeal and disposition assertions; remove in both close reports.'))
            continue
        if b=='07S' and aid=='A68':
            decisions.append(dict(blind_id=b,id=aid,operation='NO_LONGER_ASSERTED',
                reason='The original ECJ final recital-significance sentence is replaced, not retained.'))
            continue
        a=copy.deepcopy(original)
        if aid=='A27' and b=='07S':
            a['report_quote']='In the 1939 suit, the Trial Court had found that Sita Ram’s income-tax assessment for 1931-32 did not exceed the cess payable on his land'
        if aid=='A28' and b=='07S':
            a['report_quote']='thus preserving his status as an agriculturist'
        if aid=='A55':
            change(a,'label','ANNOTATION_UNRESOLVED',b,
                'Certified further appeal is stated, but this allowed CASE view does not spell out the Supreme Court name. No case-memory completion; apply identical name uncertainty across reports.')
            a['reason']='The certified further appeal under section110 is recorded; the specific Supreme Court name is not independently present in this allowed view.'
        if aid=='A60':
            a['proposition']='The unqualified summary defines a loan as recoverable from an agriculturist provided the advance was made to an agriculturist.'
            a['report_quote']="'Loan' is defined as an advance made before June 1, 1940, recoverable from an agriculturist, provided the advance was made to an agriculturist"
            change(a,'label','CONTRADICTED',b,
                'This is materially the same unqualified loan definition as2VJ, not the narrower category-limited paraphrase supplied by the original assertion judge. Property/workman/joint routes exist and the proviso is expressly limited. Earlier correct High Court attribution does not change the actual summary wording.')
            a['reason']='The unqualified definition omits the separate property-recovery route and presents the borrower-at-advance proviso as universal; the same report elsewhere correctly attributes the High Court distinction.'
            a['evidence']=[{'source_id':'L81efa2890bf4','quote':'or from the property of an agriculturist or workman'},
                           {'source_id':'Sff81fb3988bd','quote':'Provided that an advance recoverable from an agricul- turist or from an agriculturist and other persons jointly'}]
        rows.append(a)
    if b=='07S':
        old={a['id']:a for a in read(apaths['07S'])['assertions']}
        for oid,nid in [('A49','N69'),('A61','N70'),('A62','N71')]:
            a=copy.deepcopy(old[oid]);a['id']=nid;a['original_annotation_id']=oid;rows.append(a)
    labels[b]['assertions']=rows

# The common wrong statutory summary is evaluated as an actual assertion in
# all reports. Its serious material effect remains uncertain because all three
# accurately attribute the contrary property-recovery rationale to the HC.
e = labels['2VJ']['serious_errors'][0]
change(e,'severity_status','UNRESOLVED','2VJ',
    'Incorrect unqualified summary is real, but the report explicitly gives the correct contrary High Court recovery-route distinction. Whether the inconsistency determines the analysis is unresolved; apply the same severity to all near-equivalent summaries.')
e['materiality']='The unqualified summary overrestricts the statutory definition, but the earlier High Court discussion distinguishes property recovery correctly. Whether this inconsistent summary materially determines the final assessment is unresolved.'
for b in ['ECJ','07S']:
    e=copy.deepcopy(labels['2VJ']['serious_errors'][0]);e['id']='PARENT_COMMON_LOAN_SUMMARY'
    e['report_quotes']=["'Loan' is defined as an advance made before June 1, 1940, recoverable from an agriculturist, provided the advance was made to an agriculturist"]
    labels[b]['serious_errors'].append(e)

pa={a['id']:a for a in labels['2VJ']['assertions']}
change(pa['A43'],'label','ANNOTATION_UNRESOLVED','2VJ',
    'The certificate route is explicit; the proper court name is not. Apply the same allowed-source name rule as the other reports.')
pa['A43']['reason']='Section110 certificate and further appeal are recorded; the Supreme Court proper name is not in the allowed original excerpts.'
change(pa['A49'],'label','UNSUPPORTED','2VJ',
    'The report overstates accounting as primary, but the record does not affirmatively exclude a possible accounting issue on further appeal. Unsupported prioritization is not a source contradiction; question wording itself asks about the separate objection.')
pa['A49']['reason']='The source explicitly poses statutory loan classification and supplies the accounting history, but does not identify accounting as the primary actual ground on further appeal.'
e=labels['2VJ']['serious_errors'][1]
change(e,'severity_status','UNRESOLVED','2VJ',
    'Primary/must-determine phrasing overstates an actual presented appellate issue. Allowed sources establish neither its presentation nor its exclusion, so the serious effect is unresolved rather than a confirmed false issue.')
e['materiality']='Accounting priority and a mandatory further-appellate admissibility decision are not established. Whether this materially distorts the actual presented appeal is unresolved; no hidden target reasoning is used.'

literal=[]
for b,r in labels.items():
    for axis in ['coverage','assertions','serious_errors']:
        for x in r[axis]:
            qs=[x['report_quote']] if axis=='assertions' else x.get('report_quotes',[])
            for q in qs:
                if q not in texts[b]:literal.append(dict(blind_id=b,axis=axis,id=x.get('item_id',x.get('id')),type='REPORT_WITNESS_REVIEW',quote=q))
            for field in ['evidence','source_evidence']:
                for ev in x.get(field,[]):
                    if ev['source_id']=='SCOPE':ev['source_id']='scope'
                    original=view['scope'] if ev['source_id']=='scope' else view['sources'][ev['source_id']]['text']
                    if ev['quote'] not in original:
                        at=original.casefold().find(ev['quote'].casefold())
                        if at>=0:
                            before=ev['quote'];ev['quote']=original[at:at+len(before)]
                            literal.append(dict(blind_id=b,type='CASE_ONLY_SOURCE_WITNESS',before=before,after=ev['quote']))
                        else:literal.append(dict(blind_id=b,axis=axis,id=x.get('item_id',x.get('id')),type='SOURCE_WITNESS_REVIEW',evidence=ev))

write('labels-source-adjudicated-shared-units.json',{k:packet[k] for k in ['case_id','source_view_sha256','reference_sha256']}|{'reports':list(labels.values())})
write('source-adjudication-log.json',dict(at=datetime.now(timezone.utc).isoformat(),decisions=decisions,
    reading='All allowed CASE excerpts, relevant original1940Act definitions/section8,40frozenreferencecriteria/uncertainties, all4reports, all6actually received original annotation axes. No hidden final reasoning or outside legal facts.',
    method_map_opened=False,parent_perfect_blinding_claimed=False,missing_axes=['ECJ-coverage','Z5D-assertions'],
    common_inventory='ECJ68 original units, six explicit semantic duplicates removed in both;07S removes replaced A68 and adds its three actual different assertions. Raw07S62 retained unchanged.',
    model_reference_not_human_gold=True, intervals_not_statistical_CI=True))
write('literal-witness-review.json',literal)
write('pre-unmask-available-axes-freeze.json',dict(at=datetime.now(timezone.utc).isoformat(),method_map_opened=False,
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.glob('*.json')},missing_axes=['ECJ-coverage','Z5D-assertions']))
print(json.dumps(dict(assertion_counts={b:len(r['assertions']) for b,r in labels.items()},literal_review=literal),ensure_ascii=False,indent=2))
