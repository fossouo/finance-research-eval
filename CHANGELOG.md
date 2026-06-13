# Changelog

All notable changes to the **standard** and the framework are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
the project follows [Semantic Versioning](https://semver.org/) at the repo level.

Gate IDs (`G-1`..`G-6`) are stable and never reused. A breaking change to the
Recommendation Record schema or to any gate's pass/fail semantics is a **major** bump.

## [Unreleased]

### Added (Phase 3 — candidate/model branched, end-to-end)
- `harness/candidates/`: model-agnostic candidate adapters. `base.assemble_rr` (EvalItem→RR), `mock.py` (FaithfulMock + SloppyMock, deterministic, 0 VRAM), `http_openai.py` (any OpenAI-compatible endpoint; the only networked module).
- `harness/eval_run.py`: end-to-end `EvalItem → candidate → RR → gates → report`, scoring recevability AND accuracy separately (FR-011). `python3 -m harness.eval_run` (offline mock demo).
- `tests/test_candidates_e2e.py`: proves the loop and the discrimination — a faithful candidate is admissible+accurate; a sloppy (unsourced) one is BLOCKED on the client lane though its answer is correct ("right but inadmissible").

### Notes (Phase 3)
- Offline e2e: full suite 23/23 OK; faithful→all admissible, sloppy→blocked on client lane.
- Live proof: ran `http_openai` against a pre-loaded OpenAI-compatible endpoint — **0 new VRAM**. The real model returned correct numbers but unsourced/undated → gates G-1/G-4 failed → BLOCKED on the client lane. The thesis, demonstrated with a real LLM.
- Next: **Ouverture** (git init, emails, CI, hooks, `-enterprise` repo, push) — only when the standard is deemed clear enough.

### Added (Phase 2 — public source loaders, offline)
- `harness/sources/registry.py`: pointer registry for public sources (FinanceBench, FinQA, ConvFinQA, TAT-QA, SEC EDGAR) — homepage, obtain-it-yourself, license, citation, `redistribution_allowed` (default False). No data bundled.
- `harness/sources/evalitem.py`: normalized `EvalItem` (question + grounded context + gold), the seam to a P3 candidate.
- `harness/sources/loaders.py`: offline parsers for FinanceBench (JSONL), FinQA (JSON), EDGAR companyfacts (JSON). Read LOCAL files only; raise `SourceDataMissing` rather than fetch. ConvFinQA/TAT-QA are pointer-only.
- `harness/sources/samples/`: tiny SYNTHETIC samples (marked `_synthetic`) so loaders+tests run fully offline — never the real datasets.
- `harness/sources/demo.py`: `python3 -m harness.sources.demo` (offline normalization demo).
- `harness/sources/README.md`: how to obtain each dataset; corpora/ is gitignored.
- `tests/test_sources.py`: registry completeness, synthetic-sample validity, EDGAR point-in-time anchor, missing-file-raises (no fetch), pointer-only refusal, and a **no-network-import** guard.

### Notes (Phase 2)
- No network, no private data, no model. Real datasets live under `corpora/` (gitignored, never committed); only fabricated samples are versioned.
- Verified locally: full suite 19/19 OK; demo loads 7 synthetic EvalItems across 3 loaders.
- Next: **P3** — a candidate/model branched locally maps EvalItems into Recommendation Records and runs the gates, on public/synthetic data only.

### Added (Phase 1 — dry harness, local)
- `harness/schema/recommendation_record.schema.json`: machine-readable RR standard (JSON Schema 2020-12).
- `harness/rr.py`: canonical content hashing (G-2) + lightweight structural validator (stdlib only).
- `harness/compute/metrics.py`: deterministic reference computation engine (9 metrics) feeding G-3.
- `harness/gates/gates.py`: gates G-1..G-6 as pure functions + per-lane severity matrix + verdict.
- `harness/fixtures/`: synthetic RR builders + a 10-case conformity catalogue (baseline + one per failure mode).
- `harness/runner.py`: `fixtures → gates → local report` (writes `runs/p1_dry_report.json`, gitignored).
- `tests/`: 12 stdlib `unittest` tests incl. the locked conformity table (deterministic-verifier analogue). All green.
- `pyproject.toml`: zero runtime dependencies; CI extras (`jsonschema`, `pytest`) deferred to Opening.

### Notes (Phase 1)
- Pure standard library. No data, no model, no network, no GPU, no `git`. Synthetic fixtures only.
- Verified locally: `python3 -m unittest discover -s tests -t .` → 12/12 OK; runner → 10 cases, 0 verdict mismatches.
- Next: **P2** — public loaders (benchmarks + EDGAR pointers), still no private data.

### Added (Phase 0 — design-only)
- Constitution (`.specify/memory/constitution.md`): central question + principles P-1..P-7.
- SDD spec (`spec.md`): FR-001..FR-012, the Recommendation Record (RR) artifact.
- Harness structure (`harness-structure.md`): future layout, described not built.
- Dual-use contract (`dual-use-contract.md`): personal-research / client-mifid lanes.
- Evaluation gates (`eval-gates.md`): G-1 sourcing · G-2 audit-trail · G-3 independent
  computation · G-4 point-in-time · G-5 client-block · G-6 cloisonnement.
- Open-core boundary (`OPEN-CORE.md`): public framework vs. enterprise stack.
- Licensing: Apache-2.0 (code), CC-BY-4.0 (docs), DCO (contributions), trademark policy.
- Governance, contributing, security, code of conduct.

### Notes
- No executable code, no data, no network calls. Phase 0 is specification only.
  (Superseded by Phase 1 above, which adds the local dry harness.)
