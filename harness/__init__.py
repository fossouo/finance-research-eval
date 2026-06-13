"""finance-research-eval — recevability harness (public core).

Phase 1 (dry harness): synthetic Recommendation Record -> deterministic gates
-> local report. Pure standard library. No data, no model, no network, no GPU.

The judge (gates + deterministic recompute) is independent of the judged party
(any future LLM candidate). See OPEN-CORE.md and .specify/ for the standard.
"""

__version__ = "0.1.0-p1"
