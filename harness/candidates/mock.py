"""Deterministic mock candidates — 0 VRAM, 0 network. Used to prove the
end-to-end pipeline (EvalItem -> candidate -> RR -> gates) offline.

Two contrasting candidates make the harness's value visible:
  - FaithfulMock: sources its answer to the provided context and dates it ->
    admissible AND accurate.
  - SloppyMock: states the (even correct) answer with NO evidence -> flagged on
    personal, BLOCKED on client. "Right but inadmissible."
"""
from __future__ import annotations

from harness.candidates.base import Candidate, assemble_rr, DEFAULT_CUTOFF, _is_number


def _evidence_from_context(eval_item, cutoff):
    """Turn an EvalItem's context snippets into sourced evidence. The value is
    the gold answer when numeric (a faithful extractor reports the sourced
    number); otherwise the snippet is carried as a textual datum."""
    numeric = _is_number(eval_item.gold_answer)
    out = []
    for i, ctx in enumerate(eval_item.context or []):
        out.append({
            "id": f"ev-{i}",
            "figure": eval_item.question[:60],
            "value": float(eval_item.gold_answer) if numeric else 0.0,
            "unit": "",
            "source_doc": ctx.source_doc or eval_item.source,
            "locator": ctx.locator or "context",
            "as_of": ctx.as_of or cutoff,
        })
    if not out:
        # no context -> a single self-dated evidence pointing at the source
        out.append({
            "id": "ev-0",
            "figure": eval_item.question[:60],
            "value": float(eval_item.gold_answer) if numeric else 0.0,
            "unit": "", "source_doc": eval_item.source,
            "locator": "source", "as_of": cutoff,
        })
    return out


class FaithfulMockCandidate(Candidate):
    name = "faithful-mock"

    def produce_rr(self, eval_item, lane="personal-research"):
        cutoff = DEFAULT_CUTOFF
        ev = _evidence_from_context(eval_item, cutoff)
        lane_fields = None
        if lane == "client-mifid":
            lane_fields = {
                "reco_nature": "general-research",
                "disclaimers": ["not a guarantee of performance", "synthetic demo"],
                "conflicts_of_interest": "none (synthetic)",
            }
        return assemble_rr(eval_item, lane, eval_item.gold_answer, ev,
                           cutoff=cutoff, lane_fields=lane_fields)


class SloppyMockCandidate(Candidate):
    """Reports the same answer but cites NO evidence — to show that a correct
    answer is still inadmissible if it can't be sourced (gate G-1)."""
    name = "sloppy-mock"

    def produce_rr(self, eval_item, lane="personal-research"):
        lane_fields = None
        if lane == "client-mifid":
            lane_fields = {
                "reco_nature": "general-research",
                "disclaimers": ["synthetic demo"],
                "conflicts_of_interest": "none (synthetic)",
            }
        return assemble_rr(eval_item, lane, eval_item.gold_answer, [],
                           lane_fields=lane_fields)
