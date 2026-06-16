"""Evaluation gates G-1..G-6 — pure, deterministic functions over a
Recommendation Record.

No LLM, no network, no data. The judge is independent of the judged
(constitution P-3). See .specify/specs/finance-research-eval/eval-gates.md for
the normative definition of each gate.

Severity model (eval-gates.md): each gate has a per-lane severity.
  BLOCK / REQUIRED -> a failure blocks the verdict (-> BLOCKED).
  FLAG             -> a failure is recorded but does not block (personal lane:
                      the user is the sole judge).
  NA               -> the gate is not evaluated for this lane.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import date

from harness import rr as rrlib
from harness.compute import metrics as M

# Gate statuses
PASS, FAIL, NA = "PASS", "FAIL", "NA"
# Severities
BLOCK, REQUIRED, FLAG, SEV_NA = "BLOCK", "REQUIRED", "FLAG", "NA"
BLOCKING = {BLOCK, REQUIRED}

SEVERITY = {
    "personal-research": {
        "G-1": FLAG, "G-2": REQUIRED, "G-3": FLAG,
        "G-4": REQUIRED, "G-5": SEV_NA, "G-6": REQUIRED,
    },
    "client-mifid": {
        "G-1": BLOCK, "G-2": REQUIRED, "G-3": BLOCK,
        "G-4": BLOCK, "G-5": BLOCK, "G-6": REQUIRED,
    },
}

REQUIRED_LANE_FIELDS = ("reco_nature", "disclaimers", "conflicts_of_interest")
SUITABILITY_FIELDS = (
    "knowledge_experience", "financial_situation", "loss_capacity",
    "objectives_horizon", "risk_tolerance", "suitability_declaration",
)


@dataclass
class GateResult:
    gate_id: str
    status: str            # PASS | FAIL | NA
    severity: str = ""     # filled per-lane during evaluate()
    reason: str = ""


@dataclass
class Evaluation:
    rr_id: str
    lane: str
    gate_results: list
    verdict: str           # ADMISSIBLE | BLOCKED
    augmented_rr: dict     # RR with recomputed_value/agree filled by G-3

    def by_id(self, gid):
        for g in self.gate_results:
            if g.gate_id == gid:
                return g
        return None

    def status_map(self):
        return {g.gate_id: g.status for g in self.gate_results}


def _short(claim):
    return (claim.get("statement", "?") or "?")[:40]


def _all_evidence(rr):
    out = {}
    for c in rr.get("claims", []) or []:
        for ev in c.get("evidence", []) or []:
            if "id" in ev:
                out[ev["id"]] = ev
    return out


def _check_evidence_sourced(ev, problems):
    eid = ev.get("id", "?")
    if not ev.get("source_doc") or not ev.get("locator"):
        problems.append(f"evidence {eid} missing source_doc/locator")
    if not ev.get("as_of"):
        problems.append(f"evidence {eid} missing as_of")


def gate_g1(rr) -> GateResult:
    """Sourcing: every quantitative claim has >=1 sourced evidence; every
    valuation claim's computations reference sourced evidence."""
    problems = []
    evmap = _all_evidence(rr)
    for c in rr.get("claims", []) or []:
        kind = c.get("kind")
        if kind == "quantitative":
            evs = c.get("evidence") or []
            if not evs:
                problems.append(f"quantitative claim '{_short(c)}' has no evidence")
            for ev in evs:
                _check_evidence_sourced(ev, problems)
        elif kind == "valuation":
            comps = c.get("computations") or []
            if not comps:
                problems.append(f"valuation claim '{_short(c)}' has no computations")
            for comp in comps:
                for opname, evid in (comp.get("inputs") or {}).items():
                    ev = evmap.get(evid)
                    if ev is None:
                        problems.append(
                            f"valuation operand {opname} -> unknown evidence {evid}"
                        )
                    else:
                        _check_evidence_sourced(ev, problems)
    return GateResult("G-1", PASS if not problems else FAIL, reason="; ".join(problems))


def gate_g2(rr) -> GateResult:
    """Audit-trail: input_hash present and reproducible (recompute & compare)."""
    at = rr.get("audit_trail") or {}
    declared = at.get("input_hash")
    if not declared:
        return GateResult("G-2", FAIL, reason="no audit_trail.input_hash")
    if not isinstance(at.get("transformations"), list):
        return GateResult("G-2", FAIL, reason="transformations log missing")
    recomputed = rrlib.compute_input_hash(rr)
    if recomputed != declared:
        return GateResult(
            "G-2", FAIL,
            reason="input_hash mismatch (content tampered or not reproducible)",
        )
    return GateResult("G-2", PASS)


