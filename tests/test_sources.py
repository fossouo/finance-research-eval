"""Tests for the public source loaders (P2).

Enforce the P2 invariants: offline only, synthetic samples valid, pointers
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
        for sid in ("financebench", "finqa", "edgar"):
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

    def test_pointer_only_sources_refuse_to_load(self):
        for sid in ("convfinqa", "tatqa"):
            with self.subTest(source=sid):
                with self.assertRaises(NotImplementedError):
                    loaders.load(sid, path="whatever")


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
