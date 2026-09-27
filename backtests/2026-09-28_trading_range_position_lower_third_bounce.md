# Trading-range Position Lower-Third Bounce — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_trading_range_position_lower_third_bounce.py`
**Source:** https://www.luxalgo.com/library/indicator/trading-range-position/

## Hypothesis

LuxAlgo's "Trading-range Position" indicator formalizes Wyckoff-style
range-trading: a compressed window (default 20 bars, height capped by ATR)
confirms a trading range, splits it into thirds, and classifies each close
by subdivision. Source's disclosed rule: buy in the lower third ("where
structural stops are smallest relative to the ride across the range"),
avoid the middle ("no-trade zone"), target the upper third. Implemented
long-only: entry on a fresh cross into the lower third of a
compression-confirmed range, exit at the upper third, a 2-consecutive-close
range-breakdown, or a time-stop.

## Grid test (Step 6)

`validation/grid_test.py::run_strategy_grid`,
`formation_length in {15,20,30}` x `max_range_atr_mult in {2,3,4}`,
symbols equity `{QQQ, SPY}` / crypto `{BTC/USDT, ETH/USDT}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.120 (13/108)**
- by_asset_class: equity 13/54, crypto 0/54
- by_vol_regime: low 6/36, mid 6/36, high 1/36
- best_cell: QQQ, formation_length=20, max_range_atr_mult=3.0, low-vol, Sharpe 2.55
- worst_cell: ETH/USDT, formation_length=20, max_range_atr_mult=2.0, low-vol, Sharpe -1.37

## Single-config validators (config: formation_length=20, max_range_atr_mult=3.0, full sample)

| Validator | QQQ | SPY | Threshold | Passed |
|---|---|---|---|---|
| Sharpe ratio | 0.818 | 0.493 | >= 1.0 | **FAIL (both)** |
| Max drawdown | 0.099 | 0.082 | <= 0.25 | pass (both) |
| Transaction cost survival | net Sharpe 0.773 (10 trades) | net Sharpe 0.435 (12 trades) | >= 0.5 | fail (SPY), pass (QQQ) |

Crypto (BTC/USDT) full-sample Sharpe: -0.010 — decisive fail.

## Decision

**Rejected.** Full-sample Sharpe fails on both QQQ (0.818) and SPY (0.493)
despite the low-vol tercile cells clearing the grid's per-cell threshold —
the same narrow-slice pattern seen repeatedly in this repo's mean-reversion
range strategies. Trade counts are also thin (10-12 over 7.7 years),
limiting statistical confidence even within the passing cells. Crypto is a
clean decisive rejection.

## Notes for future loops

Similar to this repo's other confirmed-range/subdivision strategies
(Zscore Range Box, Percentile Channel), a compression-gated range-bounce
entry tends to only work in a narrow low-vol equity slice. A future loop
could try widening the subdivision definition (quarters instead of thirds,
per the source's own alternate setting) or adding a longer-term trend
filter to avoid buying "lower thirds" that are actually the start of a
larger downtrend rather than a genuine range.
