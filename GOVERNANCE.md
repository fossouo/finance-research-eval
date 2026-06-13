# Governance

> How decisions are made and how the standard evolves. The goal is for this
> repository to remain the **canonical source** of the financial-analysis
> recevability standard.

## Stewardship

- **finance-research-eval** is stewarded by **MARBO FINANCE** (the "Maintainer").
- The Maintainer is the final decision authority during the project's early phase
  (BDFL-style), with the explicit intent to move toward a lightweight committee
  as an external contributor community forms.

## Scope of the standard

The public project governs **one thing**: *what makes an LLM-assisted financial
analysis admissible* — the Recommendation Record, the gates (G-1..G-6), the
deterministic-verification principle, point-in-time awareness, and the dual-use
contract. Changes to that standard are the highest-scrutiny changes in the repo.

## Change classes

| Class | Examples | Process |
|---|---|---|
| **Standard change** | new/edited gate, RR schema change, dual-use contract | Proposal (issue/PR) → discussion → Maintainer approval → `CHANGELOG` + version bump |
| **Reference impl** | reference compute, mock connectors, runner | Normal PR review (DCO signed) |
| **Docs / fixtures** | synthetic fixtures, docs, examples | Normal PR review |
| **Boundary change** | anything touching `OPEN-CORE.md` | Maintainer-only; never weakens anti-leak rules |

## Versioning the standard

- The standard follows **SemVer** at the repository level.
- A **breaking** change to the RR schema or to any gate's pass/fail semantics is a
  **major** bump and must be recorded in `CHANGELOG.md` with a migration note.
- Gates are referenced by stable IDs (`G-1`..`G-6`); IDs are never reused.

## Principles that cannot be silently changed

These come from `.specify/memory/constitution.md` (P-1..P-7) and require an
explicit, documented decision to amend:

- Facts never live in model weights (P-1).
- Every quantitative claim is sourced (P-2).
- Every computation is independently verifiable, judge ≠ judged (P-3).
- Point-in-time awareness (P-4).
- Immutable audit-trail (P-5).
- Dual-use cloisonnement & non-promotion (P-6).
- Decision-support, never execution (P-7).

## Decision record

Significant standard/architecture decisions are captured as short ADR-style notes
under `docs/decisions/` (added when the first such decision is made).

## Conflicts of interest

MARBO FINANCE ships a commercial enterprise edition built on this framework. To
keep the public standard trustworthy: the **public gates and RR are never weakened
to favor the enterprise edition**, and any change that would advantage the private
edition at the expense of the open standard is out of scope for this repo.
