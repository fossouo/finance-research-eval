"""Tests for the P4 batch runner + report generator (harness.report).

All offline — 0 VRAM, 0 network, synthetic mocks only.

    python3 -m unittest discover -s tests -t .
"""
from __future__ import annotations

import csv
import io
import unittest

from harness.candidates.mock import FaithfulMockCandidate, SloppyMockCandidate
from harness.eval_run import _all_synthetic_items
from harness.report import batch_run, format_csv, format_markdown


def _all_items_by_label():
    """Load synthetic samples keyed by source id."""
    from harness.sources import loaders, registry
    out = {}
    for sid in registry.list_sources():
        src = registry.get(sid)
        if src.loader and src.sample:
            out[sid] = loaders.load_sample(sid)
    return out


class TestBatchRunStructure(unittest.TestCase):
    def setUp(self):
        items = _all_synthetic_items()
        self.report = batch_run(
            [FaithfulMockCandidate(), SloppyMockCandidate()],
            {"all": items},
        )

    def test_report_has_required_keys(self):
        for key in ("candidates", "item_sets", "lanes", "runs", "aggregate"):
            self.assertIn(key, self.report)

    def test_candidates_preserved_in_order(self):
        self.assertEqual(self.report["candidates"], ["faithful-mock", "sloppy-mock"])

    def test_item_sets_preserved(self):
        self.assertEqual(self.report["item_sets"], ["all"])

    def test_both_lanes_by_default(self):
        self.assertIn("personal-research", self.report["lanes"])
        self.assertIn("client-mifid", self.report["lanes"])

    def test_run_count_equals_candidates_times_lanes_times_sets(self):
        # 2 candidates × 2 lanes × 1 set = 4 runs
        self.assertEqual(len(self.report["runs"]), 4)

    def test_each_run_has_required_fields(self):
        for run in self.report["runs"]:
            for field in ("candidate", "lane", "item_set", "summary", "records", "run_id"):
                self.assertIn(field, run, f"run missing field: {field}")

    def test_run_id_is_hex_string(self):
        for run in self.report["runs"]:
            rid = run["run_id"]
            self.assertIsInstance(rid, str)
            # Must be parseable as hex
            int(rid, 16)

    def test_run_id_is_deterministic(self):
        items = _all_synthetic_items()
        r1 = batch_run([FaithfulMockCandidate()], {"all": items})
        r2 = batch_run([FaithfulMockCandidate()], {"all": items})
        self.assertEqual(
            [run["run_id"] for run in r1["runs"]],
            [run["run_id"] for run in r2["runs"]],
        )

    def test_summary_fields_consistent(self):
        for run in self.report["runs"]:
            s = run["summary"]
            self.assertEqual(
                s["total"], s["admissible"] + s["blocked"] + s["errors"],
                f"run {run['run_id']}: total != admissible+blocked+errors",
            )


