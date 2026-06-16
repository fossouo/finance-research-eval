"""Tests for the MEDISYN SA wealth-management ("patrimoine / CGP") worked case.

Two companion records on the client-mifid lane:
  - admissible general-research note (every computation recomputes exactly)
  - rejected note (fabricated EV/EBITDA -> G-3 FAIL -> G-5 BLOCK)

These assert the *behaviour a CGP relies on*: an honest note passes, and a note
whose headline multiple the evidence does not support is refused (not softened).
"""
import re
import unittest

from harness.gates.gates import evaluate
from harness.fixtures import cases_patrimoine as P


class TestPatrimoineBuild(unittest.TestCase):
    def setUp(self):
        self.ok, self.bad = P.build_patrimoine_cases()

    def test_both_are_client_mifid(self):
        self.assertEqual(self.ok["lane"], "client-mifid")
        self.assertEqual(self.bad["lane"], "client-mifid")

    def test_reco_nature_is_general_research(self):
        self.assertEqual(self.ok["lane_fields"]["reco_nature"], "general-research")
        self.assertEqual(self.bad["lane_fields"]["reco_nature"], "general-research")

    def test_general_research_carries_no_suitability_block(self):
        # general-research must NOT require a personalised-advice suitability block
        self.assertNotIn("suitability", self.ok["lane_fields"])
        self.assertNotIn("suitability", self.bad["lane_fields"])

    def test_required_lane_fields_present(self):
        for rr in (self.ok, self.bad):
            lf = rr["lane_fields"]
            self.assertTrue(lf.get("reco_nature"))
            self.assertTrue(lf.get("disclaimers"))
            self.assertTrue(lf.get("conflicts_of_interest"))

    def test_audit_trail_stamped_and_reproducible(self):
        for rr in (self.ok, self.bad):
            self.assertIn("audit_trail", rr)
            self.assertTrue(rr["audit_trail"].get("input_hash"))

    def test_no_real_isin_or_ticker_leak(self):
        # The case is synthetic: any ISIN-shaped token must be XX-prefixed.
        blob = repr(self.ok) + repr(self.bad)
        for m in re.findall(r"\b[A-Z]{2}[A-Z0-9]{9}[0-9]\b", blob):
            self.assertTrue(m.startswith("XX"), f"non-synthetic ISIN-shaped token: {m}")

    def test_only_ev_ebitda_differs_between_the_two_notes(self):
        # The rejected note is the admissible note with ONE perturbed number,
        # so the demonstration isolates the verifier's catch.
        def ev_ebitda(rr):
            for c in rr["claims"]:
                for comp in c.get("computations", []):
                    if comp["metric"] == "ev_ebitda":
                        return comp["llm_value"]
            return None
        self.assertEqual(ev_ebitda(self.ok), 9.0)
        self.assertEqual(ev_ebitda(self.bad), 6.5)


class TestPatrimoineAdmissible(unittest.TestCase):
    def setUp(self):
        self.ev = evaluate(P.build_patrimoine_admissible())

    def test_verdict_admissible(self):
        self.assertEqual(self.ev.verdict, "ADMISSIBLE")

    def test_all_gates_pass(self):
        for g in self.ev.gate_results:
            self.assertEqual(g.status, "PASS", f"{g.gate_id} not PASS: {g.reason}")

    def test_g3_all_computations_agree(self):
        aug = self.ev.augmented_rr
        for c in aug["claims"]:
            for comp in c.get("computations", []):
                self.assertTrue(comp["agree"], f"{comp['metric']} did not agree")

    def test_g6_pass_without_suitability_on_general_research(self):
        # The branch that does NOT require suitability fields (general-research)
        # is exercised here and must PASS.
        self.assertEqual(self.ev.by_id("G-6").status, "PASS")

    def test_gate_status_map_has_six_gates(self):
        self.assertEqual(len(self.ev.status_map()), 6)


class TestPatrimoineRejected(unittest.TestCase):
    def setUp(self):
        self.ev = evaluate(P.build_patrimoine_rejected())

    def test_verdict_blocked(self):
        self.assertEqual(self.ev.verdict, "BLOCKED")

    def test_g3_fails_on_fabricated_multiple(self):
        g3 = self.ev.by_id("G-3")
        self.assertEqual(g3.status, "FAIL")
        self.assertIn("ev_ebitda", g3.reason)
        self.assertIn("6.5", g3.reason)
        self.assertIn("9.0", g3.reason)

    def test_g5_propagates_the_block_on_client_lane(self):
        g5 = self.ev.by_id("G-5")
        self.assertEqual(g5.status, "FAIL")
        self.assertEqual(g5.severity, "BLOCK")

    def test_failure_is_isolated_only_g3_and_g5_fail(self):
        failed = {g.gate_id for g in self.ev.gate_results if g.status == "FAIL"}
        self.assertEqual(failed, {"G-3", "G-5"})

    def test_recompute_records_the_honest_value(self):
        aug = self.ev.augmented_rr
        ev_comp = next(
            comp for c in aug["claims"] for comp in c.get("computations", [])
            if comp["metric"] == "ev_ebitda"
        )
        self.assertFalse(ev_comp["agree"])
        self.assertEqual(ev_comp["recomputed_value"], 9.0)


class TestPatrimoineRunner(unittest.TestCase):
    def test_run_returns_both_labelled_triples(self):
        results = P.run_patrimoine_cases()
        labels = [r[0] for r in results]
        self.assertEqual(labels, ["admissible", "rejected"])
        verdicts = {r[0]: r[1].verdict for r in results}
        self.assertEqual(verdicts["admissible"], "ADMISSIBLE")
        self.assertEqual(verdicts["rejected"], "BLOCKED")

    def test_each_augmented_rr_has_gate_status_map(self):
        for _, _, aug in P.run_patrimoine_cases():
            self.assertIn("_gate_status_map", aug)
            self.assertEqual(len(aug["_gate_status_map"]), 6)


if __name__ == "__main__":
    unittest.main()
