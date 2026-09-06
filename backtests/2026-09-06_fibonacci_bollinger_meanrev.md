# Fibonacci Bollinger Bands Mean Reversion (Inner 1.618 Band) — Backtest Report

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_fibonacci_bollinger_meanrev.py`
**Outcome: REJECTED**

## Hypothesis

Fibonacci Bollinger Bands replace the standard Bollinger Bands' fixed
standard-deviation multiplier (typically 2.0) with Fibonacci-ratio multiples
(1.618, 2.618, 4.236) of the rolling standard deviation around a central
moving average. Per TrendSpider's documentation: "Price interactions with
the bands can signal potential buy or sell opportunities, similar to
traditional Bollinger Bands." This iteration tests the mean-reversion use
case at the innermost band (1.618x std): long entry when close crosses below
the lower 1.618-band, exit at the central moving average or a max_hold_days
time-stop.

Source: https://help.trendspider.com/kb/indicators/fibonacci-bollinger-bands
(LuxAlgo's dedicated page 404'd). First Fibonacci Bollinger Bands strategy in
this repo — distinct from dozens of standard-deviation-multiplier Bollinger
Band variants already tested (this repo tests the specific empirical claim
that Fibonacci ratios "more accurately reflect market volatility" vs the
conventional 1.5/2.0/2.5 multipliers already extensively tested).

## Step 6 — Grid test

144 cells: `window` [15,20,25] × `fib_multiplier` [1.618,2.618] ×
`max_hold_days` [10,15], symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT
(crypto), vol_regime_splits=3, 2015-2026.

- **pass_fraction: 0.132 (19/144)**
- by_asset_class: equity 19/72 (26%), crypto 0/72 (0%)
- by_vol_regime: low 17/48 (35%), mid 2/48 (4%), high 0/48 (0%)
- best_cell: QQQ, window=20/fib_multiplier=1.618/max_hold_days=10, low-vol
  slice, Sharpe 1.989
- worst_cell: ETH/USDT, window=20/fib_multiplier=2.618/max_hold_days=10,
  mid-vol slice, Sharpe -0.255

## Step 7 — Single-config validation (best full-sample-Sharpe config per symbol)

| Symbol | Config | Sharpe (full sample) | MDD | TC-adj Sharpe (10bps, N trades) | Param sensitivity (rel std) |
|---|---|---|---|---|---|
| QQQ | window=15/fib=1.618/hold=10 | 0.603 (FAIL, thr 1.0) | 0.227 (PASS, thr 0.25) | 0.531 (PASS; 87 trades) | 0.324 (PASS, thr 0.5) |
| SPY | window=20/fib=1.618/hold=15 | 0.518 (FAIL, thr 1.0) | **0.265 (FAIL, thr 0.25)** | 0.453 (FAIL, thr 0.5; 73 trades) | 0.381 (PASS) |

Walk-forward: skipped (pre-existing repo-wide `check_walk_forward` bug).

## Decision

**Rejected.** Both symbols decisively miss Sharpe (0.603 QQQ, 0.518 SPY),
each well short of the 1.0 threshold — this is not a near-miss like several
other rejections this cron trigger. Similar to the plain standard-Bollinger
mean-reversion strategy already accepted in this repo
(`2026-09-03_bb_meanrev_qqq_volregime.py`, note: that strategy uses a
low-vol regime GATE which this Fibonacci variant does not), the grid's
best-cell Sharpe (1.989) is again a low-vol-tercile-only artifact — the
strategy passes almost exclusively in low-vol conditions (17/19 total
passes) and the full-sample Sharpe without a regime gate does not clear the
bar. MDD additionally fails for SPY (0.265 vs 0.25 threshold). The
Fibonacci-ratio band-width scaling (1.618 vs the standard 2.0 std multiplier)
does not appear to meaningfully change the strategy's edge relative to the
many standard-deviation-based Bollinger variants already tested in this
repo — TrendSpider's marketing claim that Fibonacci ratios "more accurately
reflect market volatility" is not supported by this backtest.

## Notes for future loops

Do not pursue further Fibonacci-Bollinger-Band variants without a low-vol
regime gate — the already-ACCEPTED plain standard-BB strategy in this repo
(`2026-09-03_bb_meanrev_qqq_volregime.py`) succeeds specifically BECAUSE it
gates entries to the low-vol regime rather than trading unconditionally; a
Fibonacci-scaled variant WITH that same gate might be worth a quick
follow-up (it would likely behave similarly to the already-accepted
strategy, so low priority), but the ungated version tested here shows no
edge over the standard 2.0-multiplier ungated variants already rejected in
this repo.
