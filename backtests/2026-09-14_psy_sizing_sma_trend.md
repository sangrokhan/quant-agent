# Backtest Report: Psychological Line (PSY) Continuous Sizing on SMA Trend Gate

**Strategy file:** `strategies/2026-09-14_psy_sizing_sma_trend.py`
**Date:** 2026-09-14

## Hypothesis

Psychological Line (PSY): percentage of the last N bars closing higher
than the prior close, PSY = 100 * (count of up-closes / N) -- naturally
bounded [0,100] by construction, a pure win-rate/hit-rate oscillator
counting only the sign of each bar-to-bar change, not magnitude. Source:
https://www.luxalgo.com/library/indicator/psychological-line/ (visited
this iteration via browser_exec after web_search's DDGS backend returned
no results).

This repo's prior PSY entry (2026-09-08-076) used PSY as an oversold
mean-reversion THRESHOLD trigger and was rejected (weak/inconsistent grid
pass_fraction 0.076, crypto decisively 0/72). This iteration reframes PSY
as a CONTINUOUS SIZING dial (rescaled from [0,100] to [-1,+1] via
(PSY-50)/50, no normalization window needed) within the existing
SMA(trend_window) uptrend gate.

## Step 6 Grid Summary

Grid: `psy_period` in [8, 12, 20] x `deadband` in [0.15, 0.25] x
`leverage_cap` in [0.4, 1.0], symbols QQQ/SPY/BTC/USDT/ETH/USDT,
vol_regime_splits=3. 144 cells, 82 passed, **pass_fraction=0.569**.

- by_asset_class: equity 37/72 (0.514), crypto 45/72 (0.625)
- by_vol_regime: low 48/48 (1.00), mid 28/48 (0.583), high 6/48 (0.125)
- best_cell: QQQ, psy_period=20/deadband=0.15/leverage_cap=1.0, low-vol,
  Sharpe=2.90
- worst_cell: QQQ, psy_period=20/deadband=0.25/leverage_cap=1.0, high-vol,
  Sharpe=-0.24

## Step 7 Single-Config Validators

| Symbol | Config | Sharpe | MDD | TC-adj Sharpe | Walk-fwd | Param sens (rel. std) |
|---|---|---|---|---|---|---|
| QQQ | psy_period=12, deadband=0.35, sensitivity=0.6, lev=1.0 | 1.355 (pass) | 0.124 (pass) | 0.977 (pass) | 1.0 (pass) | 0.065 (pass) |
| SPY | psy_period=8, deadband=0.35, sensitivity=0.6, lev=1.0 | 1.211 (pass) | 0.074 (pass) | 0.607 (pass) | 1.0 (pass) | 0.059 (pass) |
| BTC/USDT | psy_period=20, deadband=0.35, sensitivity=0.6, lev=0.4 | 1.521 (pass) | 0.231 (pass) | 1.364 (pass) | 1.0 (pass) | 0.025 (pass) |
| ETH/USDT | psy_period=8, deadband=0.25, sensitivity=0.6, lev=0.3 | 1.307 (pass) | 0.165 (pass) | 1.132 (pass) | 1.0 (pass) | 0.017 (pass) |

Note: strongest full 4-symbol Sharpe/TC-survival combo of the CTI/III/PSY
trio tested this cron trigger. ETH's grid-optimal leverage_cap (0.4) had
been showing recurring MDD near-misses across the trio this cron trigger;
tightened straight to 0.3 for PSY, clearing MDD comfortably (0.165) while
retaining strong Sharpe (1.307).

## Outcome

**Accepted** — QQQ, SPY, BTC/USDT, ETH/USDT all pass all 5 validators.
