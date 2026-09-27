# ROC-of-ROC Thrust Agreement Trend — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_roc_of_roc_thrust_agreement_trend.py`
**Source:** https://www.luxalgo.com/library/indicator/roc-of-roc/

## Hypothesis

LuxAlgo's "ROC-of-ROC" plots price acceleration: a 9-bar % rate of change
(velocity), differenced again over 9 bars (source's explicit "second pass
as a difference, not a percent change" construction). Source's own
disclosed interpretation: velocity and acceleration AGREEING (both
positive) is "thrust"; a split (velocity positive, acceleration negative)
is "an advance still rising but losing thrust" — an early warning, not an
automatic reversal call. Implemented as a long entry on fresh
velocity+acceleration agreement within an SMA trend gate; exit on the
deceleration-warning split, trend break, or time-stop.

## Grid test (Step 6)

`validation/grid_test.py::run_strategy_grid`,
`velocity_length in {5,9,14}` x `trend_window in {30,50,100}`,
symbols equity `{QQQ, SPY}` / crypto `{BTC/USDT, ETH/USDT}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.352 (38/108)** — the best pass rate of any strategy
  tested this cron trigger
- by_asset_class: equity 25/54, crypto 13/54
- by_vol_regime: low 29/36, mid 6/36, high 3/36
- best_cell: ETH/USDT, velocity_length=5, trend_window=50, mid-vol, Sharpe 2.78

## Full-sample validators (critical finding)

Despite the strong grid pass_fraction, full-sample Sharpe on the grid's
nominal best config (velocity_length=5, trend_window=50) FAILS on both
QQQ (0.629) and SPY (0.472). A finer sweep across `velocity_length in
{5,9,14}` x `trend_window in {30,50,100}` found NO combination clears
1.0 Sharpe on both symbols simultaneously — the closest is QQQ at
trend_window=100 (1.01) paired with SPY at the same setting (only 0.59).

Crypto (ETH/USDT) full-sample: Sharpe 0.162, max drawdown 0.489 —
decisive fail on both counts (2850 trades — an adequate/large sample,
ruling out signal scarcity).

## Decision

**Rejected.** Like several other strategies in this repo, the attractive
grid pass_fraction is concentrated in the low-vol tercile and doesn't
survive a full-sample check; here it's compounded by no single parameter
setting working simultaneously across QQQ and SPY. Crypto's high full-
sample drawdown (48.9%) with an adequate trade count rules out this being
a sampling artifact — the underlying "thrust agreement" signal doesn't
translate to a full-cycle edge on any tested asset.

## Notes for future loops

The source's own framing suggests deceleration warnings are meant as a
risk-tightening cue, not a full exit trigger — a future loop could try
using the deceleration signal only to reduce position size (continuous
sizing dial, following this repo's established pattern for several other
oscillators) rather than a full exit, potentially preserving more of the
gains during the "still rising but losing thrust" phase that this
strict-exit version cuts short.
