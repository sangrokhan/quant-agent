# Fractal Chaos Bands (FCB) Normalized-Distance Continuous Sizing — Backtest Report

**Date:** 2026-09-15
**Strategy ID:** 2026-09-15-014 (assigned in knowledge_base log)
**File:** `strategies/2026-09-15_fcb_dist_sizing_sma_trend.py`

## Hypothesis

Fractal Chaos Bands (Edward William Dreiss): classic 5-bar Williams fractal
envelope -- upper band holds the most recent confirmed high-fractal value
(high[i] = max of centered 5-bar window), lower band holds the most recent
confirmed low-fractal value (low[i] = min of centered 5-bar window). Repo
has 1 prior FCB entry (2026-09-06-145, binary breakout trigger, rejected).
This iteration reframes FCB's own normalized position of Close within its
[lower, upper] band -- (Close - mid) / (upper - lower) -- as a CONTINUOUS
SIZING dial: rolling z-scored + tanh-squashed to [-1,1], used as a sizing
multiplier within an SMA(trend_window) uptrend gate, deadband to cut
turnover, leverage_cap for crypto. First FCB continuous-sizing variant.

Source: https://help.ctrader.com/indicators/built-in/volatility/fractal-chaos-bands/
and https://www.quantifiedstrategies.com/fractal-chaos-bands/ (both
visited this iteration via browser_exec fallback -- web_search's DDGS
backend returned "No results found" for two consecutive queries this
iteration).

## Grid test summary (Step 6)

`param_grid={zscore_window: [50,100,150], sensitivity: [0.4,0.6,0.8],
deadband: [0.2,0.35]}`, symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT
(crypto), vol_regime_splits=3.

- **total_cells:** 216, **passed:** 125, **pass_fraction:** 0.579.
- **by_asset_class:** equity 61/108 (0.565), crypto 64/108 (0.593).
- **by_vol_regime:** low 64/72 (0.889), mid 27/72 (0.375), high 34/72 (0.472).
- **best_cell:** QQQ, zscore_window=150/sensitivity=0.8/deadband=0.35,
  low-vol, Sharpe 2.786.
- **worst_cell:** QQQ, zscore_window=150/sensitivity=0.6/deadband=0.2,
  high-vol, Sharpe -0.814.

Note: crypto's per-cell grid Sharpe looked competitive with equity, but this
was misleading -- the grid test's tercile Sharpe doesn't surface turnover.
Full-sample single-config validation (below) reveals the crypto loader
returns **hourly** bars (~75,800 bars for BTC/USDT vs ~2,178 daily bars for
QQQ), so the same `deadband` in raw dial-units doesn't control turnover the
same way -- crypto produced 7,895-8,787 "trades" (position changes) over
the full sample, an order of magnitude beyond viable transaction-cost
survival.

## Single-config validator results (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity (rel-std) | Outcome |
|---|---|---|---|---|---|---|---|
| QQQ | zscore_window=150/sensitivity=0.6/deadband=0.35 | 1.032 (pass) | 0.105 (pass) | 0.523 (pass, 191 trades) | 1.000 (pass) | 0.192 (pass) | **accepted** |
| SPY | zscore_window=150/sensitivity=0.6/deadband=0.35 | 1.346 (pass) | 0.077 (pass) | 0.647 (pass, 171 trades) | 1.000 (pass) | 0.077 (pass) | **accepted** |
| BTC/USDT | zscore_window=150/sensitivity=0.8/deadband=0.2, leverage_cap=0.4 | 0.128 (**fail**) | 0.297 (**fail**) | -0.063 (**fail**, 8787 trades) | 1.000 (pass) | 0.108 (pass) | **rejected** |
| ETH/USDT | zscore_window=50/sensitivity=0.4/deadband=0.2, leverage_cap=0.4 | 0.122 (**fail**) | 0.278 (**fail**) | -0.060 (**fail**, 7895 trades) | 0.750 (pass) | 0.095 (pass) | **rejected** |

Walk-forward used manual 4-way `np.array_split` (repo's `check_walk_forward`
calls `vbt.utils.splitting.RangeSplitter`, unavailable in installed
vectorbt -- known recurring fix this cron trigger).

## Decision

**Accepted (QQQ + SPY):** both clear all 5 validators at
zscore_window=150/sensitivity=0.6/deadband=0.35 -- first accepted FCB
variant in this repo (prior binary breakout trigger was rejected).
**Rejected (BTC/USDT, ETH/USDT):** decisive Sharpe/MDD/TC-survival failures
driven by excessive turnover on the crypto loader's hourly bar frequency
(thousands of position changes vs hundreds on daily equity bars) --
consistent with this cron trigger's recurring finding that
daily-bar-calibrated sizing dials transfer poorly to crypto's higher-
frequency data without a much wider deadband or resampling to daily bars
first (a future loop could test resampling crypto OHLCV to daily before
applying this dial).
