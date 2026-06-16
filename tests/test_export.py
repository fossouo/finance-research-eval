"""Tests for harness.export (RR exporter) and harness.fixtures.cases_worked.

All offline — 0 VRAM, 0 network, synthetic mocks only.

    python3 -m unittest discover -s tests -t .
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from harness.export import (
    _safe_filename,
    build_index,
    export_bundle,
    export_jsonl,
    format_thesis_card,
    load_jsonl,
)
from harness.fixtures.cases_worked import build_worked_case, run_worked_case
from harness.gates.gates import evaluate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _evaluated_cases():
    """Evaluate the standard conformity catalogue and return augmented RRs."""
    from harness.fixtures.cases import all_cases
    rrs = []
    for c in all_cases():
        ev = evaluate(c["rr"])
        aug = ev.augmented_rr
        aug["_gate_status_map"] = ev.status_map()
        rrs.append(aug)
    return rrs


# ---------------------------------------------------------------------------
# tests: cases_worked — the FICTEX SA fixture
# ---------------------------------------------------------------------------

class TestWorkedCaseBuildRR(unittest.TestCase):
    def setUp(self):
        self.personal, self.client = build_worked_case()

    def test_personal_rr_has_required_fields(self):
        for f in ("id", "lane", "subject", "information_cutoff", "claims", "audit_trail"):
            self.assertIn(f, self.personal, f"personal RR missing: {f}")

    def test_client_rr_has_required_fields(self):
        for f in ("id", "lane", "subject", "information_cutoff", "claims", "audit_trail", "lane_fields"):
            self.assertIn(f, self.client, f"client RR missing: {f}")

    def test_lanes_are_correct(self):
        self.assertEqual(self.personal["lane"], "personal-research")
        self.assertEqual(self.client["lane"], "client-mifid")

    def test_audit_trail_stamped(self):
        for rr in (self.personal, self.client):
            at = rr.get("audit_trail") or {}
            self.assertIn("input_hash", at, "audit_trail.input_hash missing")
            self.assertIsInstance(at["input_hash"], str)
            self.assertGreater(len(at["input_hash"]), 0)

    def test_input_hash_reproducible(self):
        """Building the same RR twice must produce the same hash (deterministic)."""
        from harness.rr import compute_input_hash
        p1, _ = build_worked_case()
        p2, _ = build_worked_case()
        self.assertEqual(
            compute_input_hash(p1), compute_input_hash(p2),
            "input_hash is not deterministic between identical builds",
        )

    def test_claims_include_all_three_kinds(self):
        for rr in (self.personal, self.client):
            kinds = {c.get("kind") for c in rr.get("claims", [])}
            for expected in ("qualitative", "quantitative", "valuation"):
                self.assertIn(expected, kinds, f"claim kind {expected!r} missing")

    def test_all_evidence_has_source_and_locator(self):
        for rr in (self.personal, self.client):
            for claim in rr.get("claims", []):
                for ev in claim.get("evidence", []):
                    self.assertTrue(ev.get("source_doc"), f"ev {ev.get('id')} missing source_doc")
                    self.assertTrue(ev.get("locator"), f"ev {ev.get('id')} missing locator")
                    self.assertTrue(ev.get("as_of"), f"ev {ev.get('id')} missing as_of")

    def test_client_lane_fields_complete(self):
        lf = self.client.get("lane_fields") or {}
        for f in ("reco_nature", "disclaimers", "conflicts_of_interest"):
            self.assertIn(f, lf, f"lane_fields missing: {f}")

    def test_no_real_tickers_or_isins(self):
        """Guard rail: the worked case must not contain real ISINs or broker names."""
        full = json.dumps([self.personal, self.client])
        # Real ISIN prefixes (FR, US, DE, GB, NL, ...) should not appear in
        # ISIN-shaped strings (12 uppercase alphanumeric, starts with 2-letter country).
        import re
        # Our synthetic ISIN starts with "XX" which is not a real country code.
        # Check that no real-prefix ISIN shape appears.
        real_isin_pattern = re.compile(
            r'\b(?:FR|US|DE|GB|NL|CH|LU|BE|IT|ES|IE|SE|DK|NO|FI|AT|PT|GR)'
            r'[A-Z0-9]{10}\b'
        )
        self.assertFalse(
            real_isin_pattern.search(full),
            "found a real-country-prefix ISIN in the worked case fixture",
        )


class TestWorkedCaseEvaluation(unittest.TestCase):
    def setUp(self):
        self.results = run_worked_case()

    def test_returns_two_results(self):
        self.assertEqual(len(self.results), 2)

    def test_labels_are_personal_and_client(self):
        labels = {label for label, _, _ in self.results}
        self.assertEqual(labels, {"personal", "client"})

    def test_both_verdicts_are_admissible(self):
        """The FICTEX SA worked case is designed to be fully ADMISSIBLE."""
        for label, ev, _ in self.results:
            self.assertEqual(
                ev.verdict, "ADMISSIBLE",
                f"worked case [{label}] should be ADMISSIBLE, got {ev.verdict}",
            )

    def test_all_gates_pass_on_personal(self):
        personal_ev = next(ev for lbl, ev, _ in self.results if lbl == "personal")
        status = personal_ev.status_map()
        for gid, st in status.items():
            if gid == "G-5":
                self.assertEqual(st, "NA", "G-5 must be NA on personal-research")
            else:
                self.assertEqual(st, "PASS", f"{gid} failed on personal lane")

    def test_all_gates_pass_on_client(self):
        client_ev = next(ev for lbl, ev, _ in self.results if lbl == "client")
        status = client_ev.status_map()
        for gid, st in status.items():
            self.assertEqual(st, "PASS", f"{gid} not PASS on client lane: {st}")

    def test_g3_computations_agree(self):
        """Every computation in the worked case must have agree=True after G-3."""
        for label, ev, aug in self.results:
            for claim in aug.get("claims", []):
                for comp in claim.get("computations", []):
                    self.assertTrue(
                        comp.get("agree") is True,
                        f"[{label}] computation {comp.get('metric')!r} "
                        f"has agree={comp.get('agree')!r} "
                        f"(llm={comp.get('llm_value')}, "
                        f"recomputed={comp.get('recomputed_value')})",
                    )

    def test_gate_status_map_attached(self):
        for label, _, aug in self.results:
            gate_map = aug.get("_gate_status_map") or {}
            self.assertEqual(len(gate_map), 6, f"[{label}] expected 6 gates in status map")

    def test_g2_passes_meaning_hash_is_reproducible(self):
        """G-2 PASS is the definitive reproducibility signal.

        Note: the augmented RR returned by evaluate() carries harness-only
        keys (_gate_status_map, recomputed_value, agree, gate_results, verdict)
        that are NOT part of the candidate-declared hash.  ``compute_input_hash``
        strips ``_HARNESS_FIELDS`` and ``_HARNESS_COMPUTATION_FIELDS`` but not
        ``_gate_status_map`` (a non-standard key we attach *after* evaluate()).
        Therefore the correct reproducibility assertion is that gate G-2 itself
        passed — which means the harness reproduced the declared hash successfully
        from the canonical candidate content.
        """
        for label, ev, aug in self.results:
            g2 = ev.by_id("G-2")
            self.assertEqual(g2.status, "PASS",
                             f"[{label}] G-2 failed — hash not reproducible: {g2.reason}")


class TestWorkedCaseMetricValues(unittest.TestCase):
    """Spot-check each metric's recomputed value against the known analytical answer."""

    def setUp(self):
        self.results = run_worked_case()

    def _comps_for(self, label):
        _, _, aug = next(r for r in self.results if r[0] == label)
        out = {}
        for claim in aug.get("claims", []):
            for comp in claim.get("computations", []):
                out[comp["metric"]] = comp
        return out

    def test_gross_margin_is_040(self):
        comps = self._comps_for("personal")
        rv = comps["gross_margin"]["recomputed_value"]
        self.assertAlmostEqual(rv, 0.40, places=6)

    def test_ebitda_margin_is_025(self):
        comps = self._comps_for("personal")
        rv = comps["ebitda_margin"]["recomputed_value"]
        self.assertAlmostEqual(rv, 0.25, places=6)

    def test_ev_ebitda_is_80(self):
        comps = self._comps_for("personal")
        rv = comps["ev_ebitda"]["recomputed_value"]
        self.assertAlmostEqual(rv, 8.0, places=6)

    def test_net_debt_to_ebitda_is_20(self):
        comps = self._comps_for("personal")
        rv = comps["net_debt_to_ebitda"]["recomputed_value"]
        self.assertAlmostEqual(rv, 2.0, places=6)

    def test_fcf_yield_approx(self):
        comps = self._comps_for("personal")
        rv = comps["fcf_yield"]["recomputed_value"]
        # 90 / 2160 = 0.041666...
        self.assertAlmostEqual(rv, 90.0 / 2160.0, places=6)

    def test_revenue_growth_is_020(self):
        comps = self._comps_for("personal")
        rv = comps["revenue_growth"]["recomputed_value"]
        self.assertAlmostEqual(rv, 0.20, places=6)

    def test_comparable_ev_is_3240(self):
        comps = self._comps_for("personal")
        rv = comps["comparable_ev"]["recomputed_value"]
        self.assertAlmostEqual(rv, 3240.0, places=2)


