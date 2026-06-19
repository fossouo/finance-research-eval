"""Tests for the gate-regression tracker (tools/gate_regression.py).

Verifies: snapshot determinism, baseline match, drift detection,
and --synthetic-only determinism. Pure stdlib, offline, no real data.

The committed baseline lives at tests/fixtures/gate_regression_baseline.json
(tests/data/ is gitignored because ".gitignore" patterns on "data/" match
anywhere in the tree, so we use tests/fixtures/ instead).
"""
import copy
import json
import os
import sys
import tempfile
import unittest

# Ensure repo root importable.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Import internal helpers directly so we can test without subprocess.
from tools.gate_regression import (
    _build_snapshot,
    _snapshot_diff,
    _BASELINE_PATH,
    main as _main,
)


class TestSnapshotDeterminism(unittest.TestCase):
    def test_same_snapshot_twice(self):
        a = _build_snapshot()
        b = _build_snapshot()
        self.assertEqual(a, b)

    def test_synthetic_only_same_snapshot_twice(self):
        a = _build_snapshot(synthetic_only=True)
        b = _build_snapshot(synthetic_only=True)
        self.assertEqual(a, b)

    def test_corpus_size_positive(self):
        snap = _build_snapshot()
        self.assertGreater(snap["corpus_size"], 0)

    def test_records_sorted_by_name(self):
        snap = _build_snapshot()
        names = [r["name"] for r in snap["records"]]
        self.assertEqual(names, sorted(names))

    def test_verdict_distribution_has_both_verdicts(self):
        snap = _build_snapshot()
        vd = snap["verdict_distribution"]
        self.assertIn("ADMISSIBLE", vd)
        self.assertIn("BLOCKED", vd)

    def test_all_expected_matches(self):
        """The synthetic catalogue has known verdicts — all must match."""
        snap = _build_snapshot()
        self.assertEqual(
            snap["expected_verdict_matches"],
            snap["expected_verdict_total"],
            "Some fixture verdict expectations do not match the current gate logic.",
        )

    def test_per_gate_counts_present(self):
        snap = _build_snapshot()
        for gid in ("G-1", "G-2", "G-3", "G-4", "G-5", "G-6"):
            self.assertIn(gid, snap["per_gate_counts"])

    def test_synthetic_only_same_size_as_full(self):
        """All fixture cases are synthetic, so both modes should produce the same size."""
        full = _build_snapshot(synthetic_only=False)
        synth = _build_snapshot(synthetic_only=True)
        self.assertEqual(full["corpus_size"], synth["corpus_size"])


class TestBaselineMatch(unittest.TestCase):
    def test_baseline_file_exists(self):
        self.assertTrue(
            os.path.exists(_BASELINE_PATH),
            f"Baseline not found: {_BASELINE_PATH}",
        )

    def test_baseline_matches_fresh_snapshot(self):
        with open(_BASELINE_PATH, encoding="utf-8") as f:
            baseline = json.load(f)
        current = _build_snapshot(synthetic_only=baseline.get("synthetic_only", False))
        diffs = _snapshot_diff(baseline, current)
        self.assertEqual(
            diffs, [],
            "Baseline drift detected:\n" + "\n".join(diffs),
        )

    def test_main_exit_0_on_match(self):
        rc = _main([])
        self.assertEqual(rc, 0)

    def test_main_synthetic_only_exit_0(self):
        rc = _main(["--synthetic-only"])
        self.assertEqual(rc, 0)


class TestDriftDetection(unittest.TestCase):
    def test_perturbed_verdict_detected(self):
        """Changing a verdict in the baseline triggers drift detection."""
        current = _build_snapshot()
        perturbed = copy.deepcopy(current)
        # Flip the first record's verdict.
        first = perturbed["records"][0]
        first["verdict"] = "ADMISSIBLE" if first["verdict"] == "BLOCKED" else "BLOCKED"
        diffs = _snapshot_diff(perturbed, current)
        self.assertGreater(len(diffs), 0)

    def test_added_record_detected(self):
        current = _build_snapshot()
        perturbed = copy.deepcopy(current)
        perturbed["records"].append({
            "name": "z_extra_record",
            "rr_id": "rr-999",
            "lane": "personal-research",
            "verdict": "ADMISSIBLE",
            "expected_verdict": None,
            "verdict_match": True,
            "gate_statuses": {},
        })
        perturbed["corpus_size"] += 1
        diffs = _snapshot_diff(current, perturbed)
        self.assertGreater(len(diffs), 0)

    def test_removed_record_detected(self):
        current = _build_snapshot()
        perturbed = copy.deepcopy(current)
        perturbed["records"] = perturbed["records"][1:]
        perturbed["corpus_size"] -= 1
        diffs = _snapshot_diff(current, perturbed)
        self.assertGreater(len(diffs), 0)

    def test_gate_status_change_detected(self):
        current = _build_snapshot()
        perturbed = copy.deepcopy(current)
        # Flip G-1 status in the first record.
        gs = perturbed["records"][0]["gate_statuses"]
        gs["G-1"] = "PASS" if gs.get("G-1") == "FAIL" else "FAIL"
        diffs = _snapshot_diff(current, perturbed)
        self.assertGreater(len(diffs), 0)

    def test_identical_snapshots_no_diff(self):
        current = _build_snapshot()
        diffs = _snapshot_diff(current, current)
        self.assertEqual(diffs, [])

    def test_main_exit_1_on_stale_baseline(self):
        """Write a wrong baseline to a temp file and verify exit 1."""
        bad_snap = {"corpus_size": 999, "verdict_distribution": {}, "records": [],
                    "per_gate_counts": {}, "expected_verdict_matches": 0,
                    "expected_verdict_total": 0, "synthetic_only": False}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tf:
            json.dump(bad_snap, tf)
            tmp_path = tf.name
        try:
            # Monkey-patch the module-level baseline path and call main.
            import tools.gate_regression as gr_mod
            orig = gr_mod._BASELINE_PATH
            gr_mod._BASELINE_PATH = tmp_path
            try:
                rc = _main([])
            finally:
                gr_mod._BASELINE_PATH = orig
        finally:
            os.unlink(tmp_path)
        self.assertEqual(rc, 1)

    def test_update_creates_valid_baseline(self):
        """--update writes a baseline that immediately compares clean."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tf:
            tmp_path = tf.name

        import tools.gate_regression as gr_mod
        orig = gr_mod._BASELINE_PATH
        gr_mod._BASELINE_PATH = tmp_path
        try:
            rc_update = _main(["--update"])
            self.assertEqual(rc_update, 0)
            rc_compare = _main([])
            self.assertEqual(rc_compare, 0)
        finally:
            gr_mod._BASELINE_PATH = orig
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()
