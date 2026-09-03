# Backtest Report: Moving Average Envelope Mean-Reversion

**Strategy file:** `strategies/2026-09-04_ma_envelope_meanrev.py`
**Knowledge base id:** 2026-09-04-065

## Hypothesis

Per RunBacktest's Moving Average Envelope Breakout page: draw upper/lower
bands at a fixed percentage distance (`envelope_pct`, default 2%)
above/below an SMA(`ma_window`, default 20). Distinct from every prior
band-based strategy in this repo (Bollinger/SD channel use std-dev bands,
Keltner uses ATR bands, VWAP bands use volume-weighted variance) since
envelope bands are a simple fixed PERCENTAGE of the moving average.
Mean-reversion variant implemented: long when close touches/crosses below
the lower envelope band, exit when price reverts back to touch the middle
SMA.

Source: https://runbacktest.com/trading-strategies/moving-average-envelope-breakout
(QuantifiedStrategies' own article 404'd; web_search failed twice with a
DDGS/Yahoo TLS connection error, fell back to browser_exec).

## Grid test summary

- Grid: `envelope_pct` in {1.5,2.0,3.0} x symbols {QQQ,SPY,BTC/USDT,ETH/USDT}
  x 3 vol-regime terciles = 36 cells.
- pass_fraction: **0.0 (0/36)** — no cell passed at all, the lowest of any
  strategy tested in this repo.
- best_cell: QQQ, envelope_pct=1.5, high-vol tercile, Sharpe only 0.72

## Full-sample sweep (envelope_pct in {1.5,2.0,3.0})

| Symbol | pct=1.5 | pct=2.0 | pct=3.0 |
|---|---|---|---|
| QQQ | 0.384 | 0.410 | 0.469 |
| SPY | 0.340 | 0.296 | 0.304 |

All far below the 1.0 threshold — skipped remaining validator suite per
Step 7 minimum-subset guidance given the unambiguous magnitude of
shortfall (no grid cell even passed).

## Outcome

**Rejected.** Full-sample Sharpe never exceeds 0.469 across 6
symbol/percentage combos on QQQ/SPY. Crypto not separately reported (grid
crypto cells also 0/18, consistent with repo pattern) but full-sample
sweep skipped for crypto given the equity-side result is already
decisive.

## Notes

First fixed-PERCENTAGE envelope (vs std-dev/ATR/volume-variance bands)
mean-reversion strategy tested in this repo. The simple touch-of-
lower-band-then-revert-to-mean logic appears too generic/low-conviction on
this daily-bar sample — a 2% fixed-percentage band on QQQ/SPY triggers far
more often in low-vol periods (band too tight) or barely triggers in
high-vol periods (band too static relative to realized vol), unlike
ATR/std-dev-based bands which adapt to volatility. A future loop could try
the breakout (rather than mean-reversion) variant this source also
documents, or replace fixed-percentage with a volatility-adaptive
percentage.