# ---------------------------------------------------------------------------
# tests: export_jsonl + load_jsonl
# ---------------------------------------------------------------------------

class TestExportJsonl(unittest.TestCase):
    def setUp(self):
        self.rrs = _evaluated_cases()

    def test_write_and_reload_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test.jsonl")
            n = export_jsonl(self.rrs, path)
            self.assertEqual(n, len(self.rrs))
            reloaded = load_jsonl(path)
            self.assertEqual(len(reloaded), len(self.rrs))

    def test_each_line_is_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test.jsonl")
            export_jsonl(self.rrs, path)
            with open(path, encoding="utf-8") as fh:
                for i, line in enumerate(fh):
                    line = line.strip()
                    if line:
                        obj = json.loads(line)  # must not raise
                        self.assertIsInstance(obj, dict, f"line {i} is not a dict")

    def test_ids_survive_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test.jsonl")
            export_jsonl(self.rrs, path)
            reloaded = load_jsonl(path)
            original_ids = [r.get("id") for r in self.rrs]
            reloaded_ids = [r.get("id") for r in reloaded]
            self.assertEqual(original_ids, reloaded_ids)

    def test_empty_list_produces_empty_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "empty.jsonl")
            n = export_jsonl([], path)
            self.assertEqual(n, 0)
            reloaded = load_jsonl(path)
            self.assertEqual(reloaded, [])

    def test_jsonl_is_deterministic(self):
        """Writing the same rrs twice must produce byte-identical output."""
        with tempfile.TemporaryDirectory() as tmp:
            p1 = os.path.join(tmp, "a.jsonl")
            p2 = os.path.join(tmp, "b.jsonl")
            export_jsonl(self.rrs, p1)
            export_jsonl(self.rrs, p2)
            with open(p1, encoding="utf-8") as f1, open(p2, encoding="utf-8") as f2:
                self.assertEqual(f1.read(), f2.read())


