"""Public data sources — pointers + offline loaders (P2).

This package NEVER downloads and NEVER bundles real datasets. It provides:
  - a registry of public sources (where to get them, license, no-redistribution),
  - loaders that normalize a LOCALLY-PRESENT file into canonical EvalItems,
  - tiny SYNTHETIC samples (fabricated, not the real data) so tests run offline.

No network. No private data. No model (that arrives in P3).
"""
