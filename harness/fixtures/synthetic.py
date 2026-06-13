"""Builders for synthetic Recommendation Records.

Everything here is fabricated: no real company, no real filing, no real market
data. The numbers are internally consistent so the deterministic recompute (G-3)
matches the model-proposed values for the 'admissible' baseline, and we then
perturb single dimensions to exercise each gate's failure mode.
"""
from __future__ import annotations

from harness import rr as rrlib


def evidence(eid, figure, value, source_doc, locator, as_of, unit="MEUR"):
    return {
        "id": eid, "figure": figure, "value": value, "unit": unit,
        "source_doc": source_doc, "locator": locator, "as_of": as_of,
    }


def claim(statement, kind, evidence=None, computations=None):
    return {
        "statement": statement, "kind": kind,
        "evidence": evidence or [], "computations": computations or [],
    }


def computation(metric, formula, inputs, llm_value):
    return {"metric": metric, "formula": formula, "inputs": inputs, "llm_value": llm_value}


def record(rid, lane, subject, cutoff, claims, lane_fields=None, stamp=True):
    rr = {
        "id": rid, "lane": lane, "subject": subject,
        "information_cutoff": cutoff, "claims": claims,
    }
    if lane_fields is not None:
        rr["lane_fields"] = lane_fields
    if stamp:
        rr = rrlib.stamp_audit_trail(rr)
    return rr


def client_lane_fields(reco_nature="personalised-advice", complete=True):
    lf = {
        "reco_nature": reco_nature,
        "disclaimers": ["not a guarantee of performance", "synthetic example"],
        "conflicts_of_interest": "none (synthetic)",
    }
    if reco_nature == "personalised-advice" and complete:
        lf["suitability"] = {
            "knowledge_experience": "experienced",
            "financial_situation": "stable",
            "loss_capacity": "moderate",
            "objectives_horizon": "3-5y",
            "risk_tolerance": "balanced",
            "suitability_declaration": "advice consistent with profile (synthetic)",
        }
    return lf


# --- internally-consistent standard building blocks -------------------------
# revenue=1200, gross_profit=480 -> gross_margin=0.40
# ebitda=300 -> ebitda_margin=0.25 ; ev=2400 -> ev_ebitda=8.0
# net_debt=600 -> net_debt_to_ebitda=2.0
# market_cap=1800, fcf=90 -> fcf_yield=0.05
# revenue_prior=1000 -> revenue_growth=0.20

def standard_evidence(as_of="2025-03-31"):
    return [
        evidence("ev-rev", "Revenue 2024", 1200.0, "ACME-URD-2024", "§4.1/table3/Revenue", as_of),
        evidence("ev-gp", "Gross profit 2024", 480.0, "ACME-URD-2024", "§4.1/table3/GrossProfit", as_of),
        evidence("ev-ebitda", "EBITDA 2024", 300.0, "ACME-URD-2024", "§4.2/table4/EBITDA", as_of),
        evidence("ev-ev", "Enterprise value", 2400.0, "ACME-URD-2024", "§6.3/EV", as_of),
        evidence("ev-netdebt", "Net debt", 600.0, "ACME-URD-2024", "§5.1/NetDebt", as_of),
        evidence("ev-mcap", "Market cap", 1800.0, "MKT-2025-03-31", "quote/market_cap", as_of),
        evidence("ev-fcf", "Free cash flow 2024", 90.0, "ACME-URD-2024", "§4.3/FCF", as_of),
        evidence("ev-revprior", "Revenue 2023", 1000.0, "ACME-URD-2024", "§4.1/table3/Revenue_py", as_of),
    ]


def standard_computations(ev_ebitda_llm=8.0):
    return [
        computation("ev_ebitda", "ev / ebitda", {"ev": "ev-ev", "ebitda": "ev-ebitda"}, ev_ebitda_llm),
        computation("net_debt_to_ebitda", "net_debt / ebitda", {"net_debt": "ev-netdebt", "ebitda": "ev-ebitda"}, 2.0),
        computation("gross_margin", "gross_profit / revenue", {"gross_profit": "ev-gp", "revenue": "ev-rev"}, 0.4),
        computation("fcf_yield", "fcf / market_cap", {"fcf": "ev-fcf", "market_cap": "ev-mcap"}, 0.05),
        computation("revenue_growth", "(revenue - revenue_prior) / revenue_prior", {"revenue": "ev-rev", "revenue_prior": "ev-revprior"}, 0.2),
    ]


def standard_claims(evidence_list=None, computations=None):
    return [
        claim("ACME shows resilient margins and modest leverage.", "qualitative"),
        claim("Key 2024 fundamentals.", "quantitative",
              evidence=evidence_list if evidence_list is not None else standard_evidence()),
        claim("Valuation looks undemanding vs peers.", "valuation",
              computations=computations if computations is not None else standard_computations()),
    ]
