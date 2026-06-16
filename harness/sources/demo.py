"""Offline demo — load the SYNTHETIC samples through the public loaders and print
normalized EvalItem counts. No network, no real data, no model.

Run:  python3 -m harness.sources.demo
"""
from __future__ import annotations

from harness.sources import loaders, registry


def main():
    print("finance-research-eval — public loaders — offline demo")
    print("(synthetic samples only — no network, no real data, no model)")
    print("=" * 64)
    for sid in registry.list_sources():
        src = registry.get(sid)
        if not src.loader:
            print(f"\n[{sid}]  {src.name}  ->  POINTER-ONLY")
            print(f"   obtain: {src.obtain}")
            continue
        items = loaders.load_sample(sid)
        bad = [e for it in items for e in it.validate()]
        first = items[0] if items else None
        print(f"\n[{sid}]  {src.name}  ->  {len(items)} EvalItem(s), "
              f"{'all valid' if not bad else f'{len(bad)} errors'}, "
              f"synthetic={all(it.is_synthetic() for it in items)}")
        if first:
            print(f"   e.g. Q: {first.question}")
            print(f"        gold[{first.gold_kind}]: {first.gold_answer}  "
                  f"({len(first.context)} context snippet(s))")
    print("\n" + "-" * 64)
    print("Loaders operate on LOCAL files only. Real datasets are never bundled;")
    print("see harness/sources/registry.py for how to obtain each one yourself.")


if __name__ == "__main__":
    main()
