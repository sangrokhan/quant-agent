# Bulkowski Double Top Setup — Time-Based Target Short — Backtest Report

**Date:** 2026-09-24
**Strategy file:** `strategies/2026-09-24_double_top_setup_time_target_short.py`
**Source:** https://thepatternsite.com/dtsetup.html (Thomas Bulkowski),
read via browser_exec.

## Hypothesis

For confirmed double tops preceded by a flat base and a fast straight-line
run-up (A->B), the decline time from confirmation (C) back to the launch
price (A's level, D) tends to equal or be shorter than the AB rise time
(source: 24-day avg AB vs 19-day avg CD, 1333 double tops/317 stocks
1990-2006). Implemented as a short position entered at confirmation (close
below the inter-peak valley), with exit at the earlier of: launch-price
target reached, the dynamically-measured AB-duration time-budget expiring,
or price recovering above the second peak (thesis invalidation). Distinct
time-based exit from all prior double-top/2B-top strategies (percentage or
pattern-based exits).

## Grid test summary (Step 6)

`max_peak_diff_pct` in {0.02,0.03}, `min_run_pct` in {0.06,0.10}, equity
{QQQ,SPY} + crypto {BTC/USDT,ETH/USDT}, vol_regime_splits=3. 48 cells.

- **pass_fraction: 0.021** (1/48) -- decisively negative.
- **by_asset_class:** equity 0/24, crypto 1/24
- **best_cell:** max_peak_diff_pct=0.03, min_run_pct=0.06, ETH/USDT,
  low-vol, Sharpe 1.028 (single passing cell, likely noise given 47 other
  failing cells)
- **worst_cell:** same params, QQQ, mid-vol, Sharpe -0.721

## Decision

**Rejected outright at the grid stage** -- 1/48 cells passed, essentially a
noise-level hit rate. No single-config validator suite run given the
decisively negative grid result (per Step 7, skip full validation when the
grid outcome already rules the strategy out). The time-based exit rule
(exit regardless of price once the AB-duration budget expires) likely
truncates winning trades too early on average while still allowing losing
trades to run to the invalidation stop, producing a poor risk/reward
profile net of the pattern's own low hit-rate (source's own disclosure:
only 24% of double tops even fit the idealized flat-base+sharp-rise shape
this strategy requires).
