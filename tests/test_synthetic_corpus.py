"""Tests for SyntheticCorpusGen v1 (harness/sources/synthetic_corpus.py).

Verifies determinism, validity, kind distribution, and count honoring.
Pure stdlib, offline, no real data.
"""
import unittest

from harness.sources.synthetic_corpus import generate
from harness.sources.evalitem import EvalItem


class TestSyntheticCorpusGenDeterminism(unittest.TestCase):
    def test_same_seed_same_ids(self):
        a = generate(n=20, seed=0)
        b = generate(n=20, seed=0)
        self.assertEqual([it.item_id for it in a], [it.item_id for it in b])

    def test_same_seed_same_golds(self):
        a = generate(n=20, seed=0)
        b = generate(n=20, seed=0)
        self.assertEqual([it.gold_answer for it in a], [it.gold_answer for it in b])

    def test_same_seed_same_questions(self):
        a = generate(n=20, seed=0)
        b = generate(n=20, seed=0)
        self.assertEqual([it.question for it in a], [it.question for it in b])

    def test_different_seeds_different_ids(self):
        a = generate(n=20, seed=0)
        b = generate(n=20, seed=42)
        # ids embed the seed so they must differ
        self.assertNotEqual([it.item_id for it in a], [it.item_id for it in b])

    def test_different_seeds_different_golds(self):
        """Different seeds should generally produce different golds (probabilistic
        but reliable for non-trivial n)."""
        a = generate(n=20, seed=0)
        b = generate(n=20, seed=99)
        self.assertNotEqual([it.gold_answer for it in a], [it.gold_answer for it in b])


class TestSyntheticCorpusGenValidity(unittest.TestCase):
    def test_all_items_pass_validate(self):
        items = generate(n=50, seed=0)
        for it in items:
            errs = it.validate()
            self.assertEqual(errs, [], f"{it.item_id}: {errs}")

    def test_all_items_are_eval_items(self):
        items = generate(n=10, seed=0)
        for it in items:
            self.assertIsInstance(it, EvalItem)

    def test_all_items_are_synthetic(self):
        items = generate(n=30, seed=0)
        for it in items:
            self.assertTrue(it.is_synthetic(), f"{it.item_id} not marked synthetic")

    def test_all_items_have_source_synthetic_corpus(self):
        items = generate(n=10, seed=0)
        for it in items:
            self.assertEqual(it.source, "synthetic_corpus")

    def test_all_items_have_generator_meta(self):
        items = generate(n=10, seed=0)
        for it in items:
            self.assertEqual(it.meta.get("generator"), "synthetic_corpus_v1")

    def test_numeric_items_gold_parseable(self):
        items = generate(n=50, seed=0)
        for it in items:
            if it.gold_kind == "numeric":
                try:
                    float(it.gold_answer)
                except ValueError:
                    self.fail(f"{it.item_id}: numeric gold not parseable: {it.gold_answer!r}")

    def test_items_have_non_empty_question(self):
        items = generate(n=30, seed=0)
        for it in items:
            self.assertTrue(it.question.strip(), f"{it.item_id} has empty question")

    def test_items_have_stable_item_id_format(self):
        items = generate(n=10, seed=7)
        for i, it in enumerate(items):
            self.assertEqual(it.item_id, f"synth-7-{i}")


class TestSyntheticCorpusGenDistribution(unittest.TestCase):
    def test_kind_distribution_non_degenerate(self):
        """With n=30 we should see all three kinds: numeric, table_lookup, text."""
        items = generate(n=30, seed=0)
        kinds = {it.meta.get("kind") for it in items}
        self.assertIn("numeric", kinds)
        self.assertIn("table_lookup", kinds)
        self.assertIn("text", kinds)

    def test_count_honored(self):
        for n in (1, 10, 50, 99):
            with self.subTest(n=n):
                items = generate(n=n, seed=0)
                self.assertEqual(len(items), n)

    def test_zero_items(self):
        items = generate(n=0, seed=0)
        self.assertEqual(items, [])

    def test_large_n_all_valid(self):
        items = generate(n=200, seed=13)
        for it in items:
            self.assertEqual(it.validate(), [], f"{it.item_id} invalid")

    def test_numeric_ratio_approximately_one_third(self):
        """Numeric items should be ~1/3 of total (cycling pattern)."""
        items = generate(n=90, seed=0)
        numeric_count = sum(1 for it in items if it.meta.get("kind") == "numeric")
        self.assertEqual(numeric_count, 30)

    def test_context_not_empty(self):
        items = generate(n=30, seed=0)
        for it in items:
            self.assertGreater(len(it.context), 0, f"{it.item_id} has no context snippets")


if __name__ == "__main__":
    unittest.main()
