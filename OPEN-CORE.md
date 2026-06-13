# Open-Core Boundary — public framework vs. enterprise stack

> **The contract that decides which side of the line every file lives on.**
> Read this before adding anything to the public repository.

## The one rule

> **Public = the _measurement_ (the standard) + every interface + mock
> implementations + synthetic fixtures.
> Enterprise (private) = the _reality_ (real implementations) + data + ops.**

The public framework defines *what a justifiable, traceable, verifiable financial
analysis is* — and lets anyone measure a candidate against it. The differentiation
lives entirely **behind the interfaces**: real ingestion, FR/EU data, premium
point-in-time, proprietary scoring, MARBO FINANCE integration, operational
compliance, GPU stack, client cases, full automation.

## Why the gates and the Record are PUBLIC on purpose

The evaluation gates (`G-1..G-6`) and the **Recommendation Record** schema are the
*legitimacy asset*. We want them cited, adopted, and treated as the reference for
"is this analysis admissible?". You do **not** protect a standard with copyleft —
you protect it by being the **canonical source** (governance + trademark). So these
are deliberately, fully open.

## The seam: interfaces (public) ↔ implementations (public-mock / private-real)

| Interface (PUBLIC, Apache-2.0) | Public ships | Enterprise ships (private repo) |
|---|---|---|
| `RecommendationRecord` (schema) | **the full standard** | — |
| `Gate` (G-1..G-6) | **the full gate engine** | — |
| `Compute` (deterministic recompute) | reference engine + public formulas | proprietary metrics / scoring |
| `Connector` (data source) | `Connector`/`ConstituentsSource` Protocols + `MockConnector` (E1) | `EdgarConnector`, `TiingoConnector`, real ingestion, dated S&P 500 membership, point-in-time premium |
| `Scorer` | naive reference scorer | proprietary MARBO scoring |
| `ComplianceWorkflow` | the **interface** + the dual-use/MiFID contract | the real operational workflow |
| Fixtures | **synthetic** filings/QA we own | real data, client cases |

**Direction of dependency:** the private `*-enterprise` repo **imports** this public
repo and implements the interfaces. The public repo never imports, references, or
knows about the private one.

## Decision checklist — "does this belong in public?"

A change goes in the **public** repo only if **all** of these are true:

- [ ] It is the standard, an interface, a mock, a synthetic fixture, a test, or docs.
- [ ] It contains **no real market/fundamentals data** and no licensed benchmark data.
- [ ] It contains **no secret, credential, or API key** (not even placeholders that look real).
- [ ] It does **not** implement a real data-provider connector.
- [ ] It does **not** contain proprietary scoring, MARBO integration, or operational compliance logic.
- [ ] It does **not** reveal client cases or private infrastructure topology.

If **any** box is unchecked → it belongs in the **private** repo. When in doubt,
keep it private (you can always open more later; you can never un-publish git history).

## What the public repo redistributes — and what it never does

- ✅ Synthetic fixtures **we created** (owned, safe to publish).
- ✅ **Loaders + pointers** to public benchmarks (FinanceBench, FinQA, ConvFinQA, TAT-QA).
- ❌ **Never** the benchmark data itself (each has its own license).
- ❌ **Never** real filings tied to point-in-time provider terms.

## Anti-leak mechanics

- Physical separation: two repos (public here, enterprise private). This is the
  only hard guarantee — git history is permanent.
- `.gitignore` is deny-by-default for `corpora/`, `data/`, `runs/`, `enterprise/`,
  `connectors/real/`, `*.env`, secrets, and provider artifacts.
- (Opening phase, not P1) a pre-commit / CI check will refuse commits touching
  excluded paths or matching secret patterns. It only makes sense once the repo is
  git-initialized and pushed; P1 stays local with no git. Described now; added at
  repository opening.

## Status

Executable framework (P1–P3) + the `Connector` seam (E1) shipped: schema, gates
G-1..G-6, deterministic compute, public source pointers/loaders, mock candidates,
and `harness/connectors/` (Protocols + `MockConnector` + as-first-reported /
point-in-time utilities). Real connectors remain private. This document is the
binding boundary for everything that follows.