class TestBatchRunAggregate(unittest.TestCase):
    def setUp(self):
        items = _all_synthetic_items()
        self.report = batch_run(
            [FaithfulMockCandidate(), SloppyMockCandidate()],
            {"all": items},
        )
        self.agg = self.report["aggregate"]

    def test_grand_total_matches_sum_of_run_totals(self):
        expected = sum(r["summary"]["total"] for r in self.report["runs"])
        self.assertEqual(self.agg["grand_total"], expected)

    def test_grand_admissible_and_blocked_sum_to_non_error_total(self):
        agg = self.agg
        self.assertEqual(
            agg["grand_admissible"] + agg["grand_blocked"] + agg["grand_errors"],
            agg["grand_total"],
        )

    def test_admissibility_rate_between_0_and_1(self):
        r = self.agg["admissibility_rate"]
        self.assertGreaterEqual(r, 0.0)
        self.assertLessEqual(r, 1.0)

    def test_accuracy_rate_between_0_and_1(self):
        # accuracy_rate = grand_correct / grand_total (all records, not just admissible)
        # so it is always in [0, 1]
        r = self.agg["accuracy_rate"]
        self.assertGreaterEqual(r, 0.0)
        self.assertLessEqual(r, 1.0)
        # cross-check the definition
        total = self.agg["grand_total"]
        correct = self.agg["grand_correct"]
        expected = round(correct / total, 4) if total else 0.0
        self.assertAlmostEqual(r, expected, places=4)

    def test_gate_stats_cover_all_six_gates(self):
        gs = self.agg["gate_stats"]
        for gid in ("G-1", "G-2", "G-3", "G-4", "G-5", "G-6"):
            self.assertIn(gid, gs, f"gate {gid} missing from gate_stats")

    def test_gate_stat_counts_are_non_negative(self):
        for gid, gs in self.agg["gate_stats"].items():
            for k in ("pass", "fail", "na"):
                self.assertGreaterEqual(gs.get(k, 0), 0)

    def test_gate_stat_totals_match_all_evaluated_records(self):
        """Each gate's (pass+fail+na) must equal the number of records that
        included that gate — which equals grand_total (all records include all gates)."""
        gt = self.agg["grand_total"]
        for gid, gs in self.agg["gate_stats"].items():
            total_g = gs.get("pass", 0) + gs.get("fail", 0) + gs.get("na", 0)
            self.assertEqual(total_g, gt, f"{gid}: gate totals {total_g} != {gt}")

    def test_faithful_candidate_all_admissible(self):
        faithful_runs = [
            r for r in self.report["runs"] if r["candidate"] == "faithful-mock"
        ]
        for run in faithful_runs:
            self.assertEqual(run["summary"]["blocked"], 0,
                             f"faithful-mock should never block (lane={run['lane']})")

    def test_sloppy_candidate_all_blocked_on_client_for_numeric(self):
        from harness.sources import loaders, registry
        numeric_sources = []
        for sid in registry.list_sources():
            src = registry.get(sid)
            if src.loader and src.sample:
                for it in loaders.load_sample(sid):
                    if it.gold_kind == "numeric":
                        numeric_sources.append(sid)
                        break
        if not numeric_sources:
            self.skipTest("no numeric items found in synthetic samples")
        numeric_items = [
            it for sid in numeric_sources
            for it in loaders.load_sample(sid)
            if it.gold_kind == "numeric"
        ]
        rep = batch_run(
            [SloppyMockCandidate()],
            {"numeric": numeric_items},
            lanes=("client-mifid",),
        )
        for run in rep["runs"]:
            self.assertEqual(
                run["summary"]["blocked"], run["summary"]["total"],
                "sloppy mock must be blocked on client lane for numeric items",
            )

    def test_total_runs_count(self):
        self.assertEqual(self.agg["total_runs"], len(self.report["runs"]))


class TestMarkdownFormat(unittest.TestCase):
    def setUp(self):
        items = _all_synthetic_items()
        self.report = batch_run(
            [FaithfulMockCandidate(), SloppyMockCandidate()],
            {"all": items},
        )
        self.md = format_markdown(self.report)

    def test_returns_non_empty_string(self):
        self.assertIsInstance(self.md, str)
        self.assertGreater(len(self.md), 100)

    def test_contains_key_headings(self):
        for heading in (
            "# finance-research-eval",
            "## Overview",
            "## Aggregate results",
            "## Per-run breakdown",
            "## Gate statistics",
            "## Key findings",
        ):
            self.assertIn(heading, self.md, f"missing heading: {heading!r}")

    def test_contains_candidate_names(self):
        self.assertIn("faithful-mock", self.md)
        self.assertIn("sloppy-mock", self.md)

    def test_gate_ids_appear_in_gate_table(self):
        for gid in ("G-1", "G-2", "G-3", "G-4", "G-5", "G-6"):
            self.assertIn(gid, self.md)

    def test_no_real_data_disclaimer_present(self):
        self.assertIn("Synthetic data only", self.md)

    def test_contains_admissibility_finding(self):
        # The faithful mock is always 100 % admissible, so the finding must appear.
        # The exact rate depends on the mix; check that *some* finding is rendered.
        self.assertTrue(
            "admissible" in self.md.lower() or "ADMISSIBLE" in self.md,
        )

    def test_markdown_has_no_tabs(self):
        # Markdown tables must use spaces, not tabs.
        self.assertNotIn("\t", self.md)

    def test_run_ids_appear_in_per_run_table(self):
        for run in self.report["runs"]:
            self.assertIn(run["run_id"], self.md)


