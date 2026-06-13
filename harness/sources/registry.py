"""Registry of public data sources — POINTERS ONLY.

This is the canonical "where to get it / what you may do with it" list. The repo
does not redistribute any dataset. For each source we record how to obtain it
yourself, its license, and whether redistribution is permitted (default: NO).

Conservative policy: ``redistribution_allowed`` defaults to False for every
benchmark — verify each dataset's actual license at the source before bundling.
We choose not to bundle any data regardless.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    homepage: str
    obtain: str                 # how to download it yourself
    license: str
    citation: str
    fmt: str                    # expected local file format
    loader: str = ""            # loader function name in loaders.py ("" = pointer-only)
    redistribution_allowed: bool = False
    local_path_hint: str = ""   # where to put the file (under corpora/, gitignored)
    sample: str = ""            # committed synthetic sample filename (offline)


SOURCES = {
    "financebench": Source(
        id="financebench",
        name="FinanceBench",
        homepage="https://github.com/patronus-ai/financebench",
        obtain="Clone the repo / download the open-source split; place the JSONL under corpora/financebench/.",
        license="Verify at source before any redistribution (treat as restricted).",
        citation="Islam et al., FinanceBench: A New Benchmark for Financial Question Answering, 2023.",
        fmt="jsonl",
        loader="load_financebench",
        local_path_hint="corpora/financebench/financebench_open_source.jsonl",
        sample="financebench_sample.jsonl",
    ),
    "finqa": Source(
        id="finqa",
        name="FinQA",
        homepage="https://github.com/czyssrs/FinQA",
        obtain="Download train/dev/test JSON from the FinQA repo; place under corpora/finqa/.",
        license="Verify at source before any redistribution (treat as restricted).",
        citation="Chen et al., FinQA: A Dataset of Numerical Reasoning over Financial Data, EMNLP 2021.",
        fmt="json",
        loader="load_finqa",
        local_path_hint="corpora/finqa/test.json",
        sample="finqa_sample.json",
    ),
    "convfinqa": Source(
        id="convfinqa",
        name="ConvFinQA",
        homepage="https://github.com/czyssrs/ConvFinQA",
        obtain="Download from the ConvFinQA repo; place under corpora/convfinqa/.",
        license="Verify at source before any redistribution (treat as restricted).",
        citation="Chen et al., ConvFinQA: Exploring the Chain of Numerical Reasoning in Conversational Finance, EMNLP 2022.",
        fmt="json",
        loader="",  # pointer-only in P2
        local_path_hint="corpora/convfinqa/dev.json",
    ),
    "tatqa": Source(
        id="tatqa",
        name="TAT-QA",
        homepage="https://github.com/NExTplusplus/TAT-QA",
        obtain="Download from the TAT-QA repo; place under corpora/tatqa/.",
        license="Verify at source before any redistribution (treat as restricted).",
        citation="Zhu et al., TAT-QA: A Question Answering Benchmark on a Hybrid of Tabular and Textual Content in Finance, ACL 2021.",
        fmt="json",
        loader="",  # pointer-only in P2
        local_path_hint="corpora/tatqa/tatqa_dataset_test.json",
    ),
    "edgar": Source(
        id="edgar",
        name="SEC EDGAR (company facts)",
        homepage="https://www.sec.gov/edgar/sec-api-documentation",
        obtain="Fetch companyfacts JSON yourself (respect SEC fair-access / User-Agent rules); place under corpora/edgar/.",
        license="U.S. government work — public domain. We still do not bundle it.",
        citation="U.S. Securities and Exchange Commission, EDGAR.",
        fmt="json",
        loader="load_edgar_companyfacts",
        redistribution_allowed=True,  # public domain; we choose not to ship it anyway
        local_path_hint="corpora/edgar/CIK##########.json",
        sample="edgar_companyfacts_sample.json",
    ),
}


def get(source_id: str) -> Source:
    if source_id not in SOURCES:
        raise KeyError(f"unknown source: {source_id!r} (known: {sorted(SOURCES)})")
    return SOURCES[source_id]


def list_sources():
    return sorted(SOURCES.keys())
