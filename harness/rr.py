"""Recommendation Record (RR) helpers — canonical hashing + lightweight
structural validation.

Pure stdlib. In P1 we do NOT pull a third-party JSON-Schema validator; the JSON
Schema under ``harness/schema/`` is the machine-readable standard, and this
module is the dependency-free dry-harness validator. A full ``jsonschema`` check
is wired at the Opening/CI phase, not in the local dry harness.
"""
from __future__ import annotations

import copy
import hashlib
import json

LANES = ("personal-research", "client-mifid")
CLAIM_KINDS = ("qualitative", "quantitative", "valuation")

# Fields added by the harness; excluded from the candidate-content hash so the
# declared input hash is stable regardless of harness augmentation.
_HARNESS_FIELDS = ("audit_trail", "gate_results", "verdict")
_HARNESS_COMPUTATION_FIELDS = ("recomputed_value", "agree")


def canonical_content(rr: dict) -> dict:
    """Return the candidate-provided content of an RR, stripped of any
    harness-added fields, for hashing (gate G-2)."""
    c = copy.deepcopy(rr)
    for f in _HARNESS_FIELDS:
        c.pop(f, None)
    for claim in c.get("claims", []) or []:
        for comp in claim.get("computations", []) or []:
            for f in _HARNESS_COMPUTATION_FIELDS:
                comp.pop(f, None)
    return c


def compute_input_hash(rr: dict) -> str:
    """Deterministic sha256 over the canonical candidate content."""
    content = canonical_content(rr)
    blob = json.dumps(
        content, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def stamp_audit_trail(rr: dict, transformations=None) -> dict:
    """Return a copy of ``rr`` with a reproducible audit_trail attached."""
    rr = copy.deepcopy(rr)
    # remove any pre-existing trail so the hash is over content only
    rr.pop("audit_trail", None)
    rr["audit_trail"] = {
        "input_hash": compute_input_hash(rr),
        "transformations": list(transformations or ["extracted", "computed"]),
    }
    return rr


def validate_structure(rr: dict) -> list:
    """Lightweight structural validation. Returns a list of error strings
    (empty == structurally valid). Not a substitute for the JSON Schema."""
    errors = []
    if not isinstance(rr, dict):
        return ["RR is not an object"]
    for field in ("id", "lane", "subject", "information_cutoff", "claims"):
        if field not in rr:
            errors.append(f"missing field: {field}")
    if rr.get("lane") not in LANES:
        errors.append(f"invalid lane: {rr.get('lane')!r}")
    claims = rr.get("claims", [])
    if not isinstance(claims, list):
        errors.append("claims must be a list")
        claims = []
    for i, claim in enumerate(claims):
        if claim.get("kind") not in CLAIM_KINDS:
            errors.append(f"claim[{i}] invalid kind: {claim.get('kind')!r}")
        for j, ev in enumerate(claim.get("evidence", []) or []):
            if "id" not in ev:
                errors.append(f"claim[{i}].evidence[{j}] missing id")
    return errors
