# AskEdgar Eval Report

_Generated 2026-05-08 17:15:13_

## 1. Accuracy by Question Type

| System | simple_calc | complex_calc | Overall |
|---|---|---|---|
| **full** | 7/7 (100%) | 16/16 (100%) | 23/23 (100%) |
| **rag_only** | 7/7 (100%) | 16/16 (100%) | 23/23 (100%) |

## 2. Latency & Cost

| System | Avg latency (s) | Input tokens | Output tokens | Est. cost (USD) | Tool calls (total) | Figures produced |
|---|---|---|---|---|---|---|
| **full** | 15.75 | 201 | 18,477 | $1.3888 | 9 | 0 |
| **rag_only** | 13.54 | 142 | 16,605 | $1.2475 | 0 | 0 |

_Cost based on Opus 4.7 list price: $15.0/1M input, $75.0/1M output. Input tokens reported by the SDK exclude prompt-cache hits, so true total compute is higher._

## 3. Paired Comparison (per question)

| ID | Type | full | rag_only | reason (worst case) |
|---|---|---|---|---|
| AAPL-2025-complex-01 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-02 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-03 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-04 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-05 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-06 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-07 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-08 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-09 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-10 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-11 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-12 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-13 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-14 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-15 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-16 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-simple-01 | simple_calc | ✓ | ✓ |  |
| AAPL-2025-simple-02 | simple_calc | ✓ | ✓ |  |
| AAPL-2025-simple-03 | simple_calc | ✓ | ✓ |  |
| AAPL-2025-simple-04 | simple_calc | ✓ | ✓ |  |
| AAPL-2025-simple-05 | simple_calc | ✓ | ✓ |  |
| AAPL-2025-simple-06 | simple_calc | ✓ | ✓ |  |
| AAPL-2025-simple-07 | simple_calc | ✓ | ✓ |  |

## 4. Where the systems diverged

_No questions where full and rag_only disagreed._
