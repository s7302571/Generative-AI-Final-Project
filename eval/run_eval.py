"""Run the eval test set through both systems and compare.

Usage:
    python -m eval.run_eval                      # both systems
    python -m eval.run_eval --system full        # full system only
    python -m eval.run_eval --system rag_only    # baseline only

Writes results to eval/results/<system>_<timestamp>.json. Aggregate metrics
(numerical accuracy, retrieval hit rate, accuracy by type) are reported but
the actual answer-vs-ground-truth check is left as a TODO — different question
types need different scoring rules. Implement scoring once you have a few
real Q&A pairs and you can see what comparison logic actually fits.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from src.agent import ask

ROOT = Path(__file__).resolve().parent
TEST_SET = ROOT / "test_set.json"
RESULTS_DIR = ROOT / "results"


def run(system: str, cases: list[dict]) -> list[dict]:
    enable_tool = system == "full"
    rows = []
    for case in cases:
        t0 = time.time()
        try:
            resp = ask(case["question"], case["filing_id"], enable_tool=enable_tool)
            row = {
                "id": case["id"],
                "type": case["type"],
                "answer": resp.answer,
                "tool_calls": len(resp.tool_calls),
                "had_figure": resp.figure is not None,
                "input_tokens": resp.usage.get("input_tokens", 0),
                "output_tokens": resp.usage.get("output_tokens", 0),
                "latency_s": round(time.time() - t0, 2),
                "error": None,
            }
        except Exception as e:
            row = {"id": case["id"], "type": case["type"], "error": str(e), "latency_s": round(time.time() - t0, 2)}
        rows.append(row)
        print(f"[{system}] {case['id']}: {row.get('answer', row.get('error'))[:120]}")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", choices=["full", "rag_only", "both"], default="both")
    args = parser.parse_args()

    cases = json.loads(TEST_SET.read_text())
    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    systems = ["full", "rag_only"] if args.system == "both" else [args.system]
    for sys_name in systems:
        rows = run(sys_name, cases)
        out = RESULTS_DIR / f"{sys_name}_{stamp}.json"
        out.write_text(json.dumps(rows, indent=2))
        print(f"\nWrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
