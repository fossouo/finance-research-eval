"""Batch runner + human-readable report generator.

Runs one or more candidates over one or more EvalItem sets (across lanes) and
produces:
  - an aggregated ``BatchReport`` dict (the authoritative, machine-readable form)
  - a Markdown summary (``format_markdown``) — tables, per-gate pass rates, key
    findings — suitable for an analyst review note or a GitHub README section
  - a flat CSV export (``format_csv``) — one row per (candidate, lane, item)

Design principles (mirrors the harness):
  - Pure stdlib. No network. Deterministic. No real data.
  - ``format_markdown`` / ``format_csv`` are pure functions over the report dict;
    they can be called independently.
  - The batch runner is a thin loop over ``harness.eval_run.run``; it adds no new
    evaluation logic.

Offline demo (0 VRAM, 0 network):  python3 -m harness.report
"""
from __future__ import annotations

import csv
import io
import zlib

from harness import eval_run


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

def batch_run(
    candidates: list,
    items_by_label: dict,
    lanes: tuple = ("personal-research", "client-mifid"),
) -> dict:
    """Run every (candidate, lane) pair over every labelled item set.

    Args:
        candidates: list of candidate objects (must have a ``.name`` attribute
            and a ``produce_rr(item, lane)`` method — the candidate contract).
        items_by_label: ``{label: [EvalItem, ...]}`` — e.g.
            ``{"financebench": items_fb, "finqa": items_fq}``.
            The labels are cosmetic; they appear in the report.
        lanes: which lanes to evaluate on (default: both).

    Returns a ``BatchReport`` dict:
    {
        "candidates": [<name>, ...],
        "item_sets": [<label>, ...],
        "lanes": [<lane>, ...],
        "runs": [
            {
                "candidate": <name>,
                "lane": <lane>,
                "item_set": <label>,
                "summary": {total, admissible, blocked, correct, errors},
                "records": [...],
                "run_id": <crc32 fingerprint of (candidate+lane+label)>,
            },
            ...
        ],
        "aggregate": {
            "total_runs": int,
            "grand_total": int,
            "grand_admissible": int,
            "grand_blocked": int,
            "grand_correct": int,
            "grand_errors": int,
            "admissibility_rate": float,
            "accuracy_rate": float,       # among admissible records
            "gate_stats": {<gate_id>: {"pass": int, "fail": int, "na": int}},
        },
    }
    """
    report: dict = {
        "candidates": [getattr(c, "name", str(c)) for c in candidates],
        "item_sets": list(items_by_label.keys()),
        "lanes": list(lanes),
        "runs": [],
    }

    # Gate counters: accumulate over all runs for the aggregate gate stats.
    gate_stats: dict[str, dict[str, int]] = {}

    grand = {"total": 0, "admissible": 0, "blocked": 0, "correct": 0, "errors": 0}

    for cand in candidates:
        for lane in lanes:
            for label, items in items_by_label.items():
                run_result = eval_run.run(cand, items, lane)
                # deterministic run_id: stable across identical inputs
                fingerprint = f"{getattr(cand, 'name', '?')}|{lane}|{label}"
                run_id = format(
                    zlib.crc32(fingerprint.encode("utf-8")) & 0xFFFFFFFF, "08x"
                )
                entry = {
                    "candidate": getattr(cand, "name", str(cand)),
                    "lane": lane,
                    "item_set": label,
                    "summary": run_result["summary"],
                    "records": run_result["records"],
                    "run_id": run_id,
                }
                report["runs"].append(entry)

                # Accumulate gate stats from this run's records.
                for rec in run_result["records"]:
                    gates = rec.get("gates") or {}
                    for gid, status in gates.items():
                        if gid not in gate_stats:
                            gate_stats[gid] = {"pass": 0, "fail": 0, "na": 0}
                        gate_stats[gid][status.lower()] = (
                            gate_stats[gid].get(status.lower(), 0) + 1
                        )

                # Accumulate grand totals.
                s = run_result["summary"]
                for k in ("total", "admissible", "blocked", "correct", "errors"):
                    grand[k] += s[k]

    total = grand["total"]
    admissible = grand["admissible"]
    report["aggregate"] = {
        "total_runs": len(report["runs"]),
        "grand_total": total,
        "grand_admissible": admissible,
        "grand_blocked": grand["blocked"],
        "grand_correct": grand["correct"],
        "grand_errors": grand["errors"],
        "admissibility_rate": round(admissible / total, 4) if total else 0.0,
        # accuracy_rate = fraction of ALL records (incl. blocked) whose answer was
        # correct.  Dividing only by admissible would mislead: a sloppy candidate
        # that is 100 % correct but 100 % blocked would show ∞.  Dividing by
        # total gives the end-to-end signal: "did the model know the right answer?"
        "accuracy_rate": round(grand["correct"] / total, 4) if total else 0.0,
        "gate_stats": gate_stats,
    }
    return report


