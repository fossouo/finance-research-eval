"""End-to-end P3 tests (offline, 0 VRAM, 0 network).

Prove the full loop EvalItem -> candidate -> RR -> gates, and that the harness
discriminates a faithful candidate from a sloppy one — the core value of P3.
"""
import unittest

from harness.eval_run import run, _all_synthetic_items
from harness.candidates.mock import FaithfulMockCandidate, SloppyMockCandidate


class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        self.items = _all_synthetic_items()
        self.assertGreater(len(self.items), 0)

    def test_faithful_candidate_is_admissible_and_accurate(self):
        rep = run(FaithfulMockCandidate(), self.items, "personal-research")
        s = rep["summary"]
        self.assertEqual(s["blocked"], 0, "faithful candidate should never be blocked")
        self.assertEqual(s["errors"], 0)
        # faithful mock reports the sourced gold -> every item correct
        self.assertEqual(s["correct"], s["total"])

    def test_faithful_candidate_admissible_on_client_lane_too(self):
        rep = run(FaithfulMockCandidate(), self.items, "client-mifid")
        self.assertEqual(rep["summary"]["blocked"], 0)

    def test_sloppy_candidate_blocked_on_client_for_numeric_items(self):
        # numeric-gold sources (finqa, edgar) make a quantitative claim; with no
        # evidence, G-1 fails -> client lane BLOCKS even though the answer is right.
        numeric_items = [it for it in self.items if it.gold_kind == "numeric"]
        self.assertGreater(len(numeric_items), 0)
        rep = run(SloppyMockCandidate(), numeric_items, "client-mifid")
        self.assertEqual(rep["summary"]["blocked"], rep["summary"]["total"],
                         "unsourced numeric answers must be blocked on the client lane")
        # ...and they were 'correct' yet still blocked: recevability primes accuracy
        self.assertEqual(rep["summary"]["correct"], rep["summary"]["total"])

    def test_sloppy_flagged_but_admissible_on_personal(self):
        numeric_items = [it for it in self.items if it.gold_kind == "numeric"]
        rep = run(SloppyMockCandidate(), numeric_items, "personal-research")
        # personal lane: G-1 is a flag, not a block -> admissible but recorded
        self.assertEqual(rep["summary"]["blocked"], 0)
        for r in rep["records"]:
            self.assertEqual(r["gates"]["G-1"], "FAIL")


if __name__ == "__main__":
    unittest.main()
