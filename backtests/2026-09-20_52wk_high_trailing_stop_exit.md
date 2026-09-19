# Backtest Report: 52-Week High Breakout, Trailing-Stop Exit ("Exit 2")

**Strategy file:** `strategies/2026-09-20_52wk_high_trailing_stop_exit.py`
**Date:** 2026-09-20
**Outcome:** REJECTED (second rescue attempt failed, worse than parent on both Sharpe AND MDD)

## Hypothesis / rescue attempt

Second follow-up to prior id 2026-09-20-054 (52-Week High breakout +
200d-SMA-exit, near-miss REJECTED at SPY/QQQ Sharpe 0.879/0.880). The
first rescue attempt (2026-09-20-055, low-vol regime gate) made things
worse (Sharpe dropped to 0.56) and was rejected as a documented negative
result. This iteration tries the OTHER exit variant the source article
disclosed: a 25% trailing stop ("Exit 2" in
https://www.quantifiedstrategies.com/52-week-high-strategy/'s cited
enlightenedstocktrading.com backtest), replacing the flat 200d-SMA-cross
exit with a trailing peak-based stop.

## Full-sample parameter search (SPY + QQQ jointly, 25 combos)

Searched `lookback_days` in {63,100,126,189,252} x `trail_pct` in
{0.10,0.15,0.20,0.25,0.30}. Best shared config:
`lookback_days=126, trail_pct=0.25`:

| Symbol | Sharpe | Max Drawdown |
|---|---|---|
| SPY | 0.694 | 0.301 (fails MDD) |
| QQQ | 0.789 | 0.271 (fails MDD) |
| BTC/USDT | 0.080 | 0.783 (fails badly) |
| ETH/USDT | 0.114 | 0.899 (fails badly) |

## Result: worse than both the parent AND the low-vol-gate rescue

This variant is decisively worse than the original 200d-SMA-exit parent
(Sharpe 0.88 both symbols, MDD 0.16-0.19, both passing MDD) on every
metric: lower Sharpe AND now failing MDD too (a 25% trailing stop from the
peak, applied without the SMA's smoothing, lets more round-trip giveback
happen before triggering, compounding with holding through choppy
post-breakout pullbacks). Crypto is catastrophically bad (MDD 0.78-0.90).

## Decision

**REJECTED.** Neither of the two rescue directions suggested by the parent
near-miss (2026-09-20-054) — low-vol regime gate (2026-09-20-055) or
trailing-stop exit (this entry) — improves on the original 200d-SMA-exit
config. Both documented as negative results. The parent's own 200d-SMA
exit remains the best version of this idea found so far, still short of
acceptance (Sharpe 0.88 vs 1.0 threshold). Future loops should try Exit 3
(100-bar lowest close) or pivot to individual stocks instead of continuing
to iterate on exit-rule variants of the index-ETF version.
