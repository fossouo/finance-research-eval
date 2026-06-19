"""Tests for the generated-corpus gate-regression mode.

Verifies:
  - Snapshot is deterministic across two calls with the same (n, seed).
  - The committed generated baseline matches a fresh n=60/seed=0 snapshot.
  - Thesis assertion: SloppyMockCandidate x client-mifid has blocked>0 and
    correct==total (right-but-inadmissible); FaithfulMockCandidate x
    client-mifid has blocked==0.
  - A perturbed/truncated snapshot is detected as drift.
  - Default (fixtures) mode still works and its baseline file path is unchanged.

Pure stdlib, offline, no real data.  Runs via ``python -m unittest discover``.
"""
from __future__ import annotations

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

from tools.gate_regression import (
    _build_generated_snapshot,
    _build_snapshot,
    _generated_snapshot_diff,
    _snapshot_diff,
    _BASELINE_PATH,
    _GENERATED_BASELINE_PATH,
    main as _main,
)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestGeneratedSnapshotDeterminism(unittest.TestCase):
    """The generated snapshot must be identical across two calls with the same
    (n, seed) pair — no randomness, no timestamp, no free-text leaking in."""

    def test_same_snapshot_twice_small(self):
        a = _build_generated_snapshot(n=10, seed=0)
        b = _build_generated_snapshot(n=10, seed=0)
        self.assertEqual(a, b)

    def test_same_snapshot_twice_full(self):
        """Full n=60 seed=0 — the size used by the committed baseline."""
        a = _build_generated_snapshot(n=60, seed=0)
        b = _build_generated_snapshot(n=60, seed=0)
        self.assertEqual(a, b)

    def test_different_seeds_differ(self):
        a = _build_generated_snapshot(n=20, seed=0)
        b = _build_generated_snapshot(n=20, seed=42)
        # Different seeds should produce (at least occasionally) different counts.
        # We don't assert they always differ, but structure must be the same shape.
        self.assertEqual(a["mode"], b["mode"])
        self.assertEqual(set(a["runs"].keys()), set(b["runs"].keys()))

    def test_snapshot_has_required_keys(self):
        snap = _build_generated_snapshot(n=10, seed=0)
        for key in ("mode", "n", "seed", "runs", "per_gate_distribution"):
            self.assertIn(key, snap)
        self.assertEqual(snap["mode"], "generated")
        self.assertEqual(snap["n"], 10)
        self.assertEqual(snap["seed"], 0)

    def test_expected_run_keys_present(self):
        snap = _build_generated_snapshot(n=10, seed=0)
        expected_keys = {
            "faithful-mock/client-mifid",
            "faithful-mock/personal-research",
            "sloppy-mock/client-mifid",
            "sloppy-mock/personal-research",
        }
        self.assertEqual(set(snap["runs"].keys()), expected_keys)

    def test_no_free_text_in_snapshot(self):
        """Ensure no per-item answer text leaks into the snapshot (keeps it small
        and stable across model versions)."""
        snap = _build_generated_snapshot(n=10, seed=0)
        serialized = json.dumps(snap)
        # 'answer' or 'gold' keys would indicate per-record leakage.
        self.assertNotIn('"answer"', serialized)
        self.assertNotIn('"gold"', serialized)

    def test_run_summary_has_integer_counts(self):
        snap = _build_generated_snapshot(n=10, seed=0)
        for key, s in snap["runs"].items():
            for count_key in ("total", "admissible", "blocked", "correct", "errors"):
                self.assertIn(count_key, s, f"Missing {count_key} in run {key}")
                self.assertIsInstance(s[count_key], int,
                                      f"Non-integer {count_key} in run {key}")

    def test_total_equals_admissible_plus_blocked_plus_errors(self):
        snap = _build_generated_snapshot(n=20, seed=1)
        for key, s in snap["runs"].items():
            self.assertEqual(
                s["total"], s["admissible"] + s["blocked"] + s["errors"],
                f"total != admissible+blocked+errors in run {key}",
            )


# ---------------------------------------------------------------------------
# Committed baseline match
# ---------------------------------------------------------------------------

class TestGeneratedBaselineMatch(unittest.TestCase):
    """The committed baseline at n=60 seed=0 must match a freshly-built snapshot."""

    def test_generated_baseline_file_exists(self):
        self.assertTrue(
            os.path.exists(_GENERATED_BASELINE_PATH),
            f"Generated baseline not found: {_GENERATED_BASELINE_PATH}",
        )

    def test_generated_baseline_matches_fresh_snapshot(self):
        with open(_GENERATED_BASELINE_PATH, encoding="utf-8") as f:
            baseline = json.load(f)
        n = baseline["n"]
        seed = baseline["seed"]
        current = _build_generated_snapshot(n=n, seed=seed)
        diffs = _generated_snapshot_diff(baseline, current)
        self.assertEqual(
            diffs, [],
            "Generated baseline drift detected:\n" + "\n".join(diffs),
        )

    def test_main_generated_exit_0(self):
        rc = _main(["--generated", "60", "--seed", "0"])
        self.assertEqual(rc, 0)


