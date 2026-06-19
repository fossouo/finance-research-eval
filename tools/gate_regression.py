"""Gate-regression tracker — deterministic snapshot + drift detection.

Builds a fixed corpus from the labeled synthetic fixtures and runs every
Recommendation Record through the evaluation gates.  The resulting snapshot
is compared to a committed baseline; any drift exits 1.

Usage:
    python3 tools/gate_regression.py            # compare to baseline, exit 1 on drift
    python3 tools/gate_regression.py --update   # overwrite baseline, exit 0
    python3 tools/gate_regression.py --json     # print snapshot JSON, exit 0
    python3 tools/gate_regression.py --synthetic-only  # restrict to synthetic RRs

The baseline lives at: tests/fixtures/gate_regression_baseline.json
(runs/ is gitignored; tests/fixtures/ is committed; tests/data/ is gitignored
because .gitignore patterns on "data/" match anywhere in the tree).

Hard rules: stdlib only.  No network.  No third-party deps.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# Ensure the repo root is importable regardless of cwd.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from harness.fixtures.cases import all_cases  # noqa: E402
from harness.gates.gates import evaluate       # noqa: E402

_BASELINE_PATH = os.path.join(
    _REPO_ROOT, "tests", "fixtures", "gate_regression_baseline.json"
)


# ---------------------------------------------------------------------------
# Corpus builders
# ---------------------------------------------------------------------------

def _all_fixture_rrs(synthetic_only: bool = False):
    """Return a list of (name, rr, expected_verdict) tuples from labeled cases."""
    cases = all_cases()
    result = []
    for c in cases:
        rr = c["rr"]
        # When --synthetic-only, include only RRs whose id starts with "rr-"
        # and whose subject is the standard ACME synthetic subject.
        # All fixture cases are synthetic by construction; the flag is an
        # additional filter that would be useful for a future expansion where
        # real-ish RRs are added to the catalogue.
        if synthetic_only:
            # All current all_cases() entries are synthetic; accept all.
            # If real RRs are ever added they should carry rr["_synthetic"]=False.
            if not rr.get("_synthetic", True):
                continue
        result.append((c.get("name", rr.get("id", "?")), rr, c.get("expected_verdict")))
    return result


# ---------------------------------------------------------------------------
# Snapshot builder
# ---------------------------------------------------------------------------

def _build_snapshot(synthetic_only: bool = False) -> dict:
    """Run all fixtures through the gates and build a sorted, stable snapshot."""
    corpus = _all_fixture_rrs(synthetic_only=synthetic_only)

    per_gate: dict[str, dict[str, int]] = {}
    verdict_counts: dict[str, int] = {"ADMISSIBLE": 0, "BLOCKED": 0}
    expected_match = 0
    records = []

    for name, rr, expected in corpus:
        ev = evaluate(rr)
        gate_statuses = ev.status_map()
        verdict = ev.verdict

        # accumulate per-gate counts
        for gid, status in gate_statuses.items():
            if gid not in per_gate:
                per_gate[gid] = {"PASS": 0, "FAIL": 0, "NA": 0}
            per_gate[gid][status] = per_gate[gid].get(status, 0) + 1

        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

        match = (expected is None) or (expected == verdict)
        if match and expected is not None:
            expected_match += 1

        records.append({
            "name": name,
            "rr_id": ev.rr_id,
            "lane": ev.lane,
            "verdict": verdict,
            "expected_verdict": expected,
            "verdict_match": match,
            "gate_statuses": dict(sorted(gate_statuses.items())),
        })

    # Sort records by name for stability
    records.sort(key=lambda r: r["name"])

    n_with_expected = sum(1 for r in records if r["expected_verdict"] is not None)

    snapshot = {
        "corpus_size": len(records),
        "synthetic_only": synthetic_only,
        "verdict_distribution": dict(sorted(verdict_counts.items())),
        "expected_verdict_matches": expected_match,
        "expected_verdict_total": n_with_expected,
        "per_gate_counts": {
            gid: dict(sorted(counts.items()))
            for gid, counts in sorted(per_gate.items())
        },
        "records": records,
    }
    return snapshot


# ---------------------------------------------------------------------------
# Diff helper
# ---------------------------------------------------------------------------

def _snapshot_diff(baseline: dict, current: dict) -> list[str]:
    """Return a list of human-readable drift lines; empty = no drift."""
    diffs = []

    def _cmp(label, a, b):
        if a != b:
            diffs.append(f"  {label}: baseline={a!r}  current={b!r}")

    _cmp("corpus_size", baseline.get("corpus_size"), current.get("corpus_size"))
    _cmp("verdict_distribution", baseline.get("verdict_distribution"), current.get("verdict_distribution"))
    _cmp("expected_verdict_matches", baseline.get("expected_verdict_matches"), current.get("expected_verdict_matches"))
    _cmp("per_gate_counts", baseline.get("per_gate_counts"), current.get("per_gate_counts"))

    # Per-record diff (by name)
    base_by_name = {r["name"]: r for r in (baseline.get("records") or [])}
    curr_by_name = {r["name"]: r for r in (current.get("records") or [])}

    for name in sorted(set(base_by_name) | set(curr_by_name)):
        if name not in base_by_name:
            diffs.append(f"  record added: {name!r}")
        elif name not in curr_by_name:
            diffs.append(f"  record removed: {name!r}")
        else:
            br, cr = base_by_name[name], curr_by_name[name]
            for field in ("verdict", "gate_statuses"):
                if br.get(field) != cr.get(field):
                    diffs.append(
                        f"  {name}.{field}: baseline={br.get(field)!r}  current={cr.get(field)!r}"
                    )
    return diffs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Gate-regression tracker: compare gate snapshot to baseline.",
        prog="gate_regression",
    )
    parser.add_argument(
        "--update", action="store_true",
        help="Overwrite the committed baseline with the current snapshot (exit 0).",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Print the current snapshot as JSON (exit 0, does not compare).",
    )
    parser.add_argument(
        "--synthetic-only", action="store_true",
        help="Restrict the corpus to synthetic-only RRs (deterministic subset).",
    )
    args = parser.parse_args(argv)

    synthetic_only = args.synthetic_only
    snapshot = _build_snapshot(synthetic_only=synthetic_only)

    if args.json:
        print(json.dumps(snapshot, indent=2, ensure_ascii=False))
        return 0

    if args.update:
        os.makedirs(os.path.dirname(_BASELINE_PATH), exist_ok=True)
        with open(_BASELINE_PATH, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"Baseline updated: {_BASELINE_PATH}")
        print(
            f"  corpus_size={snapshot['corpus_size']}  "
            f"admissible={snapshot['verdict_distribution'].get('ADMISSIBLE', 0)}  "
            f"blocked={snapshot['verdict_distribution'].get('BLOCKED', 0)}  "
            f"expected_matches={snapshot['expected_verdict_matches']}/"
            f"{snapshot['expected_verdict_total']}"
        )
        return 0

    # --- compare to baseline ---
    if not os.path.exists(_BASELINE_PATH):
        print(
            f"ERROR: baseline not found at {_BASELINE_PATH}\n"
            "Run with --update to create it.",
            file=sys.stderr,
        )
        return 1

    with open(_BASELINE_PATH, encoding="utf-8") as f:
        baseline = json.load(f)

    diffs = _snapshot_diff(baseline, snapshot)
    if diffs:
        print("DRIFT DETECTED — gate regression baseline does not match current snapshot:")
        for d in diffs:
            print(d)
        print(
            f"\nBaseline: {_BASELINE_PATH}\n"
            "Run with --update to accept the new snapshot as the baseline."
        )
        return 1

    print(
        f"gate_regression: OK  "
        f"(corpus={snapshot['corpus_size']}  "
        f"admissible={snapshot['verdict_distribution'].get('ADMISSIBLE', 0)}  "
        f"blocked={snapshot['verdict_distribution'].get('BLOCKED', 0)}  "
        f"expected_matches={snapshot['expected_verdict_matches']}/"
        f"{snapshot['expected_verdict_total']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