# ---------------------------------------------------------------------------
# tests: build_index
# ---------------------------------------------------------------------------

class TestBuildIndex(unittest.TestCase):
    def setUp(self):
        self.rrs = _evaluated_cases()
        self.index = build_index(self.rrs)

    def test_index_has_required_keys(self):
        for k in ("count", "admissible", "blocked", "entries"):
            self.assertIn(k, self.index)

    def test_count_matches_input(self):
        self.assertEqual(self.index["count"], len(self.rrs))

    def test_admissible_plus_blocked_leq_count(self):
        # admissible + blocked may be < count if some have UNKNOWN verdict
        self.assertLessEqual(
            self.index["admissible"] + self.index["blocked"],
            self.index["count"],
        )

    def test_each_entry_has_id_subject_lane_verdict(self):
        for entry in self.index["entries"]:
            for field in ("id", "subject", "lane", "verdict", "information_cutoff", "input_hash"):
                self.assertIn(field, entry, f"index entry missing field: {field}")

    def test_entry_ids_match_rr_ids(self):
        original_ids = [r.get("id") for r in self.rrs]
        index_ids = [e["id"] for e in self.index["entries"]]
        self.assertEqual(original_ids, index_ids)

    def test_admissible_count_correct(self):
        expected = sum(1 for r in self.rrs if r.get("verdict") == "ADMISSIBLE")
        self.assertEqual(self.index["admissible"], expected)

    def test_blocked_count_correct(self):
        expected = sum(1 for r in self.rrs if r.get("verdict") == "BLOCKED")
        self.assertEqual(self.index["blocked"], expected)

    def test_gate_map_in_entry_when_attached(self):
        """Entries should carry the gate map when _gate_status_map was attached."""
        for entry, rr in zip(self.index["entries"], self.rrs):
            if rr.get("_gate_status_map"):
                self.assertIsInstance(entry["gates"], dict)
            else:
                self.assertIsInstance(entry["gates"], dict)  # may be empty {}

    def test_empty_list_produces_empty_index(self):
        idx = build_index([])
        self.assertEqual(idx["count"], 0)
        self.assertEqual(idx["admissible"], 0)
        self.assertEqual(idx["blocked"], 0)
        self.assertEqual(idx["entries"], [])


