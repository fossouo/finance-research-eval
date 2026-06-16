"""A fully worked synthetic end-to-end case: FICTEX SA.

This module is a *reference case* — a single coherent company story that
exercises every stage of the harness pipeline:

    extraction → valuation (deterministic recompute) → gates G-1..G-6
    → RR.stamp_audit_trail → export (export_bundle + format_thesis_card)

FICTEX SA is entirely fabricated: no real company, no real ISIN, no real
filing, no real market data. Numbers are internally consistent so:
  - G-1 PASS: all quantitative/valuation evidence is sourced + locatable
  - G-2 PASS: audit trail stamped and reproducible
  - G-3 PASS: every recomputed metric matches the LLM-proposed value
  - G-4 PASS: all evidence.as_of <= information_cutoff
  - G-5 PASS/NA: no G-1/G-3 failures to propagate
  - G-6 PASS: lane declared, lane_fields present for client-mifid

Scenario overview
-----------------
FICTEX SA — a synthetic mid-cap industrial manufacturer (Euronext Paris
fictional listing, ticker: FCTX, fabricated ISIN: XX0000000000).

Fiscal year: 2024 (year ending 31 Dec 2024).
Reporting: annual report "FICTEX-URD-2024" (fabricated filing reference).

Financial summary (all amounts in MEUR):
  Revenue 2024:       1 440
  Revenue 2023:       1 200
  Gross profit:         576   (gross margin = 40.0 %)
  EBITDA:               360   (EBITDA margin = 25.0 %)
  Enterprise value:   2 880   (EV/EBITDA = 8.0×)
  Net debt:             720   (Net debt/EBITDA = 2.0×)
  Market cap:         2 160   (FCF yield = 4.2 % approx)
  Free cash flow:        90   (FCF yield = 90/2160 ≈ 0.0417)
  Revenue growth:       0.20  (20.0 % YoY)

Comparable valuation:
  Peer EV/EBITDA multiple used: 9.0×
  Implied EV from comparables:  9.0 × 360 = 3 240 MEUR
  Implied upside: (3240 - 2880) / 2880 ≈ 12.5 % (not a recomputed metric,
  stated qualitatively to show the thesis without hard-coding the percentage).

Usage
-----
    from harness.fixtures.cases_worked import build_worked_case
    personal, client = build_worked_case()
    # personal/client are RR dicts ready to pass to gates.evaluate()

    # Or run the worked case E2E:
    from harness.fixtures.cases_worked import run_worked_case
    results = run_worked_case()   # returns list of (label, Evaluation, augmented_rr)
"""
from __future__ import annotations

from harness import rr as rrlib
from harness.fixtures import synthetic as S

# ---------------------------------------------------------------------------
# Synthetic company constants — ZERO real data
# ---------------------------------------------------------------------------

COMPANY = "FICTEX SA (synthetic)"
FILING = "FICTEX-URD-2024"          # fabricated filing reference
CUTOFF = "2025-01-31"               # information cutoff: one month after FY close
AS_OF = "2024-12-31"                # all evidence dated to FY-end
MKT_AS_OF = "2025-01-31"           # market data as of cutoff date

# Evidence ids — stable across tests so G-2 is reproducible
_EVIDENCE = {
    "rev":      ("ev-fctx-rev",     "Revenue FY2024",            1440.0, "MEUR", FILING, "§4.1/p32/Revenue",              AS_OF),
    "rev_py":   ("ev-fctx-rev-py",  "Revenue FY2023",            1200.0, "MEUR", FILING, "§4.1/p32/Revenue_prior",         AS_OF),
    "gp":       ("ev-fctx-gp",      "Gross profit FY2024",        576.0, "MEUR", FILING, "§4.1/p33/GrossProfit",           AS_OF),
    "ebitda":   ("ev-fctx-ebitda",  "EBITDA FY2024",              360.0, "MEUR", FILING, "§4.2/p35/EBITDA",                AS_OF),
    "ev":       ("ev-fctx-ev",      "Enterprise value (spot)",   2880.0, "MEUR", FILING, "§6.3/p52/EV",                   MKT_AS_OF),
    "netdebt":  ("ev-fctx-nd",      "Net debt FY2024",            720.0, "MEUR", FILING, "§5.1/p41/NetDebt",               AS_OF),
    "mcap":     ("ev-fctx-mcap",    "Market cap (spot)",         2160.0, "MEUR", "MKT-FCTX-2025-01-31", "quote/market_cap", MKT_AS_OF),
    "fcf":      ("ev-fctx-fcf",     "Free cash flow FY2024",       90.0, "MEUR", FILING, "§4.3/p36/FCF",                   AS_OF),
    "peer_mul": ("ev-fctx-peer",    "Peer EV/EBITDA (median)",      9.0, "×",    "BROKER-PEERS-2025-01", "table/peer_multiples", MKT_AS_OF),
}


def _mk_ev(key):
    eid, fig, val, unit, src, loc, aof = _EVIDENCE[key]
    return S.evidence(eid, fig, val, src, loc, aof, unit=unit)


def _all_evidence():
    return [_mk_ev(k) for k in _EVIDENCE]


