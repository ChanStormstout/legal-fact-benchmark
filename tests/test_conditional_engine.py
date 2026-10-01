import copy
import json
import unittest

from legal_bench import conditional_engine as engine
from legal_bench import exhaustive_oracle as oracle
from legal_bench.conditional_controls import controls, mappings, raw_case, query
from legal_bench.development_experiment import prepare, run_query, candidate_set, run_patterns, CONDITIONAL_POLICY
from legal_bench.core import digest


class ConditionalMatchingTests(unittest.TestCase):
    def view(self, raw):
        return prepare(raw, mappings(), CONDITIONAL_POLICY)

    def test_all_hand_expected_cases_and_independent_binding_oracle(self):
        fixture = controls()
        for raw, expected in zip(fixture["cases"], fixture["expected"]):
            view = self.view(raw)
            for name, q in fixture["queries"].items():
                with self.subTest(case=raw["case_id"], query=name):
                    result, truth = run_query(view, q), oracle.answer(view, q)
                    self.assertEqual(result["status"], expected["statuses"][name])
                    self.assertEqual(result["status"], truth["status"])
                    self.assertEqual(sorted(tuple(sorted(w["binding"].items())) for w in result["witnesses"]), truth["matches"])

    def test_amount_uncertainty_blocks_amount_condition_only(self):
        raw = raw_case("c")
        raw["assertions"][1]["unresolved"] = [{"field": "attributes.amount", "reason": "Approximate"}]
        v = self.view(raw)
        q = query()
        self.assertEqual(run_query(v, q)["status"], "MATCH")
        q["constraints"].append({"op": "equals", "left": "p.attributes.amount", "value": 100})
        self.assertEqual(run_query(v, q)["status"], "UNKNOWN")

    def test_failure_of_one_pair_does_not_negate_case(self):
        raw = raw_case("c")
        raw["assertions"][1]["roles"]["debt"] = "d2"
        extra = dict(copy.deepcopy(raw["assertions"][1]), id="p2")
        extra["roles"]["debt"] = None
        raw["assertions"].append(extra)
        q = query()
        self.assertEqual(run_query(self.view(raw), q)["status"], "UNKNOWN")
        specified = copy.deepcopy(q)
        specified["atoms"][0]["event_id"], specified["atoms"][1]["event_id"] = "n1", "p1"
        self.assertEqual(run_query(self.view(raw), specified)["status"], "MISMATCH")
        extra["roles"]["debt"] = "d1"
        raw["assertions"][-1] = extra
        self.assertEqual(run_query(self.view(raw), q)["status"], "MATCH")

    def test_unresolved_type_not_dropped_from_possible_pool(self):
        raw = raw_case("c")
        raw["assertions"][1]["unresolved"] = [{"field": "predicate", "reason": "P or N not decided"}]
        q = {"atoms": [{"var": "n", "type": "OTHER"}], "constraints": []}
        self.assertEqual(run_query(self.view(raw), q)["status"], "UNKNOWN")

    def test_date_conflict_does_not_block_identity_and_invalid_date_not_compared(self):
        raw = raw_case("c")
        raw["assertions"][1]["scope"] = {"date_conflict": ["2020-02-01", "2020-03-01"]}
        self.assertEqual(run_query(self.view(raw), query())["status"], "MATCH")
        self.assertEqual(run_query(self.view(raw), query(1, True))["status"], "UNKNOWN")
        raw["assertions"][1]["scope"] = {}
        raw["assertions"][1]["time"]["date"] = "2020-2-1"
        self.assertEqual(run_query(self.view(raw), query(1, True))["status"], "UNKNOWN")

    def test_context_and_extent_retained_without_claiming_extent_equality(self):
        raw = raw_case("c")
        raw["assertions"][1]["scope"] = {"period": "Earlier proceeding", "portion": "North section"}
        result = run_query(self.view(raw), query())
        self.assertEqual(result["status"], "MATCH")
        self.assertEqual(result["witnesses"][0]["scopes"]["p"], raw["assertions"][1]["scope"])
        self.assertIn("NOT_GLOBAL", result["answer_scope"])

    def test_no_approved_fields_or_source_mutations(self):
        raw = raw_case("c")
        before = digest(raw)
        v = self.view(raw)
        run_query(v, query())
        candidate_set([v])
        self.assertEqual(digest(raw), before)
        self.assertNotIn("approved_fields", v["events"][0])
        self.assertEqual(v["events"][0]["semantic_review_state"], "PENDING")

    def test_invalid_dependency_rejected(self):
        raw = raw_case("c")
        raw["assertions"][1]["scope"] = {"limited_to": {"affects": "roles.debt", "resolved": False}}
        with self.assertRaises(ValueError):
            self.view(raw)

    def test_resolved_limit_not_automatically_erased(self):
        raw = raw_case("c")
        raw["assertions"][1]["scope"] = {"limited_to": {"affects": ["roles.debt"], "resolved": True, "value": "D2 only"}}
        self.assertEqual(run_query(self.view(raw), query())["status"], "UNKNOWN")

    def test_unsupported_aggregates_return_unsupported(self):
        q = dict(query(), aggregate="sum")
        self.assertEqual(run_query(self.view(raw_case("c")), q)["status"], "UNSUPPORTED")

    def test_boolean_not_numeric_amount_and_time_not_object_identifier(self):
        raw = raw_case("c")
        raw["assertions"][1]["attributes"]["amount"] = 1
        q = query()
        q["constraints"].append({"op": "equals", "left": "p.attributes.amount", "value": True})
        self.assertEqual(run_query(self.view(raw), q)["status"], "NOT_FOUND")
        q["constraints"][-1] = {"op": "before", "left": "n.roles.debt", "right": "p.roles.debt"}
        self.assertEqual(run_query(self.view(raw), q)["status"], "UNSUPPORTED")


