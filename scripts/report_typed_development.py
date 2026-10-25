"""Produce complete, nonselective development results with source-audit limits."""
import json
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256

ROOT=Path('outputs/development-20-typed-relations-v2')
RUN=ROOT/'runs/first-run'
read=lambda p:json.loads(p.read_text())
s=read(RUN/'summary.json');ps=read(RUN/'patterns.json');replay=read(RUN/'prior-audit-binding-replay.json')
audit=read(ROOT/'web-tasks/typed-audit-001/import-v1/audit.json')
validated=read(ROOT/'web-tasks/typed-audit-001/import-v1/validation.json')
assert validated['valid'] and len(audit['items'])==6
audit_counts=Counter((i['assertions_supported'],i['bindings_supported'],i['relation_holds']) for i in audit['items'])
categories={pool:dict(Counter(p['category'] for p in rows if p['repeated'])) for pool,rows in ps['pools'].items()}
changes=Counter()
for p in ps['pools']['typed']:
    for k,v in p['exact_identity_vs_typed_statuses'].items():changes[k]+=v
extra=[x for x in replay if x['previous_method']=='cooccurrence_extra']
recovered=sum(any(v['result']['status']=='MATCH' for v in x['typed_variants']) for x in extra)
lines=[
 '20-Case Method Development: Direct Membership and Part Relations (v2)', '',
 'Completed: reuse of the original 20 cases and 277 events/assertions without re-extraction; addition of source-supported direct object relations; reruns of co-occurrence, exact-identity and new relational queries; and a fixed six-match audit. All results remain development data. No formal evaluation set is frozen and no independent test accuracy is established.', '',
 '1. Changes in This Iteration',
 'same(A,B) requires two roles to reference the same resolved object. part_of(A,B) requires source evidence that A is a direct physical part of B. member_of(A,B) requires explicit membership of person or institution A in party group B. The latter relations are directional and do not imply identity.',
 'Only recorded direct relation evidence is used, without transitive closure. Individuals do not inherit group actions, and property parts do not inherit whole-building legal attributes. Model-added relations do not lift old unknown-field restrictions or qualifications. Missing relation records remain unknown; silence does not prove absence. Source stage is preserved, but queries do not establish that records hold in the same period.', '',
 '2. Sources and Supplementary Review',
 'Seventeen cases contain eligible targets: 10 existing parent-child property pairs and 22 groups already present in main-request records were submitted in one local web task. The other three cases have no such targets but remain in all 20-case computations. Existing objects and source contexts were supplied for itemwise review, without new event annotation.',
 'The web result supports 8 part relations and 9 membership relations, with 2 part relations unknown. Unidentified members do not imply an empty group. Coverage is recorded for all 17 cases and targets; no relations were rejected for formatting, references or quote location. These are model-reference relations, not human gold or a complete relation graph.',
 'The two unknown relations concern a set of eight shops, one shop and the remaining seven. The document does not adequately identify a common physical whole. Membership in a shop collection is not forced into physical part_of; a separate set relation is needed and the status remains unknown.', '',
 '3. Frozen Configuration and Complete Results',
 'The support threshold remains at least two documents, with 1,000 unique candidates per pool ordered by canonical query strings. Facts and statement statuses are shared. Queries use at most two records and one relation condition, not time, amounts, outcomes or legally sufficient conditions. New candidates arise only from sourced direct edges. Candidates, unsearched items, matches, unknowns and failures remain preserved.',
 'Method | Candidates | Executed | Recurring query variants | Display skeleton groups with recurring variants',
]
for pool,label in [('cooccurrence','Fact-type co-occurrence'),('identity','Exact-identity joins'),('typed','New direct membership/part relations')]:
    m=s['pools'][pool];lines.append('%s | %d | %d | %d | %d'%(label,m['generated'],m['executed'],m['repeated'],m['repeated_display_families']))
lines += [
 'None of the three pools reached its budget. Of 65 new queries, 3 have support in two cases and 62 in one. Thresholds and cases were not changed to increase recurrence.',
 'Support counts replay exactly for all 318 old recurring queries: 113 co-occurrence and 205 identity queries. The prior description of 76 status-qualified combinations was inaccurate: that count used record types only. Display grouping now explicitly uses type, statement status and relation operator; the 205 recurring identity queries occupy 96 skeleton groups.',
 'Skeleton groups aid reading only. Same-type record pairs may join beneficiaries, affected parties or property, with different meanings; all role variants remain separate. These are not automatically discovered fact families or proven-equivalent semantic clusters.',
 'Recurring queries classified by declared record type:'+json.dumps(categories,ensure_ascii=False),
 'Among identity queries, 62 contain only procedural acts, 93 mix facts and procedure, and 50 contain facts only. Procedural structures are not legal elements or outcome rules.', '',
 '4. All New Recurring Patterns',
]
for p in ps['pools']['typed']:
    if p['repeated']:
        lines += ['Query ID '+p['id']+'; support '+str(p['support'])+' cases; '+p['category'],json.dumps(p['query'],ensure_ascii=False)]
