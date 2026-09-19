# Backtest Report: Shooting Star Candlestick RSI-Confirmed Short Reversal

**Strategy file:** `strategies/2026-09-20_shooting_star_rsi_short_reversal.py`
**Date:** 2026-09-20
**Outcome:** REJECTED

## Hypothesis

Per quantifiedstrategies.com's "Shooting Star Candlestick Pattern: (Statistics,
Facts, & Historical Backtest)"
(https://www.quantifiedstrategies.com/shooting-star-candlestick-pattern/,
read via browser_exec fallback this iteration -- web_search DDGS backend hit
repeated TLS/connection-reset errors and timeouts on every query attempted),
the Shooting Star candlestick (small body near the low of the day's range,
long upper shadow ~2x+ the body, little/no lower shadow, occurring after an
upswing) is a bearish reversal pattern that signals price rejection at
higher levels. The source explicitly recommends combining it with an
oscillator ("the overbought signal in an oscillator can be combined with the
shooting star pattern to generate a short-selling signal") and moving
averages as dynamic resistance/targets.

Mechanical rules implemented (mirroring this repo's already-tested Hanging
Man/RSI short methodology, id 2026-09-11-116, using the Shooting Star's
inverse geometry):
1. Uptrend context: close > SMA(trend_window).
2. Shooting Star shape: body <= body_max_pct of range, upper shadow >=
   shadow_ratio * body, lower shadow <= body.
3. RSI(rsi_period) was >= rsi_overbought within rsi_lookback bars and is now
   falling.
4. Entry: short at next close.
5. Exit: close <= SMA(trend_window), or max_hold_days time-stop.

The source's own exact numeric backtest rules (705 trades, Sharpe 1.35,
SPY since 1993) are paywalled/"members only"; this repo's rules are our own
concrete mechanical adaptation of the disclosed pattern-shape definition and
the source's own combination guidance, not a reproduction of the paywalled
ruleset.

## Grid test summary (`grid_summary_shooting_star_rsi_short.json`)

- Grid: `trend_window` in {30,50,75} x `shadow_ratio` in {1.5,2.0,2.5} x
  `rsi_overbought` in {65,70} = 18 param combos x {QQQ, SPY, BTC/USDT,
  ETH/USDT} x 3 vol-regime terciles = 216 cells.
- **pass_fraction: 0.0139 (3/216)** -- decisively weak.
- By asset class: equity 2/108 passed, crypto 1/108 passed.
- By vol regime: low 3/72 passed, mid 0/72, high 0/72 -- only survives in
  low-vol terciles, and only barely.
- Best cell: crypto BTC/USDT, low-vol regime, trend_window=75/
  shadow_ratio=2.0/rsi_overbought=65.0, Sharpe 1.01 (single narrow cell).
- Worst cell: equity QQQ, trend_window=30/shadow_ratio=2.5/
  rsi_overbought=65.0, Sharpe -1.13.

## Full-sample confirmation of grid's best config (trend_window=75,
shadow_ratio=2.0, rsi_overbought=65.0), 2018-01-01 to 2026-09-01:

| Symbol | Sharpe | Max Drawdown | Nonzero-return days |
|---|---|---|---|
| BTC/USDT | 0.0007 | 0.224 | 2264 |
| QQQ | -0.193 | 0.063 | 50 |
| SPY | 0.111 | 0.051 | 70 |

Full-sample Sharpe decisively fails the >=1.0 threshold on all three
symbols tested -- the grid's single "best cell" (BTC low-vol tercile,
Sharpe 1.01) does not hold up over the full sample; it was a narrow-regime
artifact. Equity symbols additionally have very low trade counts
(50-70 nonzero-return days over 8.5 years), consistent with a rare pattern
that doesn't compound to a tradeable edge once RSI overbought + uptrend +
shape confirmation are all required simultaneously.

## Decision

**REJECTED.** Sharpe fails decisively on all three tested symbols at the
grid's own best-performing configuration; pass_fraction 0.014 is one of the
weakest grid results in this repo's history. No further validator runs
(walk-forward, transaction-cost, parameter-sensitivity) were performed given
the decisive full-sample Sharpe failure already disqualifies the strategy
under `suggested_workload=max` scoping (Sharpe + MDD checks are sufficient
to reject cleanly; running the remaining validators would not change the
outcome).
