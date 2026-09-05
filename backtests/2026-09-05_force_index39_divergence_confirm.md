# Elder's Force Index(39) Bullish Divergence + Zero-Line Confirmation — Backtest Report

**Date:** 2026-09-05
**Strategy file:** `strategies/2026-09-05_force_index39_divergence_confirm.py`
**Knowledge base id:** 2026-09-05-048

## Hypothesis

Per StockCharts ChartSchool's Force Index page (mirrored verbatim on
MQL5): "A bullish divergence is confirmed when the Force Index (39)
crosses into positive territory." Implemented: detect price
lower-low/FI(39)-higher-low divergence at confirmed swing lows (same
swing-detection construction as 2026-09-05-047), then require FI(39) to
cross from <=0 to >0 within `confirm_window` bars as the entry trigger.
Exit on FI(39) turning negative again, a failed bounce below the
divergence swing-low's close, or a max_hold_days time-stop. Distinct
from the already-accepted (QQQ) Force Index pullback-continuation
strategy (2026-09-04-049), which trades a SHORT-EMA-dip-in-an-uptrend
setup rather than this divergence-at-a-reversal setup.

Source: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/force-index
(fetched via `browser_exec`; note the exact divergence-confirmation
sentence was found via a targeted Google SERP snippet search since the
live page's rendered text didn't include a dedicated "Bullish
Divergence" heading at fetch time -- likely reformatted since the
snippet was indexed. Cross-confirmed by an independent MQL5 mirror
carrying the identical sentence.)

## Grid test summary (Step 6)

`validation/grid_test.py::run_strategy_grid`, param grid
`pivot_window=[4,5,7] x lookback_bars=[40,60,90] x confirm_window=[10,15,25]`,
symbols `equity=[QQQ,SPY]`, `crypto=[BTC/USDT,ETH/USDT]`, `vol_regime_splits=3`,
2019-01-01 to 2026-09-01. **324 cells total.**

- **pass_fraction: 0.0 (0/324)** — every single cell failed
- by_asset_class: equity 0/162; crypto 0/162
- by_vol_regime: low 0/108; mid 0/108; high 0/108
- best_cell (still below threshold): `pivot_window=7, lookback_bars=40,
  confirm_window=10`, QQQ, high-vol tercile, Sharpe 0.986 (just under the
  1.0 bar)
- worst_cell: `pivot_window=4, lookback_bars=40, confirm_window=10`, SPY,
  mid-vol tercile, Sharpe -0.50

## Decision: **REJECTED**

Decisive, unambiguous rejection — 0 of 324 grid cells cleared the
Sharpe/MDD bar in any asset class or volatility regime, with the best
cell still short of the threshold. No single-config validator suite run
given the grid result leaves no config worth promoting; skipped per
Step 7's guidance to scope validation effort to what the grid result
warrants. The added zero-line confirmation trigger (vs. the simpler
divergence-only detection in the sibling CMF-divergence strategy,
2026-09-05-047, itself already rejected) makes entries even rarer
without improving the edge.
