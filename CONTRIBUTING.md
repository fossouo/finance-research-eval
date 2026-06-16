# Contributing to finance-research-eval

Thanks for your interest. This is the **public, open-core** repository for a
*recevability framework* for LLM-assisted financial analysis. Please read this
before opening an issue or PR.

## Before anything: what this repo is

- It is **the standard + framework**: Recommendation Record, gates (G-1..G-6),
  deterministic reference computation, synthetic fixtures, mock connectors, docs.
- It is **not** a stock screener, a trading bot, or investment/legal advice.
- The enterprise stack (real data, connectors, scoring, compliance ops) lives in a
  **separate private repository** and is out of scope here. See `OPEN-CORE.md`.

## Sign your commits — DCO (no CLA)

This project uses the **Developer Certificate of Origin** (`DCO`), not a CLA.
Every commit must be signed off with your real name:

```
git commit -s -m "your message"
```

which appends:

```
Signed-off-by: Your Name <you@example.com>
```

By signing off you certify the `DCO`. Pseudonymous sign-offs are not accepted.
Because the code is Apache-2.0 (inbound = outbound), the DCO is sufficient — there
is no contributor agreement to sign.

## What belongs here (and what doesn't)

Run the **decision checklist** in `OPEN-CORE.md` before contributing. In short, a
contribution is welcome here **only** if it contains:

- ✅ standard / interface / mock / synthetic fixture / test / docs

and contains **none** of:

- ❌ real market or fundamentals data
- ❌ licensed benchmark data (ship a loader + pointer, never the data)
- ❌ secrets, credentials, or realistic-looking keys
- ❌ real data-provider connectors
- ❌ proprietary scoring, MARBO integrations, or operational compliance logic
- ❌ private infrastructure details or client cases

If your idea is real-data or enterprise-flavored, it does not go in this repo.

## Standard changes are high-scrutiny

Changes to a **gate**, to the **Recommendation Record schema**, or to the
**dual-use contract** change the standard itself. They require a proposal
(issue or PR description explaining the rationale + impact), Maintainer approval,
a `CHANGELOG.md` entry, and a version bump per `GOVERNANCE.md`.

## Pull request expectations

- One focused change per PR.
- Commits signed off (`-s`).
- Docs updated when behavior/standard changes.
- Tests pass (`python3 -m unittest discover -s tests -t .`) and no excluded path is
  touched. Synthetic fixtures only — never add real data to make a test pass.

## A note on the subject matter

This project deals with finance and a MiFID II / AMF compliance contract that is an
**engineering proposal, not validated legal advice**. Do not represent any output
of this framework as regulated financial advice. See `SECURITY.md` and
`.specify/specs/finance-research-eval/dual-use-contract.md`.

## Status

The core framework is **shipped and public**: Recommendation Record, gates
G-1..G-6, deterministic recompute, public source loaders (pointers), model-agnostic
candidates, batch reporting, and RR export — all pure stdlib, with a green test
suite. Contributions are welcome (code, tests, fixtures, docs) within the scope
defined in [`OPEN-CORE.md`](OPEN-CORE.md). Real data, live connectors, and
proprietary scoring belong to the separate private enterprise edition.
