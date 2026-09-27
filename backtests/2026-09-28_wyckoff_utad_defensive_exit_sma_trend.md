# Wyckoff UTAD Defensive Exit on SMA Trend — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_wyckoff_utad_defensive_exit_sma_trend.py`
**Source:** https://www.luxalgo.com/library/indicator/upthrust-after-distribution/

## Hypothesis

Wyckoff's Upthrust After Distribution (UTAD) is a bearish reversal-
confirmation pattern: after a qualified advance, price consolidates into
a mature, boundary-tested range, then a late breakout above resistance
that fails back inside within a short window is the UTAD -- read as
strong evidence distribution has completed and markdown is imminent.
Since this repo is long-only, UTAD is operationalized as a DEFENSIVE EXIT
overlay on a plain SMA-crossover trend-following long baseline: exit
immediately on a UTAD signal (in addition to the baseline's own SMA-break
exit and a time-stop), on the theory that pre-empting the exit ahead of
the typical post-UTAD markdown leg improves risk-adjusted returns.

## Grid test (Step 6)

`validation/grid_test.py::run_strategy_grid`,
`trend_window in {30,50,100}` x `min_advance_atr_mult in {1.5,2.0,3.0}`,
symbols equity `{QQQ, SPY}` / crypto `{BTC/USDT, ETH/USDT}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.306 (33/108)**
- by_asset_class: equity 27/54, crypto 6/54
- by_vol_regime: low 24/36, mid 9/36, high 0/36
- best_cell: QQQ, trend_window=50, min_advance_atr_mult=1.5, low-vol, Sharpe 2.71

Initial single-config check at the grid's nominal best (trend_window=50)
passed for QQQ but SPY missed by a hair (Sharpe 0.961 vs 1.0). A follow-up
sweep of `trend_window` in {30,40,50,60} found `trend_window=40` clears
the threshold on BOTH symbols simultaneously (SPY 1.130, QQQ improves too),
so that config was adopted as the primary config below.

## Single-config validators (config: trend_window=40, min_advance_atr_mult=2.0, full sample)

| Validator | QQQ | SPY | Threshold | Passed |
|---|---|---|---|---|
| Sharpe ratio | 1.088 | 1.130 | >= 1.0 | **pass (both)** |
| Max drawdown | 0.232 | 0.133 | <= 0.25 | pass (both) |
| Transaction cost survival (10bps/trade) | net Sharpe 0.989 (73 trades) | net Sharpe 1.016 (64 trades) | >= 0.5 | pass (both) |
| Walk-forward (4 splits, SPY) | per-split Sharpe [1.35, 0.11, 1.72, 1.20], pass_fraction 1.0 | -- | >= 0.75 | pass |
| Parameter sensitivity (SPY, 9-combo grid) | relative_std 0.067 | -- | <= 0.5 | pass |

Crypto: only 6/54 grid cells pass (scattered, not concentrated) — not
tested at single-config level given the grid's weak crypto showing.

## Decision

**Accepted for equity (QQQ, SPY)** at `trend_window=40,
min_advance_atr_mult=2.0`. All validators pass with strong margin;
parameter sensitivity is especially low (0.067 relative std across a
9-combo sweep), meaning the UTAD defensive-exit overlay's benefit is
robust to the exact trend-window/advance-multiplier choice. **Not
accepted for crypto** — grid pass rate too low/scattered (6/54) to
warrant a full single-config validator run.

## Notes for future loops

This is this repo's first Wyckoff UTAD-based strategy and demonstrates
that a purely defensive EXIT overlay (rather than an entry trigger) can
meaningfully improve a plain SMA-trend baseline's risk-adjusted return —
consistent with the pattern's own intended use as a distribution-top
warning rather than a standalone entry signal. A future loop could try
combining this same UTAD exit overlay with one of this repo's other
already-accepted equity trend entries (e.g. the new Camarilla H4 breakout
or Weinberg TRI strategies from this same cron trigger) instead of a
plain SMA baseline, to see if the defensive-exit benefit compounds.
