"""Field-dependent execution under an explicit accurate-annotation assumption.

Only existential matching of individually scoped records is supported. Identity
joins compare recorded object IDs, not group membership, equal physical extent,
simultaneous occupation, current truth, or legal sufficiency. No review approvals
are manufactured. Unregistered natural-language qualifiers remain blocked.
"""
import copy
import itertools
import json
import math
from datetime import datetime

from .core import canonical, digest
from .engine import canonical_query, query_error


TEMPORAL_KEYS = set("after after_event approximate_time current_description effective_date end expiry_date feature_time historical historical_period month_year period relative_time source_characterization start start_year temporal temporal_scope time timing year judgment_date".split())
CONTEXT_KEYS = set("appeal appeal_no appellate_disposition appellate_stage applies_to asserted_basis basis basis_alleged basis_used_by_high_court claim_basis claimant_source context court_scope current_appeal_scope current_civil_appeal current_court_characterization current_deciding_stage current_disposition current_review_scope decree document document_no documentary_support fresh_suit high_court_second_appeal_scope historical_finding historical_high_court_second_appeal instrument judgment origin_scope proceeding proceeding_identifier_variants sequence source_form source_wording stage stage_context statute statutory_basis suit testimony testimony_scope".split())
DESCRIPTIVE_KEYS = set("High Court characterization alterations asserted_use character construction debt description distinction event extent frequency manner method portion protected_feature purpose qualification record_scope relief remaining_extent replacement restoration_state restraint restriction result_of scope source_characterization status status_described subject_matter".split())
ROLE_KEYS = set("against_role_unresolved claimant co_plaintiff collective filer_scope participants payer_scope recipient".split())
# These names alone do not tell us which predicate/argument is restricted.
# They require a typed dependency or later semantic review, even in the
# accurate-input experiment. An accurate transcription is not a parsed meaning.
DESCRIPTIVE_KEYS -= {"qualification", "restriction", "scope", "debt", "event", "restraint"}


def iso_date(value):
    if not isinstance(value, str):
        return False
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d") == value
    except ValueError:
        return False


def scalar(value):
    return isinstance(value, (str, bool, int, float)) and not (isinstance(value, float) and not math.isfinite(value))


def equal_value(left, right):
    # JSON booleans are not numeric amounts (Python otherwise equates True/1).
    if isinstance(left, bool) != isinstance(right, bool):
        return False
    return left == right


def contract(event):
    """Translate explicit uncertainty domains; never guess from free-text values.

    Resolved qualifiers stay attached to the scoped proposition. They are not
    erased or treated as unresolved solely because a scope object is nonempty.
    A typed unresolved qualifier may declare affected fields; unknown domains
    block that proposition. Only the explicitly assumed accurate input path uses
    this contract. The reviewed production view remains a separate path.
    """
    original = event["source_assertion"]
    role_map = event["mapping_rule"]["roles"]
    reverse = {src: target for target, src in role_map.items()}
    blocked, preserved = [], []

    def normalize(field):
        if field.startswith("roles."):
            src = field.split(".", 1)[1]
            return "roles." + reverse.get(src, src)
        return {"predicate": "type", "deciding_court_treatment": "status"}.get(field, field)

    for item in original["unresolved"]:
        field = item["field"]
        if field in ["predicate", "procedural_outcome"]:
            affected = ["type", "polarity"]
        elif field == "deciding_court_treatment / filer identity":
            affected = ["status", "roles." + reverse.get("filer", "filer")]
        elif field == "object_identity":
            affected = ["roles"]
        elif field in ["time", "scope.temporal"]:
            affected = ["time"]
        elif field == "scope.property_extent":
            # An object-ID query does not claim equal occupied extent. Exact
            # extent/area questions are outside this language.
            affected = ["attributes.extent", "attributes.area", "attributes.portion"]
        elif field in ["origin", "status", "polarity", "roles", "attributes", "deciding_court_treatment"] or field.startswith(("roles.", "attributes.", "origin.")):
            affected = [normalize(field)]
        else:
            affected = ["*"]
        blocked.append({"source_field": "unresolved." + field, "affected_fields": affected,
                        "reason": item["reason"], "kind": "EXPLICIT_UNCERTAINTY"})

    for key, value in original["scope"].items():
        if isinstance(value, dict) and "affects" in value:
            affected = value["affects"]
            allowed = lambda f: f in ["*", "type", "status", "polarity", "time", "roles", "attributes", "origin"] or f.startswith(("roles.", "attributes.", "origin."))
            if not isinstance(affected, list) or not affected or any(not isinstance(f, str) or not allowed(f) for f in affected):
                raise ValueError("Invalid explicit qualifier dependency")
            # A dependency declaration only makes uncertainty local. Resolved
            # restrictions are not licensed to disappear from an unconstrained
            # query; their compatibility has to be checked before admission.
            if value.get("resolved") is not False:
                blocked.append({"source_field": "scope." + key, "affected_fields": [normalize(f) for f in affected],
                                "reason": "Resolved restriction requires a supported compatibility check", "kind": "UNSUPPORTED_RESTRICTION"})
            else:
                blocked.append({"source_field": "scope." + key, "affected_fields": [normalize(f) for f in affected],
                                "reason": str(value.get("value", "Explicit unresolved qualifier")), "kind": "TYPED_QUALIFIER"})
            preserved.append({"source_field": "scope." + key, "value": copy.deepcopy(value), "interpretation": "DECLARED_FIELD_DEPENDENCY"})
        elif key in ["date_conflict", "date_texts"]:
            blocked.append({"source_field": "scope." + key, "affected_fields": ["time"], "reason": "Conflicting source dates", "kind": "DATE_CONFLICT"})
        elif key == "quantifier":
            blocked.append({"source_field": "scope.quantifier", "affected_fields": ["*"],
                            "reason": "Universal or quantified scope is outside concrete-record matching", "kind": "UNSUPPORTED_QUANTIFIER"})
        elif key in TEMPORAL_KEYS | CONTEXT_KEYS | DESCRIPTIVE_KEYS | ROLE_KEYS:
            preserved.append({"source_field": "scope." + key, "value": copy.deepcopy(value),
                              "interpretation": "INDIVIDUAL_RECORD_SCOPE_PRESERVED_NO_GLOBAL_OR_SIMULTANEOUS_INFERENCE"})
        else:
            blocked.append({"source_field": "scope." + key, "affected_fields": ["*"],
                            "reason": "Unregistered qualifier; no automatic semantic interpretation", "kind": "UNREGISTERED_QUALIFIER"})
    return {"version": "conditional-fields-v1", "assumption": "ANNOTATED_FIELDS_ACCURATE_WITH_EXPLICIT_UNCERTAINTY",
            "blocked": blocked, "preserved_qualifiers": preserved,
            "type_unresolved": any(x["source_field"] in ["unresolved.predicate", "unresolved.procedural_outcome"] for x in blocked),
            "claim_boundary": "Existence of these scoped records with equal recorded IDs; not equal extent, same period, group membership, universal truth, current state, or legal sufficiency"}


