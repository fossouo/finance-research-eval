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

# ConvFinQA accepted shape (documented for load_convfinqa):
#
#   A JSON array; each entry is an object with the following fields
#   (all accessed via .get() with safe fallbacks):
#
#   id          : str — unique entry identifier (fallback: "")
#   pre_text    : list[str] — paragraphs preceding the table (fallback: [])
#   post_text   : list[str] — paragraphs following the table (fallback: [])
#   table       : list[list] — 2-D array of cell strings (fallback: [])
#   annotation  : dict with either:
#       dialogue_break : list[str] — ordered turn questions (primary key)
#       questions      : list[str] — alternate key when dialogue_break absent
#       exe_ans_list   : list[str] — per-turn answers (used only for meta)
#       answer         : str|num   — final gold answer (primary)
#       gold           : str|num   — alternate gold key when answer absent
#
#   Mapping:
#     question  = conversation turns joined with " → " (or the single final
#                 turn when only one is present)
#     gold      = annotation.answer (or annotation.gold as fallback)
#     item_id   = entry id; falls back to a stable positional id
#                 ("convfinqa-<idx>") so it is never empty
#     context   = ContextSnippets from pre_text + post_text (locator="text")
#                 plus one flattened table snippet (locator="table")
#     meta      = {"synthetic": bool, "conversational": True, "turns": <n>}
#
#   Question-less entries are skipped, and every emitted item is verified to pass
#   .validate() before being returned.

# TAT-QA accepted shape (documented for load_tatqa):
#
#   A JSON array; each entry covers one passage/table and may contain multiple
#   questions. Accepted fields (all accessed via .get() with safe fallbacks):
#
#   uid         : str — entry identifier (fallback: "")
#   table       : either {"table": [[...]]} or a bare list[list] (fallback: [])
#   paragraphs  : list of {"text": str} dicts OR list of str (fallback: [])
#   questions   : list of question objects, each with:
#       uid         : str — question identifier (fallback: positional index)
#       question    : str — question text
#       answer      : str | list[str] — gold answer(s); if a list, joined with ", "
#       answer_type : str — e.g. "span", "arithmetic", "count" (fallback: "")
#       scale       : str — e.g. "million", "percent", "" (fallback: "")
#
#   Mapping (one EvalItem per question):
#     item_id   = "<entry_uid>-<question_uid>"; falls back to a stable positional
#                 id ("tatqa-<entry_idx>-<q_idx>") so it is never empty
#     question  = question text; if scale present, appended as "(scale: <scale>)"
#     gold      = answer joined if list (scale is NOT folded into gold)
#     gold_kind = numeric when the RAW answer (before scale) parses as float, else
#                 text — so a numeric answer like "1200" stays numeric-evaluable
#     context   = one flattened table snippet + one snippet per paragraph
#     meta      = {"synthetic": bool, "answer_type": str, "scale": str}
#
#   Question-less entries are skipped, and every emitted item is verified to pass
#   .validate() before being returned.

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


