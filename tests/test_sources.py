"""Tests for the public source loaders.

Enforce the invariants: offline only, synthetic samples valid, pointers
complete, no network imports, pointer-only sources refuse to load.
"""
import os
import unittest

from harness.sources import loaders, registry
from harness.sources.evalitem import EvalItem

SOURCES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "harness", "sources"
)
FORBIDDEN_IMPORTS = ("urllib", "requests", "http.client", "socket", "httpx", "aiohttp")


class TestRegistry(unittest.TestCase):
    def test_every_source_is_a_complete_pointer(self):
        for sid in registry.list_sources():
            src = registry.get(sid)
            for field in ("id", "name", "homepage", "obtain", "license", "citation", "fmt"):
                self.assertTrue(getattr(src, field), f"{sid}: empty {field}")

    def test_benchmarks_default_to_no_redistribution(self):
        for sid in ("financebench", "finqa", "convfinqa", "tatqa"):
            self.assertFalse(
                registry.get(sid).redistribution_allowed,
                f"{sid}: benchmark must default to no-redistribution",
            )


class TestLoaders(unittest.TestCase):
    def test_synthetic_samples_load_and_validate(self):
        for sid in ("financebench", "finqa", "edgar", "convfinqa", "tatqa"):
            with self.subTest(source=sid):
                items = loaders.load_sample(sid)
                self.assertGreater(len(items), 0)
                for it in items:
                    self.assertIsInstance(it, EvalItem)
                    self.assertEqual(it.validate(), [], f"{sid}: {it.item_id} invalid")
                    self.assertTrue(it.is_synthetic(), f"{sid}: sample not marked synthetic")

    def test_edgar_items_are_numeric_with_pointintime_anchor(self):
        items = loaders.load_sample("edgar")
        for it in items:
            self.assertEqual(it.gold_kind, "numeric")
            self.assertTrue(it.context and it.context[0].as_of, "edgar item lacks as_of anchor")

    def test_missing_local_file_raises_not_fetches(self):
        with self.assertRaises(loaders.SourceDataMissing):
            loaders.load("financebench", path="corpora/does/not/exist.jsonl")

    def test_pointer_only_sources_are_now_implemented(self):
        """convfinqa and tatqa now have loaders — load_sample must succeed."""
        for sid in ("convfinqa", "tatqa"):
            with self.subTest(source=sid):
                items = loaders.load_sample(sid)
                self.assertGreater(len(items), 0)

    # --- ConvFinQA-specific tests -------------------------------------------

    def test_convfinqa_source_id(self):
        items = loaders.load_sample("convfinqa")
        for it in items:
            self.assertEqual(it.source, "convfinqa")

    def test_convfinqa_items_have_conversational_meta(self):
        items = loaders.load_sample("convfinqa")
        for it in items:
            self.assertIn("conversational", it.meta)
            self.assertTrue(it.meta["conversational"])
            self.assertIn("turns", it.meta)
            self.assertGreaterEqual(it.meta["turns"], 1)

    def test_convfinqa_question_joins_turns(self):
        """Multi-turn questions should contain the ' → ' separator."""
        items = loaders.load_sample("convfinqa")
        multi = [it for it in items if it.meta.get("turns", 0) > 1]
        for it in multi:
            self.assertIn(" → ", it.question)

    def test_convfinqa_numeric_golds_parse(self):
        items = loaders.load_sample("convfinqa")
        numeric = [it for it in items if it.gold_kind == "numeric"]
        self.assertGreater(len(numeric), 0)
        for it in numeric:
            try:
                float(it.gold_answer)
            except ValueError:
                self.fail(f"convfinqa numeric gold not parseable: {it.gold_answer!r}")

    def test_convfinqa_context_not_empty(self):
        items = loaders.load_sample("convfinqa")
        for it in items:
            self.assertGreater(len(it.context), 0, f"{it.item_id} has no context")

    # --- TAT-QA-specific tests ----------------------------------------------

    def test_tatqa_source_id(self):
        items = loaders.load_sample("tatqa")
        for it in items:
            self.assertEqual(it.source, "tatqa")

    def test_tatqa_one_item_per_question(self):
        """The sample has 2 entries with 3+2 questions = 5 items total."""
        items = loaders.load_sample("tatqa")
        self.assertEqual(len(items), 5)

    def test_tatqa_meta_fields(self):
        items = loaders.load_sample("tatqa")
        for it in items:
            self.assertIn("answer_type", it.meta)
            self.assertIn("scale", it.meta)

    def test_tatqa_scale_kept_in_meta_not_gold(self):
        """Scale must be preserved in meta and hinted in the question, but must
        NOT be folded into gold_answer (otherwise a numeric answer like '1200'
        would stop being numeric-evaluable)."""
        items = loaders.load_sample("tatqa")
        scaled = [it for it in items if it.meta.get("scale")]
        self.assertGreater(len(scaled), 0, "sample should exercise a scaled answer")
        for it in scaled:
            self.assertIn("scale:", it.question, "scale should be hinted in question")
            self.assertNotIn(it.meta["scale"], it.gold_answer,
                             "scale must not be folded into gold_answer")

    def test_tatqa_scaled_numeric_stays_numeric(self):
        """A numeric answer carrying a scale (e.g. '1200' + 'million') must keep
        gold_kind=='numeric' and a parseable gold_answer."""
        items = loaders.load_sample("tatqa")
        scaled_numeric = [
            it for it in items if it.meta.get("scale") and it.gold_kind == "numeric"
        ]
        self.assertGreater(len(scaled_numeric), 0,
                           "sample should exercise a scaled-numeric answer")
        for it in scaled_numeric:
            float(it.gold_answer)  # raises if not parseable

    def test_tatqa_numeric_golds_parse(self):
        items = loaders.load_sample("tatqa")
        numeric = [it for it in items if it.gold_kind == "numeric"]
        self.assertGreater(len(numeric), 0)
        for it in numeric:
            try:
                float(it.gold_answer)
            except ValueError:
                self.fail(f"tatqa numeric gold not parseable: {it.gold_answer!r}")

    def test_tatqa_context_has_table_and_text(self):
        items = loaders.load_sample("tatqa")
        locators = {loc for it in items for ctx in it.context for loc in [ctx.locator]}
        self.assertIn("table", locators)
        self.assertIn("text", locators)

    def test_tatqa_items_are_synthetic(self):
        items = loaders.load_sample("tatqa")
        for it in items:
            self.assertTrue(it.is_synthetic(), f"{it.item_id} not marked synthetic")


