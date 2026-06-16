"""A worked synthetic wealth-management ("patrimoine / CGP") case: MEDISYN SA.

This module models how a *conseiller en gestion de patrimoine* (CGP) would use
the harness to produce a **general-research note** on a listed company for a
client dossier — and, crucially, what happens when the underlying numbers do
**not** hold up.

It complements ``cases_worked.py`` (FICTEX SA, the analyst angle) with two
companion records on the **client-mifid** lane:

  - ``build_patrimoine_admissible()`` — a coherent general-research note whose
    every computation recomputes exactly. Verdict: **ADMISSIBLE**.
  - ``build_patrimoine_rejected()`` — the *same* company, but the model claimed
    an EV/EBITDA that makes MEDISYN look like a bargain (6.5×) while the sourced
    figures recompute to 9.0×. G-3 (independent recompute) FAILS; on the
    client-mifid lane G-3 is BLOCK and G-5 propagates the failure → the note is
    **BLOCKED**, never emitted to the client.

This is the financial analogue of the pedagogical verifier: the judge never
trusts the judged party's own number (constitution P-1/P-3). A "cheap multiple"
that the evidence does not support is refused, not softened.

Everything is fabricated: no real company, no real ISIN (``XX``-prefixed),
no real filing, no real market data. Numbers are internally consistent.

Scenario overview
-----------------
MEDISYN SA — a synthetic mid-cap pharmaceutical company (fictional Euronext
Paris listing, ticker MDSY, fabricated ISIN XX0000000001).

Fiscal year: 2024 (year ending 31 Dec 2024).
Reporting: annual report "MEDISYN-URD-2024" (fabricated filing reference).

Financial summary (all amounts in MEUR):
  Revenue 2024:        800
  Revenue 2023:        640      (revenue_growth = 0.25)
  Gross profit:        560      (gross_margin = 0.70 — pharma-typical)
  EBITDA:              240      (ebitda_margin = 0.30)
  Enterprise value:  2 160      (ev_ebitda = 9.0×)
  Net debt:            120      (net_debt_to_ebitda = 0.5× — low leverage)
  Market cap:        2 040      (fcf_yield = 0.05)
  Free cash flow:      102
  Peer EV/EBITDA:       11.0     (comparable_ev = 11.0 × 240 = 2 640 MEUR)

The peer-comparison implies ~22 % EV upside (2640 vs 2160) — a defensible
"slightly undervalued" thesis *when the inputs are honest*. The rejected note
fabricates a 6.5× headline multiple to overstate the discount; the harness
catches it.

Usage
-----
    from harness.fixtures.cases_patrimoine import build_patrimoine_cases
    admissible, rejected = build_patrimoine_cases()

    # Or run both E2E:
    from harness.fixtures.cases_patrimoine import run_patrimoine_cases
    for label, ev, aug in run_patrimoine_cases():
        print(label, ev.verdict)
"""
from __future__ import annotations

from harness.fixtures import synthetic as S

# ---------------------------------------------------------------------------
# Synthetic company constants — ZERO real data
# ---------------------------------------------------------------------------

COMPANY = "MEDISYN SA (synthetic)"
FILING = "MEDISYN-URD-2024"         # fabricated filing reference
CUTOFF = "2025-02-28"               # information cutoff: two months after FY close
AS_OF = "2024-12-31"                # all fundamental evidence dated to FY-end
MKT_AS_OF = "2025-02-28"            # market data as of the cutoff date

# Evidence ids — stable across tests so G-2 (audit trail) is reproducible.
_EVIDENCE = {
    "rev":      ("ev-mdsy-rev",     "Revenue FY2024",            800.0,  "MEUR", FILING, "§3.1/p28/Revenue",        AS_OF),
    "rev_py":   ("ev-mdsy-rev-py",  "Revenue FY2023",            640.0,  "MEUR", FILING, "§3.1/p28/Revenue_prior",  AS_OF),
    "gp":       ("ev-mdsy-gp",      "Gross profit FY2024",       560.0,  "MEUR", FILING, "§3.1/p29/GrossProfit",    AS_OF),
    "ebitda":   ("ev-mdsy-ebitda",  "EBITDA FY2024",             240.0,  "MEUR", FILING, "§3.2/p31/EBITDA",         AS_OF),
    "ev":       ("ev-mdsy-ev",      "Enterprise value (spot)",  2160.0,  "MEUR", FILING, "§6.1/p48/EV",            MKT_AS_OF),
    "netdebt":  ("ev-mdsy-nd",      "Net debt FY2024",           120.0,  "MEUR", FILING, "§5.2/p44/NetDebt",        AS_OF),
    "mcap":     ("ev-mdsy-mcap",    "Market cap (spot)",        2040.0,  "MEUR", "MKT-MDSY-2025-02-28", "quote/market_cap", MKT_AS_OF),
    "fcf":      ("ev-mdsy-fcf",     "Free cash flow FY2024",     102.0,  "MEUR", FILING, "§3.3/p32/FCF",            AS_OF),
    "peer_mul": ("ev-mdsy-peer",    "Peer EV/EBITDA (median)",    11.0,  "×",    "BROKER-PHARMA-PEERS-2025-02", "table/peer_multiples", MKT_AS_OF),
}


def _mk_ev(key):
    eid, fig, val, unit, src, loc, aof = _EVIDENCE[key]
    return S.evidence(eid, fig, val, src, loc, aof, unit=unit)


