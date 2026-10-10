"""Independent receipt checking plus explicit rule composition.

Does not import the overlay assembler, search, reference labels, or learner.
Research policy acceptance is NOT independent legal semantic certification.
"""
import copy
from .contracts import content_hash
from .semantic_checker_v13 import check as check_legacy, source_match
from .use_contract_v14 import CONTRACT, inspect_use


def check_receipt(snapshot, step, slot, receipt, policy):
    errors, pending, witnesses = [], [], []
    rr = step["rule_ref"]
    rule = snapshot["rules"][rr]
    candidate_bindings = {b["role"]: b["entity"] for b in step["bindings"]}
    if receipt.get("premise_id") != slot["name"] or receipt.get("predicate_hash") != content_hash(slot["predicate"]):
        errors.append("RECEIPT_PROPOSITION_MISMATCH")
    if receipt.get("case_id") != snapshot["case_id"] or receipt.get("rule_ref") != rr:
        errors.append("RECEIPT_CASE_OR_VERSION_MISMATCH")
    if not policy or content_hash(policy) != snapshot.get("calibration_policy_hash"):
        errors.append("EXTERNAL_POLICY_MISSING_OR_MISMATCH")
    elif not policy.get("research_acceptance") or receipt.get("review_decision") != "ACCEPT_FOR_RECONSTRUCTION":
        pending.append("EXTERNAL_REVIEW_NOT_ACCEPTED")
    elif policy.get("accepted_receipt_hashes", {}).get(receipt.get("id")) != content_hash(receipt):
        errors.append("EXTERNAL_RECEIPT_NOT_IN_REVIEWED_POLICY_VERSION")
    if receipt.get("statement_status") not in slot["allowed_statuses"]:
        errors.append("EXTERNAL_STATEMENT_STATUS_NOT_ALLOWED")
    if not receipt.get("court_level") or not receipt.get("stage") or not receipt.get("reason"):
        pending.append("EXTERNAL_ATTRIBUTION_INCOMPLETE")
    if receipt.get("stage") != rule.get("stage"):
        errors.append("EXTERNAL_PROCEDURAL_STAGE_MISMATCH")
    if receipt.get("state") not in CONTRACT["truth_states"]:
        pending.append("EXTERNAL_PREMISE_STATE_MISSING")
    if receipt.get("predicate_hash") == content_hash(rule["conclusion_predicate"]):
        errors.append("CIRCULAR_CONCLUSION_AS_PREMISE")
    sources = snapshot["sources"]
    for w in receipt.get("source_witnesses", []):
        loc = source_match(w, sources)
        witnesses.append({"record": w, "source_check": loc})
        if loc.get("error"):
            pending.append("EXTERNAL_SOURCE:" + loc["error"])
        elif any(sources[r].get("document_role") != "TARGET" or sources[r].get("role") == "DISPOSITION_ONLY" for r in w["refs"]):
            errors.append("EXTERNAL_FOREIGN_OR_DISPOSITION_SOURCE")
    if not witnesses:
        pending.append("EXTERNAL_SOURCE_WITNESS_MISSING")
    bw = receipt.get("binding_witnesses", [])
    mapping = snapshot["contracts"][rr].get("slot_variables", {}).get(slot["name"], {})
    for role, var in mapping.items():
        matching = [w for w in bw if w.get("role") == role and w.get("variable") == var]
        expected = candidate_bindings.get(var)
        if expected is None or expected == "" or not matching:
            pending.append("EXTERNAL_BINDING_UNESTABLISHED:" + role)
        for w in matching:
            if w.get("value") != expected:
                errors.append("EXTERNAL_OBJECT_MISMATCH:" + role)
            if not w.get("reason") or source_match(w, sources).get("error"):
                pending.append("EXTERNAL_BINDING_WITNESS_UNVERIFIED:" + role)
    if snapshot["contracts"][rr].get("unmapped_roles", {}).get(slot["name"]):
        pending.append("ROLE_MAPPING_UNRESOLVED")
    key = step["candidate_id"] + "::" + slot["name"]
    raw = next((u for u in snapshot.get("raw_proposal", {}).get("uses", []) if u["id"] == receipt.get("raw_use_id")), {})
    if receipt.get("original_evidence_ids") != raw.get("evidence_ids"):
        errors.append("EXTERNAL_EVIDENCE_LINEAGE_MISMATCH")
    proposal_use = snapshot.get("model_uses", {}).get(key)
    declaration = snapshot.get("use_declarations", {}).get(receipt.get("raw_use_id"))
    audit = inspect_use(raw, declaration, sources)
    required_components = (declaration or {}).get("required_components", [])
    supplied_components = receipt.get("component_coverage", [])
    if not required_components or set(required_components) != {c.get("id") for c in supplied_components}:
        pending.append("WHOLE_PREMISE_COMPONENT_COVERAGE_UNESTABLISHED")
    for c in supplied_components:
        if not c.get("reason") or source_match(c, sources).get("error"):
            pending.append("WHOLE_PREMISE_COMPONENT_WITNESS_UNVERIFIED")
    errors.extend("USE:" + e for e in audit["errors"])
    pending.extend("USE:" + e for e in audit["pending"])
    if not audit.get("can_supply_whole_premise"):
        pending.append("USE_FUNCTION_CANNOT_ESTABLISH_WHOLE_PREMISE")
    if not proposal_use or proposal_use.get("raw_use_id") != receipt.get("raw_use_id"):
        errors.append("EXTERNAL_USE_ADDRESS_MISMATCH")
    elif proposal_use.get("label") != "USABLE":
        pending.append("MODEL_USE_UNRESOLVED_OR_REJECTED")
    # CONTRARY evidence remains usable; direction is not automatically truth.
    state = receipt.get("state", "UNKNOWN") if not errors and not pending else "UNKNOWN"
    return {"state": state, "errors": errors, "pending": pending, "witnesses": witnesses, "use_audit": audit, "evidence_ids": receipt.get("original_evidence_ids", []), "truth_origin": "EXTERNAL_MODEL_ASSISTED_SOURCE_REVIEW", "independently_semantic_verified": False, "formal_legal_approval": False}


