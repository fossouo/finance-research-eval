# Changelog

All notable changes to the **standard** and the framework are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
the project follows [Semantic Versioning](https://semver.org/) at the repo level.

Gate IDs (`G-1`..`G-6`) are stable and never reused. A breaking change to the
Recommendation Record schema or to any gate's pass/fail semantics is a **major** bump.

## [Unreleased]

> **Current state:** public open-core, test suite **163 green** (stdlib, no network).
> Per-phase counts below are historical snapshots at the time each block shipped.

### Added (Patrimoine / CGP worked case)
- `harness/fixtures/cases_patrimoine.py`: MEDISYN SA, a synthetic mid-cap pharma. Two companion `client-mifid` general-research notes — one **ADMISSIBLE** (every computation recomputes exactly) and one **BLOCKED** (a fabricated EV/EBITDA of 6.5× vs a recomputed 9.0× → G-3 FAIL → G-5 propagates). Demonstrates the verifier refusing, not softening, a "cheap multiple" the evidence does not support.
- `docs/usage-patrimoine-dossier-client.md`: step-by-step guide for using the harness on a fictitious client dossier (run both notes, read the verdict, adapt to your own synthetic case). 100 % offline/synthetic; production sources/models remain locked.
- `tests/test_cases_patrimoine.py`: 19 tests — lane/reco_nature/no-suitability invariants, admissible all-PASS, rejected isolated to G-3/G-5, no real-ISIN leak.

### Added (P5 — RR exporter + FICTEX SA worked case)
- `harness/export.py`: durable RR archival — `export_jsonl`/`load_jsonl` (one JSON Lines bundle per RR), `build_index` (lightweight `index.json` manifest: id, lane, verdict, hash, gates), `format_thesis_card` (Markdown analyst artifact: provenance, claims, evidence table, independent-recompute table, gate summary), `export_bundle` (writes `index.json` + per-RR `.jsonl` + `*-card.md` to a caller-supplied `out_dir`). Local file I/O only — **no network**.
- `harness/fixtures/cases_worked.py`: **FICTEX SA**, a synthetic mid-cap internally consistent across all 7 metrics; exercises G-1..G-6 end-to-end on both lanes; `comparable_ev` demonstrates peer-multiple valuation. `build_worked_case()` / `run_worked_case()`.
- `tests/test_export.py`: 69 tests — RR structure/determinism, JSONL roundtrip, index counts, thesis-card sections, bundle idempotency, full conformity catalogue, ISIN guard. **stdlib pur, offline, fixtures synthétiques, aucune donnée client réelle, aucun connecteur réel, aucun secret.**

### Added (P4 — batch runner + Markdown/CSV report)
- `harness/report.py`: `batch_run()` (N candidates × M lanes × K item-sets → aggregated gate stats, admissibility/accuracy rates, deterministic `run_id` via `zlib.crc32`, stable across runs), `format_markdown()` (human-readable report: overview, aggregate, per-run breakdown, gate statistics, key findings), `format_csv()` (flat one-row-per-record export, stable column order). `python3 -m harness.report` offline demo entry-point.
- `tests/test_report.py`: 41 tests — batch structure, run-count, `run_id` stability, aggregate invariants, faithful/sloppy discrimination, Markdown headings/disclaimer, CSV header/verdict columns. **stdlib pur, offline, fixtures synthétiques, aucune donnée réelle, aucun connecteur, aucun secret.**

### Added (Phase 3 — candidate/model branched, end-to-end)
- `harness/candidates/`: model-agnostic candidate adapters. `base.assemble_rr` (EvalItem→RR), `mock.py` (FaithfulMock + SloppyMock, deterministic, 0 VRAM), `http_openai.py` (any OpenAI-compatible endpoint; the only networked module).
- `harness/eval_run.py`: end-to-end `EvalItem → candidate → RR → gates → report`, scoring recevability AND accuracy separately (FR-011). `python3 -m harness.eval_run` (offline mock demo).
- `tests/test_candidates_e2e.py`: proves the loop and the discrimination — a faithful candidate is admissible+accurate; a sloppy (unsourced) one is BLOCKED on the client lane though its answer is correct ("right but inadmissible").

### Notes (Phase 3)
- Offline e2e: full suite 23/23 OK; faithful→all admissible, sloppy→blocked on client lane.
- Live proof: ran `http_openai` against a pre-loaded OpenAI-compatible endpoint — **0 new VRAM**. The real model returned correct numbers but unsourced/undated → gates G-1/G-4 failed → BLOCKED on the client lane. The thesis, demonstrated with a real LLM.
- Published as public open-core (separate private enterprise repo for real data/connectors).

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
