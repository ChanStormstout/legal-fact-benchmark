"""Explicit, reversible source-calibration overlay. No case-ID branches.

Receipts are research review decisions supplied as data, not model discoveries.
Original P, labels, fact quotations, operators and rule meanings are preserved.
"""
import copy
from .contracts import content_hash
from .use_contract_v14 import CONTRACT


def apply_overlay(snapshot, candidates, overlay):
    s, cs = copy.deepcopy(snapshot), copy.deepcopy(candidates)
    changes = []
    if overlay["case_id"] != s["case_id"]:
        raise ValueError("OVERLAY_CASE_MISMATCH")
    if overlay["original_snapshot_hash"] != content_hash(snapshot):
        raise ValueError("OVERLAY_SNAPSHOT_MISMATCH")
    s["interface_version"] = "V14_SOURCE_CALIBRATED_NOT_AUTOMATIC"
    s["use_contract"] = CONTRACT
    s["external_premise_receipts"] = copy.deepcopy(overlay["premises"])
    s["use_declarations"] = copy.deepcopy(overlay["use_declarations"])
    s["calibration_policy_hash"] = content_hash(overlay["policy"])
    s["calibration_provenance"] = {"original_snapshot_hash": content_hash(snapshot), "overlay_hash": content_hash(overlay), "track": "SOURCE_CALIBRATED_NOT_LEARNER_RESULT"}
    raw_uses = {u["id"]: u for u in snapshot.get("raw_proposal", {}).get("uses", [])}
    for uid, declaration in overlay["use_declarations"].items():
        raw = raw_uses[uid]
        changes.append({"field": "use_declarations." + uid,
                        "original": {"use_judgment": raw.get("use_judgment"), "premise_state": raw.get("premise_state"), "explanation": raw.get("explanation"), "declared_purpose": None},
                        "calibrated": declaration, "kind": "SEMANTIC_REVIEW_CONCRETE_USE_NOT_RELABEL",
                        "external_acceptance_required": True, "refs": [r for w in declaration.get("source_witnesses", []) for r in w.get("refs", [])]})
    for receipt in overlay["premises"].values():
        raw = raw_uses[receipt["raw_use_id"]]
        changes.append({"field": "external_premise_receipts." + receipt["id"],
                        "original": {"premise_state": raw.get("premise_state"), "basis": raw.get("premise_judgment_basis")},
                        "calibrated": {"state": receipt["state"], "basis": receipt["reason"], "statement_status": receipt["statement_status"], "component_coverage": receipt["component_coverage"]},
                        "kind": "SEMANTIC_REVIEW_WHOLE_PREMISE", "external_acceptance_required": True, "refs": receipt["refs"]})
    for fix in overlay.get("rule_quote_corrections", []):
        r = s["rules"][fix["rule_ref"]]
        if r["quote"] != fix["original"]:
            raise ValueError("RULE_QUOTE_ORIGINAL_MISMATCH")
        changes.append({"field": fix["rule_ref"] + ".quote", **fix})
        r["quote"] = fix["calibrated"]
        s["contracts"][fix["rule_ref"]]["rule_hash"] = content_hash(r)
    for mapping in overlay.get("role_mappings", []):
        rc = s["contracts"][mapping["rule_ref"]]
        pid = mapping["premise_id"]
        changes.append({"field": mapping["rule_ref"] + ".slot_variables." + pid, "original": rc["slot_variables"].get(pid), "original_unmapped": rc.get("unmapped_roles", {}).get(pid), "calibrated": mapping["mapping"], "refs": mapping["refs"], "kind": "SEMANTIC_REVIEW_EXPLICIT_ROLE_ADDRESS", "external_acceptance_required": True})
        rc["slot_variables"][pid] = mapping["mapping"]
        rc.setdefault("unmapped_roles", {})[pid] = {}
    by_id = {c["id"]: c for c in cs}
    c = by_id[overlay["candidate_id"]]
    for x in c["inputs"]:
        receipt = overlay["premises"].get(x["slot"])
        if receipt is None:
            continue
        original = copy.deepcopy(x)
        x.clear()
        x.update(slot=original["slot"], kind="EXTERNAL_PREMISE", id=receipt["id"])
        changes.append({"field": c["id"] + ".inputs." + x["slot"], "original": original, "calibrated": x, "raw_evidence_retained": receipt["original_evidence_ids"], "kind": "SEMANTIC_REVIEW_OF_WHOLE_PREMISE", "refs": receipt["refs"], "external_acceptance_required": True})
    return s, cs, changes
