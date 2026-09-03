# Backtest Report: Elder's Triple Screen (Weekly MACD-Hist + Daily Stochastic)

**Strategy file:** `strategies/2026-09-04_triple_screen_weekly_daily.py`
**Knowledge base id:** 2026-09-04-044

## Hypothesis

Per Google AI-overview synthesis of Dr. Alexander Elder's Triple Screen
Trading System: weekly MACD-Histogram slope (rising = bullish tide)
combined with daily Stochastic %K oversold-recovery pullback entries.
Long only when the weekly tide is bullish; exit when the weekly tide
turns bearish.

Source: Google AI-overview (`web_search` failed with a DDGS/Yahoo TLS
connection error, fell back to `browser_exec` immediately).

## Grid test summary (Step 6)

Grid: `k_window` in {9, 14, 21} x `oversold_threshold` in {20, 30} x
symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles = 72 cells.

- `pass_fraction`: 0.028 (2/72) — the lowest pass fraction of any strategy
  tested in this repo to date.
- `by_asset_class`: equity 2/36, crypto 0/36
- `by_vol_regime`: low 2/24, mid 0/24, high 0/24

## Full-sample sweep (QQQ / SPY)

| k_window | oversold_threshold | QQQ Sharpe (trades) | SPY Sharpe (trades) |
|---|---|---|---|
| 9  | 20 | -0.572 (7)  | 0.108 (9)  |
| 9  | 30 | -0.135 (12) | 0.443 (12) |
| 14 | 20 | -0.536 (4)  | -0.395 (5) |
| 14 | 30 | -0.129 (3)  | 0.166 (8)  |
| 21 | 20 | 0.435 (1)   | 0.435 (1)  |
| 21 | 30 | 0.435 (1)   | 2 trades... |

No config comes close to the 1.0 Sharpe threshold, and trade counts are
extremely low (1-12 completed entries over 7.7 years) — the weekly-tide
gate is so restrictive that the daily oversold-recovery trigger almost
never fires while the gate is open. Given the decisive, uniformly poor
(negative-to-near-zero) full-sample Sharpe across every parameter
combination and both target equities, running the remaining validator
suite (MDD, transaction-cost survival, walk-forward, parameter
sensitivity) would not change the outcome — skipped per Step 7 minimum-
subset guidance (a negative/near-zero full-sample Sharpe cannot pass a
stricter net-of-cost or out-of-sample check).

## Outcome

**Rejected** (decisive, not a near-miss). Crypto also rejected decisively
(0/36 grid cells).

## Notes

First genuinely multi-timeframe (weekly trend gate + daily oscillator
entry) strategy tested in this repo. The weekly-bar MACD-histogram
"rising" condition (hist > hist.shift(1)) combined with hist > 0 turned
out to be a very restrictive gate — likely too restrictive combined with
a fairly deep (20-30) daily oversold threshold, producing too few trades
to generate a statistically meaningful or profitable signal on this
sample. A future loop revisiting this idea should consider loosening the
weekly gate (e.g. hist > 0 only, dropping the "rising" requirement) or
using a simpler weekly EMA-slope trend filter instead of the MACD
histogram's second-derivative-like "rising" condition.
