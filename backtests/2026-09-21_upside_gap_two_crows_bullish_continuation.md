# Upside Gap Two Crows (Bullish Continuation Reading) — Backtest Report

**Date:** 2026-09-21
**Strategy file:** `strategies/2026-09-21_upside_gap_two_crows_bullish_continuation.py`
**Source:** https://www.quantifiedstrategies.com/types-candlestick-patterns/ ("75 Types of Candlestick Patterns")

## Hypothesis

QuantifiedStrategies.com's classic-pattern catalog notes the "Upside Gap
Two Crows" pattern is traditionally bearish-reversal but "some traders
instead use it as a continuation pattern," with the source's own reasoning
implying a bullish continuation bias (bulls initiate both gaps; the 3-bar
sequence closes above bar1's close). This strategy operationalizes that
bullish-continuation reading. First test in this repo (0 prior KB hits for
this pattern), distinct from the already-tested Unique Three Rivers
(downward-drift structure vs this pattern's upward-drift gap structure).

## Feasibility check (before grid test)

At the source's full disclosed 7-condition structure (tall bullish bar1,
bar2 gaps above bar1's high but closes bearish, bar3 gaps above bar2's
open and closes bearish while engulfing bar2's body, bar3's close remains
above bar1's close), the pattern already only fires **9 times on QQQ
2010-2026** with NO body-size ("tall") filter applied to bar1 at all.
Adding even a modest 0.5x-ATR tallness requirement on bar1 (loosened from
an initial 1.0x, which produced 0 trades) drops the count to **0 trades on
QQQ, 2 on SPY, 0 on BTC/USDT, 0 on ETH/USDT** over the full 2018-2026
multi-asset test window.

## Decision: **REJECT (infeasible -- insufficient sample size)**

Same failure mode as this cron trigger's Kicking Pattern rejection
(2026-09-21-273): the pattern's own strict multi-bar gap-and-reversal
structure is simply too rare an event on daily-bar equity/crypto data to
produce a statistically meaningful sample at any reasonable
parameterization. No grid/validator run was performed. Structural
feasibility rejection, not a performance rejection. Strategy file kept as
a record.
