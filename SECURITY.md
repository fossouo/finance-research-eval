# Security & Responsible Use

## Reporting a vulnerability

If you discover a security issue (e.g., a way the framework could leak secrets, a
flaw in a gate that lets unsourced numbers pass, or a path-exclusion bypass), please
report it **privately** rather than opening a public issue.

- Contact: **fossouodonald@gmail.com**.
- Please include: a description, reproduction steps, and the potential impact.
- We aim to acknowledge within a reasonable delay and to coordinate disclosure.

Do **not** include real credentials, real client data, or licensed datasets in a
report. Use synthetic examples.

## Two security surfaces specific to this project

### 1. Leak prevention (open-core hygiene)
The most damaging "vulnerability" here is **publishing something private**. If you
find that the public repo tracks, or could be made to track, real data, secrets, or
a real connector — that is a security issue. See `.gitignore` and `OPEN-CORE.md`.

### 2. Gate integrity (the standard's trustworthiness)
A bug that lets a **non-admissible** Recommendation Record pass a gate (an
unsourced number through G-1, an unverified computation through G-3, a look-ahead
through G-4, a non-promoted personal→client output through G-6) **undermines the
standard itself**. Treat such bugs as high severity.

## Responsible use — read this

This framework is **decision-support, not execution** (constitution P-7). It:

- is **NOT** investment advice;
- is **NOT** legal advice;
- does **NOT** place orders or move money, and must never be wired to do so.

The MiFID II / AMF dual-use contract is an **engineering proposal**. Before any use
that constitutes regulated financial advice, have it validated by qualified
compliance / legal counsel. Outputs must carry the disclaimers defined in the
dual-use contract and must never be presented as a guarantee of performance.
