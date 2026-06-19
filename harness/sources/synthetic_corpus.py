"""SyntheticCorpusGen v1 — deterministic, license-free EvalItem corpus.

Generates a mix of EvalItems without any real data, for use by the
gate-regression tracker, offline demos, and nightly CI.  Every item is
internally consistent and passes EvalItem.validate().

Usage:
    from harness.sources.synthetic_corpus import generate
    items = generate(n=50, seed=0)

CLI:
    python3 -m harness.sources.synthetic_corpus --n 20

Hard rule: stdlib only.  No network, no third-party deps.
"""
from __future__ import annotations

import json
import random
import sys
from typing import List

from harness.sources.evalitem import ContextSnippet, EvalItem

# ---------------------------------------------------------------------------
# Company names and document identifiers (all purely synthetic)
# ---------------------------------------------------------------------------
_COMPANIES = [
    "ACME SA", "BETA Corp", "GAMMA Inc", "DELTA Partners", "EPSILON Ltd",
    "ZETA Holdings", "ETA Group", "THETA Capital", "IOTA Ventures", "KAPPA SA",
    "LAMBDA Corp", "MU Industries", "NU Financials", "XI Partners", "OMICRON Ltd",
]

_YEARS = ["FY2022", "FY2023", "FY2024"]

# ---------------------------------------------------------------------------
# Deterministic numeric generators
# ---------------------------------------------------------------------------

def _gen_numeric_item(rng: random.Random, seed: int, idx: int) -> EvalItem:
    """Generate a numeric-reasoning item with internally consistent figures."""
    company = _COMPANIES[rng.randint(0, len(_COMPANIES) - 1)]
    year = _YEARS[rng.randint(0, len(_YEARS) - 1)]
    # revenue in [500, 3000] MEUR, rounded to nearest 50
    revenue = round(rng.randint(10, 60) * 50)
    # margin in [0.15, 0.45] -> ebitda
    margin = round(rng.uniform(0.15, 0.45), 2)
    ebitda = round(revenue * margin, 2)
    # ev = ebitda * multiple [6, 12]
    multiple = round(rng.uniform(6.0, 12.0), 1)
    ev = round(ebitda * multiple, 2)
    # which ratio to ask for
    question_kind = rng.choice(["ev_ebitda", "ebitda_margin"])
    if question_kind == "ev_ebitda":
        gold = round(ev / ebitda, 4) if ebitda else 0.0
        question = (
            f"What is {company}'s EV/EBITDA multiple for {year}? "
            f"(enterprise value: {ev} MEUR, EBITDA: {ebitda} MEUR)"
        )
        table = [
            ["Metric", year],
            ["Enterprise value (MEUR)", str(ev)],
            ["EBITDA (MEUR)", str(ebitda)],
        ]
    else:  # ebitda_margin
        gold = round(ebitda / revenue, 4) if revenue else 0.0
        question = (
            f"What is {company}'s EBITDA margin for {year}? "
            f"(EBITDA: {ebitda} MEUR, revenue: {revenue} MEUR)"
        )
        table = [
            ["Metric", year],
            ["Revenue (MEUR)", str(revenue)],
            ["EBITDA (MEUR)", str(ebitda)],
        ]
    flat_table = " | ".join(" ".join(str(c) for c in row) for row in table)
    doc_id = f"SYNTH-{company.replace(' ', '')}-{year}"
    ctx = [
        ContextSnippet(
            text=f"{company} reported the following figures for {year} (synthetic).",
            source_doc=doc_id,
            locator="text",
        ),
        ContextSnippet(text=flat_table, source_doc=doc_id, locator="table"),
    ]
    return EvalItem(
        source="synthetic_corpus",
        item_id=f"synth-{seed}-{idx}",
        question=question,
        gold_answer=str(gold),
        gold_kind="numeric",
        context=ctx,
        meta={
            "synthetic": True,
            "generator": "synthetic_corpus_v1",
            "kind": "numeric",
            "company": company,
            "year": year,
        },
    )