lines += [
 'The three structures express: subleased property is part of property described in an ownership record; a person initiating separate proceedings belongs to the respondent group in an eviction request; and a lease tenant belongs to that group. These are traceable record structures, not proof that ownership and subletting were simultaneous or that eviction is legally justified.', '',
 '5. Treatment of the Three Additional Co-occurrence Combinations',
 'All three still fail the original exact-identity condition, but now have direct membership or part relations. Original identity judgments remain unchanged; new relations answer a different, explicitly defined question.',
 'The appellant is not identical to the group comprising appellant and second defendant, but belongs to it. Sublet rooms are not identical to the whole building, but are part of it. The ground floor sought to be vacated similarly links by part relation to the building in the ownership record. Unequal identity does not mean unrelated, and membership/part relations do not mean identity.',
 'Fixed-combination replay finds direct relations in %s/%s items. This is a design check on known error-analysis material, not a new-sample result.'%(recovered,len(extra)),
 'Paired status counts for exact identity and directional relations across 65 new queries and 20 cases:'+json.dumps(dict(changes),ensure_ascii=False),
 'Different operators answer different questions; changed statuses and additional matches do not establish accuracy gains.', '',
 '6. Fixed Small Source Audit',
 'The first three recurring new queries plus three other queries sampled with a fixed seed each contribute their first match, yielding six items. All replies returned and all quotes were locatable. Assertion, role-binding and direct-relation judgments:'+str(dict(audit_counts)),
 'All six items have source support: three recurring-query matches and three single-case matches. Several reuse the same case/object relation. A new review conversation still uses the same model and is not independent human validation; 6/6 is not overall accuracy.',
]
for i in audit['items']:
    lines.append(i['id']+' | assertions='+i['assertions_supported']+' | bindings='+i['bindings_supported']+' | relation='+i['relation_holds']+' | '+i['explanation'])
lines += [
 '', '7. Remaining Gaps and Next Iteration',
 'New relations connect already extracted objects but do not repair missing facts, misunderstood statement status, unresolved identity or arbitrary qualifications. The 1,300 document judgments for new queries contain 68 matches, 872 unknowns and 360 NOT_FOUND results. Unknowns reflect both old record restrictions and incomplete new-edge coverage, not necessarily poor annotation.',
 'Next distinguish unknowns caused by absent source information, unresolved extraction, purpose-specific qualifications and missing object-relation types. Apply limited purpose restrictions to unusable records while retaining the conservative version. Define element-of-set and subset relations separately when needed; do not conflate them with physical parts or individual membership.',
 'Before improving computational coverage, do not treat pattern-count growth or outcome prediction as success. Continue development on these 20 cases, then evaluate generalization on new cases.', '',
 '8. Engineering Acceptance and Files',
 'All 138 program tests passed, including 16 new tests for direction, unknowns, conflicts, no transitive inference, no group-action inheritance, persistent old restrictions and reference integrity. All event/evidence/relation references resolve across 14,540 trace rows.',
 'Original input hashes match the prior run and old results remain preserved. Full traces now reference cases/events/relations; inputs/ stores source text, fields and relation evidence once. traces.jsonl.gz is approximately %.2f MB, retaining all failures and unknowns rather than only successful examples.'%(RUN.joinpath('traces.jsonl.gz').stat().st_size/1e6),
 'This run used one relation-supplement conversation and one fixed-match review conversation, both ordinary High rather than Pro, with 0 paid API calls. The exact model ID was not visible. Relation tasks contain 257,004 characters and replies 69,100; review tasks contain 86,211 and replies 9,897. Local execution took approximately %.2f seconds.'%(s['elapsed_local_seconds']),
 'Entry points: config.json, input-manifest.json; relations/ for per-case relations; web-tasks/ for raw tasks, replies, URLs, screenshots and quote checks; runs/first-run/patterns.json, candidates.json, traces.jsonl.gz, prior-audit-binding-replay.json and artifact-validation.json.',
]
(RUN/'report-zh.txt').write_text('\n\n'.join(lines)+'\n')
complete_listing=[]
for pool,rows in ps['pools'].items():
    for p in rows:
        complete_listing.append('%s | %s | support=%s | repeated=%s | family=%s | %s'%(pool,p['id'],p['support'],p['repeated'],p['family_id'],json.dumps(p['query'],ensure_ascii=False)))
(RUN/'all-patterns.txt').write_text('\n'.join(complete_listing)+'\n')
status={'completed_at':datetime.now(timezone.utc).isoformat(),'cases':20,'unchanged_events':277,
        'targeted_enrichment_complete':True,'typed_query_audit_complete':True,'audit_items':6,
        'held_out':False,'formal_check_set_frozen':False,'independence_proven':False,
        'tests_passed':138,'prior_repeated_query_supports_replayed':318,
        'trace_rows_validated':14540,'source_reference_kind':'WEB_MODEL_REFERENCE_NOT_HUMAN_GOLD',
        'report':str(RUN/'report-zh.txt'),'config_hash':s['config_hash'],
        'code_hashes':{p:sha256(Path(p).read_bytes()).hexdigest() for p in ['legal_bench/typed_relations.py','scripts/run_typed_development.py','scripts/prepare_typed_relations.py','tests/test_typed_relations.py']}}
(ROOT/'status-complete-v1.json').write_text(json.dumps(status,indent=2))
print({'report':str(RUN/'report-zh.txt'),'audit_counts':dict(audit_counts),'recovered_known_combinations':recovered,'repeated_categories':categories})
