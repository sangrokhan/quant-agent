# Bearish Side by Side White Lines (Short) — Backtest Report

**Date:** 2026-09-21
**Strategy file:** `strategies/2026-09-21_bearish_side_by_side_white_lines_short.py`
**Source:** https://www.quantifiedstrategies.com/types-candlestick-patterns/ ("75 Types of Candlestick Patterns")

## Hypothesis

The "Bearish Side by Side White Lines" pattern (tall bearish bar1, bar2
gaps down and is bullish, bar3 is bullish with an open similar to bar2's
own open) is disclosed as a bearish continuation pattern by
QuantifiedStrategies.com's catalog: two failed bullish bounce attempts
after aggressive selling confirm the downtrend will resume. First test of
this pattern in this repo (0 prior KB hits).

## Feasibility check

Unlike this cron trigger's two prior rejected gap patterns (Kicking
Pattern, Upside Gap Two Crows), this pattern produces a usable sample:
46 trades (QQQ), 36 trades (SPY), 2 trades (BTC/USDT) over the test
window at default parameters.

## Grid test (Step 6)

`param_grid={"long_body_mult": [0.5,0.7,1.0], "max_hold_days": [5,10,15]}`,
symbols `{"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2018-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.009 (1/108 cells) -- decisive fail**
- By asset class: equity 1/54, crypto 0/54
- By vol regime: low 0/36, mid 0/36, high 1/36
- Best cell: QQQ, long_body_mult=0.5/max_hold_days=5, high-vol regime,
  Sharpe 1.237 (isolated single passing cell, not representative)
- Worst cell: QQQ, same params, low-vol regime, Sharpe -1.339

## Decision: **REJECT (decisive)**

The pattern fires reasonably often (unlike the prior two iterations'
feasibility-blocked patterns) but the resulting short-side trades show no
systematic edge -- only 1 of 108 grid cells clears the Sharpe/MDD bar, and
that single pass is not corroborated by any neighboring parameter or
regime cell (the same QQQ config fails decisively in the low-vol regime).
This is consistent with the source's own hedged framing ("many traders use
this pattern as a bearish continuation pattern" -- an unconfirmed folk
claim, not a disclosed backtest result) rather than a verified edge. No
single-config validator suite run given the decisive grid failure.
Strategy/report files kept as a record.