# ---------------------------------------------------------------------------
# Thesis assertions (receivability primacy)
# ---------------------------------------------------------------------------

class TestThesisAssertions(unittest.TestCase):
    """Core receivability-primacy thesis: a correct answer is still BLOCKED if
    it cannot be sourced (G-1 BLOCK on client-mifid lane).

    With n=60 seed=0:
      - sloppy-mock / client-mifid  : blocked>0  AND correct==total  (right but inadmissible)
      - faithful-mock / client-mifid: blocked==0                       (sourced -> admissible)
    """

    @classmethod
    def setUpClass(cls):
        cls.snap = _build_generated_snapshot(n=60, seed=0)

    def _run(self, candidate: str, lane: str) -> dict:
        key = f"{candidate}/{lane}"
        self.assertIn(key, self.snap["runs"], f"Run key {key!r} not found in snapshot")
        return self.snap["runs"][key]

    def test_sloppy_client_mifid_has_blocked_gt_0(self):
        s = self._run("sloppy-mock", "client-mifid")
        self.assertGreater(
            s["blocked"], 0,
            "sloppy-mock/client-mifid should have at least one BLOCKED record "
            "(receivability primacy thesis)",
        )

    def test_sloppy_client_mifid_correct_equals_total(self):
        """The sloppy mock always reports the gold answer — so correct==total even
        when blocked. This is the proof that 'right but inadmissible' holds."""
        s = self._run("sloppy-mock", "client-mifid")
        self.assertEqual(
            s["correct"], s["total"],
            "sloppy-mock/client-mifid: expected correct==total (all answers are "
            "gold-sourced by construction, even if blocking on sourcing gate)",
        )

    def test_faithful_client_mifid_blocked_equals_0(self):
        s = self._run("faithful-mock", "client-mifid")
        self.assertEqual(
            s["blocked"], 0,
            "faithful-mock/client-mifid should have 0 BLOCKED (sourced evidence "
            "passes G-1 and G-5 on client-mifid lane)",
        )

    def test_faithful_client_mifid_all_admissible(self):
        s = self._run("faithful-mock", "client-mifid")
        self.assertEqual(
            s["admissible"], s["total"],
            "faithful-mock/client-mifid: expected all records ADMISSIBLE",
        )

    def test_faithful_personal_blocked_equals_0(self):
        s = self._run("faithful-mock", "personal-research")
        self.assertEqual(s["blocked"], 0)

    def test_sloppy_personal_blocked_equals_0(self):
        """On personal-research lane G-1 is FLAG (not BLOCK), so sloppy is
        admissible despite unsourced evidence."""
        s = self._run("sloppy-mock", "personal-research")
        self.assertEqual(
            s["blocked"], 0,
            "sloppy-mock/personal-research: G-1 is FLAG on personal lane, "
            "so all records should be ADMISSIBLE",
        )

    def test_total_is_n_for_all_runs(self):
        n = self.snap["n"]
        for key, s in self.snap["runs"].items():
            self.assertEqual(s["total"], n, f"run {key}: total should equal n={n}")

    def test_sloppy_g1_fails_for_subset_of_items(self):
        """The sloppy mock provides no evidence for numeric/table items (only
        qualitative-text items have a trivially-sourced gold path).  Check that
        G-1 FAIL count is positive in the client-mifid gate distribution."""
        dist = self.snap["per_gate_distribution"].get("sloppy-mock/client-mifid", {})
        g1 = dist.get("G-1", {})
        self.assertGreater(
            g1.get("FAIL", 0), 0,
            "Expected G-1 FAILs in sloppy-mock/client-mifid gate distribution",
        )

    def test_faithful_all_gates_pass_client_mifid(self):
        dist = self.snap["per_gate_distribution"].get("faithful-mock/client-mifid", {})
        for gid, counts in dist.items():
            self.assertEqual(
                counts.get("FAIL", 0), 0,
                f"Gate {gid} should have 0 FAILs for faithful-mock/client-mifid",
            )


# ---------------------------------------------------------------------------
# Drift detection for generated snapshots
# ---------------------------------------------------------------------------