# ---------------------------------------------------------------------------
# tests: format_thesis_card
# ---------------------------------------------------------------------------

class TestFormatThesisCard(unittest.TestCase):
    def setUp(self):
        self.results = run_worked_case()
        _, _, self.aug_personal = next(r for r in self.results if r[0] == "personal")
        _, _, self.aug_client = next(r for r in self.results if r[0] == "client")

    def test_returns_non_empty_string(self):
        card = format_thesis_card(self.aug_personal)
        self.assertIsInstance(card, str)
        self.assertGreater(len(card), 200)

    def test_subject_appears_in_card(self):
        card = format_thesis_card(self.aug_personal)
        self.assertIn("FICTEX SA", card)

    def test_verdict_appears_in_card(self):
        card = format_thesis_card(self.aug_personal)
        self.assertIn("ADMISSIBLE", card)

    def test_lane_appears_in_card(self):
        card = format_thesis_card(self.aug_personal)
        self.assertIn("personal-research", card)

    def test_rr_id_appears_in_card(self):
        card = format_thesis_card(self.aug_personal)
        self.assertIn(self.aug_personal["id"], card)

    def test_input_hash_abbreviated_in_header(self):
        card = format_thesis_card(self.aug_personal)
        full_hash = (self.aug_personal.get("audit_trail") or {}).get("input_hash", "")
        # The card abbreviates to first 16 chars + "…"
        self.assertIn(full_hash[:16], card)

    def test_gate_table_present_when_gate_map_attached(self):
        card = format_thesis_card(self.aug_personal)
        self.assertIn("## Gate summary", card)
        for gid in ("G-1", "G-2", "G-3", "G-4", "G-5", "G-6"):
            self.assertIn(gid, card)

    def test_claims_section_present(self):
        card = format_thesis_card(self.aug_personal)
        self.assertIn("## Claims", card)
        self.assertIn("### Claim", card)

    def test_evidence_table_present(self):
        card = format_thesis_card(self.aug_personal)
        self.assertIn("**Evidence**", card)
        # At least one evidence id should appear
        self.assertIn("ev-fctx-rev", card)

    def test_computations_table_present(self):
        card = format_thesis_card(self.aug_personal)
        self.assertIn("**Computations", card)
        self.assertIn("gross_margin", card)
        self.assertIn("ev_ebitda", card)

    def test_no_fabricated_real_isins_in_card(self):
        import re
        card = format_thesis_card(self.aug_personal) + format_thesis_card(self.aug_client)
        real_isin_pattern = re.compile(
            r'\b(?:FR|US|DE|GB|NL|CH|LU|BE|IT|ES|IE|SE|DK|NO|FI|AT|PT|GR)'
            r'[A-Z0-9]{10}\b'
        )
        self.assertFalse(real_isin_pattern.search(card))

    def test_not_investment_advice_disclaimer_present(self):
        card = format_thesis_card(self.aug_personal)
        self.assertIn("Not investment advice", card)

    def test_provenance_section_present(self):
        card = format_thesis_card(self.aug_personal)
        self.assertIn("## Provenance", card)
        self.assertIn("input hash", card.lower())

    def test_card_without_gate_map_still_renders(self):
        """Cards must render gracefully when _gate_status_map is absent."""
        import copy
        aug = copy.deepcopy(self.aug_personal)
        aug.pop("_gate_status_map", None)
        card = format_thesis_card(aug)
        self.assertIsInstance(card, str)
        self.assertGreater(len(card), 50)

    def test_blocked_verdict_shown_in_client_without_lane_fields(self):
        """A blocked RR should show BLOCKED in its card."""
        from harness.fixtures.cases import all_cases
        blocked = next(c for c in all_cases() if c["expected_verdict"] == "BLOCKED")
        ev = evaluate(blocked["rr"])
        aug = ev.augmented_rr
        aug["_gate_status_map"] = ev.status_map()
        card = format_thesis_card(aug)
        self.assertIn("BLOCKED", card)


