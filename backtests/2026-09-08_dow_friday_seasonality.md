# Backtest Report: Day-of-Week (Friday-Only) Seasonality

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_dow_friday_seasonality.py`
**Source:** https://tradesaveplus.com/blog/day-of-week-effect-in-trading

## Hypothesis

Per the source, the classic 1980s academic "weekend effect": Monday returns
average negative, Friday returns "unusually positive." Long-only mirror
tested here: long only on Fridays, flat Mon-Thu. Source itself is
explicitly skeptical the effect survives today ("shrank as more people
knew about it... concentrated in small-cap stocks, specific decades") --
tested here as a falsification check on this repo's own 2019-2026 sample.

## Grid Test Summary (param_grid: long_weekday=[0,1,2,3,4] (Mon-Fri);
symbols QQQ/SPY/BTC-USDT/ETH-USDT; vol_regime_splits=3; 2019-01-01 to 2026-09-01)

- total_cells: 60, passed: 11, **pass_fraction: 0.183**
- by_asset_class: equity 11/30, crypto **0/30**
- by_vol_regime: low 8/20, mid 1/20, high 2/20 -- concentrated low-vol
- best_cell: long_weekday=4 (Friday, as the classic hypothesis predicts),
  QQQ, low-vol, Sharpe 2.13

## Single-Config Full-Period Check (long_weekday=4/Friday, 2019-2026)

| Symbol | Trades | Full-period Sharpe |
|---|---|---|
| QQQ | 385 | 0.526 (decisive FAIL) |
| SPY | 385 | 0.411 (decisive FAIL) |

Despite the grid correctly identifying Friday as the best weekday (matching
the classic literature's own directional claim) and a large, well-sampled
trade count (385 Fridays over 7.7yr, no sparse-signal concern), the
full-period Sharpe fails decisively on both symbols -- consistent with the
source's own stated skepticism that the effect has decayed/is
sample-specific in modern data. No further validators run given the
decisive full-sample fail.

## Decision: **REJECT**

Confirms the source's own caveat: the historical Monday/Friday seasonality
does not produce a standalone tradeable edge on 2019-2026 QQQ/SPY/crypto
daily data, despite correctly identifying the historically-favored weekday
as the grid's best cell. A well-sampled, mechanistically-motivated but
ultimately decayed anomaly.
