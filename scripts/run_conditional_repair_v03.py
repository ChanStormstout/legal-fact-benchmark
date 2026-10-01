"""Verify field-dependent matching/search, then replay unchanged five-case inputs."""
import argparse
import json
import platform
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.core import read, write_new, digest, log_run
from legal_bench.development_experiment import prepare, candidate_set, run_patterns, run_query, metrics, CONDITIONAL_POLICY
from legal_bench.conditional_engine import candidate_order
from legal_bench.conditional_controls import controls, mappings
from legal_bench import exhaustive_oracle as oracle
from run_native_pattern_diagnostic_v03 import native_mapping, composition


def proof_check(views, candidates):
    failures, comparisons = [], 0
    for serialized in candidates:
        q = json.loads(serialized)
        for view in views:
            result, truth = run_query(view, q), oracle.answer(view, q)
            proposed = {tuple(sorted(w["binding"].items())) for w in result["witnesses"]}
            uncertain = {tuple(sorted(w["binding"].items())) for w in result["uncertain_bindings"]}
            comparisons += 1
            if result["status"] != truth["status"] or proposed != set(truth["matches"]) or uncertain != set(truth["unknown"]):
                failures.append({"case_id": view["case_id"], "query": q, "result": result, "oracle": truth})
    return {"comparisons": comparisons, "failures": failures, "passed": not failures,
            "shared_assumption": "Declared field contract; hand-specified controls test its translation separately"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--snapshot", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--resume", action="store_true")
    args = p.parse_args()
    snapshot, out = Path(args.snapshot), Path(args.out)
    if out.exists() and not args.resume:
        raise ValueError("Use a fresh directory or --resume the unchanged run")
    out.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    manifest, old_config, queries = (read(snapshot / name) for name in ("input-manifest.json", "config.json", "queries.json"))
    code_paths = [Path(__file__)] + [Path("legal_bench") / (name + ".py") for name in
                  ("conditional_engine", "exhaustive_oracle", "conditional_controls", "development_experiment", "engine", "core")]
    code_paths += [Path("scripts/run_native_pattern_diagnostic_v03.py")]
    config = {"version": "conditional-repair-v2", "input_manifest_hash": digest(manifest),
              "mapping_config_hash": digest(old_config), "query_hash": digest(queries),
              "code_hashes": {str(path): digest(path.read_bytes()) for path in code_paths},
              "policy": CONDITIONAL_POLICY, "budget": 1000, "min_support": 2,
              "max_joins": 2, "max_extra_conditions": 1,
              "search_order": "All structural bases, then extensions; join count then canonical string",
              "assumption": "Annotated fields and explicit uncertainty accurate; draft type mappings separately assumed",
              "inference_boundary": "Scoped-record existence, not legal truth/current state/extent equality/group membership",
              "annotation_review": "PENDING_SIDE_CHAT", "held_out": False,
              "native_scope": "Syntactic signatures only, semantic cross-case equivalence unverified"}
    write_new(out / "config.json", config)
    write_new(out / "input-manifest.json", manifest)
    write_new(out / "mapping-config.json", old_config)
    write_new(out / "queries.json", queries)
    for path in code_paths:
        destination = out / "code" / path.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        content = path.read_bytes()
        if destination.exists():
            if destination.read_bytes() != content:
                raise ValueError("Resume code snapshot differs")
        else:
            destination.write_bytes(content)

    def stage(relative, computation):
        path = out / relative
        if path.exists():
            return read(path)
        value = computation()
        write_new(path, value)
        return value

    raw_by_side = {"A": [], "B": []}
    input_paths, verified = [snapshot / "input-manifest.json", snapshot / "config.json", snapshot / "queries.json"], []
    for item in manifest["annotations"]:
        for field, hash_field in (("snapshot_path", "annotation_hash"), ("notes_snapshot_path", "notes_hash")):
            source = snapshot / item[field]
            value = read(source)
            if digest(value) != item[hash_field]:
                raise ValueError("Snapshot changed: " + str(source))
            write_new(out / item[field], value)
            verified.append({"path": str(source), "object_hash": digest(value), "byte_hash": digest(source.read_bytes())})
            input_paths.append(source)
        raw_by_side[item["pass"]].append(read(snapshot / item["snapshot_path"]))
    write_new(out / "input-verification.json", verified)

    fixture = controls()
    write_new(out / "controls/input-and-expected.json", fixture)
    control_views = [prepare(a, mappings(), CONDITIONAL_POLICY) for a in fixture["cases"]]
    hand_results, failures = [], []
    for view, expected in zip(control_views, fixture["expected"]):
        for name, q in fixture["queries"].items():
            result = run_query(view, q)
            entry = {"case_id": view["case_id"], "query_id": name, "expected": expected["statuses"][name], "result": result}
            hand_results.append(entry)
            if result["status"] != entry["expected"]:
                failures.append(entry)
    write_new(out / "controls/matching.json", {"checks": len(hand_results), "failures": failures, "results": hand_results})
    control_candidates = candidate_set(control_views)
    control_oracle = stage("controls/search-oracle.json", lambda: oracle.check(control_views, control_candidates))
    control_proof = stage("controls/execution-oracle.json", lambda: proof_check(control_views, control_candidates))
    control_mining = stage("controls/mining.json", lambda: run_patterns(control_views, control_candidates))
    for pattern in control_mining["patterns"]:
        truth = [oracle.answer(v, pattern["query"]) for v in control_views]
        if pattern["support"] != sum(t["status"] == "MATCH" for t in truth) or pattern["unknown"] != sum(t["status"] == "UNKNOWN" for t in truth):
            raise AssertionError("Control support differs from oracle")
    truncated = run_patterns(control_views, control_candidates, budget=1)
    expected_repeated = [s for s in control_oracle["candidates"]
                         if sum(oracle.answer(v, json.loads(s))["status"] == "MATCH" for v in control_views) >= 2]
    missed = sorted(set(expected_repeated) & set(truncated["frontier"]))
    write_new(out / "controls/truncation.json", {"budget": 1, "executed": truncated["executed"],
                                               "remaining": len(truncated["frontier"]), "missed_repeated_count": len(missed),
                                               "missed_repeated_queries": missed, "frontier": truncated["frontier"]})
    if failures or not control_oracle["exact"] or not control_proof["passed"]:
        raise AssertionError("Independent program controls failed")
    summary = {"controls": {"hand_expected_checks": len(hand_results), "hand_expected_failures": len(failures),
                            "oracle_templates": control_oracle["templates_checked"], "candidates": len(control_candidates),
                            "search_exact": control_oracle["exact"], "execution": control_proof,
                            "repeated": sum(p["repeated"] for p in control_mining["patterns"]),
                            "budget_one_missed_repeated": len(missed)}, "runs": {}, "held_out": False,
               "natural_annotation_accuracy": None, "assumption": config["assumption"]}
    print("Independent controls passed:", summary["controls"], flush=True)

    for side in ("A", "B"):
        raw = raw_by_side[side]
        views = [prepare(a, old_config["mappings"][side][a["case_id"]], CONDITIONAL_POLICY) for a in raw]
        legacy = [prepare(a, old_config["mappings"][side][a["case_id"]], "STRICT_SCOPE") for a in raw]
        write_new(out / side / "core/views.json", views)
        candidates = candidate_set(views)
        write_new(out / side / "core/candidates.json", candidates)
        print(side, "core enumeration", len(candidates), flush=True)
        space = stage(side + "/core/search-oracle.json", lambda: oracle.check(views, candidates))
        proof = stage(side + "/core/execution-oracle.json", lambda: proof_check(views, candidates))
        if not space["exact"] or not proof["passed"]:
            raise AssertionError("Natural structured-input oracle disagreement")
        mining = stage(side + "/core/mining.json", lambda: run_patterns(views, candidates))
        for pattern in mining["patterns"]:
            truth = [oracle.answer(v, pattern["query"]) for v in views]
            if pattern["support"] != sum(t["status"] == "MATCH" for t in truth) or pattern["unknown"] != sum(t["status"] == "UNKNOWN" for t in truth):
                raise AssertionError("Natural support differs from oracle")
        pool = sorted(set(candidates) | set(candidate_set(legacy)), key=candidate_order)
        write_new(out / side / "core/common-candidate-pool.json", pool)
        old_on_pool = stage(side + "/core/legacy-common-pool.json", lambda: run_patterns(legacy, pool))
        new_on_pool = stage(side + "/core/conditional-common-pool.json", lambda: run_patterns(views, pool))
        fixed = []
        for current, previous in zip(views, legacy):
            for item in queries:
                old, new, truth = run_query(previous, item["query"]), run_query(current, item["query"]), oracle.answer(current, item["query"])
                if new["status"] != truth["status"]:
                    raise AssertionError("Fixed query oracle disagreement")
                fixed.append({"case_id": current["case_id"], "query_id": item["id"], "meaning": item["meaning"],
                              "legacy": old, "conditional": new, "oracle": truth})
        write_new(out / side / "core/fixed-queries.json", fixed)
        info = metrics(views, mining)
        info.update(oracle_templates=space["templates_checked"], search_exact=space["exact"], execution_oracle=proof,
                    fixed_legacy_statuses=dict(Counter(r["legacy"]["status"] for r in fixed)),
                    fixed_conditional_statuses=dict(Counter(r["conditional"]["status"] for r in fixed)),
                    fixed_changed=sum(r["legacy"]["status"] != r["conditional"]["status"] for r in fixed),
                    common_pool_size=len(pool), common_pool_legacy_repeated=sum(p["repeated"] for p in old_on_pool["patterns"]),
                    common_pool_conditional_repeated=sum(p["repeated"] for p in new_on_pool["patterns"]))
        # A distinct assertion ID is not proof of a distinct real-world event.
        # Same-type pairs may just repeat a statement; retain them for audit and
        # report that issue instead of inflating meaningful combination counts.
        info["repeated_mixed_type_candidates"] = sum(p["repeated"] and len({a["type"] for a in p["query"]["atoms"]}) > 1
                                                      for p in mining["patterns"])
        info["repeated_same_type_record_pairs_require_coreference_review"] = info["repeated_patterns"] - info["repeated_mixed_type_candidates"]
        write_new(out / side / "core/repeated-with-boundaries.json", [dict(p,
                  event_distinctness="RECORD_IDS_ONLY_NOT_PROVEN_DISTINCT_EVENTS",
                  same_type_pair=len({a["type"] for a in p["query"]["atoms"]}) == 1,
                  interpretation="Candidate record structure, not accepted legal pattern")
                  for p in mining["patterns"] if p["repeated"]])
        summary["runs"][side + "/core"] = info
        print(side, "core passed", info, flush=True)

        native_views = [prepare(a, native_mapping(a), CONDITIONAL_POLICY) for a in raw]
        write_new(out / side / "native/views.json", native_views)
        native_candidates = candidate_set(native_views)
        write_new(out / side / "native/candidates.json", native_candidates)
        print(side, "native generation", len(native_candidates), "executing up to 1000", flush=True)
        native_mining = stage(side + "/native/mining.json", lambda: run_patterns(native_views, native_candidates))
        repeated = []
        for pattern in native_mining["patterns"]:
            if pattern["repeated"]:
                pattern["witness_kind_composition"] = composition(pattern, native_views)
                repeated.append(pattern)
        write_new(out / side / "native/repeated.json", repeated)
        native_info = metrics(native_views, native_mining)
        native_info.update(exhaustive_oracle="NOT_RUN_FOR_FULL_NATIVE_VOCABULARY", semantic_equivalence="NOT_VERIFIED",
                           repeated_with_some_fact_witnesses=sum(bool(set(x["witness_kind_composition"]) & {"FACT_ONLY", "MIXED"}) for x in repeated))
        summary["runs"][side + "/native"] = native_info
        print(side, "native complete", native_info, flush=True)

    summary["state"] = "CONDITIONAL_ALGORITHM_CHECKS_AND_REAL_INPUT_REPLAY_COMPLETE"
    write_new(out / "summary.json", summary)
    runtime = {"elapsed_seconds_this_invocation": time.monotonic() - started, "python": platform.python_version(),
               "paid_API_calls": 0, "web_tasks": 0, "resumed": args.resume}
    if not (out / "runtime.json").exists():
        write_new(out / "runtime.json", runtime)
    write_new(out / "checkpoint.json", {"state": "COMPLETE", "config_hash": digest(config), "summary_hash": digest(summary)})
    for item in verified:
        if digest(Path(item["path"]).read_bytes()) != item["byte_hash"]:
            raise AssertionError("Original input modified")
    log_run(out, "conditional-algorithm-repair", input_paths + code_paths, [out / "summary.json", out / "checkpoint.json"])


if __name__ == "__main__":
    main()