# ---------------------------------------------------------------------------
# tests: export_bundle
# ---------------------------------------------------------------------------

class TestExportBundle(unittest.TestCase):
    def setUp(self):
        self.results = run_worked_case()
        self.rrs = [aug for _, _, aug in self.results]

    def test_bundle_creates_index_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = export_bundle(self.rrs, tmp)
            self.assertTrue(os.path.exists(result["index_path"]))

    def test_index_json_is_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = export_bundle(self.rrs, tmp)
            with open(result["index_path"], encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertIn("count", data)
            self.assertEqual(data["count"], len(self.rrs))

    def test_bundle_creates_per_rr_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = export_bundle(self.rrs, tmp)
            for rec in result["records"]:
                self.assertTrue(
                    os.path.exists(rec["jsonl"]),
                    f"missing JSONL for rr={rec['id']}",
                )

    def test_bundle_creates_per_rr_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = export_bundle(self.rrs, tmp, include_cards=True)
            for rec in result["records"]:
                self.assertIsNotNone(rec["card"])
                self.assertTrue(
                    os.path.exists(rec["card"]),
                    f"missing card for rr={rec['id']}",
                )

    def test_bundle_no_cards_when_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = export_bundle(self.rrs, tmp, include_cards=False)
            for rec in result["records"]:
                self.assertIsNone(rec["card"])

    def test_each_rr_jsonl_contains_exactly_one_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = export_bundle(self.rrs, tmp)
            for rec in result["records"]:
                reloaded = load_jsonl(rec["jsonl"])
                self.assertEqual(
                    len(reloaded), 1,
                    f"per-rr JSONL for {rec['id']} should have exactly 1 line",
                )
                self.assertEqual(reloaded[0].get("id"), rec["id"])

    def test_bundle_summary_record_count_matches_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = export_bundle(self.rrs, tmp)
            self.assertEqual(len(result["records"]), len(self.rrs))

    def test_bundle_is_idempotent(self):
        """Running export_bundle twice to the same dir must not corrupt anything."""
        with tempfile.TemporaryDirectory() as tmp:
            export_bundle(self.rrs, tmp)
            export_bundle(self.rrs, tmp)  # second write: should overwrite cleanly
            with open(os.path.join(tmp, "index.json"), encoding="utf-8") as fh:
                reloaded_index = json.load(fh)
            self.assertEqual(reloaded_index["count"], len(self.rrs))

    def test_all_conformity_cases_exportable(self):
        """The full conformity catalogue (10 cases) must export without error."""
        rrs = _evaluated_cases()
        with tempfile.TemporaryDirectory() as tmp:
            result = export_bundle(rrs, tmp)
            self.assertEqual(len(result["records"]), len(rrs))


# ---------------------------------------------------------------------------
# tests: _safe_filename
# ---------------------------------------------------------------------------

class TestSafeFilename(unittest.TestCase):
    def test_plain_id_unchanged(self):
        self.assertEqual(_safe_filename("rr-001"), "rr-001")

    def test_colons_replaced(self):
        fn = _safe_filename("rr:foo:bar")
        self.assertNotIn(":", fn)

    def test_spaces_replaced(self):
        fn = _safe_filename("rr foo bar")
        self.assertNotIn(" ", fn)

    def test_slashes_replaced(self):
        fn = _safe_filename("rr/sub/path")
        self.assertNotIn("/", fn)
        self.assertNotIn("\\", fn)

    def test_long_id_truncated(self):
        long_id = "a" * 300
        fn = _safe_filename(long_id)
        self.assertLessEqual(len(fn), 130, "filename should be truncated")

    def test_empty_id_returns_fallback(self):
        fn = _safe_filename("")
        self.assertEqual(fn, "rr-unnamed")

    def test_result_is_filesystem_safe(self):
        """Result should contain only alnum, dash, underscore, dot."""
        import re
        test_ids = [
            "rr-001-admissible",
            "rr/complex:id/with:colons",
            "rr foo bar baz",
            "CAPS_and_123",
        ]
        for rid in test_ids:
            fn = _safe_filename(rid)
            self.assertRegex(fn, r'^[A-Za-z0-9\-_.]+$',
                             f"filename {fn!r} contains unsafe chars (from {rid!r})")


if __name__ == "__main__":
    unittest.main()
