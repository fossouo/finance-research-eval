"""Unit tests for the deterministic reference computation engine."""
import unittest

from harness.compute import metrics as M


class TestCompute(unittest.TestCase):
    def test_known_metrics_recompute_correctly(self):
        self.assertAlmostEqual(M.recompute("ev_ebitda", {"ev": 2400.0, "ebitda": 300.0}), 8.0)
        self.assertAlmostEqual(M.recompute("gross_margin", {"gross_profit": 480.0, "revenue": 1200.0}), 0.4)
        self.assertAlmostEqual(M.recompute("net_debt_to_ebitda", {"net_debt": 600.0, "ebitda": 300.0}), 2.0)
        self.assertAlmostEqual(M.recompute("fcf_yield", {"fcf": 90.0, "market_cap": 1800.0}), 0.05)
        self.assertAlmostEqual(M.recompute("revenue_growth", {"revenue": 1200.0, "revenue_prior": 1000.0}), 0.2)

    def test_unknown_metric_raises(self):
        with self.assertRaises(M.ComputeError):
            M.recompute("made_up_metric", {"a": 1.0})

    def test_missing_operand_raises(self):
        with self.assertRaises(M.ComputeError):
            M.recompute("ev_ebitda", {"ev": 2400.0})  # ebitda missing

    def test_zero_division_raises_compute_error(self):
        with self.assertRaises(M.ComputeError):
            M.recompute("ev_ebitda", {"ev": 2400.0, "ebitda": 0.0})

    def test_tolerance_band(self):
        # within 0.5 % -> agree ; outside -> disagree
        self.assertTrue(M.values_agree(8.0, 8.03))      # ~0.375 %
        self.assertFalse(M.values_agree(8.0, 6.0))      # way off
        self.assertFalse(M.values_agree(0.05, 0.06))    # 20 %


if __name__ == "__main__":
    unittest.main()
