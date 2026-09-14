# Backtest Report: Intraday Intensity Index (Bostian) Continuous Sizing on SMA Trend Gate

**Strategy file:** `strategies/2026-09-14_iii_bostian_sizing_sma_trend.py`
**Date:** 2026-09-14

## Hypothesis

Intraday Intensity Index (III, David Bostian): III = ((Close*2 - High -
Low) / (High - Low)) * Volume -- a per-bar volume-weighted measure of
where the close falls within the day's high-low range. Source:
https://www.investopedia.com/terms/i/intradayintensityindex.asp (visited
this iteration via browser_exec after web_search's DDGS backend hit a TLS
RequestError).

First Intraday Intensity Index / Bostian entry in this repo. Raw III is
unbounded (raw CLV * volume); this iteration normalizes it Chaikin-Money-
Flow-style (rolling N-bar sum of III / rolling N-bar sum of volume),
bounding the result ~[-1,+1], then uses that bounded ratio directly as a
continuous sizing dial within the existing SMA(trend_window) uptrend gate.

## Step 6 Grid Summary

Grid: `smooth_window` in [14, 21, 34] x `deadband` in [0.15, 0.25] x
`leverage_cap` in [0.4, 1.0], symbols QQQ/SPY/BTC/USDT/ETH/USDT,
vol_regime_splits=3. 144 cells, 83 passed, **pass_fraction=0.576**.

- by_asset_class: equity 36/72 (0.50), crypto 47/72 (0.653)
- by_vol_regime: low 48/48 (1.00), mid 29/48 (0.604), high 6/48 (0.125)
- best_cell: QQQ, smooth_window=14/deadband=0.25/leverage_cap=1.0, low-vol,
  Sharpe=2.92
- worst_cell: QQQ, smooth_window=34/deadband=0.15/leverage_cap=1.0,
  high-vol, Sharpe=-0.49

## Step 7 Single-Config Validators

| Symbol | Config | Sharpe | MDD | TC-adj Sharpe | Walk-fwd | Param sens (rel. std) |
|---|---|---|---|---|---|---|
| QQQ | smooth_window=21, deadband=0.15, sensitivity=0.8, lev=1.0 | 1.148 (pass) | 0.113 (pass) | 0.597 (pass) | 1.0 (pass) | 0.059 (pass) |
| SPY | smooth_window=14, deadband=0.25, sensitivity=0.6, lev=1.0 | 1.114 (pass) | 0.065 (pass) | 0.521 (pass) | 1.0 (pass) | 0.058 (pass) |
| BTC/USDT | smooth_window=21, deadband=0.15, sensitivity=0.6, lev=0.4 | 1.479 (pass) | 0.211 (pass) | 1.257 (pass) | 1.0 (pass) | 0.011 (pass) |
| ETH/USDT | smooth_window=14, deadband=0.15, sensitivity=0.8, lev=0.3 | 1.261 (pass) | 0.212 (pass) | 1.068 (pass) | 1.0 (pass) | 0.004 (pass) |

Note: ETH's grid-optimal leverage_cap (0.4) breached MDD (0.258 vs 0.25
threshold); tightened to leverage_cap=0.3, which cleared MDD (0.212)
while keeping Sharpe attractive (1.261) -- same recurring leverage-cap
recalibration pattern seen across several other sizing-dial strategies
this cron trigger.

## Outcome

**Accepted** — QQQ, SPY, BTC/USDT, ETH/USDT all pass all 5 validators.
