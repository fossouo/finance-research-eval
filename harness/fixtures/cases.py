"""The synthetic conformity catalogue.

One admissible baseline per lane, then one fixture per gate failure mode. This
is the locked expectation table — the financial analogue of a deterministic-verifier
conformity suite: each gate must PASS/FAIL exactly as specified, and the lane
severity must turn a personal FLAG into an admissible-but-flagged record while a
client BLOCK refuses it outright.
"""
from __future__ import annotations

import copy

from harness.fixtures import synthetic as S

SUBJECT = "ACME SA (synthetic)"
CUTOFF = "2025-03-31"


def _unsourced_claims():
    # standard claims + an extra quantitative claim with NO evidence (G-1 fail)
    return S.standard_claims() + [
        S.claim("Unsupported quantitative assertion.", "quantitative")
    ]


def _lookahead_evidence():
    ev = S.standard_evidence()
    for e in ev:
        if e["id"] == "ev-fcf":
            e["as_of"] = "2025-06-30"  # after the cutoff -> look-ahead
    return ev


def all_cases():
    cases = []

    # 1 — admissible, personal lane
    cases.append({
        "name": "admissible_personal",
        "rr": S.record("rr-001-admissible-personal", "personal-research", SUBJECT, CUTOFF,
                       S.standard_claims()),
        "expected_verdict": "ADMISSIBLE",
        "expected_gates": {"G-1": "PASS", "G-2": "PASS", "G-3": "PASS",
                           "G-4": "PASS", "G-5": "NA", "G-6": "PASS"},
    })

    # 2 — admissible, client-mifid lane (full lane_fields)
    cases.append({
        "name": "admissible_client",
        "rr": S.record("rr-002-admissible-client", "client-mifid", SUBJECT, CUTOFF,
                       S.standard_claims(), lane_fields=S.client_lane_fields()),
        "expected_verdict": "ADMISSIBLE",
        "expected_gates": {"G-1": "PASS", "G-2": "PASS", "G-3": "PASS",
                           "G-4": "PASS", "G-5": "PASS", "G-6": "PASS"},
    })

    # 3 — G-1 fails on personal lane -> FLAG -> still ADMISSIBLE
    cases.append({
        "name": "g1_flag_personal",
        "rr": S.record("rr-003-g1-flag-personal", "personal-research", SUBJECT, CUTOFF,
                       _unsourced_claims()),
        "expected_verdict": "ADMISSIBLE",
        "expected_gates": {"G-1": "FAIL", "G-2": "PASS", "G-3": "PASS",
                           "G-4": "PASS", "G-5": "NA", "G-6": "PASS"},
    })

    # 4 — G-1 fails on client lane -> G-5 blocks -> BLOCKED
    cases.append({
        "name": "g5_block_client_unsourced",
        "rr": S.record("rr-004-g5-block-client", "client-mifid", SUBJECT, CUTOFF,
                       _unsourced_claims(), lane_fields=S.client_lane_fields()),
        "expected_verdict": "BLOCKED",
        "expected_gates": {"G-1": "FAIL", "G-2": "PASS", "G-3": "PASS",
                           "G-4": "PASS", "G-5": "FAIL", "G-6": "PASS"},
    })

    # 5 — audit-trail tampered (subject changed after stamping) -> G-2 fail
    _base5 = S.record("rr-005-g2-tampered-personal", "personal-research", SUBJECT, CUTOFF,
                      S.standard_claims())
    _tampered = copy.deepcopy(_base5)
    _tampered["subject"] = "TAMPERED Corp"  # invalidates input_hash
    cases.append({
        "name": "g2_tampered_personal",
        "rr": _tampered,
        "expected_verdict": "BLOCKED",
        "expected_gates": {"G-1": "PASS", "G-2": "FAIL", "G-3": "PASS",
                           "G-4": "PASS", "G-5": "NA", "G-6": "PASS"},
    })

    # 6 — wrong computation on personal lane -> G-3 FLAG -> still ADMISSIBLE
    cases.append({
        "name": "g3_flag_personal",
        "rr": S.record("rr-006-g3-flag-personal", "personal-research", SUBJECT, CUTOFF,
                       S.standard_claims(computations=S.standard_computations(ev_ebitda_llm=6.0))),
        "expected_verdict": "ADMISSIBLE",
        "expected_gates": {"G-1": "PASS", "G-2": "PASS", "G-3": "FAIL",
                           "G-4": "PASS", "G-5": "NA", "G-6": "PASS"},
    })

    # 7 — wrong computation on client lane -> G-3 BLOCK + G-5 -> BLOCKED
    cases.append({
        "name": "g3_block_client",
        "rr": S.record("rr-007-g3-block-client", "client-mifid", SUBJECT, CUTOFF,
                       S.standard_claims(computations=S.standard_computations(ev_ebitda_llm=6.0)),
                       lane_fields=S.client_lane_fields()),
        "expected_verdict": "BLOCKED",
        "expected_gates": {"G-1": "PASS", "G-2": "PASS", "G-3": "FAIL",
                           "G-4": "PASS", "G-5": "FAIL", "G-6": "PASS"},
    })

    # 8 — look-ahead evidence -> G-4 fail (REQUIRED both lanes) -> BLOCKED
    cases.append({
        "name": "g4_lookahead_personal",
        "rr": S.record("rr-008-g4-lookahead-personal", "personal-research", SUBJECT, CUTOFF,
                       S.standard_claims(evidence_list=_lookahead_evidence())),
        "expected_verdict": "BLOCKED",
        "expected_gates": {"G-1": "PASS", "G-2": "PASS", "G-3": "PASS",
                           "G-4": "FAIL", "G-5": "NA", "G-6": "PASS"},
    })

    # 9 — client-mifid missing lane_fields -> G-6 fail -> BLOCKED
    cases.append({
        "name": "g6_missing_lanefields_client",
        "rr": S.record("rr-009-g6-missing-lanefields-client", "client-mifid", SUBJECT, CUTOFF,
                       S.standard_claims()),  # no lane_fields
        "expected_verdict": "BLOCKED",
        "expected_gates": {"G-1": "PASS", "G-2": "PASS", "G-3": "PASS",
                           "G-4": "PASS", "G-5": "PASS", "G-6": "FAIL"},
    })

    # 10 — promotion without re-evaluation -> G-6 fail -> BLOCKED
    _base10 = S.record("rr-010-g6-promotion-client", "client-mifid", SUBJECT, CUTOFF,
                       S.standard_claims(), lane_fields=S.client_lane_fields())
    _promoted = copy.deepcopy(_base10)
    _promoted["gate_results"] = {"evaluated_lane": "personal-research", "verdict": "ADMISSIBLE"}
    cases.append({
        "name": "g6_promotion_client",
        "rr": _promoted,
        "expected_verdict": "BLOCKED",
        "expected_gates": {"G-1": "PASS", "G-2": "PASS", "G-3": "PASS",
                           "G-4": "PASS", "G-5": "PASS", "G-6": "FAIL"},
    })

    return cases
