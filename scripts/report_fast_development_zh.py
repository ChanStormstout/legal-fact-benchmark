"""Render the actual first development run without selecting successful patterns."""
import json
from collections import Counter
from pathlib import Path

root = Path('outputs/development-20-single-pass-v1')
run = root / 'runs/first-run'
read = lambda p: json.loads(p.read_text())
s = read(run / 'summary.json')
d = read(run / 'diagnostics.json')
selection = read(run / 'audit-selection.json')
audit = read(root / 'web-tasks/pattern-audit-001/import-v1/audit.json')
items = {i['id']: i for i in selection['items']}
counts = Counter((items[i['id']]['method'], i['assertions_supported'],
                  i['bindings_supported'], i['relation_holds']) for i in audit['items'])
views = [read(p) for p in (root / 'views').glob('*.json')]
core_blocked = sum(any(set(b['affected_fields']) & {'*', 'type', 'status', 'polarity'}
                       for b in e['field_contract']['blocked'])
                   for v in views for e in v['events'])
fields = Counter(f for v in views for e in v['events']
                 for b in e['field_contract']['blocked'] for f in b['affected_fields'])
model_metadata = [read(p) for p in (root / 'web-tasks').glob('extract-*/submission.json')]
cost = {'extraction_conversations': len(model_metadata), 'cases_per_conversation': 4,
        'extraction_passes_per_case': 1, 'audit_conversations': 1,
        'extraction_prompt_characters': sum(len(p.read_text()) for p in (root / 'web-tasks').glob('extract-*/task.txt')),
        'extraction_reply_characters': sum(len(p.read_text()) for p in (root / 'web-tasks').glob('extract-*/*-result.json')),
        'local_compute_seconds_excluding_serialization': s['elapsed_local_compute_seconds'],
        'paid_api_calls': 0, 'tokens': 'NOT_OBSERVED',
        'observed_setting': 'Ordinary High, not Pro; exact model ID not exposed by UI'}
(run / 'costs.json').write_text(json.dumps(cost, indent=2))
lines = [
    '20-Case Method Development: First Complete Run', '',
    'Conclusion: Single-pass web extraction, local search with two methods and the prespecified small match audit are complete for 20 cases. Exact object joins distinguish identity differences that co-occurrence cannot express in this audit. Evidence covers only the selected matches, not general accuracy, legal value or predictive advantage.', '',
    '1. Data and Actual Completion',
    'Twenty complete judgments were selected in the existing fixed candidate order, all involving tenant eviction or recovery of possession. Confirmed same-dispute duplicates were excluded; uncertain relationships remain flagged. Independence of all 20 cases is not established. These are development data; the formal evaluation set is not frozen.',
    'All 20 cases imported successfully, with 0 pending and 0 failed. Field-constrained computation can use 277 records concerning the main request; 96 records about other requests or related proceedings are stored separately. Deterministic quote-location and object-reference checks passed, which does not establish extraction completeness or semantic correctness.',
    'The 277 records include 167 facts and 110 procedural acts; 191 qualify for candidate generation. Assertions, negations, disputes and unparsed qualifications remain preserved and are not automatically definite positive facts. Model references came from ordinary High mode in ChatGPT Web, not Pro or paid API calls. The exact model ID was not visible and is recorded as unobserved.', '',
    '2. Comparison Design',
    'Case facts use fixed types, roles, object identities, statement statuses and source locations. Co-occurrence checks whether two record types occur; the relational method additionally requires specified roles to refer to the same explicit object. Paired comparisons keep facts, types, statuses and positive conditions identical and remove only object joins. Different record IDs do not imply different physical events.',
    'The prespecified support threshold is at least 2 documents, with at most 1,000 unique candidates per method ordered by canonical query strings. Search covers two records and at most one object join, not time, amounts, outcomes or legally sufficient conditions. Fact types are predefined; automatic fact-category discovery was not evaluated.', '',
    '3. Complete Search Results',
    'Method | Generated candidates | Executed | Query variants supported by at least 2 cases',
]
for method, label in [('cooccurrence', 'Fact-type co-occurrence'), ('relation', 'Shared-object relations')]:
    m = s['methods'][method]
    lines.append('%s | %s | %s | %s' % (label, m['generated'], m['executed'], m['repeated_patterns']))
