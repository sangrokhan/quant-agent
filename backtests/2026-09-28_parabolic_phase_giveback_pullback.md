# Parabolic Phase Giveback Pullback — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_parabolic_phase_giveback_pullback.py`
**Source:** https://www.luxalgo.com/library/indicator/parabolic-phase/

## Hypothesis

LuxAlgo's "Parabolic Phase" indicator detects a trend's terminal
accelerating stage: 3 consecutive impulse legs each steepening by a 1.2x
slope-ratio factor, contracting pullbacks, AND a long-term stretch extreme
(price at the 95th percentile of its distance from SMA200 over the
trailing 500 bars). Source's own trading guidance: once confirmed, manage
the exit — the phase ends on a trendline break, after which "a dotted
level marks the midpoint of the accelerated move as a reference for the
give-back that often follows." Adapted for daily-OHLCV-only data (no
swing-pivot trendline geometry) using ROC5-acceleration and EMA(10)-break
proxies; entry on the proxy "phase end", targeting an R-multiple of the
phase's own drawdown as the stop.

## Grid test (Step 6)

`validation/grid_test.py::run_strategy_grid`,
`acceleration_factor in {1.05,1.1,1.2}` x `stretch_percentile in {80,90}`,
symbols equity `{QQQ, SPY}` / crypto `{BTC/USDT, ETH/USDT}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.083 (6/72)**
- by_asset_class: equity 6/36, crypto 0/36
- by_vol_regime: low 0/24, mid 6/24, high 0/24

## Signal-frequency check (critical finding)

On equity (QQQ, SPY), the combined stretch-extreme + accelerating-ROC5
condition fires only **2-4 times over the full 7.7-year window** regardless
of parameter setting (acceleration_factor 1.05-1.2, stretch_percentile
80-90) — far too rare to draw any statistical conclusion, even though a
couple of these rare cells happen to clear the grid's per-cell Sharpe
threshold. This is the same "signal-scarcity" failure mode already
documented in this repo for other multi-condition structural patterns
(Cup-and-Handle `2026-09-06-172`, Morning Star `2026-09-06-161`).

On crypto (BTC/USDT, ETH/USDT), the setup fires far more often (95-142
trades over the same window, since 24/7 crypto has proportionally more
extreme-stretch/acceleration episodes), but the aggregate Sharpe is
decisively near zero to negative (-0.02 to +0.08 across all R-multiples
tested), a clean rejection with adequate sample size.

## Decision

**Rejected.** Equity's apparent "passes" are a statistical artifact of a
2-4-trade sample size, not a real edge — cannot be trusted regardless of
grid-cell Sharpe. Crypto has plenty of trades but a decisively flat-to-
negative edge. Neither asset class supports acceptance.

## Notes for future loops

The daily-bar proxy construction here (ROC5-acceleration + EMA10-break) is
a rough substitute for LuxAlgo's actual swing-pivot trendline geometry —
a future loop with access to intraday/pivot-detection tooling could
implement the indicator's real mechanics more faithfully, but given
crypto's clean negative result even with a much larger sample, the
underlying "buy the post-blowoff give-back" thesis itself looks weak, not
just under-tested. Recommend deprioritizing further Parabolic-Phase-style
attempts unless a fundamentally different exit/target construction is
tried.
