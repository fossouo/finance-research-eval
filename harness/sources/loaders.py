"""Offline loaders — normalize a LOCALLY-PRESENT file into EvalItems.

Hard rule: **no network**. These functions read a path the user provides (data
they downloaded themselves) and never fetch anything. There is intentionally no
import of urllib / http / socket / requests anywhere in this package — a test
enforces it.

Real datasets live under corpora/ (gitignored, never committed). The committed
samples under samples/ are SYNTHETIC stand-ins so this code is exercisable
offline without redistributing anyone's data.
"""
from __future__ import annotations

import json
import os

from harness.sources.evalitem import ContextSnippet, EvalItem
from harness.sources import registry

_SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "samples")


class SourceDataMissing(FileNotFoundError):
    """Raised when the real data file is not present locally. The repo does not
    download it — see the registry pointer for how to obtain it yourself."""


def _require_file(path):
    if not path or not os.path.exists(path):
        raise SourceDataMissing(
            f"data file not found: {path!r}. This repo does not download or "
            f"redistribute datasets — obtain it yourself (see the source registry)."
        )


def _num_or_text(value):
    try:
        float(value)
        return "numeric"
    except (TypeError, ValueError):
        return "text"


# --- concrete loaders -------------------------------------------------------

def load_financebench(path) -> list:
    """Parse a FinanceBench-shaped JSONL file into EvalItems."""
    _require_file(path)
    items = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            ctx = [
                ContextSnippet(
                    text=ev.get("evidence_text", ""),
                    source_doc=obj.get("doc_name", ""),
                    locator=f"page {ev.get('page')}" if ev.get("page") is not None else "",
                )
                for ev in obj.get("evidence", []) or []
            ]
            items.append(EvalItem(
                source="financebench",
                item_id=str(obj.get("financebench_id", "")),
                question=obj.get("question", ""),
                gold_answer=str(obj.get("answer", "")),
                gold_kind=_num_or_text(obj.get("answer", "")),
                context=ctx,
                meta={"synthetic": bool(obj.get("_synthetic")), "doc_name": obj.get("doc_name", "")},
            ))
    return items


def load_finqa(path) -> list:
    """Parse a FinQA-shaped JSON array into EvalItems."""
    _require_file(path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    items = []
    for obj in data:
        gold = obj.get("gold", obj.get("answer", ""))
        ctx = []
        for snippet in (obj.get("pre_text", []) or []) + (obj.get("post_text", []) or []):
            ctx.append(ContextSnippet(text=str(snippet), source_doc=str(obj.get("id", "")), locator="text"))
        table = obj.get("table")
        if table:
            flat = " | ".join(" ".join(str(c) for c in row) for row in table)
            ctx.append(ContextSnippet(text=flat, source_doc=str(obj.get("id", "")), locator="table"))
        items.append(EvalItem(
            source="finqa",
            item_id=str(obj.get("id", "")),
            question=obj.get("question", ""),
            gold_answer=str(gold),
            gold_kind=_num_or_text(gold),
            context=ctx,
            meta={"synthetic": bool(obj.get("_synthetic"))},
        ))
    return items


def load_edgar_companyfacts(path, max_items=50) -> list:
    """Parse an SEC EDGAR companyfacts JSON into EvalItems (one per reported
    fact). Each fact already carries a filing date -> a natural point-in-time
    anchor for future G-4 checks."""
    _require_file(path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    entity = data.get("entityName", "")
    synthetic = bool(data.get("_synthetic"))
    items = []
    for taxonomy, concepts in (data.get("facts", {}) or {}).items():
        for concept, body in concepts.items():
            for unit, entries in (body.get("units", {}) or {}).items():
                for e in entries:
                    if len(items) >= max_items:
                        return items
                    form = e.get("form", "")
                    end = e.get("end", "")
                    val = e.get("val")
                    items.append(EvalItem(
                        source="edgar",
                        item_id=f"{concept}:{end}:{form}",
                        question=f"What is {concept} ({form} {e.get('fy', '')}) for the period ending {end}?",
                        gold_answer=str(val),
                        gold_kind="numeric",
                        context=[ContextSnippet(
                            text=f"{concept} = {val} {unit}",
                            source_doc=f"{entity} {form}".strip(),
                            locator=f"{taxonomy}:{concept} period {end}",
                            as_of=e.get("filed", ""),
                        )],
                        meta={"synthetic": synthetic, "taxonomy": taxonomy, "unit": unit},
                    ))
    return items


# --- dispatch ---------------------------------------------------------------

_LOADERS = {
    "load_financebench": load_financebench,
    "load_finqa": load_finqa,
    "load_edgar_companyfacts": load_edgar_companyfacts,
}


def load(source_id: str, path=None) -> list:
    """Load EvalItems for a registered source from a local path. Falls back to
    the source's ``local_path_hint`` if no path is given. Pointer-only sources
    (no loader implemented in P2) raise NotImplementedError."""
    src = registry.get(source_id)
    if not src.loader:
        raise NotImplementedError(
            f"'{source_id}' is pointer-only in P2 (see registry: {src.homepage})."
        )
    fn = _LOADERS[src.loader]
    return fn(path or src.local_path_hint)


def load_sample(source_id: str) -> list:
    """Load the committed SYNTHETIC sample for a source (offline)."""
    src = registry.get(source_id)
    if not src.sample:
        raise NotImplementedError(f"'{source_id}' has no synthetic sample.")
    fn = _LOADERS[src.loader]
    return fn(os.path.join(_SAMPLES_DIR, src.sample))
