"""Local runner — synthetic fixtures -> deterministic gates -> local report.

Pure stdlib. No data, no network, no model, no GPU. This IS the dry proof of
recevability: a Recommendation Record (synthetic) flows through the gates and
produces a local report.

Run:  python3 -m harness.runner
"""
from __future__ import annotations

import json
import os

from harness.gates.gates import evaluate
from harness.fixtures.cases import all_cases


def run(cases=None):
    cases = cases if cases is not None else all_cases()
    report = {"records": [], "summary": {"total": 0, "admissible": 0, "blocked": 0,
                                         "mismatches": 0}}
    for case in cases:
        ev = evaluate(case["rr"])
        expected = case.get("expected_verdict")
        rec = {
            "name": case.get("name"),
            "id": ev.rr_id,
            "lane": ev.lane,
            "verdict": ev.verdict,
            "expected_verdict": expected,
            "gates": [
                {"gate": g.gate_id, "status": g.status,
                 "severity": g.severity, "reason": g.reason}
                for g in ev.gate_results
            ],
        }
        report["records"].append(rec)
        report["summary"]["total"] += 1
        if ev.verdict == "ADMISSIBLE":
            report["summary"]["admissible"] += 1
        else:
            report["summary"]["blocked"] += 1
        if expected and expected != ev.verdict:
            report["summary"]["mismatches"] += 1
    return report


def format_text(report) -> str:
    mark = {"PASS": "ok ", "FAIL": "XX ", "NA": " - "}
    lines = [
        "finance-research-eval — recevability harness — local report",
        "(synthetic data only — no model, no network, no real data)",
        "=" * 64,
    ]
    for rec in report["records"]:
        exp = rec.get("expected_verdict")
        flag = f"   !! expected {exp}" if exp and exp != rec["verdict"] else ""
        lines.append(f"\n[{rec['id']}]  {rec['name']}")
        lines.append(f"   lane={rec['lane']}  ->  {rec['verdict']}{flag}")
        for g in rec["gates"]:
            reason = f"   ({g['reason']})" if g["reason"] else ""
            lines.append(f"     {mark[g['status']]}{g['gate']} [{g['severity']}]{reason}")
    s = report["summary"]
    lines.append("\n" + "-" * 64)
    lines.append(
        f"total={s['total']}  admissible={s['admissible']}  "
        f"blocked={s['blocked']}  verdict_mismatches={s['mismatches']}"
    )
    return "\n".join(lines)


def main():
    report = run()
    print(format_text(report))
    os.makedirs("runs", exist_ok=True)  # gitignored
    out = os.path.join("runs", "p1_dry_report.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nJSON report written to {out}")
    return report


if __name__ == "__main__":
    main()
