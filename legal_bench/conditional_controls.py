"""Hand-specified synthetic controls, not natural cases or legal gold labels."""
import copy


def query(joins=1, temporal=False):
    clauses = [{"op": "different", "left": "n.id", "right": "p.id"},
               {"op": "same", "left": "n.roles.debt", "right": "p.roles.debt"}]
    if joins == 2:
        clauses.append({"op": "same", "left": "n.roles.actor", "right": "p.roles.actor"})
    if temporal:
        clauses.append({"op": "before", "left": "n.time", "right": "p.time"})
    return {"atoms": [{"var": "n", "type": "N"}, {"var": "p", "type": "P"}], "constraints": clauses}


def mappings():
    return {name: {"type": name, "roles": {"debt": "debt", "actor": "person"}} for name in ("N", "P")}


def raw_case(case_id):
    assertions = []
    for identifier, kind, day in (("n1", "N", "2020-01-01"), ("p1", "P", "2020-02-01")):
        assertions.append({"id": identifier, "kind": "FACT", "predicate": kind,
                           "roles": {"debt": "d1", "person": "person1"}, "attributes": {"amount": 100},
                           "scope": {}, "time": {"date": day}, "polarity": "POSITIVE", "unresolved": [],
                           "origin": {"mode": "NARRATED"}, "deciding_court_treatment": {"value": "ADOPTED", "evidence": []},
                           "evidence": [{"segment_id": "synthetic", "quote": "Manually constructed control"}]})
    return {"case_id": case_id, "units": [{"id": "u", "primary": True}],
            "predicate_definitions": [{"id": name, "roles": {"debt": "Debt object", "person": "Individual person"}, "meaning": name}
                                      for name in ("N", "P")], "assertions": assertions}


def controls():
    cases, expected = [], []

    def add(name, mutation=None, statuses=("MATCH", "MATCH", "MATCH")):
        raw = raw_case(name)
        if mutation:
            mutation(raw)
        cases.append(raw)
        expected.append({"case_id": name, "statuses": dict(zip(("debt", "debt_and_actor", "debt_before_payment"), statuses))})

    def uncertain(raw, field):
        raw["assertions"][1]["unresolved"].append({"field": field, "reason": "Control: this field is unknown"})

    add("positive1")
    add("positive2")
    add("multiple_witnesses", lambda r: r["assertions"].append(dict(copy.deepcopy(r["assertions"][1]), id="p2")))
    add("other_debt", lambda r: r["assertions"][1]["roles"].update(debt="d2"), ("NOT_FOUND",) * 3)
    add("other_actor", lambda r: r["assertions"][1]["roles"].update(person="person2"), ("MATCH", "NOT_FOUND", "MATCH"))
    add("unknown_actor", lambda r: r["assertions"][1]["roles"].update(person=None), ("MATCH", "UNKNOWN", "MATCH"))
    add("unknown_date", lambda r: uncertain(r, "time"), ("MATCH", "MATCH", "UNKNOWN"))
    add("negative", lambda r: r["assertions"][1].update(polarity="NEGATIVE"), ("NOT_FOUND",) * 3)
    add("unknown_adoption", lambda r: r["assertions"][1]["deciding_court_treatment"].update(value="UNCLEAR"), ("UNKNOWN",) * 3)
    add("unknown_amount", lambda r: uncertain(r, "attributes.amount"))
    add("unparsed_debt_limit", lambda r: r["assertions"][1]["scope"].update(
        limited_to={"value": "Only for another debt; binding not parsed", "affects": ["roles.debt"], "resolved": False}), ("UNKNOWN",) * 3)
    add("unregistered_limit", lambda r: r["assertions"][1]["scope"].update(restriction="Only one part of the debt"), ("UNKNOWN",) * 3)
    add("quantified", lambda r: r["assertions"][1]["scope"].update(quantifier="all debts"), ("UNKNOWN",) * 3)
    add("unknown_origin", lambda r: uncertain(r, "origin"))
    add("unknown_predicate", lambda r: uncertain(r, "predicate"), ("UNKNOWN",) * 3)
    add("role_alias_uncertain", lambda r: uncertain(r, "roles.person"), ("MATCH", "UNKNOWN", "MATCH"))
    add("reversed_time", lambda r: r["assertions"][1]["time"].update(date="2019-01-01"), ("MATCH", "MATCH", "NOT_FOUND"))
    return {"cases": cases, "expected": expected, "queries": dict(zip(
        ("debt", "debt_and_actor", "debt_before_payment"), (query(), query(2), query(1, True)))),
        "label_origin": "HAND_SPECIFIED_SYNTHETIC_PROGRAM_SEMANTICS_NOT_LEGAL_ANNOTATIONS"}
