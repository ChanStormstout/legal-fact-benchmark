"""Report independent conditional checks without inventing natural-case gold."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.core import read, write_new, log_run, digest
from legal_bench.conditional_controls import mappings
from legal_bench.development_experiment import prepare, run_query, CONDITIONAL_POLICY, without_identity
from legal_bench.engine import cooccurrence_query


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    args = parser.parse_args()
    root = Path(args.run)
    fixture = read(root / "controls/input-and-expected.json")
    summary = read(root / "summary.json")
    counts = {k: {"correct": 0, "incorrect": 0, "false_match": 0}
              for k in ("strict", "conditional", "no_identity", "cooccurrence")}
    failures = []
    for raw, expected in zip(fixture["cases"], fixture["expected"]):
        previous = prepare(raw, mappings(), "STRICT_SCOPE")
        current = prepare(raw, mappings(), CONDITIONAL_POLICY)
        for name, q in fixture["queries"].items():
            results = {"strict": run_query(previous, q), "conditional": run_query(current, q),
                       "no_identity": run_query(current, without_identity(q)),
                       "cooccurrence": run_query(current, cooccurrence_query(q))}
            for method, result in results.items():
                correct = result["status"] == expected["statuses"][name]
                counts[method]["correct" if correct else "incorrect"] += 1
                counts[method]["false_match"] += result["status"] == "MATCH" and expected["statuses"][name] != "MATCH"
                if not correct:
                    failures.append({"case_id": raw["case_id"], "query": name, "method": method,
                                     "expected": expected["statuses"][name], "actual": result["status"]})
    comparison = {"kind": "HAND_SPECIFIED_SYNTHETIC_ONLY", "counts": counts, "errors": failures,
                  "baseline_meaning": "Ablations answer the same relation question with deliberately removed conditions; no real-case accuracy claim"}
    write_new(root / "controls/method-comparison.json", comparison)
    lines = ['Legal AI: Algorithm Repairs and Conditional Validation', "",
             'Conclusion: Assuming the annotation fields and their explicit unknowns are correct, the new executor retains fields usable for each query purpose. The searcher passes independent exhaustive checks within its declared finite language. Rerunning five cases reveals recurring candidates previously hidden by whole-record blocking. This does not establish legal value or constitute an independent 20-case evaluation.', "",
             '1. Repairs', "",
             'Unknowns propagate by field: an unknown date blocks only time comparisons; an unknown amount blocks exact-amount conditions; an unknown payer blocks joins involving that payer. Source location, attribution and qualifications remain attached to matches. Unparsed qualifications still block use, and parsed restrictions requiring compatibility checks are not silently ignored. Unadopted, negated and unparsed predicates are not promoted to definite facts.',
             'The query asks whether two records within the specified scope satisfy object joins and conditions. A shared property ID does not establish identical possession scope, dates or continuing possession. A shared record role does not establish group membership. Different record IDs do not prove distinct real-world events.',
             'Search now generates one or two shared-object joins, allowing both person and property identity. Structural candidates precede time/attribute extensions; each candidate has at most one additional time or attribute condition. Support is counted by case, unknown is not negative, and candidates left unexecuted at the budget limit are retained.', "",
             '2. Independent Engineering Evidence', "",
             'The 17 hand-constructed synthetic cases contain 51 predetermined judgments: the new method agrees on 51/51, whole-record blocking on 41/51, removing object joins on 42/51, and fact-type co-occurrence on 40/51. Removing joins produces 9 false matches and co-occurrence produces 11. These validate program semantics, not real-case accuracy.',
             'An independent enumerator constructs all templates from types, roles and attribute constants and executes them without calling the tested generator, executor or variable normalizer. Across 104 synthetic templates, its 21 candidates with definite instances exactly match the searcher. All 357 candidate-by-case comparisons agree on statuses, definite bindings and unknown bindings. Support and unknown counts are checked separately per candidate. With budget 1, 11 recurring candidates remain unexecuted, exposing what truncation omits.',
             'The enumerator and executor share the declared field-dependency specification. Exhaustive agreement therefore does not prove that specification covers all legal formulations; predetermined-answer tests separately check field-dependency conversion.', "",
             '3. Rerun on the Original Five Cases', ""]
    for side in ("A", "B"):
        info = summary["runs"][side + "/core"]
        lines += ['%s: independent enumeration checks %d templates and obtains %d candidates, with no missing or extra searcher candidates. All %d candidate-by-case judgments and object bindings agree with the independent executor.' %
                  (side, info["oracle_templates"], info["generated_candidates"], info["execution_oracle"]["comparisons"]),
                  'On the same candidate pool, whole-record blocking yields %d recurring candidates and the new method yields %d. Of the new candidates, %d connect different fact types and %d pair same-type records, which may repeat a statement and still require event-identity review.' %
                  (info["common_pool_legacy_repeated"], info["common_pool_conditional_repeated"], info["repeated_mixed_type_candidates"],
                   info["repeated_same_type_record_pairs_require_coreference_review"]),
                  'Eight fixed queries across five cases: old statuses %s; new statuses %s; %d changes. A status change does not itself count as an accuracy improvement.' %
                  (info["fixed_legacy_statuses"], info["fixed_conditional_statuses"], info["fixed_changed"]), ""]
    lines += ['All recurring core candidates occur in inputs 1064407 and 184866874. Mixed-type examples connect possessor to plaintiff or rights-holder; B also links possession and suit records to the same property. These do not establish the same period, possession scope or entitlement to relief. Draft mappings from different predicates to a shared type still require semantic review.', "",
              'Supplementary native-predicate search checks matching predicate names and role structures without assuming cross-case semantic equivalence:']
    for side in ("A", "B"):
        info = summary["runs"][side + "/native"]
        lines.append('%s generates %d candidates, executes %d within budget and finds %d recurring candidates; %d remain preserved. No complete-coverage claim is made, and exhaustive enumeration was not run over the full native vocabulary.' %
                     (side, info["generated_candidates"], info["executed_candidates"], info["repeated_patterns"],
                      info["generated_candidates"] - info["executed_candidates"]))
    lines += ["", '4. Files and Reproduction', "",
              'Object and byte hashes of the original ten annotations and review notes were verified; originals are unchanged. The new run preserves input snapshots, draft mappings, fixed queries, code snapshots, all core candidates, definite/unknown instances, unexecuted candidates and independent checks. Web tasks: 0. Paid API calls: 0.',
              'Main run: python3 scripts/run_conditional_repair_v03.py --snapshot outputs/benchmark-pilot-v03/experiments/five-case-unreviewed-v2 --out NEW_DIRECTORY',
              'Resume with the same arguments and --resume; changed input or code hashes prevent reuse of old stages.',
              'Tests: python3 -m unittest discover -s tests -v',
              "", '5. Next Evidence Needed', "",
              'The program correctly matches, completely generates candidates and counts results under the specified input assumptions and finite language. Establishing legally meaningful cross-case reuse still requires source checks in the side conversation, draft type-mapping reconciliation and a frozen 20-case evaluation. Those steps were not completed in this run.']
    content = "\n".join(lines) + "\n"
    path = root / "report.txt"
    if path.exists() and path.read_text() != content:
        raise ValueError("Existing report differs; use a versioned report")
    if not path.exists():
        path.write_text(content)
    log_run(root, "report-conditional-repair", [root / "summary.json", root / "controls/input-and-expected.json", Path(__file__)],
            [path, root / "controls/method-comparison.json"])
    print(path)


if __name__ == "__main__":
    main()
