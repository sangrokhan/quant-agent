# Ross Hook Trend-Continuation Entry — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_ross_hook_trend_continuation.py`
**Source:** https://fxopen.com/blog/en/how-to-trade-with-a-ross-hook-pattern/

## Hypothesis

The Ross Hook (Joe Ross) is a trend-CONTINUATION pattern built on top of
the classic 1-2-3 reversal structure (already tested in this repo as a
standalone reversal entry -- 2026-09-11-022/025, 2026-09-18-090/091). The
Ross Hook is mechanically distinct: it fires AFTER an initial 1-2-3
breakout has already trended, when price forms a smaller SECONDARY
1-2-3-shaped "hook" during a retracement; the breakout of THIS secondary
hook (not the original 1-2-3) is the entry, used to add to/re-enter an
established trend. Source's disclosed rules: entry on the hook's
breakout; stop just beyond the hook's low; target measured from the
original 1-2-3's start to the hook's peak.

## Grid test (Step 6)

`validation/grid_test.py::run_strategy_grid`,
`pivot_window in {7,9,13}` x `target_r_multiple in {0.5,1.0,1.5}`,
symbols equity `{QQQ, SPY}` / crypto `{BTC/USDT, ETH/USDT}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.222 (24/108)**
- by_asset_class: equity 16/54, crypto 8/54
- by_vol_regime: low 13/36, mid 4/36, high 7/36
- best_cell: QQQ, pivot_window=7, target_r_multiple=1.0, low-vol, Sharpe 2.06

A follow-up full-sample sweep across `pivot_window in {7,9,13}` x
`target_r_multiple in {0.5,1.0,1.5}` on QQQ/SPY found `pivot_window=7,
target_r_multiple=1.5` clears Sharpe >= 1.0 on BOTH symbols simultaneously
(QQQ 1.175, SPY 1.023), adopted as the primary config below.

## Single-config validators (config: pivot_window=7, target_r_multiple=1.5, hook_lookback=25, max_hold_days=25, full sample)

| Validator | QQQ | SPY | Threshold | Passed |
|---|---|---|---|---|
| Sharpe ratio | 1.175 | 1.023 | >= 1.0 | **pass (both)** |
| Max drawdown | 0.155 | 0.094 | <= 0.25 | pass (both) |
| Transaction cost survival (10bps/trade) | net Sharpe 1.130 (23 trades) | net Sharpe 0.938 (26 trades) | >= 0.5 | pass (both) |
| Walk-forward (4 splits, SPY, manual fallback) | per-split Sharpe [1.83, 1.11, 1.12, 0.28], pass_fraction 1.0 | -- | >= 0.75 | pass |
| Parameter sensitivity (9-combo grid) | relative_std 0.507 | -- | <= 0.5 | **FAIL (borderline, 0.007 over)** |

## Decision

**Rejected** — despite Sharpe/MDD/transaction-cost/walk-forward all
passing with good margin on both QQQ and SPY, the parameter sensitivity
check fails narrowly (relative_std 0.507 vs threshold 0.5): performance
varies meaningfully across the pivot_window/target_r_multiple grid
(Sharpe ranges from 0.186 at pivot_window=13 up to 1.099 at
pivot_window=7, target_r_multiple=1.5), indicating the strong headline
result is somewhat parameter-fragile rather than robust across the
grid. Strategy/report kept as a record of a near-miss rejection.

## Notes for future loops

This is a genuine near-miss — only one validator failed, and only by a
small margin (0.507 vs 0.5). A future loop could try narrowing the grid
around pivot_window in {6,7,8} (all near the best-performing region) to
see if a less parameter-sensitive sub-region exists, or could try a
volatility-normalized target_r_multiple (scaling by ATR rather than a
fixed multiplier of the primary leg height) to reduce cross-symbol/
cross-regime dispersion. Distinct mechanic from the already-tested plain
1-2-3 reversal entries — worth revisiting given how close this came to
passing.
