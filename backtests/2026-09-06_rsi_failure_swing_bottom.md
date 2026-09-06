# RSI Failure Swing Bottom (Wilder's Original Reversal Signal)

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_rsi_failure_swing_bottom.py`
**KB id:** 2026-09-06-134

## Hypothesis

Per J. Welles Wilder's "New Concepts in Technical Trading Systems"
(summarized by Elearnmarkets): a failure swing bottom occurs when price
makes a lower low but RSI fails to make a lower low (RSI's second swing
low stays above the oversold level, e.g. 30), then RSI breaks back above
the intervening swing high ("fail point"), confirming a bullish reversal.
Wilder: "Failure Swings above 70 or below 30 are very strong indications
of a market reversal." First strategy in this repo implementing the full
4-point failure-swing state machine (distinct from plain RSI threshold
crosses, Connors RSI, and prior divergence-only strategies which don't
require the fail-point breakout confirmation).

**Source:** https://blog.elearnmarkets.com/rsi-failure-swing/ (browser_exec
— explicit definition, price/RSI divergence precondition, fail-point break
confirmation rule).

## Grid test (oversold_level=[25,30,35] x swing_window=[3,5] x max_hold_days=[10,15], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026)

- 3/144 cells passed (equity 3/72, **crypto 0/72 decisively rejected**)
- By vol regime: low 0/48, mid 1/48, high 2/48 — mostly a high-vol-slice
  effect
- Best cell: oversold_level=35, swing_window=5, max_hold_days=15, QQQ
  high-vol, Sharpe 1.252

## Single-config validators (QQQ, oversold_level=35, swing_window=5, max_hold_days=15, full sample)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | FAIL | 0.719 | ≥ 1.0 |
| Max drawdown | PASS | 2.5% | ≤ 25% |

Only 15 trades over the full 2019-2026 sample — the 4-point pattern is
rare and the high-vol-regime edge does not generalize to the full sample.

## Decision: **REJECT**

Grid pass_fraction 0.021 (3/144) is decisive — narrow high-vol-regime
equity slice only, crypto fully rejected (0/72), and full-sample Sharpe on
the best config (0.719) misses the 1.0 threshold with very few trades (15).
Skipped walk-forward/TC-survival/parameter-sensitivity given the decisive
grid + full-sample rejection.
