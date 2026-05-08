"""End-to-end eval pipeline: run_eval -> grader -> aggregate.

One command runs all three stages with fixed filenames between them:

  Stage 1 (API): run both systems on the test set
      -> eval/results/full.json
      -> eval/results/rag_only.json
  Stage 2 (local): grade each result file against ground truth
      -> eval/results/graded_full.json
      -> eval/results/graded_rag_only.json
  Stage 3 (local): aggregate graded files into a markdown report
      -> eval/results/report.md

Each run overwrites the previous files. Use git to keep history.

Usage:
    uv run python -m eval.pipeline                # both systems
    uv run python -m eval.pipeline --system full  # full only (no comparison)
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from eval.aggregate import REPORT_PATH, render_report
from eval.grader import grade_file
from eval.run_eval import (
    RESULTS_DIR,
    TEST_SET,
    _load_stores,
    graded_path,
    results_path,
    run,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", choices=["full", "rag_only", "both"], default="both")
    args = parser.parse_args()

    cases = json.loads(TEST_SET.read_text())
    stores = _load_stores(sorted({c["filing_id"] for c in cases}))
    if not stores:
        print("No filings loadable. Place PDFs in data/filings/<filing_id>.pdf and retry.")
        return

    RESULTS_DIR.mkdir(exist_ok=True)
    systems = ["full", "rag_only"] if args.system == "both" else [args.system]

    # Stage 1: run eval against each system
    raw_paths: list[Path] = []
    for sys_name in systems:
        t0 = time.time()
        rows = run(sys_name, cases, stores)
        out = results_path(sys_name)
        out.write_text(json.dumps(rows, indent=2))
        raw_paths.append(out)
        print(f"\n[eval]  {sys_name}: wrote {out.name} ({len(rows)} rows, {time.time()-t0:.1f}s)")

    # Stage 2: grade each result file
    graded: dict[str, list[dict]] = {}
    for path in raw_paths:
        sys_name = path.stem  # "full.json" -> "full"
        out_path, rows = grade_file(path, TEST_SET)
        graded[sys_name] = rows
        n_ok = sum(1 for r in rows if r.get("correct"))
        print(f"[grade] {sys_name}: {n_ok}/{len(rows)} correct  ->  {out_path.name}")

    # Stage 3: aggregate graded files into a markdown report
    report = render_report(graded)
    REPORT_PATH.write_text(report)
    print(f"\n[report] wrote {REPORT_PATH.name}\n")
    print(report)


if __name__ == "__main__":
    main()
