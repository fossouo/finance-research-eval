# Public data sources — pointers, not data

This directory wires the harness to **public** evaluation sources. It follows two
hard rules from `OPEN-CORE.md`:

1. **No redistribution.** The repo never bundles a dataset. We ship *pointers*
   (where to get it, license, citation) + *loaders* that read a file **you**
   downloaded. The only committed data are the tiny **synthetic samples** under
   `samples/` — fabricated stand-ins, clearly marked `_synthetic`, never the real
   thing.
2. **No network, no private data, no model.** Loaders read local files only. A
   test (`tests/test_sources.py`) enforces that this package imports no network
   library.

## Where real data goes

Downloaded datasets live under `corpora/` at the repo root, which is **gitignored**
(see `.gitignore`). Nothing under `corpora/` is ever committed.

## Sources (P2)

| id | name | loader | status | how to obtain |
|---|---|---|---|---|
| `financebench` | FinanceBench | `load_financebench` | offline loader | clone patronus-ai/financebench → `corpora/financebench/` |
| `finqa` | FinQA | `load_finqa` | offline loader | czyssrs/FinQA → `corpora/finqa/` |
| `convfinqa` | ConvFinQA | — | **pointer-only** | czyssrs/ConvFinQA → `corpora/convfinqa/` |
| `tatqa` | TAT-QA | — | **pointer-only** | NExTplusplus/TAT-QA → `corpora/tatqa/` |
| `edgar` | SEC EDGAR (company facts) | `load_edgar_companyfacts` | offline loader | fetch companyfacts JSON yourself → `corpora/edgar/` |

`license`, `citation`, `obtain`, and `redistribution_allowed` for each source are
in `registry.py`. Default `redistribution_allowed = False` for every benchmark —
**verify the actual license at the source before bundling**; we don't bundle.

## Try it offline

```bash
python3 -m harness.sources.demo
```

Loads the synthetic samples through the real loaders and prints normalized
`EvalItem` counts — no network, no real data.

## What P2 does NOT do

- It does **not** download anything (you fetch data yourself).
- It does **not** run a model (the candidate arrives in **P3**).
- It does **not** produce answers or recommendations — an `EvalItem` is an INPUT
  (question + grounded context + gold). The context snippets are pre-shaped like
  sourced evidence so a P3 candidate can map them into a Recommendation Record.
