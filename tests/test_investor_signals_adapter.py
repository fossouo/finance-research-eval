"""Conformity test for the investor-signals adapter.

Uses only synthetic fixtures (no real data — open-core). Asserts:
  - a clean, point-in-time-consistent decision -> ADMISSIBLE
  - folding the hindsight outcome into the decision -> BLOCKED on G-4 (look-ahead)
  - adapter output is structurally valid

Pure stdlib unittest, no network.
"""
import unittest

from harness import rr as rrlib
from harness.gates.gates import evaluate
from tools.investor_signals.adapter import record_to_rr, evaluate_corpus
from tools.investor_signals.fixtures_synthetic import synthetic_records


class TestInvestorSignalsAdapter(unittest.TestCase):
    def test_adapter_output_is_structurally_valid(self):
        for rec in synthetic_records():
            rr = record_to_rr(rec)
            self.assertEqual(
                rrlib.validate_structure(rr), [],
                f"{rec['id']}: structural errors in adapted RR",
            )

    def test_clean_decision_is_admissible(self):
        for rec in synthetic_records():
            rr = record_to_rr(rec)
            ev = evaluate(rr)
            self.assertEqual(
                ev.verdict, "ADMISSIBLE",
                f"{rec['id']}: expected ADMISSIBLE, got {ev.verdict} ({ev.status_map()})",
            )
            self.assertEqual(ev.status_map()["G-4"], "PASS")

    def test_outcome_lookahead_is_blocked_on_g4(self):
        rec = synthetic_records()[0]
        rr = record_to_rr(rec, include_outcome=True)
        ev = evaluate(rr)
        self.assertEqual(ev.verdict, "BLOCKED",
                         "folding hindsight outcome must be BLOCKED (look-ahead)")
        self.assertEqual(ev.status_map()["G-4"], "FAIL")

    def test_evaluate_corpus_summary_counts(self):
        report = evaluate_corpus(synthetic_records())
        self.assertEqual(report["summary"]["total"], len(synthetic_records()))
        self.assertEqual(report["summary"]["blocked"], 0)
        self.assertEqual(report["summary"]["structurally_invalid"], 0)


if __name__ == "__main__":
    unittest.main()
