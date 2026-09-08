# TTM Squeeze Pro Three-Level Compression Breakout — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_ttm_squeeze_pro_threelevel.py`
**Outcome:** REJECTED

## Hypothesis
John Carter's Squeeze Pro (per Simpler Trading's own explainer,
https://www.simplertrading.com/tutorials/squeeze-pro) extends the classic
single-level TTM Squeeze (already rejected twice in this repo: 2026-09-04-091,
2026-09-08-004) into THREE progressively tighter Bollinger-inside-Keltner
compression levels. Requiring a higher-compression level (min_squeeze_level)
before firing was claimed by the source to be a higher-conviction filter
catching moves the single-level squeeze misses. Long entry on release from a
squeeze that reached at least min_squeeze_level within lookback_window bars,
gated by a positive momentum proxy; exit on momentum turning non-positive or
a max_hold_days time-stop.

## Grid test summary (min_squeeze_level x [1,2], max_hold_days x [10,15,20], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2018-01-01 to 2026-09-01)

- total_cells: 72, passed_cells: 1, **pass_fraction: 0.014** (decisive fail)
- by_asset_class: equity 1/36, crypto 0/36
- by_vol_regime: low 1/24, mid 0/24, high 0/24
- best_cell: SPY, min_squeeze_level=1, max_hold_days=20, low-vol, Sharpe 1.783 (single cell, not representative)
- worst_cell: QQQ, min_squeeze_level=2, max_hold_days=20, low-vol, Sharpe -1.013

## Full-sample checks at plausible best configs

| Symbol | min_squeeze_level | max_hold_days | Full-sample Sharpe | Trades |
|---|---|---|---|---|
| QQQ | 1 | 20 | 0.227 | 41 |
| QQQ | 2 | 15 | -0.402 | 10 |
| SPY | 1 | 20 | 0.459 | 39 |
| SPY | 2 | 15 | -0.115 | 6 |

All configs decisively fail the 1.0 Sharpe threshold. Requiring a higher
compression level (min_squeeze_level=2) actually made results WORSE (fewer,
weaker trades) rather than better -- the source's claimed higher-conviction
filter does not hold up in this backtest.

## Decision: REJECTED

Decisive grid failure (pass_fraction 0.014) and full-sample Sharpe fails
across every tested config on both equity symbols; crypto 0/36. The
"require higher compression before firing" idea from Squeeze Pro's marketing
does not improve on the already-rejected single-level TTM Squeeze variants
in this repo -- if anything it degrades signal quality by cutting trade
count without improving per-trade edge. Not a near-miss worth revisiting.
