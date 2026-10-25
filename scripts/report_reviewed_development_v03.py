"""Summarize source-reviewed development results and trace prior changes."""
import argparse
import copy
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.core import read, write_new, digest, log_run
from legal_bench.scoped_mining import mine


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--prior', default='outputs/benchmark-pilot-v03/experiments/conditional-repair-v2')
    args = parser.parse_args()
    root, prior = Path(args.run), Path(args.prior)
    summary = read(root / 'summary.json')
    traces = {}
    for side in ['A', 'B']:
        views = read(root / side / 'CORE/views.json')
        by_case = {v['case_id']: v for v in views}
        old = read(prior / side / 'core/mining.json')
        # Exactly the prior executed candidate set, with legal states retained
        # in this diagnostic only, isolates updated permissions and input view.
        candidates = [json.dumps(p['query'], ensure_ascii=False, sort_keys=True, separators=(',', ':')) for p in old['patterns']]
        result = mine(views, candidates=candidates)
        write_new(root / side / 'CORE/review-only-prior-candidates.json', result)
        updated = {p['id']: p for p in result['patterns']}
        entries = []
        for pattern in old['patterns']:
            if not pattern['repeated']:
                continue
            new = next(p for p in result['patterns'] if {k: v for k, v in p['query'].items() if k != 'mode'} == pattern['query'])
            lost = []
            for item in new['results']:
                original = next(x for x in pattern['results'] if x['case_id'] == item['case_id'])
                if original['relation']['status'] == 'MATCH' and item['relation']['status'] != 'MATCH':
                    lost.append({'case_id': item['case_id'], 'previous_witnesses': original['relation']['witnesses'],
                                 'reviewed_status': item['relation']['status'],
                                 'reviewed_uncertain_bindings': item['relation']['uncertain_bindings'],
                                 'reviewed_rejected_bindings': item['relation']['rejected_bindings'],
                                 'answer_boundary': 'This is not evidence the original real-world pattern is absent'})
            entries.append({'query': pattern['query'], 'previous_support': pattern['support'], 'reviewed_support': new['support'],
                            'reviewed_unknown_cases': new['unknown'], 'lost_matches': lost})
        traces[side] = {'previous_repeated': sum(p['repeated'] for p in old['patterns']),
                        'reviewed_repeated_on_exact_prior_candidates': sum(p['repeated'] for p in result['patterns']),
                        'pattern_changes': entries, 'scope': 'All CORE profile records including legal-state diagnostics; no new candidates'}
    write_new(root / 'previous-pattern-change-trace.json', traces)
    atlas_a, atlas_b = (read(root / side / 'ATLAS/repeated-with-evidence.json') for side in ['A', 'B'])
    a_ids, b_ids = {p['id'] for p in atlas_a}, {p['id'] for p in atlas_b}
    agreement = {'common_repeated_candidate_ids': sorted(a_ids & b_ids), 'A_only': sorted(a_ids - b_ids), 'B_only': sorted(b_ids - a_ids),
                 'interpretation': 'Independent extraction/reference-process diagnostic; not accuracy or independent cases'}
    write_new(root / 'AB-pattern-overlap.json', agreement)
    lines = ['Legal AI: Source-Review Integration and Five-Case Development', '',
             'Conclusion: Review decisions are integrated, types and roles standardized under explicit task definitions, and five-case queries and pattern searches complete. The possession/lease CORE vocabulary yields no candidates recurring in two cases. The expanded vocabulary yields recurring candidates, mostly procedural structures. Independent finite-language checks passed; these results do not establish legally valuable factual regularities.', '',
             '1. How Review Results Enter Computation', '',
             'Review decisions are retained for all 401 original factual/procedural records. Of these, 212 permit limited use; 12 approve only the proposition core, not object joins. Original files, paragraph-content hashes and review versions are checked per case; all ten inputs match the side-conversation snapshots. Unknown and exclusion decisions remain preserved. Suggested model rewrites were not applied automatically and annotations were not redone.',
             'Original field values remain traceable; only approved_fields enter execution and candidate generation. Role renaming carries permissions and unknown reasons with it and cannot reauthorize an object. Exact times and amounts were not approved, so dates or amounts present in the original JSON do not enter those comparisons.',
             'For example, suit record a6 in 755721 B retains property=o5, but only its event core is approved. Mapping it to SUIT_FILING_RECORD does not authorize property joins using o5. Record a35 in 184866874 B explicitly describes an A.S. appeal and maps to APPEAL_FILING_RECORD; a3/a31 are O.S. suit records. Administrative requests were not classified as suits.', '',
             '2. Type Standardization and Search Scope', '',
             'type-cards.json and each registry.json preserve 14 task types, original definitions, role mappings, use limits and input hashes. LEASE_PROPERTY, EXECUTE_LEASE and LET_PROPERTY map to a weaker lease-record type without claiming strict equivalence or event identity. Three business-activity names are standardized from source definitions. Rent amounts do not become actual payments, receiving notice does not become replying, and the trial court does not become the appellate court.',
             'CORE serves the original possession/lease queries; ATLAS adds business and procedural acts from a predefined type list; NATIVE retains original predicates/roles as a syntactic control. Fixed CORE queries retain legal-status records; observable-event search in CORE/ATLAS excludes them separately. NATIVE retains original types without treating all as physical events. ATLAS was not selected for performance and all candidates are preserved.',
             'Search uses two distinct records, one or two shared-object joins and at most one approved time/attribute condition. No time/attribute fields are approved here, so only structural conditions are generated. Support is counted by case, not records or matches. A/B run separately and cannot be combined into ten cases. Distinct record IDs do not prove distinct events; same-type pairs and court-only joins are listed separately.', '',
             '3. Fixed Development Queries', '']
    for side in ['A', 'B']:
        info = summary['runs'][side + '/CORE']
        lines += ['%s: eight queries across five cases yield 40 judgments, with statuses %s; %d statuses differ from the earlier run assuming accurate input fields.' %
                  (side, info['fixed_statuses'], info['changed_after_source_review'])]
    lines += ['Q1/Q2 test shared property and tenant-payer identity between payment and lease records; Q3 tests possession/lease property; Q4/Q5 involve rights status and possession; Q6 tests possession/suit property; Q7 tests loss-of-possession/possession property; Q8 additionally requires lease-before-suit timing. Natural-language meanings remain unchanged; definitions were not adjusted to increase matches.',
              'Q8 remains unknown where relevant records exist but timing is unapproved. Some formerly definite results are withdrawn; some NOT_FOUND results become UNKNOWN because required identity or status fields were not approved. NOT_FOUND means no match in currently usable records, not absence in the source or reality. fixed-query-statuses.csv and per-item JSON preserve every result and its evidence.', '',
              '4. Pattern Search Results', '', 'Version/scope | Generated and executed candidates | Candidates recurring in at least two cases | Recurring candidates containing factual records']
    for side in ['A', 'B']:
        for profile in ['CORE', 'ATLAS', 'NATIVE']:
            info = summary['runs'][side + '/' + profile]
            lines.append('%s %s | %d/%d | %d | %d' % (side, profile, info['generated'], info['executed'], info['repeated'], info['repeated_with_fact_witnesses']))
    lines += ['', 'All generated candidates fit within the 1,000-candidate budget, without truncation. ATLAS yields 22/7 recurring candidates for A/B: 20/6 contain only procedural acts and 2/1 mix facts with procedure. No purely factual combination reaches two-case support. Court-only joins account for 4/2; A also has 7 same-type record pairs that may reflect repeated descriptions or stages, not established distinct events. Categories overlap and cannot be subtracted to count remaining valid patterns.',
              'A/B share %d recurring candidates. Extraction differences and field-approval scope still change discovery results.' % len(a_ids & b_ids),
              'An example present in both annotations links a possession record and a judgment-reversal record to the same property ID in 1064407 and 184866874. This establishes only that those scoped records share an object, not a request or period, lawful possession or entitlement to win. A also has a two-case tenant-appellant identity candidate, mainly reflecting procedural participation.',
              'The earlier conditional run yielded 6/3 recurring CORE candidates for A/B. On the same old candidate sets with reviewed records, both counts become 0. previous-pattern-change-trace.json explains why each old instance loses definite support. This does not prove the patterns absent: restrictions, unapproved joins, uncertain sources or missing comparable facts may explain the change.', '',
              '5. Engineering Validation and Interpretation', '',
              'The independent enumerator checks 827 templates per CORE side and 6,527/5,032 ATLAS templates. Candidates with definite instances exactly match the searcher. Execution statuses, definite/unknown bindings and support counts agree across all scopes. NATIVE checks every generated candidate, without claiming exhaustive coverage of its language. Program independence is not source-review independence or proof of legal usefulness.',
              'All 91 local tests passed. Added checks cover permission-preserving role renaming, unapproved known dates remaining unusable, unknown source roles staying restricted after renaming, double-join enumeration, per-case counting and unchanged inputs. Synthetic cases validate programs; these five real development cases are not an independent 20-case evaluation set.',
              'Relation and co-occurrence methods yield different statuses, but no independent per-query answers are available. Differences are therefore not counted as errors or accuracy. Source reviews are source-checked model references, not human gold. No outcome-label training, paid API calls or new web tasks occurred.', '',
              '6. Next Step', '',
              'Integration, task-type standardization and development execution are complete. A 20-case freeze still requires a fixed request type and sampling unit. The current mix of leases, acquisition, trusts and management rights tests workflow, but recurring procedural patterns do not establish reusable factual abstraction across comparable cases. Select the next cases by source completeness and dispute grouping, not prediction success or pattern occurrence.',
              'The prespecified comparison of direct model reading, model-structured answering and the executor remains to run under a frozen configuration; this report covers local program experiments only. Do not rewrite these five cases or adjust support thresholds to manufacture patterns. Make versioned, evidenced local corrections only when fixed queries require corrections already identified in the review list; do not re-extract everything.', '',
              'Reproduce: python3 scripts/run_reviewed_development_v03.py --out NEW_DIRECTORY',
              'Resume with the same arguments and --resume; changed input/code hashes prevent reuse.',
              'Report: python3 scripts/report_reviewed_development_v03.py --run RUN_DIRECTORY']
    content = '\n'.join(lines) + '\n'
    path = root / 'report-v2.txt'
    if path.exists() and path.read_text() != content:
        raise ValueError('Refuse to overwrite a changed report')
    if not path.exists():
        path.write_text(content)
    log_run(root, 'report-reviewed-development', [root / 'summary.json', Path(__file__)],
            [path, root / 'previous-pattern-change-trace.json', root / 'AB-pattern-overlap.json'])
    print(path)


if __name__ == '__main__':
    main()