def check(snapshot, search, policy):
    s, route = copy.deepcopy(snapshot), copy.deepcopy(search)
    details, ordinary_use_audits = {}, {}
    for step in route["steps"]:
        r = s["rules"].get(step["rule_ref"], {})
        slots = {slot["name"]: slot for slot in r.get("slots", [])}
        for x in step["inputs"]:
            if x["kind"] != "EXTERNAL_PREMISE":
                if x["kind"] in ("PREMISE", "BUNDLE"):
                    key = step["candidate_id"] + "::" + x["slot"]
                    base = copy.deepcopy(s.get("model_uses", {}).get(key, {}))
                    raw = next((u for u in s.get("raw_proposal", {}).get("uses", []) if u["id"] == base.get("raw_use_id")), {})
                    decl = s.get("use_declarations", {}).get(base.get("raw_use_id"))
                    audit = inspect_use(raw, decl, s["sources"])
                    audit["whole_premise_acceptance"] = "RAW_MODEL_JUDGMENT_NOT_SOURCE_CALIBRATED"
                    ordinary_use_audits[step["id"] + "::" + x["slot"]] = audit
                    # Keep eligibility and original P truth in the audit. The
                    # newly explicit contract cannot silently promote background
                    # or an ambiguous legacy use into an accepted premise.
                    base["premise_state"] = "UNKNOWN"
                    s["model_uses"][key] = base
                continue
            receipt = next((v for v in s.get("external_premise_receipts", {}).values() if v["id"] == x["id"]), {})
            detail = check_receipt(s, step, slots[x["slot"]], receipt, policy)
            details[step["id"] + "::" + x["slot"]] = detail
            # Feed only a checked, explicitly attributed receipt to the unchanged
            # ALL/ANY/exception evaluator. This is not a new model fact.
            pid = "EXTERNAL::" + x["id"]
            s["premises"][pid] = {"id": pid, "text": slots[x["slot"]]["predicate"], "statement_status": receipt.get("statement_status"), "court_level": receipt.get("court_level"), "stage": receipt.get("stage"), "bindings": [{"role": w["role"], "entity": w["value"]} for w in receipt.get("binding_witnesses", [])], "refs": receipt.get("refs", []), "quote": receipt.get("quote"), "external_receipt_not_raw_fact": True}
            x.update(kind="PREMISE", id=pid)
            key = step["candidate_id"] + "::" + x["slot"]
            base = copy.deepcopy(s["model_uses"].get(key, {}))
            base.update(premise_state=detail["state"], premise_judgment_basis=receipt.get("reason", ""), external_receipt_id=receipt.get("id"))
            s["model_uses"][key] = base
    result = check_legacy(s, route)
    result.update(external_receipt_checks=details, ordinary_use_audits=ordinary_use_audits, use_contract_hash=content_hash(CONTRACT), accepted_external_policy=bool(policy and policy.get("research_acceptance")), input_track=snapshot.get("input_track"), formal_legal_approval=False)
    for sid, st in result["steps"].items():
        for key, detail in details.items():
            if key.startswith(sid + "::"):
                st["pending"] += detail["pending"]
                st["pending"] += ["INVALID_EXTERNAL_RECEIPT:" + e for e in detail["errors"]]
        for a in st["assumptions"]:
            if any(f.startswith("EXTERNAL::") for f in a.get("facts", [])):
                a["status"] = "MODEL_ASSISTED_SOURCE_REVIEW_ACCEPTED_UNDER_RESEARCH_POLICY"
    result["all_original_records"] = list(snapshot.get("premises", {}))
    result["all_original_opposition"] = snapshot.get("relations", [])
    result["automatic_legal_semantic_verification"] = False
    return result
