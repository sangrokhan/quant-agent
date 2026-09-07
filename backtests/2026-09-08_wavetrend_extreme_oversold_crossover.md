# Backtest Report: WaveTrend Extreme-Zone Oversold Crossover

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_wavetrend_extreme_oversold_crossover.py`
**Source:** https://strategyquant.com/codebase/wavetrend-wt/

## Hypothesis

Per the source: WaveTrend's primary buy signal is WT1 crossing above WT2,
and "the most reliable crossovers occur when both lines are in extreme
territory -- bullish crosses near -60 to -80." First WaveTrend strategy in
this repo (CCI-style normalization through two layers of EMA smoothing,
distinct from all prior oscillator constructions tested).

## Grid Test Summary (param_grid: oversold_level=[-50,-60,-70] x
max_hold_days=[10,20]; symbols QQQ/SPY/BTC-USDT/ETH-USDT; vol_regime_splits=3;
2019-01-01 to 2026-09-01)

- total_cells: 72, passed: 5, **pass_fraction: 0.069** (weak)
- by_asset_class: equity 5/36, crypto 0/36
- by_vol_regime: low 2/24, mid 1/24, high 2/24 -- scattered, no coherent pattern
- best_cell: oversold_level=-70, max_hold_days=20, SPY, high-vol, Sharpe 1.88

## Single-Config Full-Period Check (oversold_level=-70, max_hold_days=20, 2019-2026)

| Symbol | Trades | Full-period Sharpe |
|---|---|---|
| QQQ | 0 | n/a (no signal fired at all) |
| SPY | 1 | 0.856 (single trade, not statistically meaningful) |

The "most reliable" extreme-zone (-70) threshold is so restrictive it
produces essentially no signal over 7.7 years on daily bars -- QQQ never
crosses into that oversold-then-cross condition at all, SPY only once. No
further validators run given the signal is not tradeable (n=0-1 trades).

## Decision: **REJECT**

The extreme-oversold-crossover variant of WaveTrend, as parameterized on
daily equity/crypto bars, produces too few signals to constitute a testable
strategy (0-1 trades/7.7yr on equity, 0/36 crypto grid cells pass). The
"-60 to -80" extreme zone described in the source may be calibrated for a
different (likely intraday/shorter) timeframe or a different WT1/WT2 scale
than what this repo's daily-bar reconstruction produces.
