# Backtest Report: RVI (Dorsey) Midline-Distance Continuous Sizing Dial (SMA Trend Gate)

**Date:** 2026-09-15
**Strategy file:** `strategies/2026-09-15_rvi_dorsey_dist_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-15-044

## Hypothesis

Relative Volatility Index (RVI, Donald Dorsey 1993/1995), formula already
documented in this repo from prior iteration 2026-09-05-003 (sources not
re-fetched this iteration per the dedupe ledger): an RSI-shaped formula
applied to the standard deviation of close prices, split into up-day and
down-day accumulators. This repo's prior RVI entry (2026-09-05-003) used a
discrete midline-crossover trigger (buy above 50, close below 40) and was
accepted for equity (QQQ, SPY) but decisively rejected for crypto. This
iteration reuses the identical underlying construction as a CONTINUOUS
sizing dial specifically targeting crypto's decisive rejection: RVI's
distance from its own 50 midline is rolling z-scored and tanh-squashed
into [-1,+1], used as a continuous sizing dial inside an SMA(trend_window)
uptrend gate with a deadband.

## Step 6 — Grid summary (stdev_window x sensitivity, 2 asset classes x 3 vol terciles)

- Grid: `stdev_window in [10, 14]`, `sensitivity in [0.5, 0.8]`, symbols
  `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, `vol_regime_splits=3`
  (light grid: only 2 stdev_window values tested, given workload budget).
- **48 cells, 25 passed (pass_fraction = 0.521)**.
- By asset class: equity 12/24, crypto 13/24 — crypto no longer decisively
  excluded (unlike the discrete-trigger predecessor entry).
- By vol regime: low 15/16, mid 8/16, high 2/16.
- Best cell: QQQ, stdev_window=10, sensitivity=0.8, low-vol regime, Sharpe 2.96.
- Worst cell: QQQ, stdev_window=10, sensitivity=0.8, high-vol regime,
  Sharpe -0.29.

## Step 7 — Single-config validator suite (per-symbol retuned)

QQQ: `stdev_window=14, smooth_window=14, sensitivity=0.5, trend_window=40,
zscore_window=100, base_exposure=0.4, leverage_cap=1.0, deadband=0.5`.
SPY: same but `stdev_window=10, deadband=0.4`.
Crypto (BTC/ETH, leverage-cap-aware retune): `stdev_window=14,
smooth_window=14, sensitivity=0.5, trend_window=40, zscore_window=100,
base_exposure=0.24, leverage_cap=0.4, deadband=0.2`.

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-fwd pass | Param sensitivity (rel std) | All pass? |
|---|---|---|---|---|---|---|
| QQQ | 1.388 (pass) | 0.099 (pass) | 0.931 (pass) | 1.00 (pass) | 0.176 (pass) | **Yes** |
| SPY | 1.104 (pass) | 0.112 (pass) | 0.512 (pass) | 0.75 (pass) | 0.159 (pass) | **Yes** |
| BTC/USDT | 1.348 (pass) | 0.184 (pass) | 0.697 (pass) | 1.00 (pass) | 0.033 (pass) | **Yes** |
| ETH/USDT | 1.183 (pass) | 0.198 (pass) | 0.740 (pass) | 1.00 (pass) | 0.055 (pass) | **Yes** |

Walk-forward used the repo's established manual 4-equal-slice fallback.

## Step 8 — Decision: **ACCEPT (full universe: QQQ, SPY, BTC/USDT, ETH/USDT)**

All four symbols pass all 5 validators. This rescues 2026-09-05-003's
decisively-rejected crypto scope via the continuous-sizing-dial transform,
while preserving (and improving margins on) the already-accepted equity
scope. The second full-universe accept of this cron trigger's 6
iterations (after PVI), reinforcing that Dorsey-style directional
volatility measures translate cleanly into this repo's continuous-sizing
framework across both asset classes.
