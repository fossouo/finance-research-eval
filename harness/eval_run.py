"""End-to-end run: EvalItem -> candidate -> Recommendation Record -> gates
-> report (recevability AND accuracy).

This closes the loop. A candidate (mock or a real model via http_openai) turns
each EvalItem into an RR; the gates judge recevability; we also score the answer
against the gold. By design the two scores are reported separately —
recevability primes (a correct-but-unsourced answer is still BLOCKED).

Offline demo (0 VRAM, 0 network):  python3 -m harness.eval_run
"""
from __future__ import annotations

import math

from harness.gates.gates import evaluate
from harness.sources import loaders, registry


def score_answer(answer, gold, kind, rel_tol=0.01):
    if answer is None or answer == "":
        return False
    if kind == "numeric":
        try:
            return math.isclose(float(answer), float(gold), rel_tol=rel_tol, abs_tol=1e-9)
        except (TypeError, ValueError):
            return False
    a = str(answer).strip().lower()
    g = str(gold).strip().lower()
    return bool(a) and (a == g or g in a or a in g)


def run(candidate, items, lane="personal-research"):
    report = {"candidate": getattr(candidate, "name", "?"), "lane": lane,
              "records": [], "summary": {"total": 0, "admissible": 0, "blocked": 0,
                                         "correct": 0, "errors": 0}}
    for it in items:
        try:
            rr = candidate.produce_rr(it, lane)
        except Exception as exc:  # a dead/garbled candidate must not crash the run
            report["records"].append({"item": it.item_id, "error": str(exc)[:160]})
            report["summary"]["total"] += 1
            report["summary"]["errors"] += 1
            continue
        ev = evaluate(rr)
        ans = (rr.get("meta") or {}).get("answer")
        correct = score_answer(ans, it.gold_answer, it.gold_kind)
        report["records"].append({
            "item": it.item_id,
            "verdict": ev.verdict,
            "correct": correct,
            "answer": ans,
            "gold": it.gold_answer,
            "gates": {g.gate_id: g.status for g in ev.gate_results},
        })
        s = report["summary"]
        s["total"] += 1
        s["admissible" if ev.verdict == "ADMISSIBLE" else "blocked"] += 1
        if correct:
            s["correct"] += 1
    return report


def format_text(report):
    s = report["summary"]
    lines = [f"candidate={report['candidate']}  lane={report['lane']}",
             "-" * 60]
    for r in report["records"]:
        if "error" in r:
            lines.append(f"  {r['item']:<28} ERROR: {r['error']}")
            continue
        mark = "OK " if r["verdict"] == "ADMISSIBLE" else "XX "
        acc = "correct" if r["correct"] else "wrong  "
        failed = [g for g, st in r["gates"].items() if st == "FAIL"]
        why = f" fail={','.join(failed)}" if failed else ""
        lines.append(f"  {mark}{r['item']:<28} {r['verdict']:<11} {acc}{why}")
    lines.append("-" * 60)
    lines.append(f"  total={s['total']} admissible={s['admissible']} "
                 f"blocked={s['blocked']} correct={s['correct']} errors={s['errors']}")
    return "\n".join(lines)


def _all_synthetic_items():
    items = []
    for sid in registry.list_sources():
        if registry.get(sid).loader:
            items.extend(loaders.load_sample(sid))
    return items


def main():
    from harness.candidates.mock import FaithfulMockCandidate, SloppyMockCandidate
    items = _all_synthetic_items()
    print("finance-research-eval — end-to-end (offline, mock candidates, 0 VRAM)")
    print("=" * 64)
    for cand in (FaithfulMockCandidate(), SloppyMockCandidate()):
        for lane in ("personal-research", "client-mifid"):
            rep = run(cand, items, lane)
            print()
            print(format_text(rep))


if __name__ == "__main__":
    main()
