"""Deterministic reference computation engine.

Given a metric key and its operand values (resolved from *sourced* evidence),
recompute the metric independently of whatever value a model proposed. This is
the financial analogue of a deterministic verifier: the judge never trusts the
judged party's own number (constitution P-1, P-3).

Pure stdlib. No LLM, no network. All metrics are explicit, auditable formulas.
"""
from __future__ import annotations

import math

# Relative tolerance between a model-proposed value and the independently
# recomputed value. Default 0.5 % (intentionally configurable) to absorb
# presentation rounding. abs_tol guards near-zero.
DEFAULT_REL_TOL = 0.005
DEFAULT_ABS_TOL = 1e-9


class ComputeError(Exception):
    """Raised when a metric cannot be reproduced (unknown metric, missing
    operands, division by zero)."""


def _ratio(numerator, denominator):
    if denominator == 0:
        raise ZeroDivisionError("denominator is zero")
    return numerator / denominator


# metric -> (required operand names, function(operands)->float, human formula)
METRICS = {
    "gross_margin": (
        ["gross_profit", "revenue"],
        lambda o: _ratio(o["gross_profit"], o["revenue"]),
        "gross_profit / revenue",
    ),
    "ebitda_margin": (
        ["ebitda", "revenue"],
        lambda o: _ratio(o["ebitda"], o["revenue"]),
        "ebitda / revenue",
    ),
    "pe_ratio": (
        ["price", "eps"],
        lambda o: _ratio(o["price"], o["eps"]),
        "price / eps",
    ),
    "ev_ebitda": (
        ["ev", "ebitda"],
        lambda o: _ratio(o["ev"], o["ebitda"]),
        "ev / ebitda",
    ),
    "net_debt_to_ebitda": (
        ["net_debt", "ebitda"],
        lambda o: _ratio(o["net_debt"], o["ebitda"]),
        "net_debt / ebitda",
    ),
    "fcf_yield": (
        ["fcf", "market_cap"],
        lambda o: _ratio(o["fcf"], o["market_cap"]),
        "fcf / market_cap",
    ),
    "current_ratio": (
        ["current_assets", "current_liabilities"],
        lambda o: _ratio(o["current_assets"], o["current_liabilities"]),
        "current_assets / current_liabilities",
    ),
    "revenue_growth": (
        ["revenue", "revenue_prior"],
        lambda o: _ratio(o["revenue"] - o["revenue_prior"], o["revenue_prior"]),
        "(revenue - revenue_prior) / revenue_prior",
    ),
    # Simplified comparable valuation: implied EV from a peer multiple.
    "comparable_ev": (
        ["peer_ev_ebitda", "ebitda"],
        lambda o: o["peer_ev_ebitda"] * o["ebitda"],
        "peer_ev_ebitda * ebitda",
    ),
}


def known_metrics():
    return sorted(METRICS.keys())


def required_operands(metric: str):
    if metric not in METRICS:
        raise ComputeError(f"unknown metric: {metric}")
    return list(METRICS[metric][0])


def formula_for(metric: str) -> str:
    return METRICS[metric][2] if metric in METRICS else ""


def recompute(metric: str, operands: dict) -> float:
    """Recompute ``metric`` from ``operands``. Raises ComputeError on any
    condition that prevents independent reproduction."""
    if metric not in METRICS:
        raise ComputeError(f"unknown metric: {metric}")
    needed, fn, _ = METRICS[metric]
    missing = [n for n in needed if n not in operands]
    if missing:
        raise ComputeError(f"missing operands for {metric}: {missing}")
    try:
        return float(fn(operands))
    except ZeroDivisionError as exc:
        raise ComputeError(f"{metric}: {exc}")


def values_agree(a: float, b: float, rel_tol: float = DEFAULT_REL_TOL) -> bool:
    return math.isclose(a, b, rel_tol=rel_tol, abs_tol=DEFAULT_ABS_TOL)