class TestGeneratedDriftDetection(unittest.TestCase):
    def _fresh(self):
        return _build_generated_snapshot(n=20, seed=7)

    def test_identical_snapshots_no_diff(self):
        snap = self._fresh()
        diffs = _generated_snapshot_diff(snap, snap)
        self.assertEqual(diffs, [])

    def test_perturbed_run_count_detected(self):
        snap = self._fresh()
        perturbed = copy.deepcopy(snap)
        # Flip a count in one run.
        first_key = sorted(perturbed["runs"].keys())[0]
        perturbed["runs"][first_key]["blocked"] += 99
        diffs = _generated_snapshot_diff(snap, perturbed)
        self.assertGreater(len(diffs), 0)

    def test_truncated_runs_detected(self):
        snap = self._fresh()
        perturbed = copy.deepcopy(snap)
        # Remove one run.
        first_key = sorted(perturbed["runs"].keys())[0]
        del perturbed["runs"][first_key]
        diffs = _generated_snapshot_diff(snap, perturbed)
        self.assertGreater(len(diffs), 0)

    def test_wrong_n_detected(self):
        snap = self._fresh()
        perturbed = copy.deepcopy(snap)
        perturbed["n"] = snap["n"] + 1
        diffs = _generated_snapshot_diff(snap, perturbed)
        self.assertGreater(len(diffs), 0)

    def test_wrong_seed_detected(self):
        snap = self._fresh()
        perturbed = copy.deepcopy(snap)
        perturbed["seed"] = snap["seed"] + 1
        diffs = _generated_snapshot_diff(snap, perturbed)
        self.assertGreater(len(diffs), 0)

    def test_main_exit_1_on_stale_generated_baseline(self):
        """Write a wrong generated baseline and verify exit 1."""
        bad = {"mode": "generated", "n": 999, "seed": 0,
               "runs": {}, "per_gate_distribution": {}}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tf:
            json.dump(bad, tf)
            tmp_path = tf.name
        try:
            import tools.gate_regression as gr_mod
            orig = gr_mod._GENERATED_BASELINE_PATH
            gr_mod._GENERATED_BASELINE_PATH = tmp_path
            try:
                rc = _main(["--generated", "10", "--seed", "0"])
            finally:
                gr_mod._GENERATED_BASELINE_PATH = orig
        finally:
            os.unlink(tmp_path)
        self.assertEqual(rc, 1)

    def test_main_generated_update_then_compare(self):
        """--generated N --seed S --update writes a baseline that compares clean."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tf:
            tmp_path = tf.name

        import tools.gate_regression as gr_mod
        orig = gr_mod._GENERATED_BASELINE_PATH
        gr_mod._GENERATED_BASELINE_PATH = tmp_path
        try:
            rc_update = _main(["--generated", "10", "--seed", "3", "--update"])
            self.assertEqual(rc_update, 0)
            rc_compare = _main(["--generated", "10", "--seed", "3"])
            self.assertEqual(rc_compare, 0)
        finally:
            gr_mod._GENERATED_BASELINE_PATH = orig
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_main_generated_missing_baseline_exits_1(self):
        """If the generated baseline file does not exist, exit 1 with an error."""
        import tools.gate_regression as gr_mod
        orig = gr_mod._GENERATED_BASELINE_PATH
        gr_mod._GENERATED_BASELINE_PATH = "/tmp/__nonexistent_generated_baseline__.json"
        try:
            rc = _main(["--generated", "5", "--seed", "0"])
        finally:
            gr_mod._GENERATED_BASELINE_PATH = orig
        self.assertEqual(rc, 1)

    def test_main_generated_json_exit_0(self):
        """--generated N --seed S --json prints JSON and exits 0."""
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = _main(["--generated", "5", "--seed", "0", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["mode"], "generated")
        self.assertEqual(parsed["n"], 5)


# ---------------------------------------------------------------------------
# Guard: default (fixtures) mode unchanged
# ---------------------------------------------------------------------------

class TestDefaultModeUnchanged(unittest.TestCase):
    """Ensure the --generated flag does NOT affect the fixtures mode."""

    def test_fixtures_baseline_path_unchanged(self):
        """_BASELINE_PATH must still point to the original fixtures baseline."""
        self.assertTrue(
            _BASELINE_PATH.endswith("gate_regression_baseline.json"),
            f"Unexpected _BASELINE_PATH: {_BASELINE_PATH}",
        )
        # Must NOT be the generated baseline path.
        self.assertNotEqual(_BASELINE_PATH, _GENERATED_BASELINE_PATH)

    def test_fixtures_baseline_still_matches(self):
        """The fixtures baseline must still be clean after this refactor."""
        self.assertTrue(
            os.path.exists(_BASELINE_PATH),
            f"Fixtures baseline not found: {_BASELINE_PATH}",
        )
        with open(_BASELINE_PATH, encoding="utf-8") as f:
            baseline = json.load(f)
        current = _build_snapshot(synthetic_only=baseline.get("synthetic_only", False))
        diffs = _snapshot_diff(baseline, current)
        self.assertEqual(
            diffs, [],
            "Fixtures baseline drifted after gate_regression.py refactor:\n"
            + "\n".join(diffs),
        )

    def test_main_fixtures_exit_0(self):
        rc = _main([])
        self.assertEqual(rc, 0)

    def test_main_synthetic_only_exit_0(self):
        rc = _main(["--synthetic-only"])
        self.assertEqual(rc, 0)

    def test_build_snapshot_returns_records(self):
        snap = _build_snapshot()
        self.assertIn("records", snap)
        self.assertGreater(len(snap["records"]), 0)


if __name__ == "__main__":
    unittest.main()
