# Bullish Kicking Pattern — Backtest Report

**Date:** 2026-09-21
**Strategy file:** `strategies/2026-09-21_kicking_pattern_bullish_reversal.py`
**Source:** Standard/public-domain candlestick pattern definition (classic Nison-style 2-candle reversal; same reference family as this repo's Railroad Tracks/Belt Hold/Counterattack entries)

## Hypothesis

The "Kicking" pattern (bearish marubozu immediately followed by a
full-range gap-up bullish marubozu) is one of the classic strongest
reversal signals. First test in this repo (0 prior "Kicking Pattern" KB
hits).

## Feasibility check (before grid test)

At the strict textbook definition (marubozu shadow tolerance <= 10% of
bar range, AND a full-range gap where today's low exceeds yesterday's
high), the pattern **never fires** on QQQ 2010-2026 daily bars (0 trades).
Loosening shadow_tolerance to 0.3 (30% shadows allowed -- already a
significant departure from "marubozu") produces only 2 trades over 16
years; only at shadow_tolerance=0.5 (essentially no longer a marubozu
test) does it produce a usable 34 trades.

## Decision: **REJECT (infeasible -- insufficient sample size)**

The strict full-range-gap + marubozu combination that defines this pattern
is fundamentally a poor fit for daily-bar US equity/crypto data: genuine
full-range overnight gaps (today's low > yesterday's high) are rare events
confined to crash/panic reopens, and requiring BOTH candles to be
near-shadowless marubozu on top of that gap compounds the rarity. No
grid/validator run was performed since the entry condition produces zero
or near-zero trades at any parameterization that still resembles the
pattern's actual definition -- there is no statistically meaningful sample
to test a Sharpe/MDD/walk-forward hypothesis against. This is a structural
feasibility rejection (pattern too rare on this data), not a performance
rejection. Strategy file kept as a record; not worth pursuing further
without intraday data (where full-range gaps are more common at session
opens) which this repo's pipeline does not provide.
