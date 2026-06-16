"""Candidates — model-agnostic adapters that turn an EvalItem into a
Recommendation Record, which the gates then judge.

A candidate is anything that produces an RR: a deterministic mock (0 VRAM, used
in tests) or an HTTP client to an OpenAI-compatible model endpoint. The harness is
model-agnostic by design — any candidate is interchangeable as long as it satisfies
the RR contract; the model is chosen downstream, gated by passing the harness.

Network is confined to http_openai.py (the only place a model is contacted).
"""