# ---------------------------------------------------------------------------
# Markdown formatter
# ---------------------------------------------------------------------------

def format_markdown(report: dict) -> str:
    """Render a ``BatchReport`` as a human-readable Markdown document.

    The output is safe for pasting into a review note, a GitHub wiki page, or a
    MARBO session summary.  No real data — only the synthetic harness results.
    """
    agg = report.get("aggregate", {})
    runs = report.get("runs", [])
    candidates = report.get("candidates", [])
    item_sets = report.get("item_sets", [])
    lanes = report.get("lanes", [])

    lines = [
        "# finance-research-eval — Batch Report",
        "",
        "> Synthetic data only — 0 VRAM, 0 network, 0 real data.  "
        "All numbers come from offline mock candidates.",
        "",
        "## Overview",
        "",
        f"| Parameter | Value |",
        f"|---|---|",
        f"| Candidates | {', '.join(f'`{c}`' for c in candidates)} |",
        f"| Item sets | {', '.join(f'`{s}`' for s in item_sets)} |",
        f"| Lanes | {', '.join(f'`{l}`' for l in lanes)} |",
        f"| Total runs | {agg.get('total_runs', 0)} |",
        f"| Grand total items evaluated | {agg.get('grand_total', 0)} |",
        "",
        "## Aggregate results",
        "",
        "| Metric | Count | Rate |",
        "|---|---|---|",
        f"| Admissible | {agg.get('grand_admissible', 0)} "
        f"| {agg.get('admissibility_rate', 0):.1%} |",
        f"| Blocked | {agg.get('grand_blocked', 0)} | — |",
        f"| Correct (any verdict) | {agg.get('grand_correct', 0)} "
        f"| {agg.get('accuracy_rate', 0):.1%} |",
        f"| Errors | {agg.get('grand_errors', 0)} | — |",
        "",
    ]

    # Per-run table
    lines += [
        "## Per-run breakdown",
        "",
        "| run_id | Candidate | Lane | Item set | Total | Admiss. | Blocked | Correct | Errors |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for run in runs:
        s = run["summary"]
        lines.append(
            f"| `{run['run_id']}` "
            f"| `{run['candidate']}` "
            f"| `{run['lane']}` "
            f"| `{run['item_set']}` "
            f"| {s['total']} "
            f"| {s['admissible']} "
            f"| {s['blocked']} "
            f"| {s['correct']} "
            f"| {s['errors']} |"
        )
    lines.append("")

    # Gate pass-rate table
    gate_stats = agg.get("gate_stats", {})
    if gate_stats:
        lines += [
            "## Gate statistics (across all runs)",
            "",
            "| Gate | PASS | FAIL | NA | PASS rate |",
            "|---|---|---|---|---|",
        ]
        for gid in sorted(gate_stats.keys()):
            gs = gate_stats[gid]
            p = gs.get("pass", 0)
            f = gs.get("fail", 0)
            n = gs.get("na", 0)
            evaluated = p + f  # NA is not evaluated
            rate = f"{p / evaluated:.1%}" if evaluated else "—"
            lines.append(f"| {gid} | {p} | {f} | {n} | {rate} |")
        lines.append("")

    # Key findings (auto-generated from data)
    lines += ["## Key findings", ""]
    adm_rate = agg.get("admissibility_rate", 0.0)
    acc_rate = agg.get("accuracy_rate", 0.0)
    if adm_rate == 1.0:
        lines.append(
            "- All records were **ADMISSIBLE**: every answer is sourced, "
            "dated, and passes the verifier."
        )
    elif adm_rate == 0.0:
        lines.append(
            "- **No** records were admissible: the candidates could not "
            "satisfy the recevability gates."
        )
    else:
        pct = f"{adm_rate:.0%}"
        lines.append(
            f"- **{pct}** of records were admissible "
            f"({agg.get('grand_admissible', 0)} / {agg.get('grand_total', 0)})."
        )

    if acc_rate == 1.0:
        lines.append(
            "- **Accuracy is 100 %** across all records: candidates always "
            "report the sourced gold answer (even if inadmissible)."
        )
    elif acc_rate > 0:
        lines.append(
            f"- Overall answer accuracy (all verdicts): **{acc_rate:.0%}**."
        )

    # Highlight gates with failures
    failing_gates = [
        gid for gid, gs in gate_stats.items()
        if gs.get("fail", 0) > 0
    ]
    if failing_gates:
        lines.append(
            f"- Gates with at least one failure: "
            + ", ".join(f"**{g}**" for g in sorted(failing_gates))
            + "."
        )

    # Lane insight
    personal_runs = [r for r in runs if r["lane"] == "personal-research"]
    client_runs = [r for r in runs if r["lane"] == "client-mifid"]
    if personal_runs and client_runs:
        p_blocked = sum(r["summary"]["blocked"] for r in personal_runs)
        c_blocked = sum(r["summary"]["blocked"] for r in client_runs)
        if c_blocked > p_blocked:
            lines.append(
                "- The **client-mifid** lane is stricter: more records are "
                f"blocked ({c_blocked}) than on the personal lane ({p_blocked})."
                " This confirms the severity hierarchy (FLAG vs BLOCK)."
            )

    lines += [
        "",
        "---",
        "",
        "> *Report generated by `harness.report.format_markdown`.*  "
        "> *No real financial data. No real company. For evaluation use only.*",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CSV exporter
# ---------------------------------------------------------------------------

# Fixed gate order for CSV column stability across runs.
_GATE_ORDER = ("G-1", "G-2", "G-3", "G-4", "G-5", "G-6")


def format_csv(report: dict) -> str:
    """Return a flat CSV string — one row per evaluated record.

    Columns:
        run_id, candidate, lane, item_set,
        item, verdict, correct, answer, gold,
        G-1, G-2, G-3, G-4, G-5, G-6
    """
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    header = [
        "run_id", "candidate", "lane", "item_set",
        "item", "verdict", "correct", "answer", "gold",
    ] + list(_GATE_ORDER)
    writer.writerow(header)
    for run in report.get("runs", []):
        meta = {
            "run_id": run["run_id"],
            "candidate": run["candidate"],
            "lane": run["lane"],
            "item_set": run["item_set"],
        }
        for rec in run.get("records", []):
            if "error" in rec:
                gates_vals = ["ERROR"] * len(_GATE_ORDER)
                row = [
                    meta["run_id"], meta["candidate"], meta["lane"],
                    meta["item_set"], rec.get("item", "?"),
                    "ERROR", "", "", "",
                ] + gates_vals
            else:
                gates = rec.get("gates") or {}
                gates_vals = [gates.get(g, "") for g in _GATE_ORDER]
                row = [
                    meta["run_id"], meta["candidate"], meta["lane"],
                    meta["item_set"], rec.get("item", "?"),
                    rec.get("verdict", ""), "1" if rec.get("correct") else "0",
                    rec.get("answer", ""), rec.get("gold", ""),
                ] + gates_vals
            writer.writerow(row)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Offline demo entry-point
# ---------------------------------------------------------------------------

def main():
    """Demo: batch-run both mock candidates over synthetic samples, print report."""
    from harness.candidates.mock import FaithfulMockCandidate, SloppyMockCandidate
    from harness.sources import loaders, registry

    items_by_label: dict = {}
    for sid in registry.list_sources():
        if registry.get(sid).loader and registry.get(sid).sample:
            items_by_label[sid] = loaders.load_sample(sid)

    candidates = [FaithfulMockCandidate(), SloppyMockCandidate()]
    rep = batch_run(candidates, items_by_label)
    print(format_markdown(rep))
    print()
    print("# --- CSV preview (first 5 lines) ---")
    csv_text = format_csv(rep)
    for line in csv_text.splitlines()[:6]:
        print(line)


if __name__ == "__main__":
    main()
