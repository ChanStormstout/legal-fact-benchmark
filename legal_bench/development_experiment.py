"""Local record-level diagnostics before semantic review, never a reference view.

The strict policy blocks every scoped or unresolved assertion. The scope-blind
policy is a deliberately unsafe diagnostic that retains the original scope in
the trace. Both keep unknown model fields unknown. Neither creates review
decisions, gold labels, or held-out results.
"""
import copy
import json
import re
from collections import Counter
from datetime import datetime

from .core import canonical, digest
from .engine import execute, generate, cooccurrence_query
from . import conditional_engine


CONDITIONAL_POLICY = "ASSUMED_ACCURATE_FIELD_SCOPED"
POLICIES = {"STRICT_SCOPE", "SCOPE_BLIND_DIAGNOSTIC", CONDITIONAL_POLICY}


def without_identity(query):
    """Remove only object joins; keep time, attributes, and distinct records."""
    result = copy.deepcopy(query)
    result["constraints"] = [c for c in query.get("constraints", [])
                             if not (c["op"] in ["same", "different"] and ".roles." in c["left"])]
    return result


def exact_date(value):
    if not isinstance(value, str):
        return False
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d") == value
    except ValueError:
        return False


def prepare(annotation, mappings, policy):
    if policy not in POLICIES:
        raise ValueError("Unknown diagnostic policy")
    primary = [u for u in annotation["units"] if u["primary"]]
    if len(primary) != 1:
        raise ValueError("Exactly one recorded primary unit required")
    unit = copy.deepcopy(primary[0])
    definitions = {d["id"]: d for d in annotation["predicate_definitions"]}
    events, excluded = [], []
    for assertion in annotation["assertions"]:
        rule = mappings.get(assertion["predicate"])
        if assertion["kind"] not in ["FACT", "PROCEDURAL_ACT"] or not rule:
            excluded.append({"id": assertion["id"], "reason": "OUTSIDE_DRAFT_QUERY_VOCABULARY"})
            continue
        guard = rule.get("attribute_guard")
        if guard and not re.search(guard["pattern"], str(assertion["attributes"].get(guard["field"], ""))):
            excluded.append({"id": assertion["id"], "reason": "MAPPING_GUARD_NOT_MET"})
            continue
        if not set(rule["roles"].values()) <= set(definitions[assertion["predicate"]]["roles"]):
            raise ValueError("Mapping references a role absent from source definition")
        roles = {target: assertion["roles"].get(original) for target, original in rule["roles"].items()}
        treatment = assertion["deciding_court_treatment"]["value"]
        status = "COURT_FOUND" if treatment == "ADOPTED" else "REJECTED" if treatment == "REJECTED" else "UNDETERMINED"
        # Missing/null fields are not made into negative facts. The legacy
        # executor conservatively blocks all uses of unresolved records.
        unresolved = copy.deepcopy(assertion["unresolved"])
        if policy == "STRICT_SCOPE" and assertion["scope"]:
            unresolved.append({"field": "scope", "reason": "Qualifier has not been reviewed for this query use"})
        date = assertion["time"]["date"] if assertion["time"] else None
        if date is not None and not exact_date(date):
            unresolved.append({"field": "time", "reason": "Exact ISO event date unavailable"})
            date = None
        # Assertions with unknown polarity/status cannot seed mining candidates.
        e = {"id": assertion["id"], "type": rule["type"], "unit_id": unit["id"],
             "roles": roles, "attributes": copy.deepcopy(assertion["attributes"]),
             "time": date, "polarity": assertion["polarity"], "status": status,
             "evidence": copy.deepcopy(assertion["evidence"]), "unresolved": unresolved,
             "scope": copy.deepcopy(assertion["scope"]), "origin": copy.deepcopy(assertion["origin"]),
             "source_assertion": copy.deepcopy(assertion), "source_definition": copy.deepcopy(definitions[assertion["predicate"]]),
             "mapping_rule": copy.deepcopy(rule), "semantic_review_state": "PENDING"}
        events.append(conditional_engine.add_contract(e) if policy == CONDITIONAL_POLICY else e)
    return {"case_id": annotation["case_id"], "units": [unit], "events": events,
            "policy": policy, "excluded": excluded, "annotation_hash": digest(annotation),
            "material_scope": "Full supplied judgment; mapped factual/procedural records, including historical background",
            "analysis_unit_semantics": "Retrospective case-level diagnostic attached to the recorded primary unit; relevance is not inferred",
            "label_origin": "EXISTING_MODEL_ANNOTATION_UNRECONCILED", "mapping_state": "DRAFT_ENGINEERING_ABSTRACTION_NOT_REVIEWED"}