class TestCSVFormat(unittest.TestCase):
    def setUp(self):
        items = _all_synthetic_items()
        self.report = batch_run(
            [FaithfulMockCandidate(), SloppyMockCandidate()],
            {"all": items},
        )
        self.csv_text = format_csv(self.report)

    def test_returns_non_empty_string(self):
        self.assertIsInstance(self.csv_text, str)
        self.assertGreater(len(self.csv_text), 0)

    def test_header_row_is_correct(self):
        reader = csv.reader(io.StringIO(self.csv_text))
        header = next(reader)
        expected_start = [
            "run_id", "candidate", "lane", "item_set",
            "item", "verdict", "correct", "answer", "gold",
        ]
        self.assertEqual(header[: len(expected_start)], expected_start)

    def test_header_includes_all_gates(self):
        reader = csv.reader(io.StringIO(self.csv_text))
        header = next(reader)
        for gid in ("G-1", "G-2", "G-3", "G-4", "G-5", "G-6"):
            self.assertIn(gid, header)

    def test_row_count_matches_grand_total(self):
        # rows = header + one row per evaluated record
        lines = [r for r in self.csv_text.splitlines() if r]
        expected_rows = self.report["aggregate"]["grand_total"]
        self.assertEqual(len(lines) - 1, expected_rows)

    def test_all_rows_same_column_count(self):
        reader = csv.reader(io.StringIO(self.csv_text))
        rows = list(reader)
        n_cols = len(rows[0])
        for i, row in enumerate(rows[1:], start=2):
            self.assertEqual(
                len(row), n_cols,
                f"row {i} has {len(row)} columns, expected {n_cols}",
            )

    def test_verdict_values_are_valid(self):
        reader = csv.reader(io.StringIO(self.csv_text))
        header = next(reader)
        verdict_col = header.index("verdict")
        valid = {"ADMISSIBLE", "BLOCKED", "ERROR"}
        for row in reader:
            self.assertIn(row[verdict_col], valid,
                          f"unexpected verdict value: {row[verdict_col]!r}")

    def test_correct_column_is_0_or_1(self):
        reader = csv.reader(io.StringIO(self.csv_text))
        header = next(reader)
        correct_col = header.index("correct")
        for row in reader:
            if row[header.index("verdict")] != "ERROR":
                self.assertIn(row[correct_col], ("0", "1"),
                              f"correct column has unexpected value: {row[correct_col]!r}")

    def test_run_ids_match_batch_report(self):
        expected = {run["run_id"] for run in self.report["runs"]}
        reader = csv.reader(io.StringIO(self.csv_text))
        header = next(reader)
        rid_col = header.index("run_id")
        actual = {row[rid_col] for row in reader}
        self.assertEqual(actual, expected)


class TestBatchRunCustomLanes(unittest.TestCase):
    def test_single_lane_only(self):
        items = _all_synthetic_items()
        rep = batch_run(
            [FaithfulMockCandidate()],
            {"all": items},
            lanes=("personal-research",),
        )
        # 1 candidate × 1 lane × 1 set = 1 run
        self.assertEqual(len(rep["runs"]), 1)
        self.assertEqual(rep["runs"][0]["lane"], "personal-research")

    def test_multiple_item_sets(self):
        items = _all_synthetic_items()
        rep = batch_run(
            [FaithfulMockCandidate()],
            {"set-a": items, "set-b": items},
            lanes=("personal-research",),
        )
        # 1 candidate × 1 lane × 2 sets = 2 runs
        self.assertEqual(len(rep["runs"]), 2)
        labels = {r["item_set"] for r in rep["runs"]}
        self.assertEqual(labels, {"set-a", "set-b"})

    def test_empty_items_set_produces_zero_totals(self):
        rep = batch_run(
            [FaithfulMockCandidate()],
            {"empty": []},
            lanes=("personal-research",),
        )
        self.assertEqual(rep["aggregate"]["grand_total"], 0)
        self.assertEqual(rep["aggregate"]["admissibility_rate"], 0.0)

    def test_format_markdown_on_empty_run(self):
        rep = batch_run(
            [FaithfulMockCandidate()],
            {"empty": []},
            lanes=("personal-research",),
        )
        md = format_markdown(rep)
        self.assertIn("## Overview", md)

    def test_format_csv_on_empty_run(self):
        rep = batch_run(
            [FaithfulMockCandidate()],
            {"empty": []},
            lanes=("personal-research",),
        )
        csv_text = format_csv(rep)
        rows = [r for r in csv_text.splitlines() if r]
        # Only the header row, no data rows
        self.assertEqual(len(rows), 1)


class TestMultiLabelBatchReport(unittest.TestCase):
    """Ensure the multi-set path aggregates correctly."""

    def test_multi_set_grand_total_is_sum_of_sets(self):
        items = _all_synthetic_items()
        rep_multi = batch_run(
            [FaithfulMockCandidate()],
            {"a": items, "b": items},
            lanes=("personal-research",),
        )
        rep_single = batch_run(
            [FaithfulMockCandidate()],
            {"all": items},
            lanes=("personal-research",),
        )
        # multi has 2 sets, single has 1 — totals should be 2× and 1× respectively
        self.assertEqual(
            rep_multi["aggregate"]["grand_total"],
            2 * rep_single["aggregate"]["grand_total"],
        )


if __name__ == "__main__":
    unittest.main()