class TestLoaderRobustness(unittest.TestCase):
    """Regression guards: the loaders must honor the docstring contract that
    every returned item passes .validate() — even on fallback paths (missing
    ids, missing questions). Uses tmp files with hand-built in-memory shapes,
    all clearly synthetic.
    """

    def _write_tmp(self, payload):
        import json as _json
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            _json.dump(payload, f)
        self.addCleanup(os.unlink, path)
        return path

    # --- ConvFinQA ----------------------------------------------------------

    def test_convfinqa_missing_id_gets_stable_nonempty_id(self):
        payload = [{
            "_synthetic": True,
            # no "id"
            "pre_text": ["context (synthetic)"],
            "annotation": {"dialogue_break": ["What is X?"], "answer": "42"},
        }]
        items = loaders.load_convfinqa(self._write_tmp(payload))
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0].item_id, "item_id must never be empty")
        self.assertEqual(items[0].item_id, "convfinqa-0")
        self.assertEqual(items[0].validate(), [])

    def test_convfinqa_no_turns_is_skipped(self):
        payload = [
            {  # question-less entry -> skipped
                "_synthetic": True,
                "id": "bad-entry",
                "annotation": {"answer": "1"},
            },
            {  # well-formed sibling -> loaded
                "_synthetic": True,
                "id": "good-entry",
                "annotation": {"dialogue_break": ["What is Y?"], "answer": "2"},
            },
        ]
        items = loaders.load_convfinqa(self._write_tmp(payload))
        ids = [it.item_id for it in items]
        self.assertNotIn("bad-entry", ids)
        self.assertIn("good-entry", ids)
        self.assertEqual(len(items), 1)
        for it in items:
            self.assertEqual(it.validate(), [])

    # --- TAT-QA -------------------------------------------------------------

    def test_tatqa_missing_uids_get_stable_nonempty_ids(self):
        payload = [{
            "_synthetic": True,
            # no entry "uid"
            "table": [["Metric", "FY2024"], ["Revenue", "100"]],
            "paragraphs": ["context (synthetic)"],
            "questions": [
                {  # no question "uid"
                    "question": "What is revenue?",
                    "answer": ["100"],
                    "answer_type": "span",
                    "scale": "million",
                },
            ],
        }]
        items = loaders.load_tatqa(self._write_tmp(payload))
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0].item_id, "item_id must never be empty")
        self.assertEqual(items[0].item_id, "tatqa-0-0")
        self.assertEqual(items[0].validate(), [])

    def test_tatqa_scaled_numeric_answer_kept_numeric(self):
        payload = [{
            "_synthetic": True,
            "uid": "e1",
            "table": [["Metric", "FY2024"], ["Revenue", "1200"]],
            "paragraphs": ["synthetic context"],
            "questions": [{
                "uid": "q1",
                "question": "What was revenue?",
                "answer": "1200",
                "answer_type": "span",
                "scale": "million",
            }],
        }]
        items = loaders.load_tatqa(self._write_tmp(payload))
        self.assertEqual(len(items), 1)
        it = items[0]
        self.assertEqual(it.gold_kind, "numeric")
        self.assertEqual(it.gold_answer, "1200")
        float(it.gold_answer)  # parseable
        self.assertEqual(it.meta["scale"], "million")
        self.assertNotIn("million", it.gold_answer)
        self.assertEqual(it.validate(), [])

    def test_tatqa_question_less_question_is_skipped(self):
        payload = [{
            "_synthetic": True,
            "uid": "e1",
            "table": [["Metric", "FY2024"], ["Revenue", "100"]],
            "questions": [
                {"uid": "q1", "answer": "100", "scale": ""},  # no question -> skip
                {"uid": "q2", "question": "What is revenue?", "answer": "100", "scale": ""},
            ],
        }]
        items = loaders.load_tatqa(self._write_tmp(payload))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].item_id, "e1-q2")
        self.assertEqual(items[0].validate(), [])


class TestNoNetwork(unittest.TestCase):
    def test_sources_package_imports_no_network_library(self):
        for fname in os.listdir(SOURCES_DIR):
            if not fname.endswith(".py"):
                continue
            with open(os.path.join(SOURCES_DIR, fname), encoding="utf-8") as f:
                text = f.read()
            for bad in FORBIDDEN_IMPORTS:
                self.assertNotIn(
                    f"import {bad}", text,
                    f"{fname} imports forbidden network library {bad}",
                )


if __name__ == "__main__":
    unittest.main()
