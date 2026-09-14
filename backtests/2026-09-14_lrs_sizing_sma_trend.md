# Normalized Linear Regression Slope (LRS) Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-146
**File:** `strategies/2026-09-14_lrs_sizing_sma_trend.py`

## Hypothesis

Normalized Linear Regression Slope (LRS): the raw least-squares regression
slope (beta) of closing price fit over a rolling `lrs_window`-bar lookback,
normalized by current price: `normalized_slope = (raw_slope / price) * 100`.
Per tradingpedia.com-style synthesis (Google AI-overview, `browser_exec`
fallback — `web_search`'s DDGS backend returned only non-actionable snippets
for the query).

This repo has 1 prior LRS entry (2026-09-10-100, a short-lookback
mean-reversion pullback trigger per the source's own counter-trend rule).
This iteration is structurally distinct: uses LRS as a TREND-FOLLOWING
continuous sizing dial — rolling z-scored + tanh-squashed normalized slope,
sized within an SMA(trend_window) uptrend gate. First continuous-sizing /
trend-following framing of LRS in this repo.

## Grid test summary (Step 6)

`param_grid={lrs_window: [10,20,30], deadband: [0.15,0.25], leverage_cap: [0.4,1.0]}`,
symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 144, **passed:** 77, **pass_fraction:** 0.535
- **by_asset_class:** equity 38/72 (0.528), crypto 39/72 (0.542) — balanced.
- **by_vol_regime:** low 44/48 (0.917), mid 26/48 (0.542), high 7/48 (0.146)
  — usual concentration in low/mid-vol regimes.
- **best_cell:** QQQ, lrs_window=20/deadband=0.15/leverage_cap=1.0, low-vol,
  Sharpe 2.90.
- **worst_cell:** QQQ, lrs_window=30/deadband=0.25/leverage_cap=1.0,
  high-vol, Sharpe -0.38.

## Single-config validator results (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Outcome |
|---|---|---|---|---|---|---|---|
| QQQ | lw=10, db=0.25, lc=0.4 | 1.409 (pass) | pass | pass | pass | pass | **accepted** |
| SPY | lw=10, db=0.15, lc=0.4 | 1.128 (pass) | pass | **FAIL** | pass | pass | **rejected (near-miss on TC)** |
| BTC/USDT | lw=20, db=0.15, lc=0.4 | 1.474 (pass) | pass | pass | pass | pass | **accepted** |
| ETH/USDT | lw=10, db=0.25, lc=0.4 | 1.278 (pass) | pass | pass | pass | pass | **accepted** |

## Decision

**Accepted:** QQQ, BTC/USDT, ETH/USDT (all 5 validators pass at
leverage_cap=0.4).
**Rejected:** SPY (near-miss, transaction-cost survival fails; gross
Sharpe/MDD/WF/param-sensitivity all pass — candidate for a future
deadband-widening follow-up, consistent with this cron trigger's other SPY
near-miss pattern).

Full raw grid: `grid_result_lrs_sizing.json`. Full raw validators:
`validators_lrs_sizing.json`.