def gate_g3(rr) -> GateResult:
    """Independent computation: recompute each metric from sourced evidence and
    compare to the model-proposed value. Mutates ``rr`` to record
    recomputed_value/agree on each computation."""
    problems = []
    evmap = _all_evidence(rr)
    any_comp = False
    for c in rr.get("claims", []) or []:
        for comp in c.get("computations", []) or []:
            any_comp = True
            metric = comp.get("metric")
            operands = {}
            resolve_err = None
            for opname, evid in (comp.get("inputs") or {}).items():
                ev = evmap.get(evid)
                if ev is None:
                    resolve_err = f"input {opname} -> unknown evidence {evid}"
                    break
                val = ev.get("value")
                if not isinstance(val, (int, float)) or isinstance(val, bool):
                    resolve_err = f"evidence {evid} value is not numeric"
                    break
                operands[opname] = float(val)
            if resolve_err:
                comp["recomputed_value"] = None
                comp["agree"] = False
                problems.append(f"{metric}: {resolve_err}")
                continue
            try:
                rv = M.recompute(metric, operands)
            except M.ComputeError as exc:
                comp["recomputed_value"] = None
                comp["agree"] = False
                problems.append(str(exc))
                continue
            comp["recomputed_value"] = rv
            llm_val = comp.get("llm_value")
            ok = isinstance(llm_val, (int, float)) and not isinstance(llm_val, bool) \
                and M.values_agree(float(llm_val), rv)
            comp["agree"] = bool(ok)
            if not ok:
                problems.append(
                    f"{metric}: model={llm_val} vs recomputed={round(rv, 6)}"
                )
    if not any_comp:
        return GateResult("G-3", PASS, reason="no computations to verify")
    return GateResult("G-3", PASS if not problems else FAIL, reason="; ".join(problems))


def _parse_date(s):
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def gate_g4(rr) -> GateResult:
    """Point-in-time: cutoff present; every evidence.as_of present and <= cutoff."""
    cutoff_s = rr.get("information_cutoff")
    cutoff = _parse_date(cutoff_s) if cutoff_s else None
    if cutoff is None:
        return GateResult(
            "G-4", FAIL, reason=f"missing/invalid information_cutoff: {cutoff_s!r}"
        )
    problems = []
    for ev in _all_evidence(rr).values():
        a = ev.get("as_of")
        d = _parse_date(a) if a else None
        if d is None:
            problems.append(f"evidence {ev.get('id', '?')} missing/invalid as_of")
        elif d > cutoff:
            problems.append(
                f"evidence {ev.get('id', '?')} as_of {a} > cutoff {cutoff_s} (look-ahead)"
            )
    return GateResult("G-4", PASS if not problems else FAIL, reason="; ".join(problems))


def gate_g5(rr, g1, g3) -> GateResult:
    """Client-block: in client-mifid, a record failing G-1 or G-3 is BLOCKED,
    never emitted. N/A for personal-research."""
    if rr.get("lane") != "client-mifid":
        return GateResult("G-5", NA, reason="not a client-mifid record")
    if g1.status == FAIL or g3.status == FAIL:
        return GateResult(
            "G-5", FAIL,
            reason="client record fails sourcing/verification -> blocked, not degraded",
        )
    return GateResult("G-5", PASS)


def gate_g6(rr) -> GateResult:
    """Cloisonnement: lane declared; client-mifid requires lane_fields; no
    promotion without re-evaluation."""
    lane = rr.get("lane")
    if lane not in rrlib.LANES:
        return GateResult("G-6", FAIL, reason=f"invalid/undeclared lane: {lane!r}")
    # Non-promotion: a stale evaluation recorded under a different lane.
    prior = (rr.get("gate_results") or {}).get("evaluated_lane")
    if prior and prior != lane:
        return GateResult(
            "G-6", FAIL,
            reason=f"promotion without re-evaluation: prior lane {prior} != {lane}",
        )
    if lane == "client-mifid":
        lf = rr.get("lane_fields") or {}
        missing = [f for f in REQUIRED_LANE_FIELDS if not lf.get(f)]
        if missing:
            return GateResult(
                "G-6", FAIL, reason=f"client-mifid missing lane_fields: {missing}"
            )
        if lf.get("reco_nature") == "personalised-advice":
            suit = lf.get("suitability") or {}
            smiss = [f for f in SUITABILITY_FIELDS if not suit.get(f)]
            if smiss:
                return GateResult(
                    "G-6", FAIL,
                    reason=f"personalised-advice missing suitability: {smiss}",
                )
    return GateResult("G-6", PASS)


def evaluate(rr_in: dict) -> Evaluation:
    """Run all gates over a copy of ``rr_in`` and return an Evaluation.

    The verdict is BLOCKED iff any gate whose per-lane severity is blocking
    (BLOCK or REQUIRED) failed; otherwise ADMISSIBLE. FLAG failures are recorded
    but do not block.
    """
    rr = copy.deepcopy(rr_in)
    lane = rr.get("lane")

    g1 = gate_g1(rr)
    g2 = gate_g2(rr)
    g3 = gate_g3(rr)          # mutates rr (recompute fields)
    g4 = gate_g4(rr)
    g5 = gate_g5(rr, g1, g3)
    g6 = gate_g6(rr)
    results = [g1, g2, g3, g4, g5, g6]

    sev_map = SEVERITY.get(lane, SEVERITY["client-mifid"])
    for g in results:
        g.severity = sev_map.get(g.gate_id, REQUIRED)

    blocked = any(g.status == FAIL and g.severity in BLOCKING for g in results)
    verdict = "BLOCKED" if blocked else "ADMISSIBLE"

    rr["gate_results"] = {"evaluated_lane": lane, "verdict": verdict}
    rr["verdict"] = verdict
    return Evaluation(rr.get("id", "?"), lane, results, verdict, rr)
