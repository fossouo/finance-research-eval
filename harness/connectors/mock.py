"""Synthetic, offline mock implementations of the connector seam.

NOT real data. Every fact is fabricated and flagged ``synthetic=True``. The mock
exists so the seam is exercisable (and the gates reachable) with no network and no
provider key — the public counterpart to the real `EdgarConnector` in the private
repo. The fixtures deliberately encode two findings from the coverage test:

  - a **restatement** (one concept/period filed twice with different values) so
    ``first_reported`` is testable — the GE case;
  - a **delisting** (a ticker present at an early date, gone later) so
    anti-survivorship membership is testable — the SVB / SIVB case.
"""
from __future__ import annotations

from harness.connectors.base import FinancialFact, SourceDoc

_SYN = {"synthetic": True}

# Fabricated facts keyed by (made-up) ticker. The "ACME" stream contains a
# restatement of FY2021 Revenues: first filed at 1000 in 2022, revised to 900 in
# 2023 (a later 10-K/A). first_reported() must keep the 2022 value.
_FACTS = {
    "ACME": [
        FinancialFact("Revenues", 1000.0, "2021-12-31", "2022-02-15",
                      "ACME Corp 10-K FY2021", "us-gaap:Revenues period 2021-12-31",
                      form="10-K", meta=_SYN),
        FinancialFact("Revenues", 900.0, "2021-12-31", "2023-02-20",
                      "ACME Corp 10-K/A FY2021 (restated)", "us-gaap:Revenues period 2021-12-31",
                      form="10-K/A", meta=_SYN),
        FinancialFact("Revenues", 1200.0, "2022-12-31", "2023-02-20",
                      "ACME Corp 10-K FY2022", "us-gaap:Revenues period 2022-12-31",
                      form="10-K", meta=_SYN),
        FinancialFact("CostOfRevenue", 700.0, "2022-12-31", "2023-02-20",
                      "ACME Corp 10-K FY2022", "us-gaap:CostOfRevenue period 2022-12-31",
                      form="10-K", meta=_SYN),
        FinancialFact("NetIncomeLoss", 150.0, "2022-12-31", "2023-02-20",
                      "ACME Corp 10-K FY2022", "us-gaap:NetIncomeLoss period 2022-12-31",
                      form="10-K", meta=_SYN),
    ],
    # A bank that filed up to the period before disappearing (the SIVB analogue):
    # facts exist as-of early 2023, then it is delisted from the index (see
    # MockConstituentsSource).
    "FAILBANK": [
        FinancialFact("Revenues", 500.0, "2022-12-31", "2023-02-24",
                      "FailBank 10-K FY2022", "us-gaap:Revenues period 2022-12-31",
                      form="10-K", meta=_SYN),
    ],
}

_DOCS = {
    "ACME": [
        SourceDoc("0000000000-22-000001", "10-K (FY2021)", "10-K", "2022-02-15",
                  url="https://example.invalid/acme/10k-2021", meta=_SYN),
        SourceDoc("0000000000-23-000007", "10-K/A (FY2021 restated)", "10-K/A", "2023-02-20",
                  url="https://example.invalid/acme/10ka-2021", meta=_SYN),
        SourceDoc("0000000000-23-000008", "10-K (FY2022)", "10-K", "2023-02-20",
                  url="https://example.invalid/acme/10k-2022", meta=_SYN),
    ],
    "FAILBANK": [
        SourceDoc("0000000000-23-000099", "10-K (FY2022)", "10-K", "2023-02-24",
                  url="https://example.invalid/failbank/10k-2022", meta=_SYN),
    ],
}


def _between(d: str, since: str | None, until: str | None) -> bool:
    if since and (not d or d < since):
        return False
    if until and (not d or d > until):
        return False
    return True


class MockConnector:
    """A faithful, fully synthetic `Connector`. Filters by ``as_of`` (filing date)
    so it behaves like a point-in-time source."""
    name = "mock"

    def fundamentals(self, ticker, since=None, until=None):
        return [f for f in _FACTS.get(ticker.upper(), []) if _between(f.as_of, since, until)]

    def filings(self, ticker, since=None, until=None):
        return [d for d in _DOCS.get(ticker.upper(), []) if _between(d.filed_at, since, until)]


class MockConstituentsSource:
    """Synthetic dated membership. ``FAILBANK`` is a member at the start of 2023 and
    delisted by mid-2023 — so ``members_at`` returns different universes across dates
    and a backtest that ignores this would survivorship-bias FAILBANK away."""
    name = "mock-constituents"

    _MEMBERS = [
        # (effective_from, effective_to_or_None, ticker)
        ("2020-01-01", None, "ACME"),
        ("2020-01-01", "2023-03-10", "FAILBANK"),   # delisted 2023-03-10
    ]

    def members_at(self, date):
        out = []
        for start, end, tkr in self._MEMBERS:
            if start <= date and (end is None or date < end):
                out.append(tkr)
        return sorted(out)
