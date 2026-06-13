"""Public data-connector seam (E1).

Defines the data shapes and Protocols a provider must satisfy to feed the
recevability harness, plus a synthetic mock. Real networked connectors
(EdgarConnector, TiingoConnector, dated ConstituentsSource) live in the PRIVATE
enterprise repo and import this package. No network here — enforced by a test.
"""
from harness.connectors.base import (
    Connector,
    ConstituentsSource,
    FinancialFact,
    SourceDoc,
    facts_to_evalitem,
    first_reported,
    visible_at,
)
from harness.connectors.mock import (
    MockConnector,
    MockConstituentsSource,
)

__all__ = [
    "Connector",
    "ConstituentsSource",
    "FinancialFact",
    "SourceDoc",
    "facts_to_evalitem",
    "first_reported",
    "visible_at",
    "MockConnector",
    "MockConstituentsSource",
]
