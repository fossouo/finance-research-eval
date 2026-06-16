"""finance-research-eval — recevability harness (public core).

Pipeline: synthetic Recommendation Record -> deterministic gates -> local report.
Pure standard library. No data, no model, no network, no GPU.

The judge (gates + deterministic recompute) is independent of the judged party
(any candidate model). See OPEN-CORE.md and harness/schema/ for the standard.
"""

__version__ = "0.2.0"
