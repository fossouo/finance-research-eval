"""Synthetic investor-decision fixtures — fully fabricated, public-safe.

These mirror the *structure* of the (gitignored) investor-signals corpus
without reproducing any real company, quote, price, or date. They exist so the
adapter and its gate behaviour can be tested in the public core with zero real
data (open-core contract).
"""
from __future__ import annotations


def synthetic_records() -> list:
    """Return fabricated investor-decision records (corpus schema shape)."""
    return [
        {
            # Clean, point-in-time-consistent decision -> ADMISSIBLE.
            "id": "SYN-ACME-1990",
            "company": "Acme Synthetic Corp",
            "ticker": "SYN",
            "action": "BUY",
            "period": "1990-1992",
            "approx_position": "fictional ~5% stake",
            "decision_summary": "Fabricated decision for adapter testing.",
            "stated_rationale": [
                "Fictional durable-moat reasoning anchored to the 1990 letter.",
                "Fictional owner-earnings valuation reasoning.",
            ],
            "rationale_sources": ["SYNTHETIC Annual Letter 1990"],
            "market_signals": [
                {"type": "valuation", "signal": "cheap vs intrinsic value",
                 "evidence": "fabricated ~5x owner earnings"},
                {"type": "moat", "signal": "fabricated pricing power",
                 "evidence": "fabricated dominant share"},
            ],
            "signal_types": ["valuation", "moat"],
            "outcome": "Fabricated favourable outcome over the following decade.",
            "outcome_known_as_of": "2026-06",
            "confidence": "high",
            "caveats": "Entirely synthetic.",
        },
        {
            # Minimal but well-dated -> ADMISSIBLE.
            "id": "SYN-BOREALIS-2005",
            "company": "Borealis Fictional SA",
            "ticker": "BOR",
            "action": "ACQUIRE",
            "period": "2005",
            "stated_rationale": ["Fictional management-quality reasoning."],
            "rationale_sources": ["SYNTHETIC Press Release 2005"],
            "market_signals": [
                {"type": "management", "signal": "fabricated trusted operator",
                 "evidence": "fabricated track record"},
            ],
            "signal_types": ["management"],
            "outcome": "Fabricated steady compounding.",
            "outcome_known_as_of": "2026-06",
            "confidence": "medium",
            "caveats": "Entirely synthetic.",
        },
    ]
