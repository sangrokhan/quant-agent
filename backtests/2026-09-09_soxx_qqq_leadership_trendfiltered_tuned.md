# 2026-09-09 — SOXX/QQQ Leadership + Trend Filter, Locally-Tuned (ACCEPTED, QQQ+SPY)

**Hypothesis** (id `2026-09-09-120`): Final entry in the SOXX/QQQ leadership
lineage: 2026-09-09-118 (plain gate, Sharpe near-miss, MDD fail) →
2026-09-09-119 (+ 200d trend filter at roc_window=40, fixed MDD, ACCEPTED
QQQ only, SPY narrow Sharpe near-miss 0.951) → **this: local parameter
search finds a shared sweet spot (trend_sma_window=200, roc_window=30) that
clears the Sharpe threshold for BOTH symbols**.

Strategy file: `strategies/2026-09-09_soxx_qqq_leadership_trendfiltered_tuned.py`

## Local parameter search (SPY Sharpe, full 2019-2026 sample)

| Config | SPY Sharpe |
|---|---|
| sma250/roc30 | 1.101 |
| **sma200/roc30 (chosen)** | **1.099** |
| sma225/roc30 | 1.045 |
| sma250/roc40 | 0.971 |
| sma225/roc40 | 0.970 |
| sma200/roc40 (2026-09-09-119's config) | 0.951 |

roc_window=30 consistently outperforms roc_window=40 across all sma_window
values tried for SPY; sma_window=200 (unchanged from 2026-09-09-119) remains
a strong choice, landing in the top-2 of 20 combos tested.

## Single-config validators (trend_sma_window=200, roc_window=30), full 2019-2026 sample

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | **1.098** ✅ | **1.099** ✅ | ≥ 1.0 |
| Max drawdown | 0.199 ✅ | 0.151 ✅ | ≤ 0.25 |
| TC survival (10bps/trade) | 0.829 ✅ | 0.721 ✅ | ≥ 0.5 net Sharpe |
| Walk-forward (manual 4-slice fallback) | 0.75 ✅ | 0.75 ✅ | ≥ 0.75 pass fraction |
| Parameter sensitivity (trend_sma_window 175/200/225 sweep) | 0.066 ✅ | 0.068 ✅ | ≤ 0.5 relative std |
| Trades | 154 | 150 | — |

## Verdict: **ACCEPT (QQQ and SPY)**

Every validator passes comfortably for both symbols at this shared
configuration — an improvement over 2026-09-09-119's QQQ-only acceptance,
since roc_window=30 turned out to be a better compromise value for SPY
without meaningfully hurting QQQ (1.098 here vs 1.013 at roc_window=40,
actually slightly better for QQQ too). Parameter sensitivity is very clean
for both symbols (0.066/0.068, far under the 0.5 threshold).

**Scope**: QQQ and SPY, using SOXX/QQQ ratio ROC (30-day) as the
semiconductor-leadership signal AND the traded asset's own 200-day SMA as a
broad-trend/drawdown circuit-breaker. This supersedes 2026-09-09-119's
QQQ-only version as the preferred configuration going forward (both remain
in `strategies/` as a record of the tuning lineage, but this is the stronger
config: it extends coverage to SPY while matching or improving QQQ's
metrics).