lines += [
    'Neither search reached its budget. The 205 recurring relational queries span 76 status-qualified record-type combinations, not 205 independent legal concepts. Object roles, procedural stages and related queries create variants; more variants do not imply higher quality. report.txt contains recurring patterns; results.json or its equivalent results.json.gz preserves all candidates, matches and failure traces.',
    'The 450 relational queries across 20 cases produce 9,000 paired judgments: both match in 936; co-occurrence matches but relations find no match in 53; co-occurrence matches but relation information is insufficient in 249; neither finds a match in 2,268; both have insufficient information in 5,494. Units are pattern-by-document pairs, not 9,000 independent samples.',
    'Object joins exclude 995 record combinations counted repeatedly across queries: 663 have explicitly unequal object IDs and 332 have unknown join fields. Deduplicating unordered within-case record pairs leaves 586 pairs. The 995 exclusions are not an error count, and unknown fields do not mean absent facts. Empty results mean only that no match was found in the current records.', '',
    '4. Prespecified Small Audit and Examples',
    'The audit takes the first 3 recurring relational patterns in query order plus 3 other candidates sampled with seed 20260930. For each it examines the first relational match and first additional co-occurrence combination, yielding 9 items. Displayed items were not replaced based on audit results. All web reviews returned and all 9 quotes were locatable.',
    'The model audit supports assertions, role bindings and the specified identity join for 6 relational matches. For 3 additional co-occurrence combinations, assertions and their individual bindings are supported but the specified identity join fails. Several items reuse the same pair of decisions from different court levels. The 6 matches are not 6 independent successful cases, and 6/6 is not overall accuracy.',
    'Example 1: In Achuta Bhat, one decision concerns the group of appellant and second defendant, while another concerns the appellant individually. Co-occurrence detects two eviction decisions; exact identity distinguishes a group from an individual. This does not deny individual membership in the group.',
    'Example 2: In Pooran Chand, leasing the entire building to the father and subletting some rooms can both be true. A query demanding the same exact property object distinguishes part from whole. Containment remains possible; unequal identity does not imply legal irrelevance.',
    'Example 3: A trial eviction decision and appellate restoration of that decision on the same request may share affected parties, beneficiaries and property. This is a traceable procedural structure, not an eviction test or outcome rule.',
    'Audit judgments: ' + str(dict(counts)), '',
    '5. Main Bottlenecks and Next Development Step',
    'First, representation boundaries: group membership and property part-whole relations require explicit relations, not identity alone or forced object merging. Explicit membership/part relations can first be developed on these existing 20 cases while retaining exact identity as a separate condition.',
    'Second, qualification scope: %s records have restrictions on type, status, positivity or the entire record, often leaving queries unknown. Unknown dates constrain only date questions, but the model marked some multi-party or scope qualifications as unparsed, causing conservative whole-record blocking. The next iteration should specify restricted query purposes while preserving sources and old results, without expanding into complete reannotation.' % core_blocked,
    'Field-blocking counts (a record may contribute repeatedly): ' + json.dumps(dict(fields), ensure_ascii=False),
    'Finally, redundancy and purpose: many recurring variants arise from different role joins or court-level descriptions of the same fact/decision pair. Separate factual and procedural structures and deduplicate/group under a shared definition before evaluation; procedural co-occurrence is not a legal condition.',
    'Complete annotation review was not performed, so extraction recall is unmeasured. Without development/evaluation separation, no cross-case generalization advantage can be reported. These 20 cases can support development; final evaluation needs new cases unused in development.', '',
    '6. Costs, Inspectable Files and Acceptance',
    'Five web extraction conversations handled 4 cases each, once per case; one further conversation reviewed 9 matches. Extraction prompts total %s characters and replies %s characters; token counts were not observed. Concurrent web processing differs from local compute time: local search took about %.2f seconds excluding large trace serialization.' % (cost['extraction_prompt_characters'], cost['extraction_reply_characters'], cost['local_compute_seconds_excluding_serialization']),
    'All 122 program-semantics tests passed. Original inputs and experiments remain preserved, together with tasks, raw replies, sources, version hashes, field isolation, candidate budgets, match provenance and failure reasons. Engineering delivery is complete; outperforming co-occurrence was not its acceptance criterion.',
    'Entry points: sample.json and config.json; views/ for per-case computation inputs; web-tasks/ for full extraction/review records; runs/first-run/summary.json, diagnostics.json, costs.json, report.txt and results.json.gz.'
]
(run / 'report-zh.txt').write_text('\n\n'.join(lines) + '\n')
print({'report': str(run / 'report-zh.txt'), 'audit_items': len(audit['items']), 'costs': cost})
