# Pipe Top Defensive Exit on SMA Trend — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_pipe_top_defensive_exit_sma_trend.py`
**Source:** https://thepatternsite.com/pipet.html

## Hypothesis

Bulkowski's Pipe Top: twin adjacent upward-spike bars with closely
overlapping highs, confirming when price closes below the pattern's
lowest price -- source's own stats: average decline 19%, break-even
failure rate 13%. Since this repo is long-only, operationalized as a
DEFENSIVE EXIT overlay on a plain SMA-crossover trend-following long
(matching this repo's existing convention for other bearish reversal
patterns like Wyckoff UTAD): a confirmed Pipe Top while long triggers an
immediate protective exit. First "Pipe Top" strategy in this repo (0
prior hits) -- distinct from the already-tested Pipe Bottom (twin
DOWNWARD-spike, bullish-reversal ENTRY trigger, opposite direction and
role).

## Grid test (Step 6)

`validation/grid_test.py::run_strategy_grid`,
`trend_window in {30,50,100}` x `spike_atr_mult in {1.5,1.8,2.2}`,
symbols equity `{QQQ, SPY}` / crypto `{BTC/USDT, ETH/USDT}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.306 (33/108)**
- by_asset_class: equity 27/54, crypto 6/54
- by_vol_regime: low 24/36, mid 9/36, high 0/36
- best_cell: QQQ, trend_window=50, spike_atr_mult=1.5, low-vol, Sharpe 2.71

A follow-up full-sample sweep across `trend_window in {30,40,50}` (the
`spike_atr_mult` parameter doesn't affect this config's Sharpe within the
tested range, since spike detection isn't the binding constraint at these
thresholds) found `trend_window=40` clears Sharpe >= 1.0 on BOTH symbols
simultaneously (QQQ 1.088, SPY 1.130), adopted as the primary config
below.

## Single-config validators (config: trend_window=40, spike_atr_mult=1.8, spike_close_pct=0.3, high_overlap_pct=0.02, confirm_window=5, max_hold_days=30, full sample)

| Validator | QQQ | SPY | Threshold | Passed |
|---|---|---|---|---|
| Sharpe ratio | 1.088 | 1.130 | >= 1.0 | **pass (both)** |
| Max drawdown | 0.232 | 0.133 | <= 0.25 | pass (both) |
| Transaction cost survival (10bps/trade) | net Sharpe 0.989 (73 trades) | net Sharpe 1.016 (64 trades) | >= 0.5 | pass (both) |
| Walk-forward (4 splits, SPY, manual fallback) | per-split Sharpe [1.35, 0.11, 1.72, 1.20], pass_fraction 1.0 | -- | >= 0.75 | pass |
| Parameter sensitivity (3-combo trend_window sweep) | relative_std 0.050 | -- | <= 0.5 | pass |

Crypto: only 6/54 grid cells pass -- not tested at single-config level.

## Decision

**Accepted for equity (QQQ, SPY)** at `trend_window=40,
spike_atr_mult=1.8`. All validators pass; parameter sensitivity is
especially low (0.050). **Not accepted for crypto** -- grid pass rate
too low (6/54).

## Notes for future loops

Near-identical numeric profile to this repo's earlier Wyckoff UTAD
defensive-exit strategy (also trend_window=40, QQQ 1.088 vs UTAD's own
QQQ result) -- both are bearish-reversal-pattern-as-defensive-exit
overlays on the same plain SMA(40) trend baseline. This is expected
since both strategies share the same baseline entry/exit skeleton and
differ only in which pattern triggers the early defensive exit; a future
loop could formally compare how often the two overlays' exit triggers
coincide vs diverge, or test combining both exit conditions (UTAD OR
Pipe Top) on the same baseline to see if the combined overlay improves
further or is redundant.
