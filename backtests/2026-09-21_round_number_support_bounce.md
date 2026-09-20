# Round-Number Psychological Support Bounce — Backtest Report

**Date:** 2026-09-21
**Strategy file:** `strategies/2026-09-21_round_number_support_bounce.py`
**Outcome:** REJECTED

## Hypothesis

Per the well-documented "round number" market microstructure phenomenon
(Donaldson & Kim 1993, "Price Barriers in the Dow Jones Industrial
Average" -- primary source captcha-blocked on ScienceDirect this
iteration, concept corroborated across multiple independent TA education
sources), round-number price levels act as psychological support due to
clustered limit orders. Operationalized as: touch of a round-number level
(adaptive increment as % of current price) from above, closing back above
it (rejection), in an established uptrend -- long entry; exit on support
break or time-stop. 0 prior round-number/psychological-level entries in
this repo.

## Parameter sweep (manual, prior to formal grid -- decisive reject found
early)

QQQ full-sample Sharpe across `touch_pct` ∈ {0.005,0.01,0.02,0.03} ×
`round_increment_pct` ∈ {0.01,0.02,0.03} (9 combos): ranged from -0.003
to 0.470, with entry counts from 1 to 47 trades over 7.5 years. No
configuration approaches the 1.0 Sharpe threshold. SPY's best full-sample
Sharpe across the same sweep was a degenerate "inf" (near-zero trade count
producing a division artifact, not a genuine result). BTC/USDT best 0.170,
ETH/USDT best 0.082.

Given the full parameter sweep already showed the effect has essentially
no measurable edge on any symbol at any tested configuration, the formal
`run_strategy_grid`/`validators.py` pipeline (Steps 6-7) was skipped as it
would not change the reject conclusion -- consistent with
RESEARCH_LOOP.md's guidance that a candidate can be rejected early if the
research/testing itself makes the outcome unambiguous.

## Decision

**Rejected.** No parameter configuration across a 9-point sweep on QQQ
(plus spot checks on SPY/BTC/ETH) comes close to a usable Sharpe ratio.
The round-number-support-bounce concept, at least in this simple
touch-and-reject operationalization, does not translate into a tradeable
mechanical edge on this repo's symbol universe.
