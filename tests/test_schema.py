"""Tests for the RR JSON Schema file and the lightweight structural validator.

The JSON Schema is the machine-readable standard; the harness ships a
dependency-free structural validator (a full jsonschema check is an optional
CI dependency).
"""
import json
import os
import unittest

from harness import rr as rrlib
from harness.fixtures.cases import all_cases

SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "harness", "schema", "recommendation_record.schema.json",
)


class TestSchema(unittest.TestCase):
    def test_schema_file_is_valid_json_with_expected_shape(self):
        with open(SCHEMA_PATH, encoding="utf-8") as f:
            schema = json.load(f)
        self.assertEqual(schema.get("title"), "Recommendation Record")
        self.assertIn("claims", schema["properties"])
        self.assertEqual(
            schema["properties"]["lane"]["enum"],
            ["personal-research", "client-mifid"],
        )

    def test_all_fixtures_are_structurally_valid(self):
        for case in all_cases():
            with self.subTest(case=case["name"]):
                errors = rrlib.validate_structure(case["rr"])
                self.assertEqual(errors, [], f"{case['name']}: {errors}")

    def test_admissible_fixture_hash_is_reproducible(self):
        cases = {c["name"]: c for c in all_cases()}
        rr = cases["admissible_personal"]["rr"]
        declared = rr["audit_trail"]["input_hash"]
        self.assertEqual(declared, rrlib.compute_input_hash(rr))

    def test_tampered_fixture_hash_does_not_match(self):
        cases = {c["name"]: c for c in all_cases()}
        rr = cases["g2_tampered_personal"]["rr"]
        declared = rr["audit_trail"]["input_hash"]
        self.assertNotEqual(declared, rrlib.compute_input_hash(rr))


if __name__ == "__main__":
    unittest.main()
