"""The normalized evaluation item — the bridge between a public benchmark/source
and the recevability harness.

An EvalItem is purely an INPUT (a question + grounded context + a gold answer).
P2 stops here: it does NOT produce an answer (that is a candidate's job in P3).
The context snippets are already shaped like sourced evidence, so a future
candidate can map an EvalItem into a Recommendation Record with real locators.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class ContextSnippet:
    text: str
    source_doc: str = ""
    locator: str = ""
    as_of: str = ""          # ISO date when known (feeds future point-in-time / G-4)


@dataclass
class EvalItem:
    source: str              # registry id, e.g. "financebench"
    item_id: str             # id within the source
    question: str
    gold_answer: str = ""
    gold_kind: str = "text"  # "numeric" | "text"
    context: list = field(default_factory=list)   # list[ContextSnippet]
    meta: dict = field(default_factory=dict)

    def validate(self) -> list:
        errs = []
        if not self.source:
            errs.append("missing source")
        if not self.item_id:
            errs.append("missing item_id")
        if not self.question:
            errs.append("missing question")
        if self.gold_kind not in ("numeric", "text"):
            errs.append(f"invalid gold_kind: {self.gold_kind!r}")
        if self.gold_kind == "numeric":
            try:
                float(self.gold_answer)
            except (TypeError, ValueError):
                errs.append(f"numeric gold not parseable: {self.gold_answer!r}")
        return errs

    def is_synthetic(self) -> bool:
        return bool(self.meta.get("synthetic"))

    def to_dict(self) -> dict:
        return asdict(self)
