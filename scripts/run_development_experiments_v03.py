"""Snapshot and run five-case local diagnostics; reference review is external."""
import argparse
import copy
import csv
import json
import platform
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.core import read, write_new, digest, canonical, log_run
from legal_bench.development_experiment import prepare, candidate_set, run_query, run_patterns, metrics, without_identity
from legal_bench.engine import cooccurrence_query
from legal_bench.annotation_v2 import validate
from audit_dev_annotations_v03 import latest_path


def mapping_config(annotations):
    # These are engineering hypotheses for a draft task vocabulary. No semantic
    # labels or review approvals are inferred from spelling or field presence.
    specs = {
        "OCCUPY_PROPERTY": ("OCCUPATION_RECORD", {"occupant": ["occupant"], "property": ["property"]}),
        "POSSESS_PROPERTY": ("OCCUPATION_RECORD", {"occupant": ["occupant", "possessor"], "property": ["property"]}),
        "OWN_PROPERTY": ("TITLE_OR_OWNERSHIP_RECORD", {"holder": ["owner"], "property": ["property"]}),
        "HAVE_TITLE": ("TITLE_OR_OWNERSHIP_RECORD", {"holder": ["subject", "holder"], "property": ["property"]}),
        "HAVE_TITLE_TO_PROPERTY": ("TITLE_OR_OWNERSHIP_RECORD", {"holder": ["holder"], "property": ["property"]}),
        "LEASE_PROPERTY": ("LEASE_RECORD", {"landlord": ["lessor"], "tenant": ["lessee"], "property": ["property"]}),
        "EXECUTE_LEASE": ("LEASE_RECORD", {"landlord": ["landlord"], "tenant": ["tenant"], "property": ["property"]}),
        "LET_PROPERTY": ("LEASE_RECORD", {"landlord": ["lessor"], "tenant": ["lessee", "tenant"], "property": ["property"]}),
        "PAY_RENT": ("RENT_PAYMENT_RECORD", {"payer": ["payer"], "payee": ["payee"], "property": ["property"]}),
        "FILE_SUIT": ("SUIT_FILING_RECORD", {"filer": ["filer"], "property": ["property"], "court": ["court"]}),
        "FILE_POSSESSION_SUIT": ("SUIT_FILING_RECORD", {"filer": ["party", "filer"], "property": ["property"]}),
        "FILE_PROCEEDING": ("SUIT_FILING_RECORD", {"filer": ["filer"], "property": ["property"], "court": ["court"]}),
        "DISPOSSESS_FROM_PROPERTY": ("DISPOSSESSION_RECORD", {"actor": ["actor"], "dispossessed": ["dispossessed"], "property": ["property"]}),
        "SURRENDER_POSSESSION": ("SURRENDER_RECORD", {"surrenderer": ["surrendering_party", "subject"], "recipient": ["recipient"], "property": ["property"]}),
    }
    result = {"version": "draft-engineering-record-v1", "state": "UNREVIEWED_ENGINEERING_HYPOTHESIS",
              "created_at": datetime.now(timezone.utc).isoformat(), "budget": 1000, "min_support": 2,
              "case_grouping": "PENDING", "reference_answers": "PENDING_SIDE_CHAT", "mappings": {},
              "policies": {"STRICT_SCOPE": "Any unresolved field or nonempty unreviewed scope blocks the record; missing dates block temporal constraints only",
                           "SCOPE_BLIND_DIAGNOSTIC": "Ignore the computational effect of nonempty scope, retain original scope in traces. Unsafe diagnostic only; existing unresolved fields still block."},
              "limits": ["Mappings are draft abstractions, not learned or reviewed canonical clusters",
                         "Ownership/title and lease acts are grouped only for these record-level queries; original subtypes remain in trace",
                         "Neither policy is an end-to-end verified model evaluation",
                         "Distinct assertion IDs do not establish distinct physical events",
                         "No legal outcome labels, prediction, or held-out checks"]}
    for side, corpus in annotations.items():
        result["mappings"][side] = {}
        for a in corpus:
            local = {}
            for d in a["predicate_definitions"]:
                if d["id"] not in specs:
                    continue
                typ, choices = specs[d["id"]]
                roles = {}
                for target, names in choices.items():
                    available = [name for name in names if name in d["roles"]]
                    if len(available) > 1:
                        raise ValueError("Ambiguous role mapping: %s" % d["id"])
                    if available:
                        roles[target] = available[0]
                rule = {"type": typ, "roles": roles, "original_definition": copy.deepcopy(d),
                        "justification": "Explicit draft task grouping by source definition; semantic verification pending"}
                if d["id"] == "FILE_PROCEEDING":
                    rule["attribute_guard"] = {"field": "proceeding", "pattern": r"^O\.S\."}
                local[d["id"]] = rule
            result["mappings"][side][a["case_id"]] = local
    return result