class ConditionalSearchTests(unittest.TestCase):
    def views(self):
        return [prepare(raw, mappings(), CONDITIONAL_POLICY) for raw in controls()["cases"]]

    def test_candidates_exactly_equal_independent_exhaustive_language(self):
        views = self.views()
        result = oracle.check(views, candidate_set(views))
        self.assertTrue(result["exact"], {"missing": result["missing"], "extra": result["extra"]})
        self.assertGreater(result["templates_checked"], len(result["candidates"]))
        self.assertIn(oracle.normalized(query(2)), result["candidates"])

    def test_support_binding_and_unknown_counts_match_oracle(self):
        views = self.views()
        candidates = candidate_set(views)
        result = run_patterns(views, candidates)
        for pattern in result["patterns"]:
            truth = [oracle.answer(v, pattern["query"]) for v in views]
            self.assertEqual(pattern["support"], sum(t["status"] == "MATCH" for t in truth))
            self.assertEqual(pattern["unknown"], sum(t["status"] == "UNKNOWN" for t in truth))
        double = next(p for p in result["patterns"] if oracle.normalized(p["query"]) == oracle.normalized(query(2)))
        self.assertEqual(double["support"], 7)  # Multiple witnesses contribute one case.

    def test_budget_frontier_and_structural_priority(self):
        views = self.views()
        candidates = candidate_set(views)
        result = run_patterns(views, candidates, budget=1)
        self.assertFalse(result["search_complete"])
        self.assertEqual(result["frontier"], candidates[1:])
        self.assertEqual(len(result["patterns"]), 1)
        self.assertFalse(any(c["op"] in ["before", "equals"] for c in json.loads(candidates[0])["constraints"]))

    def test_duplicate_cases_rejected_and_deterministic(self):
        views = self.views()
        with self.assertRaises(ValueError):
            candidate_set([views[0], views[0]])
        self.assertEqual(candidate_set(views), candidate_set(list(reversed(views))))


if __name__ == "__main__":
    unittest.main()
