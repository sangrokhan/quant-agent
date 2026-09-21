# Backtest Report: In Neck Line Bearish Continuation Short

**Strategy file:** `strategies/2026-09-21_in_neck_line_bearish_continuation_short.py`
**Knowledge base id:** 2026-09-21-240

## Hypothesis

Per QuantifiedStrategies.com's "75 Types of Candlestick Patterns" list
(https://www.quantifiedstrategies.com/types-candlestick-patterns/, pattern
#38, read via browser_exec fallback), the In Neck Line is a 2-candle
bearish continuation pattern: bar1 long/bearish; bar2 opens with a
down-gap but rallies to close at-or-slightly-above bar1's close (source's
own reading: bulls failed to reach even the midpoint of bar1's body,
confirming bears retain control).

## Single-config validation (best grid cell: trend_lookback=10, long_body_mult=1.0, target_atr_mult=3.0)

| Symbol | Trades | Sharpe | MDD | TC-survival (net Sharpe) |
|---|---|---|---|---|
| QQQ | 20 | -0.357 (fail) | 0.143 (pass) | -0.407 (fail) |
| SPY | 12 | -0.379 (fail) | 0.057 (pass) | -0.469 (fail) |
| BTC/USDT | 6 | 0.367 (fail) | 0.112 (pass) | 0.357 (fail) |
| ETH/USDT | 6 | -0.374 (fail) | 0.123 (pass) | -0.394 (fail) |

Walk-forward: not run (pre-existing `vbt.utils.splitting` AttributeError bug).

## Grid summary (Step 6)

Grid: `trend_lookback in {10,20} x long_body_mult in {1.0,1.2,1.5} x
target_atr_mult in {1.5,2.0,3.0}`, symbols QQQ/SPY/BTC-USDT/ETH-USDT,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01, 216 cells.

- **pass_fraction: 0.139 (30/216)**
- by_asset_class: equity 30/108 (28%), crypto 0/108 (decisive fail)
- by_vol_regime: low 18/72, mid 12/72, high 0/72 (decisive fail in high-vol)
- best_cell: SPY, mid-vol regime, Sharpe 1.663 -- but full-sample SPY
  Sharpe (unrestricted to that tercile) is -0.379, confirming the grid
  pass was a narrow-regime artifact.

## Decision

**Rejected.** Decisively fails Sharpe and transaction-cost-survival on all
4 symbols full-sample. Very low trade counts (6-20 over 7+ years) reflect
a genuinely rare 5-filter conjunction (downtrend + long-bar1 + down-gap +
narrow close-tolerance band), and the one promising grid cell does not
generalize outside its narrow vol-regime slice.
