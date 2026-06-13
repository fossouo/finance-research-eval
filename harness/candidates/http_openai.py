"""HTTP candidate — an OpenAI-compatible chat endpoint as the model.

This is the ONLY module that contacts a model (network). It is model-agnostic:
point it at any /v1/chat/completions (a local server, a gateway, etc.). The model
is asked to extract an answer + cite evidence from the provided context; this
adapter assembles the RR and the gates judge it. A weak/hallucinating model will
simply fail the sourcing/verification gates — which is the point.
"""
from __future__ import annotations

import json
import urllib.request

from harness.candidates.base import Candidate, assemble_rr, DEFAULT_CUTOFF

_SYS = (
    "You are a financial analyst. Answer ONLY from the provided CONTEXT. "
    "Return a strict JSON object: "
    '{"answer": <string>, "evidence": [{"figure": <string>, "value": <number>, '
    '"source_doc": <string>, "locator": <string>, "as_of": "YYYY-MM-DD"}]}. '
    "Every number you state must come from CONTEXT and be cited in evidence. "
    "Do not invent sources. Output JSON only, no prose."
)


def _extract_json(text):
    text = (text or "").strip()
    # strip code fences
    if text.startswith("```"):
        text = text.split("```", 2)[1] if "```" in text[3:] else text[3:]
        if text.startswith("json"):
            text = text[4:]
    start = text.find("{")
    if start < 0:
        return {}
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return {}
    return {}


class HttpOpenAICandidate(Candidate):
    name = "http"

    def __init__(self, base_url, model, timeout=120, api_key=None, max_tokens=512):
        # base_url is the full chat-completions URL
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.api_key = api_key
        self.max_tokens = max_tokens

    def _chat(self, user):
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "system", "content": _SYS},
                         {"role": "user", "content": user}],
            "max_tokens": self.max_tokens,
            "temperature": 0,
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(self.base_url, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        msg = (data.get("choices") or [{}])[0].get("message", {}) or {}
        # some servers put text in reasoning when content is exhausted
        return msg.get("content") or msg.get("reasoning") or ""

    def produce_rr(self, eval_item, lane="personal-research"):
        ctx_txt = "\n".join(
            f"- {c.text} [doc={c.source_doc} loc={c.locator} as_of={c.as_of}]"
            for c in (eval_item.context or [])
        ) or "(no context provided)"
        user = f"QUESTION: {eval_item.question}\n\nCONTEXT:\n{ctx_txt}"
        parsed = _extract_json(self._chat(user))
        answer = parsed.get("answer", "")
        evidence = []
        for i, e in enumerate(parsed.get("evidence", []) or []):
            if not isinstance(e, dict):
                continue
            evidence.append({
                "id": f"ev-{i}",
                "figure": str(e.get("figure", "")),
                "value": e.get("value", 0.0),
                "unit": "",
                "source_doc": str(e.get("source_doc", "")),
                "locator": str(e.get("locator", "")),
                "as_of": str(e.get("as_of", "")),
            })
        lane_fields = None
        if lane == "client-mifid":
            lane_fields = {
                "reco_nature": "general-research",
                "disclaimers": ["not a guarantee of performance"],
                "conflicts_of_interest": "none (synthetic demo)",
            }
        return assemble_rr(eval_item, lane, answer, evidence,
                           cutoff=DEFAULT_CUTOFF, lane_fields=lane_fields)