def _qualitative_claim():
    return S.claim(
        "FICTEX SA shows resilient 40 % gross margin, moderate leverage "
        "(net debt/EBITDA 2.0×), and 20 % revenue growth in FY2024. "
        "Comparable peer analysis suggests a potential 12-13 % EV upside "
        "using a 9× EV/EBITDA multiple, though this remains sensitive to "
        "cycle normalisation.",
        "qualitative",
    )


def _quantitative_claim():
    return S.claim(
        "Key FY2024 fundamentals extracted from FICTEX-URD-2024.",
        "quantitative",
        evidence=_all_evidence(),
    )


def _valuation_claim():
    """Valuation claim with deterministic computations.

    Metric values chosen so recompute() agrees exactly (no rounding needed):
      gross_margin            = 576/1440   = 0.4
      ebitda_margin           = 360/1440   = 0.25
      ev_ebitda               = 2880/360   = 8.0
      net_debt_to_ebitda      = 720/360    = 2.0
      fcf_yield               = 90/2160    ≈ 0.041666...  (LLM reports 0.0417)
      revenue_growth          = (1440-1200)/1200 = 0.2
      comparable_ev           = 9.0 × 360  = 3240
    """
    ev_map = {k: _mk_ev(k)["id"] for k in _EVIDENCE}
    comps = [
        S.computation("gross_margin",       "gross_profit / revenue",
                      {"gross_profit": ev_map["gp"],   "revenue": ev_map["rev"]},
                      0.4),
        S.computation("ebitda_margin",      "ebitda / revenue",
                      {"ebitda": ev_map["ebitda"],     "revenue": ev_map["rev"]},
                      0.25),
        S.computation("ev_ebitda",          "ev / ebitda",
                      {"ev": ev_map["ev"],             "ebitda": ev_map["ebitda"]},
                      8.0),
        S.computation("net_debt_to_ebitda", "net_debt / ebitda",
                      {"net_debt": ev_map["netdebt"],  "ebitda": ev_map["ebitda"]},
                      2.0),
        S.computation("fcf_yield",          "fcf / market_cap",
                      {"fcf": ev_map["fcf"],           "market_cap": ev_map["mcap"]},
                      round(90.0 / 2160.0, 6)),    # 0.041667
        S.computation("revenue_growth",     "(revenue - revenue_prior) / revenue_prior",
                      {"revenue": ev_map["rev"],       "revenue_prior": ev_map["rev_py"]},
                      0.2),
        S.computation("comparable_ev",      "peer_ev_ebitda * ebitda",
                      {"peer_ev_ebitda": ev_map["peer_mul"], "ebitda": ev_map["ebitda"]},
                      3240.0),
    ]
    return S.claim(
        "Valuation analysis: FICTEX appears modestly undervalued relative to "
        "industrial sector peers (EV/EBITDA 8.0× vs peer median 9.0×). "
        "Comparable-EV of 3 240 MEUR implies ~12.5 % upside to current EV.",
        "valuation",
        computations=comps,
    )


def _personal_rr():
    """Worked RR on the personal-research lane."""
    return S.record(
        "rr-fictex-personal-2025-01",
        "personal-research",
        COMPANY,
        CUTOFF,
        [_qualitative_claim(), _quantitative_claim(), _valuation_claim()],
        stamp=True,
    )


def _client_rr():
    """Worked RR on the client-mifid lane (general-research note)."""
    lf = {
        "reco_nature": "general-research",
        "disclaimers": [
            "Past performance is not a reliable indicator of future returns.",
            "Synthetic illustrative case only — not based on real data.",
            "Not a personalised investment recommendation.",
        ],
        "conflicts_of_interest": "None — synthetic demonstration case.",
    }
    return S.record(
        "rr-fictex-client-2025-01",
        "client-mifid",
        COMPANY,
        CUTOFF,
        [_qualitative_claim(), _quantitative_claim(), _valuation_claim()],
        lane_fields=lf,
        stamp=True,
    )


def build_worked_case() -> tuple:
    """Return ``(personal_rr, client_rr)`` — two fully-formed, stamped RRs.

    Both RRs are independently consistent:
      - audit_trail present and reproducible (G-2 PASS)
      - all evidence sourced and dated (G-1 PASS, G-4 PASS)
      - computations match recomputed values (G-3 PASS)
      - lane/lane_fields valid for each lane (G-6 PASS)

    The caller decides when to call evaluate(); these are raw (pre-evaluation)
    RRs.
    """
    return _personal_rr(), _client_rr()


def run_worked_case() -> list:
    """Evaluate both worked RRs and return a list of
    ``(label, Evaluation, augmented_rr)`` triples.

    Attaches ``_gate_status_map`` to each augmented_rr so the export module
    can surface per-gate status in thesis cards and the index.
    """
    from harness.gates.gates import evaluate

    results = []
    for label, rr in [("personal", _personal_rr()), ("client", _client_rr())]:
        ev = evaluate(rr)
        aug = ev.augmented_rr
        aug["_gate_status_map"] = ev.status_map()
        results.append((label, ev, aug))
    return results
