"""Aggregate graded results from multiple systems into a markdown report.

Reads two or more `eval/results/graded_<system>_<ts>.json` files, computes
per-type accuracy / latency / token usage, and writes a markdown report with:
  - accuracy table by question type, per system
  - paired per-question table (full vs rag_only side by side)
  - cost summary

Usage:
    uv run python -m eval.aggregate eval/results/graded_full_*.json eval/results/graded_rag_only_*.json
    # writes eval/results/report_<ts>.md and prints it
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
REPORT_PATH = RESULTS_DIR / "report.md"
DEFAULT_GRADED = [RESULTS_DIR / "graded_full.json", RESULTS_DIR / "graded_rag_only.json"]

QUESTION_TYPES = ["lookup", "simple_calc", "complex_calc", "viz"]

# Rough Opus 4.7 pricing as of writing (USD per 1M tokens). Used only for a
# ballpark cost figure in the report; update if pricing changes.
PRICE_INPUT_PER_1M = 15.0
PRICE_OUTPUT_PER_1M = 75.0


def _parse_system_name(filename: str) -> str | None:
    m = re.match(r"graded_(.+?)\.json$", filename)
    return m.group(1) if m else None


def _accuracy(rows: list[dict], qtype: str | None = None) -> str:
    pool = [r for r in rows if (qtype is None or r.get("type") == qtype)]
    if not pool:
        return "—"
    n_ok = sum(1 for r in pool if r.get("correct"))
    pct = n_ok / len(pool) * 100
    return f"{n_ok}/{len(pool)} ({pct:.0f}%)"


def _avg(rows: list[dict], key: str) -> float:
    vals = [r.get(key) or 0 for r in rows]
    return sum(vals) / len(vals) if vals else 0


def _sum(rows: list[dict], key: str) -> int:
    return sum((r.get(key) or 0) for r in rows)


def _system_cost(input_tok: int, output_tok: int) -> float:
    return input_tok / 1_000_000 * PRICE_INPUT_PER_1M + output_tok / 1_000_000 * PRICE_OUTPUT_PER_1M


def render_report(systems: dict[str, list[dict]]) -> str:
    md = ["# AskEdgar Eval Report", "",
          f"_Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_", ""]

    md += ["## 1. Accuracy by Question Type", ""]
    header = ["System"] + QUESTION_TYPES + ["Overall"]
    md.append("| " + " | ".join(header) + " |")
    md.append("|" + "|".join(["---"] * len(header)) + "|")
    for sys_name, rows in systems.items():
        cells = [f"**{sys_name}**"] + [_accuracy(rows, t) for t in QUESTION_TYPES] + [_accuracy(rows)]
        md.append("| " + " | ".join(cells) + " |")
    md.append("")

    md += ["## 2. Latency & Cost", ""]
    md.append("| System | Avg latency (s) | Input tokens | Output tokens | Est. cost (USD) | Tool calls (total) | Figures produced |")
    md.append("|---|---|---|---|---|---|---|")
    for sys_name, rows in systems.items():
        avg_lat = _avg(rows, "latency_s")
        in_tok = _sum(rows, "input_tokens")
        out_tok = _sum(rows, "output_tokens")
        cost = _system_cost(in_tok, out_tok)
        tool_calls = _sum(rows, "tool_calls")
        figs = sum(1 for r in rows if r.get("had_figure"))
        md.append(f"| **{sys_name}** | {avg_lat:.2f} | {in_tok:,} | {out_tok:,} | ${cost:.4f} | {tool_calls} | {figs} |")
    md.append("")
    md.append(f"_Cost based on Opus 4.7 list price: ${PRICE_INPUT_PER_1M}/1M input, ${PRICE_OUTPUT_PER_1M}/1M output. Input tokens reported by the SDK exclude prompt-cache hits, so true total compute is higher._")
    md.append("")

    md += ["## 3. Paired Comparison (per question)", ""]
    all_ids = sorted({r["id"] for rows in systems.values() for r in rows})
    sys_names = list(systems.keys())
    md.append("| ID | Type | " + " | ".join(sys_names) + " | reason (worst case) |")
    md.append("|---|---|" + "|".join(["---"] * len(sys_names)) + "|---|")
    for qid in all_ids:
        per_sys = {s: next((r for r in rows if r["id"] == qid), None) for s, rows in systems.items()}
        types = {r["type"] for r in per_sys.values() if r}
        qtype = next(iter(types), "?")
        marks = []
        worst_reason = ""
        for s in sys_names:
            r = per_sys[s]
            if r is None:
                marks.append("?")
                continue
            ok = r.get("correct")
            marks.append("✓" if ok else "✗")
            if not ok and not worst_reason:
                worst_reason = r.get("reason", "")[:140]
        md.append(f"| {qid} | {qtype} | " + " | ".join(marks) + f" | {worst_reason} |")
    md.append("")

    md += ["## 4. Where the systems diverged", ""]
    if len(sys_names) >= 2:
        sa, sb = sys_names[0], sys_names[1]
        a_rows = {r["id"]: r for r in systems[sa]}
        b_rows = {r["id"]: r for r in systems[sb]}
        diffs = []
        for qid in all_ids:
            ra, rb = a_rows.get(qid), b_rows.get(qid)
            if ra and rb and bool(ra.get("correct")) != bool(rb.get("correct")):
                diffs.append((qid, ra, rb))
        if not diffs:
            md.append(f"_No questions where {sa} and {sb} disagreed._")
        else:
            md.append(f"| ID | Type | {sa} | {sb} | losing system's reason |")
            md.append("|---|---|---|---|---|")
            for qid, ra, rb in diffs:
                ma = "✓" if ra.get("correct") else "✗"
                mb = "✓" if rb.get("correct") else "✗"
                losing = rb if not rb.get("correct") else ra
                md.append(f"| {qid} | {ra.get('type')} | {ma} | {mb} | {losing.get('reason', '')[:160]} |")
    md.append("")

    return "\n".join(md)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("graded_files", nargs="*", type=Path,
                        default=DEFAULT_GRADED,
                        help="Graded JSON files (defaults to graded_full.json + graded_rag_only.json)")
    parser.add_argument("--out", type=Path, default=REPORT_PATH)
    args = parser.parse_args()

    systems: dict[str, list[dict]] = {}
    for path in args.graded_files:
        if not path.exists():
            print(f"[skip] {path} does not exist")
            continue
        sys_name = _parse_system_name(path.name)
        if sys_name is None:
            print(f"[skip] {path.name}: cannot parse system name from filename")
            continue
        systems[sys_name] = json.loads(path.read_text())

    if not systems:
        raise SystemExit("no graded files loaded")

    report = render_report(systems)

    out = args.out
    out.write_text(report)
    print(f"Wrote {out}")
    print()
    print(report)


if __name__ == "__main__":
    main()