def add_contract(event):
    result = copy.deepcopy(event)
    result["field_contract"] = contract(event)
    if result["time"] is not None and not iso_date(result["time"]):
        result["field_contract"]["blocked"].append({"source_field": "time", "affected_fields": ["time"],
                                                    "reason": "Exact ISO event date required", "kind": "INVALID_DATE"})
    return result


def field_value(event, field):
    reasons = [x for x in event["field_contract"]["blocked"]
               if any(f == "*" or f == field or field.startswith(f + ".") for f in x["affected_fields"])]
    if reasons:
        return None, reasons
    value = event
    for part in field.split("."):
        value = value.get(part) if isinstance(value, dict) else None
    return (value, []) if value is not None else (None, [{"affected_fields": [field], "reason": "Missing field", "kind": "MISSING"}])


def execute(annotation, query):
    try:
        error = query_error(query)
    except (TypeError, AttributeError, KeyError):
        error = "Malformed query"
    if error:
        return {"status": "UNSUPPORTED", "reason": error, "witnesses": [], "uncertain_bindings": [], "rejected_bindings": []}
    if any(c["op"] == "before" and (not c["left"].endswith(".time") or not c["right"].endswith(".time"))
           for c in query.get("constraints", [])):
        return {"status": "UNSUPPORTED", "reason": "Temporal ordering requires event time fields", "witnesses": [],
                "uncertain_bindings": [], "rejected_bindings": []}
    pools = [[e for e in annotation["events"] if (e["type"] == atom["type"] or e["field_contract"]["type_unresolved"])
              and e["unit_id"] == annotation["units"][0]["id"]
              and ("event_id" not in atom or atom["event_id"] == e["id"])] for atom in query["atoms"]]
    good, unknown, rejected, conflicts = [], [], [], []
    for combo in itertools.product(*pools):
        binding = dict(zip([a["var"] for a in query["atoms"]], combo))
        missing, failed = [], []

        def get(event, field):
            value, reasons = field_value(event, field)
            if reasons:
                missing.append({"event_id": event["id"], "field": field, "dependencies": reasons})
            return value

        for atom, e in zip(query["atoms"], combo):
            for field, target in [("type", atom["type"]), ("status", atom.get("status", "COURT_FOUND")), ("polarity", atom.get("polarity", "POSITIVE"))]:
                if target == "ANY":
                    continue
                value = get(e, field)
                if value is None:
                    continue
                if value == "UNDETERMINED":
                    missing.append({"event_id": e["id"], "field": field, "reason": "Annotation explicitly undetermined"})
                elif value != target:
                    failed.append({"event_id": e["id"], "field": field})
            if e["polarity"] == "NEGATIVE" or e["status"] in ["REJECTED", "DISPUTED"]:
                conflicts.append({"event_id": e["id"], "source_assertion": e["source_assertion"]})
        for c in query.get("constraints", []):
            var, field = c["left"].split(".", 1)
            left = get(binding[var], field)
            if c["op"] == "equals":
                right = c["value"]
            else:
                var, field = c["right"].split(".", 1)
                right = get(binding[var], field)
            if left is None or right is None:
                continue
            if c["op"] in ["same", "equals"]:
                holds = equal_value(left, right)
            elif c["op"] == "different":
                holds = not equal_value(left, right)
            elif not iso_date(left) or not iso_date(right):
                missing.append({"constraint": c, "reason": "Exact ISO event dates required"})
                continue
            else:
                holds = left < right
            if not holds:
                failed.append({"constraint": c, "left": left, "right": right})
        witness = {"binding": {v: e["id"] for v, e in binding.items()},
                   "evidence": [x for e in combo for x in e["evidence"]],
                   "scopes": {v: e["scope"] for v, e in binding.items()},
                   "origins": {v: e["origin"] for v, e in binding.items()}}
        if failed:
            rejected.append(dict(witness, failed_conditions=failed, uncertainty=missing))
        elif missing:
            unknown.append(dict(witness, uncertainty=missing))
        else:
            good.append(witness)
    specified = all("event_id" in a for a in query["atoms"])
    status = "MATCH" if good else "UNKNOWN" if unknown else "MISMATCH" if specified and all(pools) else "NOT_FOUND"
    return {"status": status, "unit_id": annotation["units"][0]["id"], "witnesses": good,
            "uncertain_bindings": unknown, "rejected_bindings": rejected,
            "conflicts": list({canonical(x): x for x in conflicts}.values()), "closed_world": False,
            "assumption": "ANNOTATED_FIELDS_ACCURATE_WITH_EXPLICIT_UNCERTAINTY",
            "answer_scope": "SCOPED_RECORD_EXISTENCE_NOT_GLOBAL_LEGAL_TRUTH"}


