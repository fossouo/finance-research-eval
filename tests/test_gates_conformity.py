"""Conformity suite — the locked expectation table for the gates.

The financial analogue of a deterministic verifier's conformity test: every synthetic fixture
must produce exactly the specified per-gate status and final verdict. If a code
change alters any of these, this test fails loudly. Runs with stdlib unittest
(no third-party dependency, no network).

    python3 -m unittest discover -s tests -t .
"""
import unittest

from harness.gates.gates import evaluate
from harness.fixtures.cases import all_cases


class TestGateConformity(unittest.TestCase):
    def test_each_case_matches_expectations(self):
        for case in all_cases():
            with self.subTest(case=case["name"]):
                ev = evaluate(case["rr"])
                self.assertEqual(
                    ev.verdict, case["expected_verdict"],
                    f"{case['name']}: verdict {ev.verdict} != {case['expected_verdict']}",
                )
                got = ev.status_map()
                for gate_id, expected_status in case["expected_gates"].items():
                    self.assertEqual(
                        got.get(gate_id), expected_status,
                        f"{case['name']}: {gate_id} = {got.get(gate_id)} "
                        f"(expected {expected_status})",
                    )

    def test_personal_flag_is_admissible_but_client_block_is_not(self):
        """The lane severity distinction must hold: the SAME sourcing failure is
        a flag on personal (admissible) and a block on client (blocked)."""
        cases = {c["name"]: c for c in all_cases()}
        personal = evaluate(cases["g1_flag_personal"]["rr"])
        client = evaluate(cases["g5_block_client_unsourced"]["rr"])
        self.assertEqual(personal.by_id("G-1").status, "FAIL")
        self.assertEqual(personal.verdict, "ADMISSIBLE")
        self.assertEqual(client.by_id("G-1").status, "FAIL")
        self.assertEqual(client.verdict, "BLOCKED")

    def test_no_verdict_is_admissible_when_a_blocking_gate_fails(self):
        for case in all_cases():
            ev = evaluate(case["rr"])
            blocking_fail = any(
                g.status == "FAIL" and g.severity in ("BLOCK", "REQUIRED")
                for g in ev.gate_results
            )
            if blocking_fail:
                self.assertEqual(
                    ev.verdict, "BLOCKED",
                    f"{case['name']}: blocking gate failed but verdict is {ev.verdict}",
                )


if __name__ == "__main__":
    unittest.main()
