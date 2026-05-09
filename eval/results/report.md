# AskEdgar Eval Report

_Generated 2026-05-09 12:08:06_

## 1. Accuracy by Question Type

| System | simple_calc | complex_calc | Overall |
|---|---|---|---|
| **full** | 7/7 (100%) | 16/16 (100%) | 23/23 (100%) |
| **rag_only** | 6/7 (86%) | 15/16 (94%) | 21/23 (91%) |

## 2. Latency & Cost

| System | Avg latency (s) | Input tokens | Output tokens | Est. cost (USD) | Tool calls (total) | Figures produced |
|---|---|---|---|---|---|---|
| **full** | 12.45 | 382 | 24,820 | $1.8672 | 19 | 0 |
| **rag_only** | 12.38 | 390 | 25,257 | $1.9001 | 0 | 0 |

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
| AAPL-2025-complex-11 | complex_calc | ✓ | ✗ | americas_share_pct: got 0.4286, expected 42.86 (diff 99.00%); europe_share_pct: got 0.2668, expected 26.68 (diff 99.00%); greater_china_shar |
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
| AAPL-2025-simple-07 | simple_calc | ✓ | ✗ | got 14.0, expected 13.51 (diff 3.63%) |

## 4. Where the systems diverged

| ID | Type | full | rag_only | losing system's reason |
|---|---|---|---|---|
| AAPL-2025-complex-11 | complex_calc | ✓ | ✗ | americas_share_pct: got 0.4286, expected 42.86 (diff 99.00%); europe_share_pct: got 0.2668, expected 26.68 (diff 99.00%); greater_china_share_pct: got 0.1547, e |
| AAPL-2025-simple-07 | simple_calc | ✓ | ✗ | got 14.0, expected 13.51 (diff 3.63%) |
