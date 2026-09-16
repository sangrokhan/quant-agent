# Backtest Report: TSI Trend-Gated Fix Attempt for SPY (2026-09-17-081 revisit)

**Strategy file:** `strategies/2026-09-17_tsi_trend_gated_spy_fix.py`
**Date:** 2026-09-17
**Hypothesis source:** Direct fix attempt of 2026-09-17-081 (same cron trigger, no new external research)

## Hypothesis

2026-09-17-081 found TSI (William Blau) centerline+signal-line crossover a
near-miss on SPY (Sharpe 0.864-0.980 depending on config, always <1.0
threshold). This iteration hypothesized that adding an SMA(trend_window)
long-term trend gate on top of the same TSI condition would filter out
whipsaw trades in range-bound/bearish regimes and lift SPY's Sharpe above
1.0.

## Parameter search

Hand sweep over `long_period∈{20,25,30}` x `signal_period∈{5,7,10}` x
`trend_window∈{100,150,200}` (27 combos) on SPY, short_period fixed at
Blau's default 13:

- Best result: Sharpe=0.772 (MDD=0.090) at (long_period=20, signal_period=5,
  trend_window=100) — **worse** than 2026-09-17-081's original near-miss
  best of Sharpe=0.980 (no trend gate).
- All 27 combos tested had lower Sharpe than the original ungated TSI
  condition's best config.

## Decision (Step 8)

**Rejected.** The trend-gate fix hypothesis is falsified: adding an
SMA-based trend filter on top of the TSI condition consistently *reduces*
SPY's Sharpe rather than improving it (likely by filtering out some of the
TSI signal's genuinely profitable early-trend entries, which occur before
price durably clears a long SMA). No config in the 27-combo sweep
approaches the 1.0 Sharpe threshold. 2026-09-17-081's SPY near-miss remains
unresolved; a different rescue approach (e.g. continuous sizing dial
instead of an additional binary gate) would need to be tried in a future
iteration.