def known_seed(event):
    for field, target in [("type", event["type"]), ("status", "COURT_FOUND"), ("polarity", "POSITIVE"), ("id", event["id"])]:
        value, reasons = field_value(event, field)
        if reasons or value != target:
            return None
    roles, attrs = {}, {}
    for root, destination in [("roles", roles), ("attributes", attrs)]:
        for key in sorted(event[root]):
            value, reasons = field_value(event, root + "." + key)
            if not reasons:
                destination[key] = value
    date, reasons = field_value(event, "time")
    if reasons or not iso_date(date):
        date = None
    return {"id": event["id"], "type": event["type"], "roles": roles, "attributes": attrs, "time": date}


def candidate_order(serialized):
    query = json.loads(serialized)
    extra = sum(c["op"] in ["before", "equals"] for c in query["constraints"])
    joins = sum(c["op"] == "same" for c in query["constraints"])
    return extra, joins, serialized


def generate(annotations):
    """Two distinct records, one or two ID joins, at most one extra condition.

    Prioritize all structural bases before time/attribute extensions. No support
    pruning, outcome supervision, or test-set filtering. Nulls never seed joins.
    """
    if len({a["case_id"] for a in annotations}) != len(annotations):
        raise ValueError("One annotation per case; A/B do not increase support")
    return generate_from_seeds([{"case_id": ann["case_id"], "events": [s for e in ann["events"]
                                 for s in [known_seed(e)] if s is not None]} for ann in annotations])


def generate_from_seeds(annotations, max_joins=2):
    """Expand only already-certified cells; caller supplies their provenance.

    Shared by reviewed and accurate-input paths. It grants no approvals and
    reads no raw assertion fields. Those paths use separate field projectors.
    """
    if max_joins not in [1, 2]:
        raise ValueError("Supported join budget: one or two")
    if len({a["case_id"] for a in annotations}) != len(annotations):
        raise ValueError("One seed annotation per case")
    candidates = set()
    for ann in sorted(annotations, key=lambda a: a["case_id"]):
        seeds = ann["events"]
        for a, b in itertools.combinations(sorted(seeds, key=lambda e: e["id"]), 2):
            atoms = [{"var": "a", "type": a["type"]}, {"var": "b", "type": b["type"]}]
            links = [{"op": "same", "left": "a.roles." + ka, "right": "b.roles." + kb}
                     for ka, va in sorted(a["roles"].items()) for kb, vb in sorted(b["roles"].items()) if va == vb]
            for size in range(1, max_joins + 1):
                for joins in itertools.combinations(links, size):
                    base = [{"op": "different", "left": "a.id", "right": "b.id"}] + list(joins)
                    variants = [base]
                    if iso_date(a["time"]) and iso_date(b["time"]) and a["time"] != b["time"]:
                        l, r = ("a.time", "b.time") if a["time"] < b["time"] else ("b.time", "a.time")
                        variants.append(base + [{"op": "before", "left": l, "right": r}])
                    for var, event in [("a", a), ("b", b)]:
                        for key, value in sorted(event["attributes"].items()):
                            if scalar(value):
                                variants.append(base + [{"op": "equals", "left": var + ".attributes." + key, "value": value}])
                    for constraints in variants:
                        candidates.add(canonical_query({"atoms": atoms, "constraints": constraints}))
    return sorted(candidates, key=candidate_order)
