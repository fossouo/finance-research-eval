"""Tests for the public connector seam (E1).

Enforce the E1 invariants:
  - the mock satisfies the Protocols (structural conformance),
  - facts carry a point-in-time anchor (as_of),
  - first_reported keeps the as-first-reported value (the GE restatement lesson),
  - visible_at excludes facts filed after the decision date (anti-look-ahead),
  - membership is dated and anti-survivorship (the SIVB delisting lesson),
  - a connector's sourced facts flow through to the gates (ADMISSIBLE), while an
    unsourced answer is BLOCKED on the client lane,
  - the connectors package imports NO network library (real ones are private).
"""
import os
import unittest

from harness.candidates.base import assemble_rr
from harness.connectors import base as cbase
from harness.connectors.base import (
    Connector,
    ConstituentsSource,
    facts_to_evalitem,
    first_reported,
    visible_at,
)
from harness.connectors.mock import MockConnector, MockConstituentsSource
from harness.fixtures.synthetic import client_lane_fields
from harness.gates import gates

CONN_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "harness", "connectors")
FORBIDDEN_IMPORTS = ("urllib", "requests", "http.client", "socket", "httpx", "aiohttp")


class TestProtocolConformance(unittest.TestCase):
    def test_mock_connector_is_a_connector(self):
        self.assertIsInstance(MockConnector(), Connector)

    def test_mock_constituents_is_a_constituents_source(self):
        self.assertIsInstance(MockConstituentsSource(), ConstituentsSource)


class TestPointInTime(unittest.TestCase):
    def setUp(self):
        self.conn = MockConnector()

    def test_every_fact_has_as_of_anchor(self):
        facts = self.conn.fundamentals("ACME")
        self.assertTrue(facts)
        for f in facts:
            self.assertTrue(f.as_of, f"{f.concept} lacks an as_of filing date")

    def test_first_reported_keeps_earliest_filing(self):
        # ACME FY2021 Revenues: filed 1000 (2022), restated to 900 (2023).
        fr = {(f.concept, f.period_end): f for f in first_reported(self.conn.fundamentals("ACME"))}
        rev2021 = fr[("Revenues", "2021-12-31")]
        self.assertEqual(rev2021.value, 1000.0, "must keep as-first-reported, not the restatement")
        self.assertEqual(rev2021.as_of, "2022-02-15")

    def test_first_reported_is_idempotent_collapse(self):
        # 2 filings of (Revenues, 2021-12-31) collapse to exactly one fact.
        keys = [(f.concept, f.period_end) for f in first_reported(self.conn.fundamentals("ACME"))]
        self.assertEqual(len(keys), len(set(keys)))

    def test_visible_at_excludes_future_filings(self):
        # At 2022-06-01 only the 2022-02-15 filing is knowable; everything filed
        # in 2023 (incl. the restatement) is in the future -> excluded.
        visible = visible_at(self.conn.fundamentals("ACME"), "2022-06-01")
        self.assertTrue(visible)
        self.assertTrue(all(f.as_of <= "2022-06-01" for f in visible))
        self.assertTrue(all(f.as_of == "2022-02-15" for f in visible))


class TestMembership(unittest.TestCase):
    def setUp(self):
        self.src = MockConstituentsSource()

    def test_membership_is_dated_and_anti_survivorship(self):
        early = self.src.members_at("2023-01-01")
        late = self.src.members_at("2023-06-01")
        self.assertIn("FAILBANK", early, "delisted name must appear at its in-index date")
        self.assertNotIn("FAILBANK", late, "delisted name must drop out after delisting")
        self.assertIn("ACME", early)
        self.assertIn("ACME", late)

    def test_filings_exist_for_delisted_name_before_delisting(self):
        conn = MockConnector()
        docs = conn.filings("FAILBANK", until="2023-03-10")
        self.assertTrue(docs, "a delisted name still filed up to the end")


class TestSeamReachesGates(unittest.TestCase):
    def _rr_from_connector(self, lane, sourced, lane_fields=None):
        facts = first_reported(MockConnector().fundamentals("ACME"))
        item = facts_to_evalitem("ACME", facts, "What is ACME FY2022 Revenues?",
                                 gold_answer="1200", gold_kind="numeric")
        evidence = [f.to_evidence() for f in facts] if sourced else []
        return assemble_rr(item, lane, answer="1200", evidence=evidence, lane_fields=lane_fields)

    def test_sourced_connector_rr_is_admissible(self):
        rr = self._rr_from_connector("personal-research", sourced=True)
        ev = gates.evaluate(rr)
        self.assertEqual(ev.verdict, "ADMISSIBLE")

    def test_unsourced_answer_blocked_on_client_lane(self):
        # Right number, no evidence -> G-1 fails -> client lane BLOCKS.
        rr = self._rr_from_connector("client-mifid", sourced=False,
                                     lane_fields=client_lane_fields())
        ev = gates.evaluate(rr)
        self.assertEqual(ev.verdict, "BLOCKED")


class TestNoNetwork(unittest.TestCase):
    def test_connectors_package_imports_no_network_library(self):
        for fname in os.listdir(CONN_DIR):
            if not fname.endswith(".py"):
                continue
            with open(os.path.join(CONN_DIR, fname), encoding="utf-8") as f:
                text = f.read()
            for bad in FORBIDDEN_IMPORTS:
                self.assertNotIn(f"import {bad}", text,
                                 f"{fname} imports forbidden network library {bad}")


if __name__ == "__main__":
    unittest.main()