def _all_evidence():
    return [_mk_ev(k) for k in _EVIDENCE]


def _qualitative_claim():
    return S.claim(
        "MEDISYN SA shows a pharma-typical 70 % gross margin, low leverage "
        "(net debt/EBITDA 0.5×) and 25 % revenue growth in FY2024. Peer "
        "comparison suggests a modest discount to sector medians, sensitive to "
        "pipeline-renewal assumptions.",
        "qualitative",
    )


def _quantitative_claim():
    return S.claim(
        "Key FY2024 fundamentals extracted from MEDISYN-URD-2024.",
        "quantitative",
        evidence=_all_evidence(),
    )


def _valuation_claim(ev_ebitda_llm: float):
    """Valuation claim with deterministic computations.

    ``ev_ebitda_llm`` is the EV/EBITDA value the *model* proposed. The honest
    recompute is 2160/240 = 9.0. The admissible note passes 9.0; the rejected
    note passes a fabricated 6.5 to overstate the discount, which G-3 catches.
    """
    ev_map = {k: _mk_ev(k)["id"] for k in _EVIDENCE}
    comps = [
        S.computation("gross_margin",       "gross_profit / revenue",
                      {"gross_profit": ev_map["gp"],   "revenue": ev_map["rev"]},
                      0.7),
        S.computation("ebitda_margin",      "ebitda / revenue",
                      {"ebitda": ev_map["ebitda"],     "revenue": ev_map["rev"]},
                      0.3),
        S.computation("ev_ebitda",          "ev / ebitda",
                      {"ev": ev_map["ev"],             "ebitda": ev_map["ebitda"]},
                      ev_ebitda_llm),
        S.computation("net_debt_to_ebitda", "net_debt / ebitda",
                      {"net_debt": ev_map["netdebt"],  "ebitda": ev_map["ebitda"]},
                      0.5),
        S.computation("fcf_yield",          "fcf / market_cap",
                      {"fcf": ev_map["fcf"],           "market_cap": ev_map["mcap"]},
                      0.05),
        S.computation("revenue_growth",     "(revenue - revenue_prior) / revenue_prior",
                      {"revenue": ev_map["rev"],       "revenue_prior": ev_map["rev_py"]},
                      0.25),
        S.computation("comparable_ev",      "peer_ev_ebitda * ebitda",
                      {"peer_ev_ebitda": ev_map["peer_mul"], "ebitda": ev_map["ebitda"]},
                      2640.0),
    ]
    return S.claim(
        "Valuation analysis: MEDISYN trades on EV/EBITDA "
        f"{ev_ebitda_llm:g}× vs a peer median of 11.0×. Comparable-EV of "
        "2 640 MEUR implies ~22 % upside to the current EV.",
        "valuation",
        computations=comps,
    )


def _client_lane_fields():
    """General-research note: no personalised advice, no suitability block."""
    return {
        "reco_nature": "general-research",
        "disclaimers": [
            "Note de recherche générale — ne constitue pas un conseil en "
            "investissement personnalisé.",
            "Les performances passées ne préjugent pas des performances futures.",
            "Cas synthétique illustratif — ne repose sur aucune donnée réelle.",
        ],
        "conflicts_of_interest": "None — synthetic demonstration case.",
    }


def build_patrimoine_admissible() -> dict:
    """A coherent CGP general-research note (client-mifid). Verdict: ADMISSIBLE.

    EV/EBITDA proposed = 9.0, which matches the recompute exactly.
    """
    return S.record(
        "rr-medisyn-client-ok-2025-02",
        "client-mifid",
        COMPANY,
        CUTOFF,
        [_qualitative_claim(), _quantitative_claim(), _valuation_claim(9.0)],
        lane_fields=_client_lane_fields(),
        stamp=True,
    )


def build_patrimoine_rejected() -> dict:
    """The same note with a fabricated headline multiple. Verdict: BLOCKED.

    EV/EBITDA proposed = 6.5 (overstates the discount) while the sourced
    figures recompute to 9.0. On the client-mifid lane G-3 is BLOCK and G-5
    propagates, so the note is refused — never degraded, never emitted.
    """
    return S.record(
        "rr-medisyn-client-rejected-2025-02",
        "client-mifid",
        COMPANY,
        CUTOFF,
        [_qualitative_claim(), _quantitative_claim(), _valuation_claim(6.5)],
        lane_fields=_client_lane_fields(),
        stamp=True,
    )


def build_patrimoine_cases() -> tuple:
    """Return ``(admissible_rr, rejected_rr)`` — two stamped client-mifid RRs.

    The caller decides when to call ``gates.evaluate()``; these are raw
    (pre-evaluation) RRs.
    """
    return build_patrimoine_admissible(), build_patrimoine_rejected()


def run_patrimoine_cases() -> list:
    """Evaluate both RRs and return ``(label, Evaluation, augmented_rr)`` triples.

    Attaches ``_gate_status_map`` to each augmented_rr so the export module can
    surface per-gate status in thesis cards and the index.
    """
    from harness.gates.gates import evaluate

    results = []
    for label, rr in [
        ("admissible", build_patrimoine_admissible()),
        ("rejected", build_patrimoine_rejected()),
    ]:
        ev = evaluate(rr)
        aug = ev.augmented_rr
        aug["_gate_status_map"] = ev.status_map()
        results.append((label, ev, aug))
    return results
