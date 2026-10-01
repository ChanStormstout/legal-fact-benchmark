"""Explore all factual/procedural predicates from an existing input snapshot.

Native syntax is not canonical semantics. Matching a predicate name plus role
names only identifies a syntactically comparable candidate for later review.
"""
import argparse
import csv
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.core import read, digest, write_new, log_run
from legal_bench.development_experiment import prepare, candidate_set, run_patterns, metrics


def native_mapping(annotation):
    return {d["id"]: {"type": "NATIVE::" + d["id"] + "::" + digest(sorted(d["roles"]))[:12],
                       "roles": {key: key for key in d["roles"]},
                       "original_definition": d,
                       "state": "SYNTACTIC_COMPARABILITY_ONLY_SEMANTIC_REVIEW_PENDING"}
            for d in annotation["predicate_definitions"]}


def composition(pattern, views):
    by_case = {a["case_id"]: {e["id"]: e for e in a["events"]} for a in views}
    counts = Counter()
    for r in pattern["results"]:
        for w in r["relation"]["witnesses"]:
            kinds = {by_case[r["case_id"]][aid]["source_assertion"]["kind"] for aid in w["binding"].values()}
            counts["PROCEDURAL_ONLY" if kinds == {"PROCEDURAL_ACT"} else "FACT_ONLY" if kinds == {"FACT"} else "MIXED"] += 1
    return dict(counts)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--snapshot", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    snapshot, out = Path(args.snapshot), Path(args.out)
    if out.exists():
        raise ValueError("Use a new output directory")
    out.mkdir(parents=True)
    start = time.monotonic()
    manifest = read(snapshot / "input-manifest.json")
    config = {"version": "native-syntax-v1", "candidate_budget": 1000, "min_support": 2,
              "input_manifest_hash": digest(manifest), "input_snapshot": str(snapshot),
              "vocabulary": "All FACT and PROCEDURAL_ACT predicates with native predicate and role-name signatures",
              "semantic_comparability": "NOT_ESTABLISHED_BY_MATCHING_NAMES", "reference_scores": None,
              "held_out": False, "policies": ["STRICT_SCOPE", "SCOPE_BLIND_DIAGNOSTIC"],
              "search_order": "Number of constraints, then canonical serialized query; no outcome labels or check-set tuning"}
    write_new(out / "config.json", config)
    summary = {"kind": "EXPLORATORY_NATIVE_SYNTAX_DIAGNOSTIC", "input_manifest_hash": digest(manifest),
               "reference_scores": None, "held_out": False, "runs": {}}
    csv_rows = []
    inputs = [snapshot / "input-manifest.json"]
    for side in ["A", "B"]:
        raw = []
        for item in manifest["annotations"]:
            if item["pass"] != side:
                continue
            path = snapshot / item["snapshot_path"]
            a = read(path)
            if digest(a) != item["annotation_hash"]:
                raise ValueError("Changed input snapshot")
            raw.append(a)
            inputs.append(path)
        write_new(out / side / "mappings.json", {a["case_id"]: native_mapping(a) for a in raw})
        for policy in config["policies"]:
            views = [prepare(a, native_mapping(a), policy) for a in raw]
            write_new(out / side / policy / "views.json", views)
            candidates = candidate_set(views)
            write_new(out / side / policy / "candidates.json", candidates)
            result = run_patterns(views, candidates, config["candidate_budget"], config["min_support"])
            for pattern in result["patterns"]:
                pattern["witness_kind_composition"] = composition(pattern, views)
                csv_rows.append([side, policy, pattern["id"], pattern["support"], pattern["cooccurrence_support"], pattern["unknown"],
                                 pattern["repeated"], pattern["witness_kind_composition"].get("PROCEDURAL_ONLY", 0),
                                 pattern["witness_kind_composition"].get("FACT_ONLY", 0), pattern["witness_kind_composition"].get("MIXED", 0)])
            write_new(out / side / policy / "mining.json", result)
            info = metrics(views, result)
            repeated = [x for x in result["patterns"] if x["repeated"]]
            info["repeated_with_procedural_only_witnesses"] = sum(set(x["witness_kind_composition"]) == {"PROCEDURAL_ONLY"} for x in repeated)
            info["repeated_with_some_fact_witnesses"] = sum(bool(set(x["witness_kind_composition"]) & {"FACT_ONLY", "MIXED"}) for x in repeated)
            summary["runs"][side + "/" + policy] = info
            print(side, policy, info, flush=True)
    with (out / "pattern-summary.csv").open("x", newline="") as handle:
        w = csv.writer(handle)
        w.writerow(["pass", "policy", "pattern_id", "support", "cooccurrence_support", "unknown_cases", "repeated", "procedural_witnesses", "fact_witnesses", "mixed_witnesses"])
        w.writerows(csv_rows)
    summary["state"] = "LOCAL_NATIVE_RUNS_COMPLETE_SEMANTIC_REVIEW_PENDING"
    write_new(out / "summary.json", summary)
    write_new(out / "runtime.json", {"elapsed_seconds": time.monotonic() - start, "paid_API_calls": 0, "web_tasks": 0})
    log_run(out, "native-pattern-diagnostic", inputs + [Path(__file__), Path("legal_bench/development_experiment.py"), Path("legal_bench/engine.py")], [out / "summary.json"])


if __name__ == "__main__":
    main()
