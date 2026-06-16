"""P5 — Recommendation Record exporter.

Exports individual Recommendation Records (RRs) into durable, portable
artifacts that are distinct from the P4 batch-stats report:

  * ``export_jsonl(rrs, path)``   — JSON Lines bundle: one RR per line, each
    stamped with its evaluation verdict + gate results.
  * ``build_index(rrs)``          — lightweight index dict (id, subject, lane,
    verdict, cutoff, input_hash) suitable for serialisation as index.json.
  * ``format_thesis_card(rr)``    — Markdown "thesis card" for a single RR:
    the analyst-facing document showing provenance, claims, computations, gate
    verdicts, and citations in a layout MARBO can paste into a review note.
  * ``export_bundle(rrs, out_dir)`` — writes everything: index.json,
    <rr-id>.jsonl, and <rr-id>-card.md for every RR in the list.

Design constraints (mirrors the harness):
  - Pure stdlib. No network. Deterministic (zlib.crc32 for run fingerprints,
    hashlib for content hashes — never hash()).
  - Receives already-evaluated RRs (the dict attached by gates.evaluate(), i.e.
    ``Evaluation.augmented_rr``); does NOT call evaluate() itself, so the
    caller controls when/how evaluation happens.
  - Zero real data: synthetic only in the module itself (see offline demo).
  - File writes are isolated to ``export_bundle``; the pure formatters
    (``format_thesis_card``) and pure builders (``build_index``) are
    side-effect-free.

Offline demo (0 VRAM, 0 network):  python3 -m harness.export
"""
from __future__ import annotations

import hashlib
import json
import os


# ---------------------------------------------------------------------------
# JSON Lines bundle
# ---------------------------------------------------------------------------

