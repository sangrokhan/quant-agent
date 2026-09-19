# Backtest Report: Sell-the-Rip 3-day RSI Crossover Baseline

**Strategy file:** `strategies/2026-09-20_sell_the_rip_rsi3_crossover.py`
**Date:** 2026-09-20
**Outcome:** REJECTED

## Hypothesis

Per quantifiedstrategies.com's "Sell the Rip Trading Strategy"
(https://www.quantifiedstrategies.com/sell-the-rip-strategy/, read via
browser_exec fallback -- web_search DDGS backend hit repeated
TLS/connection-reset errors this iteration), the article discloses its
own baseline rule: long when 3-day RSI < 30, exit ("sell the rip") when
3-day RSI crosses above 70, on SPY. The source itself explicitly judges
this baseline "far from tradable" (SPY since 1993: 391 trades, 0.61%
avg gain, 75% win rate, PF 1.6, MDD -39%) and reports (without disclosing
the exact improved rule, paywalled) that a stricter exit materially cuts
MDD to -24%.

This entry tests the source's disclosed baseline exactly, as a genuinely
distinct construction from this repo's already-accepted 2026-09-18-095
(3-day RSI<20 oversold entry + signal-based "close > yesterday's high"
exit, SPY accepted) -- this strategy instead uses a pure RSI-recrossing-70
exit with no price-level component.

## Grid test summary (`grid_summary_sell_the_rip_rsi3.json`)

- Grid: `entry_threshold` in {20,25,30} x `exit_threshold` in {60,70,80} =
  9 combos x {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles = 108
  cells.
- pass_fraction: 0.176 (19/108).
- By asset class: equity 19/54, crypto 0/54 (decisive crypto reject).
- By vol regime: low 18/36, mid 0/36, high 1/36.

## Full-sample confirmation

At the source's exact disclosed config (entry_threshold=30,
exit_threshold=70):

| Symbol | Sharpe | Max Drawdown |
|---|---|---|
| SPY | 0.549 | 0.370 (fails badly) |
| QQQ | 0.789 | 0.265 (fails) |
| BTC/USDT | 0.154 | 0.584 (fails badly) |
| ETH/USDT | 0.020 | 0.907 (fails catastrophically) |

This directly reproduces/confirms the source's own stated judgment that
the baseline rule is "far from tradable" due to drawdown size (source
reported -39% MDD on its own 1993-present SPY backtest; this repo's
2018-2026 window found -37% MDD, closely consistent).

A 30-combo full-sample search (entry_threshold in {15,20,25,30,35} x
exit_threshold in {60,65,70,75,80,85}) found a best SPY config
(entry_threshold=15, exit_threshold=85) reaching Sharpe 0.875 -- still a
near-miss short of the 1.0 threshold, and QQQ at the same shared config
only reaches 0.673.

## Decision

**REJECTED.** Decisively confirms the source's own stated finding that
this exact disclosed rule underperforms; even after widening the
threshold search, the best config remains a near-miss (Sharpe 0.875,
still below acceptance) rather than a pass. The source's own claimed
improved exit (which cuts MDD to -24% per its own backtest) is paywalled
and not implemented here -- a future loop could revisit if that specific
rule is ever found disclosed elsewhere, but it should not be reconstructed
speculatively without a concrete source.
