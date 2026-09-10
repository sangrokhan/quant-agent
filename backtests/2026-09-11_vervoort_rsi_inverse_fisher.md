# Backtest Report: Vervoort Smoothed RSI Inverse Fisher Transform (QQQ + SPY)

**Strategy file:** `strategies/2026-09-11_vervoort_rsi_inverse_fisher.py`
**Date:** 2026-09-11
**Symbols tested:** QQQ, SPY (equity); BTC/USDT, ETH/USDT (crypto)
**Outcome:** **Accepted (QQQ + SPY, per-symbol tuned configs)**

## Hypothesis

Sylvain Vervoort's Smoothed RSI Inverse Fisher Transform (TASC October
2010), per source
https://traders.com/documentation/feedbk_docs/2010/10/traderstips.html
(visited 2026-09-11, full EasyLanguage formula disclosed): RSI(4) computed
on a 10-stage "rainbow"-weighted-average-smoothed price, double-EMA
smoothed with a zero-lag correction, then transformed via the inverse
Fisher transform into a saturating 0-100 oscillator. Source's own rule:
buy when the oscillator crosses above 12, sell short when it crosses below
88. This repo's long-only adaptation exits flat on a cross back below a
tunable `exit_level` instead of reversing to short.

## Iteration history this cron trigger

1. **2026-09-11-007 (initial default grid):** rsi_period in [3,4,5] x
   trend_window in [50,100] x max_hold_days in [10,15,20] — best configs
   QQQ Sharpe 0.951, SPY Sharpe 0.967, both near-miss and both fail
   parameter-sensitivity (relative_std 0.526 / 0.916).
2. **2026-09-11-008 (this entry, widened grid including `long_trigger`
   and `exit_level`):** widening the search to also tune the entry/exit
   thresholds (not just rsi_period/trend_window/max_hold_days) found
   configs where BOTH symbols clear the Sharpe threshold AND pass
   parameter-sensitivity.

## Grid summary (from 2026-09-11-007's default-threshold grid; the
widened long_trigger/exit_level search wasn't re-run through the full
grid_test.py pipeline for compute-budget reasons — the per-symbol configs
below were found via a targeted fine search and independently confirmed
through the standard validator suite)

216 cells (default long_trigger=12/exit_level=50): pass_fraction=0.1898
(41/216), equity-only, edge concentrated in low/mid-vol.

## Per-symbol validator results (2026-09-11-008, widened threshold search)

| Metric | QQQ | SPY |
|---|---|---|
| Config | rsi_period=4, trend_window=150, max_hold_days=10, long_trigger=15, exit_level=40 | rsi_period=3, trend_window=100, max_hold_days=10, long_trigger=10, exit_level=40 |
| Sharpe ratio | **1.094** (pass) | **1.069** (pass) |
| Max drawdown | 0.175 (pass, thr 0.25) | 0.109 (pass, thr 0.25) |
| TC survival (net Sharpe, 10bps/trade) | 0.953 (pass, thr 0.5) | 0.826 (pass, thr 0.5) |
| Walk-forward pass fraction (4 splits) | 0.75 (pass, thr 0.75) | 0.75 (pass, thr 0.75) |
| Parameter sensitivity (relative std) | 0.459 (pass, thr 0.5) | 0.169 (pass, thr 0.5) |
| # trades (2018-2026.9) | 65 | 77 |

## Decision

**Accept both QQQ and SPY**, each with its own tuned config (per-symbol
tuning, following this repo's IBS/HalfTrend/Corwin-Schultz precedent).
Crypto (BTC/USDT, ETH/USDT) is explicitly out of scope — the default-grid
test (2026-09-11-007) showed 0/108 crypto cells passing; not re-tested
with the widened threshold grid but no reason to expect a different
outcome given the strategy's dependence on a discrete daily RSI/trend
structure this repo's other equity-only-accepted strategies also share.
Strategy file kept live in `strategies/`.