def export_jsonl(evaluated_rrs: list, path: str) -> int:
    """Write *evaluated_rrs* to a JSON Lines file at *path*.

    Each line is a complete, self-contained JSON object — the augmented RR
    dict (including audit_trail, gate_results, verdict) as returned by
    ``gates.evaluate().augmented_rr``.

    Returns the number of records written.
    """
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    written = 0
    with open(path, "w", encoding="utf-8") as fh:
        for rr in evaluated_rrs:
            line = json.dumps(rr, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            fh.write(line + "\n")
            written += 1
    return written


def load_jsonl(path: str) -> list:
    """Read a JSON Lines bundle back into a list of dicts. Pure stdlib."""
    items = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


# ---------------------------------------------------------------------------
# Index builder
# ---------------------------------------------------------------------------

def build_index(evaluated_rrs: list) -> dict:
    """Return a stable index over a list of evaluated RRs.

    The index contains only metadata (no full claim bodies), making it cheap
    to scan when deciding which full RR to open.

    Structure:
    {
        "count": int,
        "entries": [
            {
                "id": str,
                "subject": str,
                "lane": str,
                "information_cutoff": str,
                "verdict": str,          # ADMISSIBLE | BLOCKED
                "input_hash": str,       # from audit_trail (gate G-2)
                "gates": {G-1: PASS/FAIL/NA, ...},  # gate status map
            },
            ...
        ],
        "admissible": int,
        "blocked": int,
    }
    """
    entries = []
    admissible = 0
    blocked = 0
    for rr in evaluated_rrs:
        at = rr.get("audit_trail") or {}
        gr = rr.get("gate_results") or {}
        # gate_results may be a dict (harness augmentation) or absent
        # Gate status map may live in the Evaluation object; we reconstruct
        # it from the claim-level recomputed fields if needed, but for the
        # index we only need the top-level verdict + input_hash.
        verdict = rr.get("verdict", "UNKNOWN")
        if verdict == "ADMISSIBLE":
            admissible += 1
        elif verdict == "BLOCKED":
            blocked += 1
        # Collect the per-gate status map if stored on the RR by evaluate().
        # gates.evaluate() stores gate_results as {"evaluated_lane": ..., "verdict": ...}
        # on the augmented_rr; individual gate statuses live on the Evaluation
        # object.  The index records whatever gate map was attached by the caller.
        gate_map = rr.get("_gate_status_map") or {}
        entry = {
            "id": rr.get("id", ""),
            "subject": rr.get("subject", ""),
            "lane": rr.get("lane", ""),
            "information_cutoff": rr.get("information_cutoff", ""),
            "verdict": verdict,
            "input_hash": at.get("input_hash", ""),
            "gates": gate_map,
        }
        entries.append(entry)
    return {
        "count": len(entries),
        "admissible": admissible,
        "blocked": blocked,
        "entries": entries,
    }


# ---------------------------------------------------------------------------
# Markdown thesis card
# ---------------------------------------------------------------------------

def format_thesis_card(rr: dict) -> str:
    """Render a single evaluated RR as a Markdown "thesis card".

    The card is the analyst-facing artifact: it shows the company/subject,
    the lane (+ MIF II gate summary), every claim with its sourced evidence
    and recomputed computations, the gate verdict, and the provenance trail.

    The output is intentionally self-contained — a reviewer can read it
    without any other context.
    """
    rr_id = rr.get("id", "unknown")
    subject = rr.get("subject", "—")
    lane = rr.get("lane", "—")
    cutoff = rr.get("information_cutoff", "—")
    verdict = rr.get("verdict", "—")
    at = rr.get("audit_trail") or {}
    input_hash = at.get("input_hash", "—")
    transformations = at.get("transformations") or []
    gate_results_meta = rr.get("gate_results") or {}

    verdict_badge = "ADMISSIBLE" if verdict == "ADMISSIBLE" else "BLOCKED"
    gate_map = rr.get("_gate_status_map") or {}

    lines = [
        f"# Thesis Card — {subject}",
        "",
        f"> **RR id**: `{rr_id}`  ",
        f"> **Lane**: `{lane}`  ",
        f"> **Information cutoff**: `{cutoff}`  ",
        f"> **Verdict**: **{verdict_badge}**  ",
        f"> **Input hash (G-2)**: `{input_hash[:16]}…`  ",
        "",
    ]

    # Gate summary table (from _gate_status_map if present)
    if gate_map:
        lines += [
            "## Gate summary",
            "",
            "| Gate | Status |",
            "|---|---|",
        ]
        for gid in sorted(gate_map.keys()):
            status = gate_map[gid]
            badge = f"**{status}**" if status in ("FAIL", "BLOCKED") else status
            lines.append(f"| {gid} | {badge} |")
        lines.append("")

    # Claims
    claims = rr.get("claims") or []
    if claims:
        lines += ["## Claims", ""]
        for i, claim in enumerate(claims, 1):
            stmt = claim.get("statement", "—")
            kind = claim.get("kind", "—")
            lines.append(f"### Claim {i} ({kind})")
            lines.append("")
            lines.append(f"> {stmt}")
            lines.append("")

            # Evidence
            evidence = claim.get("evidence") or []
            if evidence:
                lines += [
                    "**Evidence**",
                    "",
                    "| id | Figure | Value | Unit | Source | Locator | as_of |",
                    "|---|---|---|---|---|---|---|",
                ]
                for ev in evidence:
                    lines.append(
                        f"| `{ev.get('id', '?')}` "
                        f"| {ev.get('figure', '—')} "
                        f"| {ev.get('value', '—')} "
                        f"| {ev.get('unit', '—')} "
                        f"| `{ev.get('source_doc', '?')}` "
                        f"| `{ev.get('locator', '?')}` "
                        f"| {ev.get('as_of', '?')} |"
                    )
                lines.append("")

            # Computations
            computations = claim.get("computations") or []
            if computations:
                lines += [
                    "**Computations (independent verifier)**",
                    "",
                    "| Metric | Formula | LLM value | Recomputed | Agree |",
                    "|---|---|---|---|---|",
                ]
                for comp in computations:
                    metric = comp.get("metric", "?")
                    formula = comp.get("formula", "?")
                    llm_val = comp.get("llm_value", "?")
                    recomp = comp.get("recomputed_value", "—")
                    agree = comp.get("agree")
                    agree_str = "YES" if agree is True else ("NO" if agree is False else "—")
                    if agree is False:
                        agree_str = f"**NO**"
                    lines.append(
                        f"| `{metric}` "
                        f"| `{formula}` "
                        f"| {llm_val} "
                        f"| {recomp if recomp is None else round(float(recomp), 6) if isinstance(recomp, (int, float)) else recomp} "
                        f"| {agree_str} |"
                    )
                lines.append("")

    # Provenance trail
    lines += [
        "## Provenance",
        "",
        f"- **Transformations**: {', '.join(transformations) if transformations else '—'}",
        f"- **Full input hash (sha256)**: `{input_hash}`",
        f"- **Evaluated lane**: `{gate_results_meta.get('evaluated_lane', lane)}`",
        "",
        "---",
        "",
        "> *Thesis card generated by `harness.export.format_thesis_card`.*  "
        "> *Synthetic/mock data only. Not investment advice.*",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Bundle exporter
# ---------------------------------------------------------------------------

def export_bundle(
    evaluated_rrs: list,
    out_dir: str,
    *,
    include_cards: bool = True,
) -> dict:
    """Write a complete, portable export bundle to *out_dir*.

    Files written:
      - ``index.json``          — lightweight manifest for the bundle
      - ``<sanitised-id>.jsonl``  — single-record JSON Lines (one line) per RR
      - ``<sanitised-id>-card.md`` — Markdown thesis card per RR (if include_cards)

    Returns a summary dict:
    {
        "out_dir": str,
        "index_path": str,
        "records": [{"id": str, "jsonl": str, "card": str | None}, ...]
    }
    """
    os.makedirs(out_dir, exist_ok=True)
    index = build_index(evaluated_rrs)

    # Write index
    index_path = os.path.join(out_dir, "index.json")
    with open(index_path, "w", encoding="utf-8") as fh:
        json.dump(index, fh, sort_keys=True, indent=2, ensure_ascii=False)

    summary_records = []
    for rr in evaluated_rrs:
        rr_id = rr.get("id", "unknown")
        safe_id = _safe_filename(rr_id)

        # Single-record JSONL
        jsonl_path = os.path.join(out_dir, f"{safe_id}.jsonl")
        export_jsonl([rr], jsonl_path)

        # Thesis card
        card_path = None
        if include_cards:
            card_path = os.path.join(out_dir, f"{safe_id}-card.md")
            card_text = format_thesis_card(rr)
            with open(card_path, "w", encoding="utf-8") as fh:
                fh.write(card_text)

        summary_records.append({
            "id": rr_id,
            "jsonl": jsonl_path,
            "card": card_path,
        })

    return {
        "out_dir": out_dir,
        "index_path": index_path,
        "records": summary_records,
    }


def _safe_filename(rr_id: str) -> str:
    """Convert an RR id to a filesystem-safe filename (no path separators,
    colons, or spaces). Uses a sha256 prefix as a tiebreaker when two ids
    would collide after sanitisation."""
    safe = rr_id.replace("/", "-").replace("\\", "-").replace(":", "-")
    safe = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in safe)
    # Avoid excessively long filenames (>200 chars can be problematic on HFS+)
    if len(safe) > 120:
        h = hashlib.sha256(rr_id.encode()).hexdigest()[:8]
        safe = safe[:110] + f"_{h}"
    return safe or "rr-unnamed"


# ---------------------------------------------------------------------------
# Offline demo entry-point
# ---------------------------------------------------------------------------

def main():
    """Demo: evaluate synthetic cases, export a bundle to runs/export-demo/,
    print thesis card for the first admissible record."""
    import tempfile

    from harness.fixtures import cases
    from harness.gates import gates as G

    case_list = cases.all_cases()
    evaluated = []
    for c in case_list:
        ev = G.evaluate(c["rr"])
        aug = ev.augmented_rr
        # Attach the per-gate status map for the thesis card and index.
        aug["_gate_status_map"] = ev.status_map()
        evaluated.append(aug)

    with tempfile.TemporaryDirectory() as tmp:
        result = export_bundle(evaluated, tmp)
        print(f"Bundle written to: {result['out_dir']}")
        print(f"  index: {result['index_path']}")
        for rec in result["records"]:
            print(f"  rr={rec['id']!r}  jsonl={os.path.basename(rec['jsonl'])}  "
                  f"card={os.path.basename(rec['card']) if rec['card'] else 'None'}")

    # Print the thesis card for the first admissible case inline.
    admissible_rrs = [r for r in evaluated if r.get("verdict") == "ADMISSIBLE"]
    if admissible_rrs:
        print()
        print("=" * 72)
        print(format_thesis_card(admissible_rrs[0]))


if __name__ == "__main__":
    main()
