"""Candidate interface + the EvalItem -> Recommendation Record assembly that all
candidates share.

A candidate supplies an *answer* and *evidence* for an EvalItem; this module
assembles them into a well-formed RR (so candidates don't each re-implement the
RR shape) and the candidate decides only the content.
"""
from __future__ import annotations

from harness import rr as rrlib

DEFAULT_CUTOFF = "2025-12-31"


class Candidate:
    name = "base"

    def produce_rr(self, eval_item, lane: str = "personal-research") -> dict:
        raise NotImplementedError


def _is_number(x):
    try:
        float(x)
        return True
    except (TypeError, ValueError):
        return False


def assemble_rr(eval_item, lane, answer, evidence, *, cutoff=DEFAULT_CUTOFF,
                computations=None, lane_fields=None, stamp=True) -> dict:
    """Build an RR from a candidate's (answer, evidence). evidence is a list of
    dicts {figure, value, source_doc, locator, as_of}. If answer is numeric the
    primary claim is 'valuation'/'quantitative', else 'qualitative'."""
    numeric = _is_number(answer)
    claims = []
    if evidence:
        claims.append({
            "statement": f"Answer to: {eval_item.question}",
            "kind": "quantitative" if numeric else "qualitative",
            "evidence": evidence,
            "computations": computations or [],
        })
    else:
        # no evidence at all -> a (sloppy) claim that G-1 will flag/block
        claims.append({
            "statement": f"Answer to: {eval_item.question} = {answer}",
            "kind": "quantitative" if numeric else "qualitative",
            "evidence": [],
            "computations": computations or [],
        })
    rr = {
        "id": f"rr-{eval_item.source}-{eval_item.item_id}",
        "lane": lane,
        "subject": eval_item.meta.get("doc_name") or eval_item.source,
        "information_cutoff": cutoff,
        "claims": claims,
        "meta": {"answer": answer, "eval_source": eval_item.source,
                 "gold": eval_item.gold_answer, "gold_kind": eval_item.gold_kind},
    }
    if lane_fields is not None:
        rr["lane_fields"] = lane_fields
    if stamp:
        # meta is already set above and is part of the hashed content
        rr = rrlib.stamp_audit_trail(rr)
    return rr
