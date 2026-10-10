"""Concrete-use contract; eligibility, evidential function and truth stay separate.

This module checks declared structure and attributed source addresses. It never
infers an intended use from USABLE/UNUSABLE, nor approves source semantics.
"""
from .contracts import content_hash
from .semantic_checker_v13 import source_match

CONTRACT = {
    "version": "evidence-use-contract-v14.1",
    "labels": {
        "USABLE": "The cited record may perform this declared evidential function for this proposition, objects and stage.",
        "UNUSABLE": "The record may not perform this declared function; neither proposition falsity nor global irrelevance follows.",
        "UNRESOLVED": "Eligibility for this concrete function cannot currently be established.",
    },
    "purposes": ["REPORT_ASSERTION", "PARTIAL_SUPPORT", "PARTIAL_OPPOSITION", "BACKGROUND", "ESTABLISH_OCCURRENCE", "RECONSTRUCT_COURT_PREMISE"],
    "directions": ["SUPPORT", "OPPOSE", "CONTEXT", "UNRESOLVED"],
    "truth_states": ["TRUE", "FALSE", "UNKNOWN", "CONFLICTED"],
    "non_promoting_purposes": ["REPORT_ASSERTION", "PARTIAL_SUPPORT", "PARTIAL_OPPOSITION", "BACKGROUND"],
    "policy": "A source-reviewed whole-premise receipt is required for executing calibrated premises. Source location is not semantic approval. Raw legacy uses without an explicit purpose remain ambiguous, not automatically relabelled.",
    "no_negative_from_missing_evidence": True,
    "no_truth_from_use_label": True,
    "no_legal_consequence_from_use_label": True,
}


def inspect_use(raw_use, declaration, sources):
    """Check a declared function. Does not rewrite the original proposal/label."""
    result = {"original_label": raw_use.get("use_judgment"), "original_premise_state": raw_use.get("premise_state"), "direction": None, "purpose": None, "errors": [], "pending": [], "legal_approval": False, "semantic_verified": False}
    if declaration is None:
        result["pending"].append("LEGACY_CONCRETE_USE_NOT_DECLARED")
        return result
    for key in ("purpose", "direction"):
        result[key] = declaration.get(key)
    if declaration.get("purpose") not in CONTRACT["purposes"]:
        result["errors"].append("INVALID_USE_PURPOSE")
    if declaration.get("direction") not in CONTRACT["directions"]:
        result["errors"].append("INVALID_DIRECTION")
    if declaration.get("premise_id") != raw_use.get("rule_premise"):
        result["errors"].append("DECLARATION_PREMISE_MISMATCH")
    if declaration.get("bindings") != raw_use.get("bindings"):
        result["errors"].append("DECLARATION_OBJECT_MISMATCH")
    if not declaration.get("stage"):
        result["pending"].append("DECLARED_STAGE_MISSING")
    if declaration.get("source_status") in ("PARTY_CLAIM", "PARTY_CONTENTION", "HYPOTHETICAL", "FUTURE_CONDITIONAL") and declaration.get("purpose") in ("ESTABLISH_OCCURRENCE", "RECONSTRUCT_COURT_PREMISE"):
        result["errors"].append("ASSERTION_OR_HYPOTHESIS_CANNOT_ESTABLISH_CONTENT")
    witnesses = declaration.get("source_witnesses", [])
    if not witnesses:
        result["pending"].append("USE_SOURCE_WITNESS_MISSING")
    for witness in witnesses:
        located = source_match(witness, sources)
        if located.get("error"):
            result["pending"].append("USE_SOURCE:" + located["error"])
    result["eligible_under_declared_review"] = not result["errors"] and not result["pending"]
    result["can_supply_whole_premise"] = result["eligible_under_declared_review"] and declaration.get("purpose") not in CONTRACT["non_promoting_purposes"]
    result["contract_hash"] = content_hash(CONTRACT)
    return result
