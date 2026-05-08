"""Grade an eval results file against the test set's ground truth.

Reads `eval/test_set.json` for ground truth and one or more
`eval/results/<system>_<ts>.json` files written by `run_eval.py`. For each
question, decides correct vs incorrect based on the question type:

  - lookup:        structured_answer["value"] exact match
  - simple_calc:   numeric within tolerance_pct
  - complex_calc:  if expected_values present, every key within tolerance;
                   otherwise treat like simple_calc
  - viz:           every key in expected_values must appear in
                   structured_answer within tolerance

Writes `eval/results/graded_<system>_<ts>.json` next to the input. Each row
contains {id, type, correct, reason, predicted, ground_truth, ...metrics}.

Usage:
    uv run python -m eval.grader eval/results/full_20260508_103416.json
    uv run python -m eval.grader eval/results/full_*.json eval/results/rag_only_*.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_TEST_SET = ROOT / "test_set.json"


def _within_tolerance(pred: float, gt: float, tolerance_pct: float) -> bool:
    if gt == 0:
        return abs(pred) <= tolerance_pct / 100
    return abs(pred - gt) / abs(gt) <= tolerance_pct / 100


def _is_number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _str_eq(a, b) -> bool:
    return isinstance(a, str) and isinstance(b, str) and a.strip().lower() == b.strip().lower()


def _grade_value(pred, gt, tolerance_pct: float) -> tuple[bool, str]:
    """Compare a single predicted value against ground truth."""
    if pred is None:
        return False, "structured_answer.value is null"
    if _is_number(gt) and _is_number(pred):
        if _within_tolerance(pred, gt, tolerance_pct):
            return True, f"within {tolerance_pct}% (got {pred}, expected {gt})"
        diff = abs(pred - gt) / abs(gt) * 100 if gt else float("inf")
        return False, f"got {pred}, expected {gt} (diff {diff:.2f}%)"
    if isinstance(gt, str):
        if _str_eq(pred, gt):
            return True, f"category match: '{pred}'"
        return False, f"got {pred!r}, expected {gt!r}"
    return False, f"type mismatch: pred={type(pred).__name__} gt={type(gt).__name__}"


def _grade_expected_values(structured: dict, expected: dict, tolerance_pct: float) -> tuple[bool, str]:
    """Every key in `expected` must appear in `structured` within tolerance."""
    misses = []
    for key, gt in expected.items():
        pred = structured.get(key)
        ok, why = _grade_value(pred, gt, tolerance_pct)
        if not ok:
            misses.append(f"{key}: {why}")
    if not misses:
        return True, f"all {len(expected)} fields ok"
    return False, "; ".join(misses)


def grade_row(case: dict, row: dict) -> dict:
    """Grade one (case, row) pair. Returns a dict ready to dump to JSON."""
    base = {
        "id": row["id"],
        "type": case["type"],
        "latency_s": row.get("latency_s"),
        "input_tokens": row.get("input_tokens"),
        "output_tokens": row.get("output_tokens"),
        "tool_calls": row.get("tool_calls"),
        "had_figure": row.get("had_figure"),
        "structured_answer": row.get("structured_answer"),
        "ground_truth": case.get("answer", case.get("expected_values")),
    }
    if row.get("error"):
        return {**base, "correct": False, "reason": f"runtime error: {row['error']}"}

    structured = row.get("structured_answer")
    if structured is None:
        return {
            **base,
            "correct": False,
            "reason": "model did not produce <answer_json> block (or it was unparseable)",
        }

    qtype = case["type"]
    tolerance = case.get("tolerance_pct") or 0.0

    if qtype == "lookup":
        ok, reason = _grade_value(structured.get("value"), case["answer"], tolerance)
    elif qtype == "simple_calc":
        ok, reason = _grade_value(structured.get("value"), case["answer"], tolerance)
    elif qtype == "complex_calc":
        if case.get("expected_values"):
            ok, reason = _grade_expected_values(structured, case["expected_values"], tolerance)
        else:
            ok, reason = _grade_value(structured.get("value"), case["answer"], tolerance)
    elif qtype == "viz":
        ok, reason = _grade_expected_values(structured, case["expected_values"], tolerance)
    else:
        ok, reason = False, f"unknown question type: {qtype}"

    return {**base, "correct": ok, "reason": reason}


def grade_file(results_path: Path, test_set_path: Path) -> tuple[Path, list[dict]]:
    cases = {c["id"]: c for c in json.loads(test_set_path.read_text())}
    rows = json.loads(results_path.read_text())
    graded = []
    for row in rows:
        case = cases.get(row["id"])
        if case is None:
            graded.append({
                "id": row["id"],
                "correct": False,
                "reason": "no matching case in test_set.json",
            })
            continue
        graded.append(grade_row(case, row))

    out_path = results_path.parent / f"graded_{results_path.name}"
    out_path.write_text(json.dumps(graded, indent=2))
    return out_path, graded


DEFAULT_RESULTS = [ROOT / "results" / "full.json", ROOT / "results" / "rag_only.json"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results_files", nargs="*", type=Path,
                        default=DEFAULT_RESULTS,
                        help="One or more eval/results/<system>.json files (defaults to full.json + rag_only.json)")
    parser.add_argument("--test-set", type=Path, default=DEFAULT_TEST_SET)
    args = parser.parse_args()

    if not args.test_set.exists():
        raise SystemExit(f"test set not found: {args.test_set}")

    for path in args.results_files:
        if not path.exists():
            print(f"[skip] {path} does not exist")
            continue
        out, graded = grade_file(path, args.test_set)
        n_ok = sum(1 for g in graded if g.get("correct"))
        print(f"{path.name}: {n_ok}/{len(graded)} correct  ->  {out.name}")
        for g in graded:
            mark = "✓" if g.get("correct") else "✗"
            print(f"  {mark}  {g['id']:30s}  {g.get('reason', '')[:120]}")


if __name__ == "__main__":
    main()
