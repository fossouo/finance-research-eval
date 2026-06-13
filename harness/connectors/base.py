"""The public data-connector seam (E1).

A *connector* is how a real or mock data provider feeds the recevability harness.
The PUBLIC repo ships ONLY:
  - the data shapes (`FinancialFact`, `SourceDoc`),
  - the interfaces (`Connector`, `ConstituentsSource`) as structural Protocols,
  - the bridge from facts into the existing RR -> gates path,
  - small as-reported / point-in-time utilities the gates rely on.

Real, networked implementations (`EdgarConnector`, `TiingoConnector`, a dated
S&P 500 `ConstituentsSource`) live in the PRIVATE enterprise repo, which *imports*
this package and satisfies these Protocols. This module therefore imports NO
network library — a test enforces it, exactly like ``harness/sources/``.

Why a Protocol and not a base class: the implementations live in a different
repository. Structural typing lets them conform without importing a base class,
keeping the dependency one-way (private -> public, never the reverse).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Protocol, runtime_checkable

from harness.sources.evalitem import ContextSnippet, EvalItem


@dataclass(frozen=True)
class FinancialFact:
    """One reported financial figure, as it was filed.

    ``as_of`` is the moment the market could know it (filing/announcement date) and
    is the anchor for the point-in-time gate (G-4). ``source_doc`` + ``locator``
    are what G-1 (sourcing) needs to cite. ``period_end`` is the fiscal period the
    figure describes — distinct from ``as_of`` (a 2017 figure can be filed in 2018,
    then *restated* in a later filing; see ``first_reported``).
    """
    concept: str        # e.g. "Revenues" (us-gaap concept or provider field)
    value: float
    period_end: str     # YYYY-MM-DD — end of the fiscal period described
    as_of: str          # YYYY-MM-DD — filing/announcement date -> G-4
    source_doc: str     # e.g. "SVB Financial 10-K 2022"
    locator: str        # e.g. "us-gaap:Revenues period 2022-12-31"
    form: str = ""      # 8-K / 10-Q / 10-K (provenance of the figure)
    unit: str = "USD"
    meta: dict = field(default_factory=dict)

    def to_evidence(self) -> dict:
        """Shape this fact as a claim's ``evidence`` entry (what assemble_rr and
        the gates consume): figure/value/source_doc/locator/as_of."""
        return {
            "figure": self.concept,
            "value": self.value,
            "source_doc": self.source_doc,
            "locator": self.locator,
            "as_of": self.as_of,
        }


@dataclass(frozen=True)
class SourceDoc:
    """A raw filing/document a figure can be cited against (the backbone of G-1).

    Point-in-time discipline: a backtest at decision date D may only use docs with
    ``filed_at <= D``. The public repo never stores the document body; ``url`` is a
    pointer (e.g. an EDGAR accession URL) resolved by the real connector."""
    doc_id: str         # e.g. accession number
    title: str          # e.g. "10-K (FY2022)"
    form: str           # 10-K / 10-Q / 8-K
    filed_at: str       # YYYY-MM-DD -> G-4
    url: str = ""       # pointer only; body never stored in the public repo
    meta: dict = field(default_factory=dict)


@runtime_checkable
class Connector(Protocol):
    """A source of point-in-time financial facts and the documents behind them."""

    def fundamentals(self, ticker: str, since: str | None = None,
                     until: str | None = None) -> list[FinancialFact]:
        """Reported facts for ``ticker``. ``since``/``until`` filter by ``as_of``
        (filing date), NOT by period — this is what keeps a backtest honest."""
        ...

    def filings(self, ticker: str, since: str | None = None,
                until: str | None = None) -> list[SourceDoc]:
        """Raw documents for ``ticker`` (the G-1 citation targets)."""
        ...


@runtime_checkable
class ConstituentsSource(Protocol):
    """Dated index membership — the N2 gap that neither EDGAR nor fundamentals
    providers fill. ``members_at`` MUST include names that were members at that
    date but later delisted (anti-survivorship)."""

    def members_at(self, date: str) -> list[str]:
        ...


# --- public as-reported / point-in-time utilities ---------------------------

def first_reported(facts: Iterable[FinancialFact]) -> list[FinancialFact]:
    """Keep the **as-first-reported** version of each (concept, period_end):
    the fact with the EARLIEST ``as_of``. Mirrors the GE restatement finding from
    the coverage test — a later filing may revise a period; the original is what
    the market knew first. Restated versions are dropped here (callers that want
    them can group the raw stream themselves)."""
    best: dict[tuple[str, str], FinancialFact] = {}
    for f in facts:
        key = (f.concept, f.period_end)
        cur = best.get(key)
        if cur is None or f.as_of < cur.as_of:
            best[key] = f
    return sorted(best.values(), key=lambda f: (f.concept, f.period_end))


def visible_at(facts: Iterable[FinancialFact], decision_date: str) -> list[FinancialFact]:
    """Only the facts knowable at ``decision_date`` (``as_of <= decision_date``) —
    the anti-look-ahead filter that backs G-4."""
    return [f for f in facts if f.as_of and f.as_of <= decision_date]


def facts_to_evalitem(ticker: str, facts: list[FinancialFact], question: str,
                      gold_answer: str = "", gold_kind: str = "numeric") -> EvalItem:
    """Bridge connector facts into a normalized EvalItem (so a connector plugs
    straight into the existing source/candidate/gate path). Each fact becomes a
    sourced ContextSnippet carrying its ``as_of`` point-in-time anchor."""
    ctx = [
        ContextSnippet(text=f"{f.concept} = {f.value} {f.unit}", source_doc=f.source_doc,
                       locator=f.locator, as_of=f.as_of)
        for f in facts
    ]
    return EvalItem(
        source="connector",
        item_id=f"{ticker}:{question[:40]}",
        question=question,
        gold_answer=str(gold_answer),
        gold_kind=gold_kind,
        context=ctx,
        meta={"ticker": ticker, "synthetic": all(f.meta.get("synthetic") for f in facts) if facts else False},
    )
