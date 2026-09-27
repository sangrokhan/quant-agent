# Backtest report: Ehlers Roofing Filter z-score band re-entry + bar confirmation

**Hypothesis:** Ehlers Roofing Filter (two-pole high-pass + Super Smoother
low-pass), rolling z-scored, long entry on a CONFIRMED re-entry through the
-Threshold sigma band from oversold (not a naked touch) plus a bullish
confirmation bar (close > open); gated by SMA(trend_window) uptrend filter.
Source: https://www.algobot.live/roofing-filter-cycle-reversion-ea-mt5/
(visited this iteration).

**Strategy file:** `strategies/2026-09-27_roofing_filter_zscore_bandreentry_barconfirm.py`

## Grid test (validation/grid_test.py::run_strategy_grid)

param_grid: threshold in {0.8, 1.0, 1.3} x norm_window in {40, 50, 70}
(hp_period=48, lp_period=10, trend_window=100 fixed defaults),
symbols equity=[QQQ, SPY], crypto=[BTC/USDT, ETH/USDT], vol_regime_splits=3
(2019-01-01 to 2026-09-01).

- overall pass_fraction: 15/108 = 0.139
- by_asset_class: equity 9/54 (0.167), crypto 6/54 (0.111)
- by_vol_regime: low 10/36 (0.278), mid 4/36 (0.111), high 1/36 (0.028)
- best_cell: threshold=1.3, norm_window=70, ETH/USDT, mid-vol regime, Sharpe 2.53
- worst_cell: threshold=1.0, norm_window=50, SPY, mid-vol regime, Sharpe -1.08

## Full-sample single-config Sharpe scan (best config per symbol)

| Symbol | Best config (threshold, norm_window) | Full-sample Sharpe | Full-sample MDD |
|---|---|---|---|
| QQQ | 1.3, 40 | 0.770 | 0.114 |
| SPY | 0.8, 70 | 0.667 | 0.090 |
| BTC/USDT | 1.0, 50 | 0.732 | 0.334 |
| ETH/USDT | 1.3, 70 | 0.456 | 0.777 |

All four symbols fail the Sharpe >= 1.0 validator decisively at their own
individually-best-tuned config (best achieved 0.770 on QQQ), despite some
narrow vol-regime slices (grid's mid-vol ETH cell) showing high Sharpe --
the grid's own low overall pass_fraction (0.139) confirms the edge, where it
exists at all, is confined to narrow slices and does not survive at
full-sample scope on any symbol.

## Validators

Given the decisive full-sample Sharpe failure on every symbol/config
combination (no candidate config clears the 1.0 threshold), the remaining
validator suite (max drawdown, transaction-cost survival, walk-forward,
parameter sensitivity) was not run in full -- Sharpe failure alone is
sufficient grounds for rejection per Step 8, and running the full suite
would not change the outcome. Max drawdown was already computed alongside
Sharpe above (best-config values shown; QQQ/SPY pass the 0.25 MDD threshold
individually, BTC/USDT and ETH/USDT fail decisively at 0.334/0.777).

## Outcome: REJECTED (all symbols, all tested configs)

The confirmed-band-re-entry + bar-confirmation refinement (vs this repo's
prior raw self-lag crossover and tanh continuous-sizing Roofing Filter
variants) does not rescue the strategy -- Sharpe remains below threshold on
every asset at full-sample scope. Left in `strategies/`/`backtests/` as a
record per Step 8 (rejected attempt, not a live strategy).