def query_config():
    def pair(left, right, joins, temporal=False):
        constraints = [{"op": "different", "left": "a.id", "right": "b.id"}]
        constraints += [{"op": "same", "left": "a.roles." + x, "right": "b.roles." + y} for x, y in joins]
        if temporal:
            constraints.append({"op": "before", "left": "a.time", "right": "b.time"})
        return {"atoms": [{"var": "a", "type": left}, {"var": "b", "type": right}], "constraints": constraints}
    tuples = [
        ("Q1", "租赁记录与实际付租记录连接到同一财产对象", "LEASE_RECORD", "RENT_PAYMENT_RECORD", [("property", "property")], False),
        ("Q2", "租赁记录中的租客与付租记录中的付款人是同一对象，且财产相同", "LEASE_RECORD", "RENT_PAYMENT_RECORD", [("tenant", "payer"), ("property", "property")], False),
        ("Q3", "占有记录与租赁记录连接到同一财产对象；不判断同时发生", "OCCUPATION_RECORD", "LEASE_RECORD", [("property", "property")], False),
        ("Q4", "产权记录与占有记录连接到同一财产对象；不推断占有人拥有该财产", "TITLE_OR_OWNERSHIP_RECORD", "OCCUPATION_RECORD", [("property", "property")], False),
        ("Q5", "产权记录的权利人与占有记录的占有人相同，且财产相同；不判断同时发生", "TITLE_OR_OWNERSHIP_RECORD", "OCCUPATION_RECORD", [("holder", "occupant"), ("property", "property")], False),
        ("Q6", "占有记录与起诉记录连接到同一财产对象；不推断该事实就是诉因", "OCCUPATION_RECORD", "SUIT_FILING_RECORD", [("property", "property")], False),
        ("Q7", "剥夺占有记录与占有记录连接到同一财产对象；不推断涉及同一占有人或同一时期", "DISPOSSESSION_RECORD", "OCCUPATION_RECORD", [("property", "property")], False),
        ("Q8", "租赁记录的明确事件日期早于同一财产的起诉日期", "LEASE_RECORD", "SUIT_FILING_RECORD", [("property", "property")], True),
    ]
    return [{"id": qid, "meaning": meaning, "query": pair(left, right, joins, temporal),
             "answer_scope": "Existing model-attributed adopted records; reference answers pending",
             "not_found_meaning": "No matching recorded binding, not real-world absence"}
            for qid, meaning, left, right, joins, temporal in tuples]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="outputs/benchmark-pilot-v03")
    parser.add_argument("--out", required=True)
    parser.add_argument("--snapshot", help="Replay an existing manifest/config without reading live annotation versions")
    args = parser.parse_args()
    root, out = Path(args.root), Path(args.out)
    if out.exists():
        raise ValueError("Use a new output directory; completed batches must not be overwritten")
    out.mkdir(parents=True)
    started = time.monotonic()
    corpora = {"A": [], "B": []}
    records = []
    if args.snapshot:
        previous = Path(args.snapshot)
        config, queries, manifest = read(previous / "config.json"), read(previous / "queries.json"), read(previous / "input-manifest.json")
        for item in manifest["annotations"]:
            path = previous / item["snapshot_path"]
            ann = read(path)
            if digest(ann) != item["annotation_hash"]:
                raise ValueError("Changed annotation snapshot")
            corpora[item["pass"]].append(ann)
            write_new(out / item["snapshot_path"], ann)
        for item in manifest["sources"]:
            src = read(previous / item["snapshot_path"])
            if digest(src) != item["object_hash"]:
                raise ValueError("Changed source snapshot")
            write_new(out / item["snapshot_path"], src)
        for item in manifest["annotations"]:
            notes = read(previous / item["notes_snapshot_path"])
            if digest(notes) != item["notes_hash"]:
                raise ValueError("Changed notes snapshot")
            write_new(out / item["notes_snapshot_path"], notes)
    else:
        catalog = read(root / "development-source-catalog-v1.json")
        sources = []
        for entry in catalog["cases"]:
            case = entry["case_id"]
            source = read(entry["source_path"])
            if digest(source["segments"]) != entry["source_text_sha256"]:
                raise ValueError("Source hash mismatch")
            spath = "inputs/sources/%s.json" % case
            write_new(out / spath, source)
            sources.append({"case_id": case, "original_path": entry["source_path"], "snapshot_path": spath,
                            "source_text_hash": entry["source_text_sha256"], "object_hash": digest(source)})
            for side in ["A", "B"]:
                path = latest_path(root, case, side)
                ann, notes = read(path), read(path.parent / "review_notes.json")
                checks = validate(ann, notes, source)
                if not checks["valid"]:
                    raise ValueError("Cannot run structurally invalid annotation: %s" % path)
                snapshot = "inputs/%s/%s/annotation.json" % (side, case)
                npath = "inputs/%s/%s/review_notes.json" % (side, case)
                write_new(out / snapshot, ann)
                write_new(out / npath, notes)
                corpora[side].append(ann)
                records.append({"case_id": case, "pass": side, "original_path": str(path),
                                "snapshot_path": snapshot, "notes_snapshot_path": npath,
                                "annotation_hash": digest(ann), "notes_hash": digest(notes), "structurally_valid": True})
        config = mapping_config(corpora)
        queries = query_config()
        manifest = {"annotations": records, "sources": sources, "split_state": "DEVELOPMENT_CANDIDATES_NOT_FROZEN_CHECK_SET",
                    "reference_state": "PENDING_SIDE_CHAT", "independent_dispute_groups": "PENDING"}
    write_new(out / "config.json", config)
    write_new(out / "queries.json", queries)
    write_new(out / "input-manifest.json", manifest)
    # Persist configuration and exact input snapshots before any experiment.
    write_new(out / "checkpoint-start.json", {"state": "INPUTS_SNAPSHOTTED", "config_hash": digest(config),
                                               "query_hash": digest(queries), "manifest_hash": digest(manifest)})
    summary = {"experiment": "FIVE_CASE_LOCAL_DEVELOPMENT_DIAGNOSTIC", "reference_scores": None,
               "semantic_review_state": "PENDING_SIDE_CHAT", "held_out": False,
               "case_candidates": len(corpora["A"]), "runs": {}, "fixed_query_runs": {}, "ablations": {}}
    csv_rows = []
    for side in ["A", "B"]:
        pools = {}
        for policy in ["STRICT_SCOPE", "SCOPE_BLIND_DIAGNOSTIC"]:
            pools[policy] = [prepare(a, config["mappings"][side][a["case_id"]], policy) for a in corpora[side]]
            write_new(out / side / policy / "views.json", pools[policy])
            answers, ablations = [], []
            for ann in pools[policy]:
                for definition in queries:
                    q = definition["query"]
                    base, common = run_query(ann, q), run_query(ann, cooccurrence_query(q))
                    any_status = copy.deepcopy(q)
                    for atom in any_status["atoms"]:
                        atom["status"] = "ANY"
                    no_status = run_query(ann, any_status)
                    no_identity = run_query(ann, without_identity(q))
                    wrong_negative = copy.deepcopy(base)
                    if wrong_negative["status"] in ["UNKNOWN", "NOT_FOUND"]:
                        wrong_negative["status"] = "MISMATCH"
                        wrong_negative["diagnostic_false_closed_world"] = True
                    answers.append({"case_id": ann["case_id"], "pass": side, "id": definition["id"], "meaning": definition["meaning"],
                                    "relation": base, "cooccurrence": common, "reference": None})
                    ablations.append({"case_id": ann["case_id"], "id": definition["id"], "base": base["status"],
                                      "remove_identity": no_identity, "ignore_status": no_status,
                                      "unknown_as_negative": wrong_negative})
                    csv_rows.append([side, policy, ann["case_id"], definition["id"], base["status"], common["status"], len(base["witnesses"]), len(base["uncertain_bindings"])])
            write_new(out / side / policy / "fixed-queries.json", answers)
            write_new(out / side / policy / "fixed-query-ablations.json", ablations)
            key = side + "/" + policy
            summary["fixed_query_runs"][key] = {"comparisons": len(answers), "statuses": dict(Counter(r["relation"]["status"] for r in answers)),
                                                "cooccurrence_statuses": dict(Counter(r["cooccurrence"]["status"] for r in answers)),
                                                "A_B_agreement_is_not_accuracy": True}
            summary["ablations"][key] = {"ignore_status_changes": sum(x["base"] != x["ignore_status"]["status"] for x in ablations),
                                         "remove_identity_only_changes": sum(x["base"] != x["remove_identity"]["status"] for x in ablations),
                                         "unknown_as_negative_changes": sum(x["base"] != x["unknown_as_negative"]["status"] for x in ablations)}
        # The strict discovery run is the primary conservative local experiment.
        strict = candidate_set(pools["STRICT_SCOPE"])
        write_new(out / side / "strict-candidates.json", strict)
        primary = run_patterns(pools["STRICT_SCOPE"], strict, config["budget"], config["min_support"])
        write_new(out / side / "strict-discovery.json", primary)
        summary["runs"][side + "/strict-discovery"] = metrics(pools["STRICT_SCOPE"], primary)
        # A separately marked scope-blind candidate set tests exactly the same
        # queries on both policies. It must not be presented as safe discovery.
        diagnostic = candidate_set(pools["SCOPE_BLIND_DIAGNOSTIC"])
        write_new(out / side / "diagnostic-candidates.json", diagnostic)
        for policy in ["STRICT_SCOPE", "SCOPE_BLIND_DIAGNOSTIC"]:
            result = run_patterns(pools[policy], diagnostic, config["budget"], config["min_support"])
            result["candidate_origin_policy"] = "SCOPE_BLIND_DIAGNOSTIC"
            write_new(out / side / policy / "fixed-candidate-diagnostic.json", result)
            summary["runs"][side + "/fixed-candidates/" + policy] = metrics(pools[policy], result)
    # No references means no accuracy, precision, semantic-error or significance
    # calculation. A/B status differences are implementation review pointers.
    for policy in ["STRICT_SCOPE", "SCOPE_BLIND_DIAGNOSTIC"]:
        a, b = [read(out / side / policy / "fixed-queries.json") for side in ["A", "B"]]
        keyed = [{(x["case_id"], x["id"]): x for x in rows} for rows in [a, b]]
        comparison = [{"case_id": key[0], "query_id": key[1], "A": keyed[0][key]["relation"]["status"],
                       "B": keyed[1][key]["relation"]["status"], "reference": None}
                      for key in sorted(keyed[0])]
        write_new(out / (policy + "-A-B-status-comparison.json"), comparison)
        summary["fixed_query_runs"][policy + "/A-B"] = {"comparisons": len(comparison),
                                                          "status_differences": sum(x["A"] != x["B"] for x in comparison),
                                                          "interpretation": "Differences are not errors or omission counts"}
    with (out / "fixed-query-statuses.csv").open("x", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["pass", "policy", "case_id", "query_id", "relation_status", "cooccurrence_status", "witness_count", "uncertain_binding_count"])
        writer.writerows(csv_rows)
    summary["output_status"] = "ALL_PLANNED_LOCAL_RUNS_COMPLETE_REFERENCE_REVIEW_PENDING"
    write_new(out / "summary.json", summary)
    write_new(out / "runtime.json", {"elapsed_seconds": time.monotonic() - started, "python": platform.python_version(),
                                     "paid_API_calls": 0, "new_web_tasks": 0, "input_manifest_hash": digest(manifest),
                                     "config_hash": digest(config), "query_hash": digest(queries)})
    code = [Path(__file__), Path("legal_bench/development_experiment.py"), Path("legal_bench/engine.py"), Path("legal_bench/core.py")]
    log_run(out, "five-case-local-diagnostics", code + [out / "input-manifest.json", out / "config.json", out / "queries.json"], [out / "summary.json"])
    write_new(out / "checkpoint-complete.json", {"state": summary["output_status"], "summary_hash": digest(summary),
                                                  "config_hash": digest(config), "manifest_hash": digest(manifest)})
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
