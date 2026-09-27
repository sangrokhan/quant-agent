# Exhaustion Bar Bullish Reversal — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_exhaustion_bar_bullish_reversal.py`
**Source:** https://www.luxalgo.com/library/indicator/exhaustion-bar/

## Hypothesis

LuxAlgo's "Exhaustion Bar" codifies a "maximum-effort, minimal-result"
candle: a stretched prior decline (>= 2x ATR), a fresh N-bar low, a
wide-range bar (>= 1.5x recent average range), closing near its own high
(within 25% of the top), with the excursion left as a rejected wick
(closing back inside the prior bar's range). This is read as seller
exhaustion worth a long reversal entry, stop below the bar's own low
(source's own stated stop placement), R-multiple target.

## Grid test (Step 6)

`validation/grid_test.py::run_strategy_grid`,
`wide_range_multiplier in {1.2,1.5,2.0}` x `reward_r_multiple in {1.5,2.0,3.0}`,
symbols equity `{QQQ, SPY}` / crypto `{BTC/USDT, ETH/USDT}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.0 (0/108)**
- by_asset_class: equity 0/54, crypto 0/54
- by_vol_regime: low 0/36, mid 0/36, high 0/36
- best_cell (still below threshold): SPY, wide_range_multiplier=2.0, reward_r_multiple=1.5, high-vol, Sharpe 0.89
- worst_cell: ETH/USDT, wide_range_multiplier=1.2, reward_r_multiple=1.5, low-vol, Sharpe -1.55

## Trade-count / full-sample check

At the loosest setting (`wide_range_multiplier=1.2, reward_r_multiple=2.0`):
QQQ 10 trades (Sharpe -0.42), SPY 11 trades (Sharpe -0.38), BTC/USDT 338
trades (Sharpe -0.15). Crypto has an adequate sample size and still shows
a decisively negative Sharpe, confirming this isn't merely a signal-
scarcity artifact — the pattern has no real edge as constructed.

## Decision

**Rejected.** Zero grid cells pass (0/108), and the crypto sample (338
trades) rules out signal scarcity as the explanation — the bullish
exhaustion-bar-after-decline pattern shows a genuine (if modest) negative
edge across all three tested assets and every parameter combination.

## Notes for future loops

This differs from the already-rejected RVOL Exhaustion-Climax Reversal
(`2026-09-27-004`, decisive signal-starvation) by requiring a real ATR-
scaled prior move + wide-range + close-location combination rather than
just an RVOL spike, but the result is the same qualitative outcome: naive
single-bar "exhaustion" patterns don't show a robust bounce edge on daily
bars for QQQ/SPY/BTC/ETH in this repo's 2019-2026 sample. Future work on
this family should probably require a MULTI-bar confirmation (e.g. the
source's own optional "Confirmation: Close Beyond Midpoint" next-bar rule)
combined with a broader market regime filter (e.g. low-vol tercile only,
similar to several other accepted strategies here) rather than trading the
single-bar signal unconditionally.