def _gen_table_lookup_item(rng: random.Random, seed: int, idx: int) -> EvalItem:
    """Generate a table-lookup item where the gold is a single cell value."""
    company = _COMPANIES[rng.randint(0, len(_COMPANIES) - 1)]
    year = _YEARS[rng.randint(0, len(_YEARS) - 1)]
    metrics = [
        ("Revenue", rng.randint(10, 60) * 50, "MEUR"),
        ("Net debt", rng.randint(2, 20) * 50, "MEUR"),
        ("Market cap", rng.randint(10, 80) * 50, "MEUR"),
        ("Free cash flow", rng.randint(1, 10) * 10, "MEUR"),
    ]
    metric_name, metric_val, unit = metrics[rng.randint(0, len(metrics) - 1)]
    gold_str = str(float(metric_val))
    question = (
        f"According to the table, what is {company}'s {metric_name} for {year} in {unit}?"
    )
    table = [
        ["Metric", f"{year} ({unit})"],
        [metric_name, str(metric_val)],
    ]
    flat_table = " | ".join(" ".join(str(c) for c in row) for row in table)
    doc_id = f"SYNTH-{company.replace(' ', '')}-{year}"
    ctx = [
        ContextSnippet(
            text=f"Selected financials for {company} {year} (synthetic).",
            source_doc=doc_id,
            locator="text",
        ),
        ContextSnippet(text=flat_table, source_doc=doc_id, locator="table"),
    ]
    return EvalItem(
        source="synthetic_corpus",
        item_id=f"synth-{seed}-{idx}",
        question=question,
        gold_answer=gold_str,
        gold_kind="numeric",
        context=ctx,
        meta={
            "synthetic": True,
            "generator": "synthetic_corpus_v1",
            "kind": "table_lookup",
            "company": company,
            "year": year,
        },
    )


def _gen_text_item(rng: random.Random, seed: int, idx: int) -> EvalItem:
    """Generate a text-answer item (qualitative description)."""
    company = _COMPANIES[rng.randint(0, len(_COMPANIES) - 1)]
    year = _YEARS[rng.randint(0, len(_YEARS) - 1)]
    lanes = ["personal-research", "client-mifid"]
    lane = lanes[rng.randint(0, 1)]
    question = (
        f"What is the recommended analytical lane for {company} in {year} "
        f"given a balanced risk profile?"
    )
    gold = lane
    doc_id = f"SYNTH-{company.replace(' ', '')}-{year}-LANE"
    ctx = [
        ContextSnippet(
            text=(
                f"{company} investment analysis for {year}: lane = {lane} "
                f"(synthetic classification, no real data)."
            ),
            source_doc=doc_id,
            locator="text",
        ),
    ]
    return EvalItem(
        source="synthetic_corpus",
        item_id=f"synth-{seed}-{idx}",
        question=question,
        gold_answer=gold,
        gold_kind="text",
        context=ctx,
        meta={
            "synthetic": True,
            "generator": "synthetic_corpus_v1",
            "kind": "text",
            "company": company,
            "year": year,
        },
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_GENERATORS = [_gen_numeric_item, _gen_table_lookup_item, _gen_text_item]


def generate(n: int = 50, seed: int = 0) -> List[EvalItem]:
    """Return a deterministic list of ``n`` synthetic EvalItems.

    The corpus is reproducible for the same ``(n, seed)`` pair.  Different
    seeds produce structurally different corpora (different company/year
    combinations and ratios).  Every item passes ``EvalItem.validate()``.

    The mix cycles through three item kinds in order:
      numeric (EV/EBITDA or margin ratio), table_lookup, text (lane label).
    This guarantees a non-degenerate kind distribution for any n >= 3.
    """
    rng = random.Random(seed)
    items: List[EvalItem] = []
    for i in range(n):
        gen = _GENERATORS[i % len(_GENERATORS)]
        item = gen(rng, seed, i)
        items.append(item)
    return items


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(
        description="SyntheticCorpusGen v1 — print a JSON summary of generated items.",
        prog="harness.sources.synthetic_corpus",
    )
    parser.add_argument("--n", type=int, default=50, help="Number of items to generate (default: 50)")
    parser.add_argument("--seed", type=int, default=0, help="Random seed (default: 0)")
    parser.add_argument("--validate", action="store_true", help="Run .validate() and report errors")
    args = parser.parse_args(argv)

    items = generate(n=args.n, seed=args.seed)
    kind_counts: dict = {}
    errors = []
    for it in items:
        k = it.meta.get("kind", "unknown")
        kind_counts[k] = kind_counts.get(k, 0) + 1
        if args.validate:
            errs = it.validate()
            if errs:
                errors.append({"item_id": it.item_id, "errors": errs})

    summary = {
        "n": len(items),
        "seed": args.seed,
        "kind_distribution": kind_counts,
    }
    if args.validate:
        summary["validation_errors"] = len(errors)
        if errors:
            summary["first_errors"] = errors[:5]

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
