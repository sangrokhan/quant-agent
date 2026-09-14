# GMMA Ribbon-Spread Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-145
**File:** `strategies/2026-09-14_gmma_ribbon_sizing_sma_trend.py`

## Hypothesis

Guppy Multiple Moving Average (GMMA, Daryl Guppy, late 1990s): two groups of
6 EMAs each — short-term group EMA(3,5,8,10,12,15), long-term group
EMA(30,35,40,45,50,60). Formula confirmed via Google AI-overview
(`browser_exec` fallback; `web_search`'s DDGS backend failed with a
TLS/connection error for this query).

This repo has 5+ prior GMMA entries, all binary ribbon-crossover or
ribbon-compression triggers, repeatedly flagged "saturated" in no_candidate
iterations. This iteration reframes GMMA as a CONTINUOUS SIZING dial: raw
ribbon spread `(short_group_avg - long_group_avg) / close`, rolling
z-scored over `zscore_window` bars, tanh-squashed to [-1,+1], used as a
sizing multiplier within an SMA(trend_window) uptrend gate — first
continuous-sizing framing of GMMA in this repo.

## Grid test summary (Step 6)

`param_grid={zscore_window: [60,100,150], deadband: [0.15,0.25], leverage_cap: [0.4,1.0]}`,
symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 144, **passed:** 78, **pass_fraction:** 0.542
- **by_asset_class:** equity 36/72 (0.5), crypto 42/72 (0.583) — slightly
  favors crypto, unlike most prior sizing-dial entries this cron trigger
  which lean equity-favorable.
- **by_vol_regime:** low 43/48 (0.896), mid 24/48 (0.5), high 11/48 (0.229)
  — usual concentration in low/mid-vol regimes.
- **best_cell:** QQQ, zscore_window=100/deadband=0.25/leverage_cap=0.4,
  low-vol, Sharpe 3.11.
- **worst_cell:** QQQ, zscore_window=150/deadband=0.15/leverage_cap=1.0,
  high-vol, Sharpe -0.59.

## Single-config validator results (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Outcome |
|---|---|---|---|---|---|---|---|
| QQQ | zw=100, db=0.25, lc=1.0 | 1.219 (pass) | pass | pass | pass | pass | **accepted** |
| SPY | zw=150, db=0.15, lc=0.4 | **0.804 (FAIL)** | pass | **FAIL** | pass | pass | **rejected** |
| BTC/USDT | zw=150, db=0.15, lc=0.4 | 1.479 (pass) | pass | pass | pass | pass | **accepted** |
| ETH/USDT | zw=60, db=0.25, lc=0.4 | 1.303 (pass) | pass | pass | pass | pass | **accepted** |

## Decision

**Accepted:** QQQ, BTC/USDT, ETH/USDT (all 5 validators pass).
**Rejected:** SPY (decisive Sharpe fail at best-found config 0.804 < 1.0
across the grid sweep, and TC-survival also fails — not a near-miss, no
passing SPY config found in the 12-value sweep).

Full raw grid: `grid_result_gmma_ribbon_sizing.json`. Full raw validators:
`validators_gmma_ribbon_sizing.json`.
