# OU Half-Life Z-Score Mean Reversion — Smoothed-Z Fix Attempt — Backtest Report

**Date:** 2026-09-12 | **Outcome:** REJECTED

## Hypothesis

Direct fix attempt for near-miss 2026-09-07-012 (OU half-life-gated Z-score
mean reversion): SPY passed Sharpe/MDD/TC/walk-forward at entry_z=1.5,
lookback=40, but FAILED parameter sensitivity (relative_std=0.59) — a
fragile local optimum with Sharpe collapsing ~68% one notch off the peak.
This iteration applies a rolling-mean smoothing to the z-score itself
(`z_smooth = z.rolling(smooth_window).mean()`) before thresholding, on the
theory that smoothing a noisy mean-reversion trigger flattens the
parameter-response surface (standard signal-processing intuition) without
changing the underlying OU AR(1)-fit/half-life-gate mechanism.

## Single-config validators (QQQ / SPY, lookback=40, entry_z=1.5, smooth_window=3, max_hold_days=20)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | **FAIL** 0.579 | **FAIL** 0.616 |
| Max drawdown (<=0.25) | pass 0.124 | pass 0.101 |
| TC survival (net Sharpe>=0.5) | pass 0.503 | pass 0.525 |
| Walk-forward (>=0.75) | **FAIL** 0.5 | **FAIL** 0.5 |
| Parameter sensitivity (rel std<=0.5) | **FAIL** 1.379 | **FAIL** 0.779 |

## Grid test (run_grid_ou_halflife_smoothed.py)

Grid: `entry_z` in [1.0,1.5,2.0] x `smooth_window` in [2,3,5], equity
(QQQ,SPY) + crypto (BTC/USDT,ETH/USDT), vol_regime_splits=3, 108 cells.

- pass_fraction = 0.074 (8/108) — WORSE than the unsmoothed original's
  overall behavior
- by_asset_class: equity 8/54, crypto 0/54 (decisive reject)
- by_vol_regime: low 6/36, mid 2/36, high 0/36
- best_cell: entry_z=1.0, smooth_window=5, QQQ, low-vol, Sharpe=1.76

## Decision: REJECT

The smoothing fix made things WORSE, not better: SPY's full-sample Sharpe
at the original best config (entry_z=1.5) dropped from 1.373 (unsmoothed,
2026-09-07-012) to 0.616 (smoothed here) — the 3-bar rolling mean applied
to an already-lagged OU z-score evidently over-smooths and destroys most
of the mean-reversion timing edge, rather than merely flattening the
parameter surface as hypothesized. Parameter sensitivity is STILL failing
(SPY 0.779, QQQ 1.379, both worse than the original's 0.59) — smoothing
the trigger did not fix the underlying overfit issue, it just moved the
whole surface down. Walk-forward also now fails for both symbols
(0.5 < 0.75), where the original at least passed for SPY. This "flatten
via smoothing" fix hypothesis is falsified for this construction.

Strategy file kept in `strategies/` as a rejected-attempt record.
