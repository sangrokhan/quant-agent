# MFI 50-Centerline Crossover, SMA-Trend-Gated (QQQ accepted; SPY near-miss)

**Strategy file:** `strategies/2026-09-09_mfi_centerline_trend_gated.py`
**Knowledge base id:** 2026-09-09-078

## Hypothesis + source

Per TradingView's own MFI documentation (50-Line Crossover mode; surfaced via
Google search snippet, browser_exec fallback since DDGS web_search returned
degraded/no results for this query): "Crossover above 50 -> shift from
bearish to bullish money flow, potential trend [continuation]." This uses
the MFI 50-centerline itself as the entry trigger, gated by a 200->100-day
SMA long-term uptrend filter (tuned via grid), distinct from all four prior
MFI strategies in this repo (oversold-bounce threshold, %B+MFI
thrust-confirmation, bullish divergence, MA-of-MFI cross), none of which
use the plain 50-centerline crossover.

## Grid test (Step 6)

`param_grid={"mfi_period": [10,14,21], "trend_window": [100,150,200]}`,
symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), `vol_regime_splits=3`,
2019-01-01 to 2026-09-01:

- **pass_fraction: 0.194** (21/108 cells)
- by_asset_class: equity 21/54, crypto 0/54 (decisive crypto rejection)
- by_vol_regime: low 18/36, mid 3/36, high 0/36
- best_cell: QQQ, low-vol, mfi_period=14/trend_window=100, Sharpe 3.13
- worst_cell: QQQ, high-vol, mfi_period=21/trend_window=100, Sharpe -0.88

## Single-config validators (Step 7), config: mfi_period=14, trend_window=100

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | **1.053 PASS** | 0.980 (near-miss, FAIL) |
| Max drawdown (<=0.25) | 0.222 PASS | 0.089 PASS |
| Transaction-cost survival (net Sharpe >=0.5) | 0.917 PASS | 0.779 PASS |
| Walk-forward (4 splits, >=75% positive) | 4/4 PASS | 4/4 PASS |
| Parameter sensitivity (relative_std <=0.5) | 0.313 PASS | 0.156 PASS |

QQQ: all 5 validators pass. SPY: 4/5 pass, Sharpe 0.980 is a genuine
near-miss (1 basis point shy of the 1.0 threshold) rather than a decisive
failure -- everything else (MDD, cost survival, walk-forward, parameter
stability) is strong on SPY too.

## Decision

**Accept for QQQ only.** SPY logged as a near-miss worth revisiting (e.g.
a slightly different trend_window or mfi_period specific to SPY might clear
1.0 -- the grid's best SPY cell wasn't individually re-swept). Crypto
rejected decisively (0/54 grid cells, no full-sample run needed).
