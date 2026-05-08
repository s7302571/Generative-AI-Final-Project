# AskEdgar Eval Report

_Generated 2026-05-08 12:17:19_

## 1. Accuracy by Question Type

| System | lookup | simple_calc | complex_calc | viz | Overall |
|---|---|---|---|---|---|
| **full** | 6/7 (86%) | 7/7 (100%) | 4/9 (44%) | 3/7 (43%) | 20/30 (67%) |
| **rag_only** | 6/7 (86%) | 7/7 (100%) | 3/9 (33%) | 3/7 (43%) | 19/30 (63%) |

## 2. Latency & Cost

| System | Avg latency (s) | Input tokens | Output tokens | Est. cost (USD) | Tool calls (total) | Figures produced |
|---|---|---|---|---|---|---|
| **full** | 14.67 | 285 | 20,007 | $1.5048 | 15 | 10 |
| **rag_only** | 11.23 | 191 | 14,260 | $1.0724 | 0 | 0 |

_Cost based on Opus 4.7 list price: $15.0/1M input, $75.0/1M output. Input tokens reported by the SDK exclude prompt-cache hits, so true total compute is higher._

## 3. Paired Comparison (per question)

| ID | Type | full | rag_only | reason (worst case) |
|---|---|---|---|---|
| AAPL-2025-complex-01 | complex_calc | ✗ | ✗ | products_gross_margin_pct: structured_answer.value is null; services_gross_margin_pct: structured_answer.value is null |
| AAPL-2025-complex-02 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-03 | complex_calc | ✗ | ✗ | structured_answer.value is null |
| AAPL-2025-complex-04 | complex_calc | ✗ | ✗ | iphone_change: structured_answer.value is null; mac_change: structured_answer.value is null; ipad_change: structured_answer.value is null; w |
| AAPL-2025-complex-05 | complex_calc | ✓ | ✗ | structured_answer.value is null |
| AAPL-2025-complex-06 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-07 | complex_calc | ✓ | ✓ |  |
| AAPL-2025-complex-08 | complex_calc | ✗ | ✗ | fy2023_services_share_pct: structured_answer.value is null; fy2025_services_share_pct: structured_answer.value is null; change_pct_points: s |
| AAPL-2025-complex-09 | complex_calc | ✗ | ✗ | fy2023_rd_intensity_pct: structured_answer.value is null; fy2025_rd_intensity_pct: structured_answer.value is null; change_pct_points: struc |
| AAPL-2025-lookup-01 | lookup | ✓ | ✓ |  |
| AAPL-2025-lookup-02 | lookup | ✓ | ✓ |  |
| AAPL-2025-lookup-03 | lookup | ✓ | ✓ |  |
| AAPL-2025-lookup-04 | lookup | ✓ | ✓ |  |
| AAPL-2025-lookup-05 | lookup | ✓ | ✓ |  |
| AAPL-2025-lookup-06 | lookup | ✓ | ✓ |  |
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
| AAPL-2025-viz-03 | viz | ✗ | ✗ | operating_income_2023: structured_answer.value is null; operating_income_2024: structured_answer.value is null; operating_income_2025: struc |
| AAPL-2025-viz-04 | viz | ✗ | ✗ | iphone: structured_answer.value is null; mac: structured_answer.value is null; ipad: structured_answer.value is null; wearables_home_accesso |
| AAPL-2025-viz-05 | viz | ✗ | ✗ | diluted_eps_2023: structured_answer.value is null; diluted_eps_2024: structured_answer.value is null; diluted_eps_2025: structured_answer.va |
| AAPL-2025-viz-06 | viz | ✓ | ✓ |  |
| AAPL-2025-viz-07 | viz | ✗ | ✗ | rd_expense_2023: structured_answer.value is null; rd_expense_2024: structured_answer.value is null; rd_expense_2025: structured_answer.value |

## 4. Where the systems diverged

| ID | Type | full | rag_only | losing system's reason |
|---|---|---|---|---|
| AAPL-2025-complex-05 | complex_calc | ✓ | ✗ | structured_answer.value is null |
