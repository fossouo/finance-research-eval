"""Candidates (P3) — model-agnostic adapters that turn an EvalItem into a
Recommendation Record, which the gates then judge.

A candidate is anything that produces an RR: a deterministic mock (0 VRAM, used
in tests) or an HTTP client to an OpenAI-compatible model endpoint. Per FR-009
the harness measures any candidate; the model is interchangeable and is chosen
downstream, gated by passing the harness.

Network is confined to http_openai.py (the only place a model is contacted).
"""
