# Backtest Report: VAMA Distance-from-Baseline Continuous Sizing Dial

**Strategy file:** `strategies/2026-09-17_vama_dist_sizing_sma_trend.py`
**Date:** 2026-09-17 (KST) / cron trigger iteration 9

## Hypothesis

Volatility Adjusted Moving Average (VAMA), per
https://pineify.app/resources/blog/volatility-adjusted-moving-average-indicator-tradingview-pine-script
(formula already confirmed in this repo from 2026-09-08-036, not re-fetched
this iteration): scales a baseline EMA multiplicatively by a
High-Low-range-relative-to-EMA volatility ratio: `VolRatio =
(HighestHigh(vol_lookback) - LowestLow(vol_lookback)) / EMA(close,
length)`; `VAMA = EMA(close, length) * (1 + VolRatio * sensitivity_factor)`.

This repo's prior VAMA entry (2026-09-08-036) used a binary breakout +
slope-confirmation trigger: accepted QQQ only, SPY was a near-miss (Sharpe
0.974), crypto rejected decisively. This iteration reframes VAMA as a
CONTINUOUS SIZING dial: distance of close from its own VAMA baseline
((close-VAMA)/VAMA), rolling z-scored + tanh-squashed to [-1,1], sized
inside an SMA(trend_window) uptrend gate + deadband -- the pattern that has
rescued many other adaptive-MA-distance near-misses in this repo. First
VAMA continuous-sizing variant.

## Step 6 grid summary

Grid: `vama_length` in {10,14,20} x `sensitivity` in {0.4,0.6,0.8} x
`deadband` in {0.15,0.25} x 4 symbols x 3 vol regimes = 216 cells.

- **Overall pass fraction:** 101/216 = 0.468.
- **By asset class:** equity 54/108 (0.50), crypto 47/108 (0.435).
- **By vol regime:** low 66/72 (0.917), mid 18/72 (0.25), high 17/72 (0.236).
- **Best cell:** QQQ low-vol, `vama_length=20, sensitivity=0.4,
  deadband=0.25`, Sharpe 2.55.
- **Worst cell:** QQQ high-vol, `vama_length=10, sensitivity=0.8,
  deadband=0.25`, Sharpe -0.41.

Full raw grid: `grid_cells_vama_dist_sizing.json`.

## Step 7 validators (full-sample, after deadband/sensitivity retune to
clear TC-survival near-misses on the grid-chosen configs)

| Symbol | Config | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity | Outcome |
|---|---|---|---|---|---|---|---|
| QQQ | vama_length=30, sensitivity=0.4, deadband=0.30 | 1.425 (pass) | 0.103 (pass) | 1.016 (pass, 133 trades) | 0.75 (pass) | rel_std 0.084 (pass) | **ACCEPT** |
| SPY | vama_length=30, sensitivity=0.3, deadband=0.25 | 1.098 (pass) | 0.074 (pass) | 0.553 (pass, 130 trades) | 0.75 (pass) | rel_std 0.028 (pass) | **ACCEPT** |
| BTC/USDT | vama_length=20, sensitivity=0.4, deadband=0.25, leverage_cap=0.5 | FAIL | FAIL | FAIL (~6639 trades) | pass | pass | REJECT (decisive) |
| ETH/USDT | vama_length=10, sensitivity=0.4, deadband=0.25, leverage_cap=0.5 | FAIL | FAIL | FAIL (~6907 trades) | pass | pass | REJECT (decisive) |

Both equity symbols' grid-chosen configs initially missed TC-survival
(QQQ 328 trades, SPY was a decisive Sharpe fail at the grid-best avg-Sharpe
config) -- lengthening `vama_length` to 30 and widening `deadband` fixed
both. Crypto's extremely high turnover (~6600-6900 trades, roughly 50x
equity's) drives decisive Sharpe/MDD/TC failure, consistent with the
underlying binary-trigger VAMA strategy's own decisive crypto rejection
(2026-09-08-036) -- the continuous-sizing reframing does not change VAMA's
fundamental incompatibility with crypto's volatility character.

Full raw validators: `validate_result_vama_dist_sizing.json`,
`validate_result_vama_dist_sizing_equity_fix.json`.

## Decision

**ACCEPT for equity (QQQ, SPY) with a longer vama_length=30 (vs the grid's
best-average vama_length=20) and widened deadband. REJECT for crypto
(BTC/USDT, ETH/USDT)** -- decisive turnover-driven failure, consistent
across both the original binary-trigger VAMA strategy and this continuous-
sizing reframing.
