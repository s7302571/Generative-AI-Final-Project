"""Run the eval test set through both systems and compare.

Each test case names a `filing_id`. The eval expects the matching PDF at
`data/filings/<filing_id>.pdf`. PDFs are indexed once per filing_id and reused
across the questions that hit them.

Usage:
    uv run python -m eval.run_eval                      # both systems
    uv run python -m eval.run_eval --system full        # full system only
    uv run python -m eval.run_eval --system rag_only    # baseline only

Writes per-question results to eval/results/<system>_<timestamp>.json. Scoring
against ground truth is left as a TODO — different question types want
different comparison rules; implement once the test set is real.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from src import config
from src.agent import ask
from src.vectorstore import VectorStore

ROOT = Path(__file__).resolve().parent
TEST_SET = ROOT / "test_set.json"
RESULTS_DIR = ROOT / "results"


def results_path(system: str) -> Path:
    """Fixed filename per system; overwrites previous run."""
    return RESULTS_DIR / f"{system}.json"


def graded_path(system: str) -> Path:
    return RESULTS_DIR / f"graded_{system}.json"


REPORT_PATH = RESULTS_DIR / "report.md"


def _load_stores(filing_ids: list[str]) -> dict[str, VectorStore]:
    stores = {}
    for fid in filing_ids:
        pdf_path = config.FILINGS_DIR / f"{fid}.pdf"
        if not pdf_path.exists():
            print(f"[skip] missing PDF for {fid}: {pdf_path}")
            continue
        print(f"[index] {fid}...", end=" ", flush=True)
        stores[fid] = VectorStore.from_pdf_path(pdf_path, name=fid)
        print(f"{len(stores[fid])} chunks")
    return stores


def run(system: str, cases: list[dict], stores: dict[str, VectorStore]) -> list[dict]:
    enable_tool = system == "full"
    rows = []
    for case in cases:
        store = stores.get(case["filing_id"])
        if store is None:
            rows.append({"id": case["id"], "type": case["type"], "error": "no store"})
            continue
        t0 = time.time()
        expected_keys = list((case.get("expected_values") or {}).keys()) or None
        try:
            resp = ask(
                case["question"],
                store=store,
                enable_tool=enable_tool,
                expected_keys=expected_keys,
            )
            row = {
                "id": case["id"],
                "type": case["type"],
                "answer": resp.answer,
                "structured_answer": resp.structured_answer,
                "tool_calls": len(resp.tool_calls),
                "had_figure": resp.figure is not None,
                "input_tokens": resp.usage.get("input_tokens", 0),
                "output_tokens": resp.usage.get("output_tokens", 0),
                "latency_s": round(time.time() - t0, 2),
                "error": None,
            }
        except Exception as e:
            row = {
                "id": case["id"],
                "type": case["type"],
                "error": str(e),
                "latency_s": round(time.time() - t0, 2),
            }
        rows.append(row)
        print(f"[{system}] {case['id']}: {(row.get('answer') or row.get('error') or '')[:120]}")
    return rows


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
    for sys_name in systems:
        rows = run(sys_name, cases, stores)
        out = results_path(sys_name)
        out.write_text(json.dumps(rows, indent=2))
        print(f"\nWrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
