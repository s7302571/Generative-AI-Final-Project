# AskEdgar Eval Report

_Generated 2026-05-08 15:50:12_

## 1. Accuracy by Question Type

| System | lookup | simple_calc | complex_calc | viz | Overall |
|---|---|---|---|---|---|
| **full** | 5/7 (71%) | 7/7 (100%) | 8/9 (89%) | 7/7 (100%) | 27/30 (90%) |
| **rag_only** | 6/7 (86%) | 7/7 (100%) | 7/9 (78%) | 7/7 (100%) | 27/30 (90%) |

## 2. Latency & Cost

| System | Avg latency (s) | Input tokens | Output tokens | Est. cost (USD) | Tool calls (total) | Figures produced |
|---|---|---|---|---|---|---|
| **full** | 15.79 | 285 | 20,348 | $1.5304 | 15 | 11 |
| **rag_only** | 11.54 | 193 | 13,259 | $0.9973 | 0 | 0 |

_Cost based on Opus 4.7 list price: $15.0/1M input, $75.0/1M output. Input tokens reported by the SDK exclude prompt-cache hits, so true total compute is higher._

## 3. Paired Comparison (per question)

| ID | Type | full | rag_only | reason (worst case) |
|---|---|---|---|---|
| AAPL-2025-complex-01 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-02 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-03 | complex_calc | ✗ | ✗ | structured_answer.value is null |
| AAPL-2025-complex-04 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-05 | complex_calc | ✓ | ✗ | structured_answer.value is null |
| AAPL-2025-complex-06 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-07 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-08 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-09 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-lookup-01 | lookup | ✓ | ✓ |  |
| AAPL-2025-lookup-02 | lookup | ✓ | ✓ |  |
| AAPL-2025-lookup-03 | lookup | ✓ | ✓ |  |
| AAPL-2025-lookup-04 | lookup | ✓ | ✓ |  |
| AAPL-2025-lookup-05 | lookup | ✓ | ✓ |  |
| AAPL-2025-lookup-06 | lookup | ✗ | ✓ | structured_answer.value is null |
| AAPL-2025-lookup-07 | lookup | ✗ | ✗ | structured_answer.value is null |
| AAPL-2025-simple-01 | simple_calc | ✓ | ✓ |  |
| AAPL-2025-simple-02 | simple_calc | ✓ | ✓ |  |
| AAPL-2025-simple-03 | simple_calc | ✓ | ✓ |  |
| AAPL-2025-simple-04 | simple_calc | ✓ | ✓ |  |
| AAPL-2025-simple-05 | simple_calc | ✓ | ✓ |  |
| AAPL-2025-simple-06 | simple_calc | ✓ | ✓ |  |
| AAPL-2025-simple-07 | simple_calc | ✓ | ✓ |  |
| AAPL-2025-viz-01 | viz | ✓ | ✓ |  |
| AAPL-2025-viz-02 | viz | ✓ | ✓ |  |
| AAPL-2025-viz-03 | viz | ✓ | ✓ |  |
| AAPL-2025-viz-04 | viz | ✓ | ✓ |  |
| AAPL-2025-viz-05 | viz | ✓ | ✓ |  |
| AAPL-2025-viz-06 | viz | ✓ | ✓ |  |
| AAPL-2025-viz-07 | viz | ✓ | ✓ |  |

## 4. Where the systems diverged

| ID | Type | full | rag_only | losing system's reason |
|---|---|---|---|---|
| AAPL-2025-complex-05 | complex_calc | ✓ | ✗ | structured_answer.value is null |
| AAPL-2025-lookup-06 | lookup | ✗ | ✓ | structured_answer.value is null |