def run_query(annotation, query):
    result = (conditional_engine.execute(annotation, query) if annotation["policy"] == CONDITIONAL_POLICY
              else execute(annotation, query, annotation["units"][0]["id"]))
    by_id = {e["id"]: e for e in annotation["events"]}
    for key in ["witnesses", "uncertain_bindings"]:
        for w in result[key]:
            w["records"] = {var: {k: copy.deepcopy(by_id[aid][k]) for k in
                                      ["scope", "origin", "source_assertion", "source_definition", "mapping_rule"]}
                            for var, aid in w["binding"].items()}
    result.update(case_id=annotation["case_id"], input_hash=annotation["annotation_hash"],
                  policy=annotation["policy"], semantic_review_state="PENDING",
                  interpretation="Record-level diagnostic status under explicit draft mapping and policy, not a verified legal answer")
    return result


def seed(annotation):
    """Missing identity prevents a join seed; keep it in the execution pool."""
    result = copy.deepcopy(annotation)
    for e in result["events"]:
        e["roles"] = {k: v for k, v in e["roles"].items() if v is not None}
    return result


def candidate_set(annotations):
    if len({a["case_id"] for a in annotations}) != len(annotations):
        raise ValueError("A/B from one case cannot be counted as separate cases")
    policies = {a["policy"] for a in annotations}
    if len(policies) > 1:
        raise ValueError("Do not mix execution policies in discovery")
    if policies == {CONDITIONAL_POLICY}:
        return conditional_engine.generate(annotations)
    return generate([seed(a) for a in annotations])


def run_patterns(annotations, candidates, budget=1000, min_support=2):
    if len({a["case_id"] for a in annotations}) != len(annotations):
        raise ValueError("Duplicate cases inflate support")
    if budget < 1 or min_support < 1:
        raise ValueError("Positive budget/support required")
    patterns = []
    for serialized in candidates[:budget]:
        q = json.loads(serialized)
        results = []
        for ann in sorted(annotations, key=lambda a: a["case_id"]):
            relation, common = run_query(ann, q), run_query(ann, cooccurrence_query(q))
            no_identity = run_query(ann, without_identity(q))
            # Full proof records are saved once in the view; these witnesses carry
            # local IDs and exact quotes, keeping the all-candidate output small.
            for result in [relation, common, no_identity]:
                for key in ["witnesses", "uncertain_bindings"]:
                    for witness in result[key]:
                        witness.pop("records", None)
                if ann["policy"] == CONDITIONAL_POLICY:
                    # Rejected Cartesian bindings can be large. Query runs
                    # retain full diagnostics; mining retains a count plus the
                    # input view so any binding can be reproduced on demand.
                    result["rejected_binding_count"] = len(result.pop("rejected_bindings", []))
                    result["conflict_event_ids"] = sorted(x["event_id"] for x in result.pop("conflicts", []))
            results.append({"case_id": ann["case_id"], "relation": relation, "cooccurrence": common,
                            "remove_identity_only": no_identity})
        support = sum(x["relation"]["status"] == "MATCH" for x in results)
        patterns.append({"id": digest(q)[:16], "query": q, "origin": "DATA_SEARCH_IN_UNREVIEWED_RECORDS",
                         "support": support, "unknown": sum(x["relation"]["status"] == "UNKNOWN" for x in results),
                         "cooccurrence_support": sum(x["cooccurrence"]["status"] == "MATCH" for x in results),
                         "repeated": support >= min_support, "results": results})
    patterns.sort(key=lambda x: (-x["support"], len(x["query"]["constraints"]), canonical(x["query"])))
    return {"patterns": patterns, "generated": len(candidates), "executed": len(patterns),
            "budget": budget, "min_support": min_support, "search_complete": len(candidates) <= budget,
            "frontier": candidates[budget:], "candidate_hash": digest(candidates),
            "support_unit": "Case, not witness; independent dispute grouping pending",
            "semantic_review_state": "PENDING", "held_out": False}


def metrics(annotations, mining):
    return {"case_candidates": len(annotations), "mapped_records": sum(len(a["events"]) for a in annotations),
            "unknown_or_qualified_records": sum(bool(e["unresolved"]) for a in annotations for e in a["events"]),
            "positive_adopted_seed_records": sum(bool(conditional_engine.known_seed(e)) if a["policy"] == CONDITIONAL_POLICY
                                                 else e["status"] == "COURT_FOUND" and e["polarity"] == "POSITIVE" and not e["unresolved"]
                                                 for a in annotations for e in a["events"]),
            "generated_candidates": mining["generated"], "executed_candidates": mining["executed"],
            "search_complete": mining["search_complete"],
            "repeated_patterns": sum(p["repeated"] for p in mining["patterns"]),
            "relation_vs_cooccurrence_status_differences": sum(x["relation"]["status"] != x["cooccurrence"]["status"]
                                                              for p in mining["patterns"] for x in p["results"]),
            "cooccurrence_match_without_relation_match": sum(x["cooccurrence"]["status"] == "MATCH" and x["relation"]["status"] != "MATCH"
                                                             for p in mining["patterns"] for x in p["results"]),
            "identity_only_status_changes": sum(x["relation"]["status"] != x["remove_identity_only"]["status"]
                                                for p in mining["patterns"] for x in p["results"]),
            "relation_statuses": dict(Counter(x["relation"]["status"] for p in mining["patterns"] for x in p["results"]))}
