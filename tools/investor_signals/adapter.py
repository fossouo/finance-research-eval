"""Investor-decision corpus -> Recommendation Record adapter.

Converts an investor-signals corpus record (a historical investment decision
with sourced rationale + dated market signals) into a Recommendation Record and
runs it through the deterministic gates.

Why this matters: the point-in-time gate (G-4) is the meaningful axis for this
corpus. A historical decision is *recevable* only if its rationale is anchored
to evidence dated at-or-before the decision (``information_cutoff``). Folding the
*outcome* — known only with hindsight — into the decision rationale is a
look-ahead violation the gate catches and BLOCKS (G-4 is REQUIRED on the
personal-research lane). That is exactly the framework's thesis applied to
historical investor data: "juste mais irrecevable" if not properly dated.

The real corpus lives under ``datasets/investor-signals/`` (gitignored, per the
open-core contract). This module also ships fully-synthetic fixtures so its
behaviour is testable in the public core with zero real data.

Pure stdlib. No network, no model, no GPU.

CLI:
    python3 -m tools.investor_signals.adapter <decisions.jsonl> [--with-outcome]
    python3 -m tools.investor_signals.adapter --synthetic
"""
from __future__ import annotations

import json
import re
import sys

from harness import rr as rrlib
from harness.gates.gates import evaluate

_YEAR = re.compile(r"(1[89]\d{2}|20\d{2})")


def _years(period: str) -> list:
    return [int(y) for y in _YEAR.findall(period or "")]


def _date_bounds(period: str):
    """Return (as_of, cutoff) ISO dates derived from a free-text period.

    as_of  = Jan 1 of the earliest year mentioned (decision-time anchor)
    cutoff = Dec 31 of the latest year mentioned (information cutoff)
    """
    ys = _years(period)
    if not ys:
        return None, None
    return f"{min(ys)}-01-01", f"{max(ys)}-12-31"


def _coerce_iso(s: str) -> str:
    """Coerce 'YYYY', 'YYYY-MM' or 'YYYY-MM-DD' to a full ISO date string."""
    s = (s or "").strip()
    if re.fullmatch(r"\d{4}", s):
        return f"{s}-12-31"
    if re.fullmatch(r"\d{4}-\d{2}", s):
        return f"{s}-01"
    return s  # assume already YYYY-MM-DD (or invalid, which G-4 will flag)


def record_to_rr(rec: dict, lane: str = "personal-research",
                 include_outcome: bool = False) -> dict:
    """Convert one corpus record into a stamped Recommendation Record dict."""
    as_of, cutoff = _date_bounds(rec.get("period", ""))
    rid = rec.get("id", "REC")
    sources = rec.get("rationale_sources") or ["unsourced"]
    end_year = max(_years(rec.get("period", "")) or [0])
    claims = []

    for i, bullet in enumerate(rec.get("stated_rationale") or []):
        claims.append({
            "statement": str(bullet),
            "kind": "qualitative",
            "evidence": [{
                "id": f"{rid}-rat-{i}",
                "figure": "stated_rationale",
                "value": end_year,
                "source_doc": sources[0],
                "locator": sources[0],
                "as_of": as_of,
            }],
        })

    for i, sig in enumerate(rec.get("market_signals") or []):
        claims.append({
            "statement": f"[{sig.get('type')}] {sig.get('signal')}",
            "kind": "qualitative",
            "evidence": [{
                "id": f"{rid}-sig-{i}",
                "figure": str(sig.get("type", "signal")),
                "value": 1,
                "source_doc": "market-signal",
                "locator": (str(sig.get("evidence") or "market observation"))[:200],
                "as_of": as_of,
            }],
        })

    if include_outcome and rec.get("outcome"):
        # Intentionally NOT recevable: the outcome is hindsight. Dating it at the
        # corpus 'known as of' (post-decision) makes G-4 catch the look-ahead.
        claims.append({
            "statement": f"OUTCOME (hindsight): {str(rec.get('outcome'))[:200]}",
            "kind": "qualitative",
            "evidence": [{
                "id": f"{rid}-outcome",
                "figure": "outcome",
                "value": 1,
                "source_doc": "hindsight",
                "locator": str(rec.get("outcome_known_as_of") or "2026-06"),
                "as_of": _coerce_iso(rec.get("outcome_known_as_of") or "2026-06"),
            }],
        })

    rr = {
        "id": rid,
        "lane": lane,
        "subject": rec.get("company", rid),
        "information_cutoff": cutoff or "1900-01-01",
        "claims": claims,
    }
    return rrlib.stamp_audit_trail(rr)


def evaluate_corpus(records: list, lane: str = "personal-research",
                    include_outcome: bool = False) -> dict:
    """Build RRs for every record, run the gates, return a JSON-able report."""
    report = {"summary": {"total": 0, "admissible": 0, "blocked": 0,
                          "structurally_invalid": 0}, "records": []}
    for rec in records:
        rr = record_to_rr(rec, lane=lane, include_outcome=include_outcome)
        struct = rrlib.validate_structure(rr)
        ev = evaluate(rr)
        report["records"].append({
            "id": ev.rr_id,
            "subject": rr.get("subject"),
            "information_cutoff": rr.get("information_cutoff"),
            "verdict": ev.verdict,
            "gates": ev.status_map(),
            "structural_errors": struct,
            "source_confidence": rec.get("confidence"),
            "validation_flags": rec.get("validation_flags"),
        })
        report["summary"]["total"] += 1
        if struct:
            report["summary"]["structurally_invalid"] += 1
        if ev.verdict == "ADMISSIBLE":
            report["summary"]["admissible"] += 1
        else:
            report["summary"]["blocked"] += 1
    return report


def _load_jsonl(path: str) -> list:
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    include_outcome = "--with-outcome" in argv
    argv = [a for a in argv if a != "--with-outcome"]
    if "--synthetic" in argv or not argv:
        from tools.investor_signals.fixtures_synthetic import synthetic_records
        records = synthetic_records()
    else:
        records = _load_jsonl(argv[0])
    report = evaluate_corpus(records, include_outcome=include_outcome)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
