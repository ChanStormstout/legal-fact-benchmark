import copy
import unittest

from legal_bench.core import digest
from legal_bench.development_experiment import prepare, run_query, candidate_set, run_patterns, without_identity


class UnreviewedDevelopmentTests(unittest.TestCase):
    def annotation(self, case="c1", unknown_object=False):
        def a(aid, predicate, debt):
            return {"id": aid, "kind": "FACT", "predicate": predicate,
                    "roles": {"debt": debt}, "attributes": {}, "scope": {}, "time": None,
                    "polarity": "POSITIVE", "unresolved": [], "origin": {"mode": "NARRATED"},
                    "deciding_court_treatment": {"value": "ADOPTED", "evidence": [{"segment_id": "s", "quote": "Synthetic"}]},
                    "evidence": [{"segment_id": "s", "quote": "Synthetic"}]}
        return {"case_id": case, "units": [{"id": "u", "primary": True}],
                "predicate_definitions": [{"id": name, "roles": {"debt": "The identified debt"}, "meaning": name}
                                          for name in ["N", "P"]],
                "assertions": [a("n1", "N", "d1"), a("p1", "P", None if unknown_object else "d1")]}

    def mappings(self):
        return {name: {"type": name, "roles": {"debt": "debt"}} for name in ["N", "P"]}

    def query(self):
        return {"atoms": [{"var": "n", "type": "N"}, {"var": "p", "type": "P"}],
                "constraints": [{"op": "same", "left": "n.roles.debt", "right": "p.roles.debt"}]}

    def test_scope_blocked_and_unsafe_diagnostic_retains_qualifier(self):
        a = self.annotation()
        a["assertions"][1]["scope"] = {"limited_to": "First instalment"}
        before = digest(a)
        safe = prepare(a, self.mappings(), "STRICT_SCOPE")
        unsafe = prepare(a, self.mappings(), "SCOPE_BLIND_DIAGNOSTIC")
        self.assertEqual(run_query(safe, self.query())["status"], "UNKNOWN")
        result = run_query(unsafe, self.query())
        self.assertEqual(result["status"], "MATCH")
        self.assertEqual(result["semantic_review_state"], "PENDING")
        self.assertEqual(result["witnesses"][0]["records"]["p"]["scope"], {"limited_to": "First instalment"})
        self.assertEqual(digest(a), before)

    def test_unknown_objects_do_not_join_or_seed_patterns(self):
        a = prepare(self.annotation(unknown_object=True), self.mappings(), "SCOPE_BLIND_DIAGNOSTIC")
        self.assertEqual(run_query(a, self.query())["status"], "UNKNOWN")
        self.assertEqual(candidate_set([a]), [])

    def test_other_possible_binding_survives_specified_failure(self):
        raw = self.annotation()
        raw["assertions"][1]["roles"]["debt"] = "d2"
        other = copy.deepcopy(raw["assertions"][1])
        other["id"], other["roles"]["debt"] = "p2", None
        raw["assertions"].append(other)
        a = prepare(raw, self.mappings(), "STRICT_SCOPE")
        specific = self.query()
        specific["atoms"][0]["event_id"], specific["atoms"][1]["event_id"] = "n1", "p1"
        self.assertEqual(run_query(a, specific)["status"], "MISMATCH")
        self.assertEqual(run_query(a, self.query())["status"], "UNKNOWN")

    def test_adoption_and_negation_are_not_overridden(self):
        raw = self.annotation()
        raw["assertions"][1]["deciding_court_treatment"]["value"] = "NOT_ESTABLISHED"
        a = prepare(raw, self.mappings(), "SCOPE_BLIND_DIAGNOSTIC")
        self.assertEqual(run_query(a, self.query())["status"], "UNKNOWN")
        self.assertEqual(candidate_set([a]), [])
        raw["assertions"][1]["deciding_court_treatment"]["value"] = "ADOPTED"
        raw["assertions"][1]["polarity"] = "NEGATIVE"
        a = prepare(raw, self.mappings(), "SCOPE_BLIND_DIAGNOSTIC")
        self.assertEqual(run_query(a, self.query())["status"], "NOT_FOUND")
        self.assertEqual(candidate_set([a]), [])

    def test_general_proceeding_guard_and_missing_roles(self):
        raw = self.annotation()
        raw["assertions"][1]["attributes"]["document"] = "administrative representation"
        mapping = self.mappings()
        mapping["P"]["attribute_guard"] = {"field": "proceeding", "pattern": r"^O\.S\."}
        result = prepare(raw, mapping, "STRICT_SCOPE")
        self.assertEqual([x["id"] for x in result["events"]], ["n1"])
        self.assertEqual(result["excluded"][0]["reason"], "MAPPING_GUARD_NOT_MET")
        mapping["N"]["roles"]["extra"] = "nonexistent"
        with self.assertRaises(ValueError):
            prepare(raw, mapping, "STRICT_SCOPE")

    def test_event_dates_never_replaced_by_judgment_dates(self):
        raw = self.annotation()
        raw["judgment_date"] = "2001-01-01"
        raw["assertions"][0]["time"] = {"date": "2000-1-1"}
        a = prepare(raw, self.mappings(), "STRICT_SCOPE")
        self.assertIsNone(a["events"][0]["time"])
        self.assertIsNone(a["events"][1]["time"])
        self.assertTrue(a["events"][0]["unresolved"])

    def test_same_case_ab_cannot_inflate_support(self):
        a = prepare(self.annotation(), self.mappings(), "STRICT_SCOPE")
        with self.assertRaises(ValueError):
            candidate_set([a, copy.deepcopy(a)])
        with self.assertRaises(ValueError):
            run_patterns([a, copy.deepcopy(a)], [])

    def test_fixed_candidates_and_unknown_not_counted_as_negative(self):
        a = prepare(self.annotation(), self.mappings(), "STRICT_SCOPE")
        b = prepare(self.annotation("c2", unknown_object=True), self.mappings(), "STRICT_SCOPE")
        candidates = candidate_set([a])
        result = run_patterns([a, b], candidates)
        self.assertEqual(result["patterns"][0]["support"], 1)
        self.assertEqual(result["patterns"][0]["unknown"], 1)
        self.assertFalse(result["patterns"][0]["repeated"])
        self.assertEqual(result, run_patterns([copy.deepcopy(a), copy.deepcopy(b)], candidates))

    def test_identity_ablation_does_not_remove_temporal_or_attribute_conditions(self):
        q = self.query()
        q["constraints"] += [{"op": "different", "left": "n.id", "right": "p.id"},
                             {"op": "before", "left": "n.time", "right": "p.time"},
                             {"op": "equals", "left": "p.attributes.amount", "value": 25}]
        changed = without_identity(q)
        self.assertEqual([c["op"] for c in changed["constraints"]], ["different", "before", "equals"])
        self.assertEqual(len(q["constraints"]), 4)

    def test_identity_ablation_keeps_unknown_dates_unknown(self):
        raw = self.annotation()
        a = prepare(raw, self.mappings(), "STRICT_SCOPE")
        q = self.query()
        q["constraints"].append({"op": "before", "left": "n.time", "right": "p.time"})
        self.assertEqual(run_query(a, without_identity(q))["status"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
