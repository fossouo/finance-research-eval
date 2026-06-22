"""End-to-end tests for the allocation-recevability metrics.

Exercises the two variadic-sum metrics added to the recompute engine
(``weights_sum_pct`` and ``holdings_value_sum``) through the real gate stack,
so we verify a CGP portfolio-allocation note the same way the harness verifies a
valuation note: weights must close to 100, holdings must reconcile to the
encours, and an unsourced fund line must be blocked on the client lane.

Pure stdlib, offline, no network. All data is synthetic (ISIN-free labels).
"""
import unittest

from harness.compute import metrics as M
from harness.fixtures import synthetic as S
from harness.gates import gates


def _g(evaluation, gid):
    return evaluation.by_id(gid)


def _comp_of(evaluation, metric):
    """Return the (mutated) computation dict for ``metric`` from the augmented RR."""
    for c in evaluation.augmented_rr.get("claims", []) or []:
        for comp in c.get("computations", []) or []:
            if comp.get("metric") == metric:
                return comp
    return None


# Three synthetic fund lines whose weights sum to exactly 100.0 and whose
# market values sum to a known encours.
_WEIGHTS = [("ev-w1", "Fonds Actions Monde", 50.0),
            ("ev-w2", "Fonds Obligataire Euro", 30.0),
            ("ev-w3", "Fonds Monetaire", 20.0)]
_VALUES = [("ev-v1", "Fonds Actions Monde", 60000.0),
           ("ev-v2", "Fonds Obligataire Euro", 36000.0),
           ("ev-v3", "Fonds Monetaire", 24000.0)]
_ENCOURS = 120000.0  # = 60000 + 36000 + 24000


def _weight_evidence(unit="pct", source_doc="ALLOC-NOTE-2025"):
    return [
        S.evidence(eid, label, w, source_doc, f"§alloc/{eid}", "2025-03-31", unit=unit)
        for eid, label, w in _WEIGHTS
    ]


def _value_evidence():
    return [
        S.evidence(eid, label, v, "ALLOC-NOTE-2025", f"§alloc/{eid}", "2025-03-31", unit="EUR")
        for eid, label, v in _VALUES
    ]


def _weights_computation(llm_value=100.0):
    inputs = {f"w{i}": eid for i, (eid, _, _) in enumerate(_WEIGHTS, start=1)}
    return S.computation("weights_sum_pct", "sum(weights) (attendu 100)", inputs, llm_value)


def _values_computation(llm_value=_ENCOURS):
    inputs = {f"v{i}": eid for i, (eid, _, _) in enumerate(_VALUES, start=1)}
    return S.computation("holdings_value_sum", "sum(montants) (attendu = encours)", inputs, llm_value)


def _alloc_record(rid, weight_evidence, computation, lane="personal-research",
                  lane_fields=None):
    claims = [
        S.claim("Repartition par ligne de fonds.", "quantitative",
                evidence=weight_evidence),
        S.claim("L'allocation est recevable.", "valuation",
                computations=[computation]),
    ]
    return S.record(rid, lane, "Portefeuille synthetique", "2025-03-31", claims,
                    lane_fields=lane_fields)


class TestAllocationMetricUnits(unittest.TestCase):
    """The variadic-sum metrics recompute directly, independent of arity."""

    def test_weights_sum_pct_is_variadic_sum(self):
        self.assertAlmostEqual(
            M.recompute("weights_sum_pct", {"w1": 50.0, "w2": 30.0, "w3": 20.0}),
            100.0,
        )

    def test_holdings_value_sum_is_variadic_sum(self):
        self.assertAlmostEqual(
            M.recompute("holdings_value_sum",
                        {"v1": 60000.0, "v2": 36000.0, "v3": 24000.0}),
            120000.0,
        )

    def test_empty_required_operands_recompute_handles_any_arity(self):
        # Two lines, five lines — recompute does not depend on a fixed operand set.
        self.assertAlmostEqual(M.recompute("weights_sum_pct", {"a": 40.0, "b": 60.0}), 100.0)
        self.assertAlmostEqual(
            M.recompute("weights_sum_pct",
                        {"a": 20.0, "b": 20.0, "c": 20.0, "d": 20.0, "e": 20.0}),
            100.0,
        )


class TestAllocationWeightsPass(unittest.TestCase):
    """Weights summing to 100 with a matching llm_value -> ADMISSIBLE, G-3 PASS."""

    def setUp(self):
        rr = _alloc_record("ALLOC-WEIGHTS-OK",
                           _weight_evidence(),
                           _weights_computation(llm_value=100.0))
        self.ev = gates.evaluate(rr)

    def test_verdict_admissible(self):
        self.assertEqual(self.ev.verdict, "ADMISSIBLE")

    def test_g3_pass(self):
        self.assertEqual(_g(self.ev, "G-3").status, gates.PASS)

    def test_recomputed_and_agree(self):
        comp = _comp_of(self.ev, "weights_sum_pct")
        self.assertIsNotNone(comp)
        self.assertEqual(comp["recomputed_value"], 100.0)
        self.assertTrue(comp["agree"])


class TestHoldingsReconciliationPass(unittest.TestCase):
    """Holdings values summing to the encours -> G-3 PASS / agree True."""

    def setUp(self):
        rr = _alloc_record("ALLOC-RECON-OK",
                           _value_evidence(),
                           _values_computation(llm_value=_ENCOURS))
        self.ev = gates.evaluate(rr)

    def test_verdict_admissible(self):
        self.assertEqual(self.ev.verdict, "ADMISSIBLE")

    def test_g3_pass(self):
        self.assertEqual(_g(self.ev, "G-3").status, gates.PASS)

    def test_reconciles_to_encours(self):
        comp = _comp_of(self.ev, "holdings_value_sum")
        self.assertIsNotNone(comp)
        self.assertEqual(comp["recomputed_value"], _ENCOURS)
        self.assertTrue(comp["agree"])


class TestAllocationWeightsMismatch(unittest.TestCase):
    """A claimed weights total of 95 while the lines sum to 100 -> G-3 FAIL."""

    def setUp(self):
        rr = _alloc_record("ALLOC-WEIGHTS-MISMATCH",
                           _weight_evidence(),
                           _weights_computation(llm_value=95.0))
        self.ev = gates.evaluate(rr)

    def test_g3_fail(self):
        self.assertEqual(_g(self.ev, "G-3").status, gates.FAIL)

    def test_disagree_recorded(self):
        comp = _comp_of(self.ev, "weights_sum_pct")
        self.assertIsNotNone(comp)
        self.assertEqual(comp["recomputed_value"], 100.0)
        self.assertFalse(comp["agree"])


class TestUnsourcedAllocationBlocked(unittest.TestCase):
    """On client-mifid, an unsourced fund line -> G-1 FAIL (BLOCK) -> BLOCKED."""

    def setUp(self):
        weights = _weight_evidence()
        # Strip the source_doc on the first fund line (unsourced evidence).
        weights[0]["source_doc"] = ""
        rr = _alloc_record(
            "ALLOC-UNSOURCED",
            weights,
            _weights_computation(llm_value=100.0),
            lane="client-mifid",
            # Provide complete lane_fields so the only blocking failure is G-1,
            # not G-6's lane-field requirement.
            lane_fields=S.client_lane_fields(),
        )
        self.ev = gates.evaluate(rr)

    def test_g1_fail(self):
        self.assertEqual(_g(self.ev, "G-1").status, gates.FAIL)

    def test_verdict_blocked(self):
        self.assertEqual(self.ev.verdict, "BLOCKED")


if __name__ == "__main__":
    unittest.main()