def load_convfinqa(path) -> list:
    """Parse a ConvFinQA-shaped JSON array into EvalItems.

    See the module-level docstring for the full accepted shape and mapping
    rationale. Every produced item passes .validate().

    The ``question`` field joins all conversation turns with " → " so the item
    captures the full dialogue chain. The gold is the final answer
    (annotation.answer, fallback annotation.gold).
    """
    _require_file(path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    items = []
    for idx, obj in enumerate(data):
        ann = obj.get("annotation") or {}
        # conversation turns: prefer dialogue_break, fall back to questions
        turns = ann.get("dialogue_break") or ann.get("questions") or []
        if isinstance(turns, list) and turns:
            question = " → ".join(str(t) for t in turns)
        else:
            question = str(ann.get("dialogue_break") or ann.get("questions") or "")
        # A question-less item is meaningless to evaluate — skip it.
        if not question:
            continue
        n_turns = len(turns) if isinstance(turns, list) else 0
        # gold: final answer
        gold = ann.get("answer", ann.get("gold", ""))
        gold_str = str(gold)
        # item_id: synthesize a stable positional id if the entry has none.
        entry_id = str(obj.get("id", "")) or f"convfinqa-{idx}"
        # context: pre_text + post_text as text snippets, table as one snippet
        ctx = []
        for snippet in (obj.get("pre_text") or []) + (obj.get("post_text") or []):
            ctx.append(ContextSnippet(text=str(snippet), source_doc=entry_id, locator="text"))
        table = obj.get("table")
        if table:
            flat = " | ".join(" ".join(str(c) for c in row) for row in table)
            ctx.append(ContextSnippet(text=flat, source_doc=entry_id, locator="table"))
        item = EvalItem(
            source="convfinqa",
            item_id=entry_id,
            question=question,
            gold_answer=gold_str,
            gold_kind=_num_or_text(gold_str),
            context=ctx,
            meta={
                "synthetic": bool(obj.get("_synthetic")),
                "conversational": True,
                "turns": n_turns,
            },
        )
        # Contract guard: only valid items are returned.
        if item.validate():
            continue
        items.append(item)
    return items


def load_tatqa(path) -> list:
    """Parse a TAT-QA-shaped JSON array into EvalItems (one per question).

    See the module-level docstring for the full accepted shape and mapping
    rationale. The table may be provided as a bare list[list] or wrapped in a
    dict with a "table" key. Paragraphs may be a list of dicts with a "text"
    key or a list of strings. Every produced item passes .validate().
    """
    _require_file(path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    items = []
    for entry_idx, obj in enumerate(data):
        entry_id = str(obj.get("uid", ""))
        synthetic = bool(obj.get("_synthetic"))
        # table: accept {"table": [[...]]} dict or bare list[list]
        raw_table = obj.get("table") or []
        if isinstance(raw_table, dict):
            table_rows = raw_table.get("table") or []
        else:
            table_rows = raw_table
        table_flat = " | ".join(" ".join(str(c) for c in row) for row in table_rows) if table_rows else ""
        # paragraphs: list of {"text": ...} or list of str
        paragraphs = obj.get("paragraphs") or []
        para_texts = []
        for p in paragraphs:
            if isinstance(p, dict):
                para_texts.append(str(p.get("text", "")))
            else:
                para_texts.append(str(p))
        # one EvalItem per question
        for q_idx, q_obj in enumerate(obj.get("questions") or []):
            question_text = str(q_obj.get("question", ""))
            # A question-less item is meaningless to evaluate — skip it.
            if not question_text:
                continue
            # item_id: always non-empty. Fall back through entry uid, question
            # uid, then a stable positional id so it can never be empty.
            q_uid = q_obj.get("uid")
            q_id = str(q_uid) if q_uid not in (None, "") else str(q_idx)
            base = entry_id or f"tatqa-{entry_idx}"
            item_id = f"{base}-{q_id}"
            scale = str(q_obj.get("scale") or "")
            answer_type = str(q_obj.get("answer_type") or "")
            # gold: string or list; if list join with ", "
            raw_answer = q_obj.get("answer", "")
            if isinstance(raw_answer, list):
                gold_str = ", ".join(str(a) for a in raw_answer)
            else:
                gold_str = str(raw_answer)
            # gold_kind is determined from the RAW answer (before any scale), so a
            # numeric answer like "1200" stays numeric-evaluable. The scale is kept
            # in meta (and hinted in the question), NOT folded into gold_answer.
            gold_kind = _num_or_text(gold_str)
            # question text: append scale hint when present
            if scale:
                question_text = f"{question_text} (scale: {scale})"
            # context: table snippet first, then paragraphs
            ctx = []
            if table_flat:
                ctx.append(ContextSnippet(text=table_flat, source_doc=entry_id, locator="table"))
            for pt in para_texts:
                if pt:
                    ctx.append(ContextSnippet(text=pt, source_doc=entry_id, locator="text"))
            item = EvalItem(
                source="tatqa",
                item_id=item_id,
                question=question_text,
                gold_answer=gold_str,
                gold_kind=gold_kind,
                context=ctx,
                meta={
                    "synthetic": synthetic,
                    "answer_type": answer_type,
                    "scale": scale,
                },
            )
            # Contract guard: only valid items are returned.
            if item.validate():
                continue
            items.append(item)
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
    "load_convfinqa": load_convfinqa,
    "load_tatqa": load_tatqa,
    "load_edgar_companyfacts": load_edgar_companyfacts,
}


def load(source_id: str, path=None) -> list:
    """Load EvalItems for a registered source from a local path. Falls back to
    the source's ``local_path_hint`` if no path is given. Pointer-only sources
    (no loader implemented) raise NotImplementedError."""
    src = registry.get(source_id)
    if not src.loader:
        raise NotImplementedError(
            f"'{source_id}' is pointer-only (see registry: {src.homepage})."
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
