# Backtest Report: Bullish Deliberation (Stalled) Pattern Continuation

**Strategy file:** `strategies/2026-09-21_deliberation_stalled_bullish_continuation.py`
**Knowledge base id:** 2026-09-21-244

## Hypothesis

Per QuantifiedStrategies.com's "75 Types of Candlestick Patterns" list
(pattern #18), Deliberation/Stalled is traditionally a bearish reversal
signal but the source's own finding is that it tends to be followed by a
rising market more often than not. Operationalized as 3 consecutive
bullish candles in an uptrend (tall, tall, small) with strictly ascending
opens/closes.

## Single-config validation (best grid cell: trend_lookback=10, small_body_mult=0.6, target_atr_mult=1.5)

| Symbol | Trades | Sharpe | MDD | TC-survival |
|---|---|---|---|---|
| QQQ | 0 | undefined | 0.0 | undefined |
| SPY | 0 | undefined | 0.0 | undefined |
| BTC/USDT | 8 | -0.050 (fail) | 0.167 (pass) | -0.068 (fail) |
| ETH/USDT | 14 | 0.538 (fail, near-miss) | 0.171 (pass) | 0.525 (borderline pass) |

## Grid summary (Step 6)

Grid: `trend_lookback in {10,20} x small_body_mult in {0.4,0.5,0.6} x
target_atr_mult in {1.5,2.0,3.0}`, symbols QQQ/SPY/BTC-USDT/ETH-USDT,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01, 216 cells.

- **pass_fraction: 0.083 (18/216)**
- by_asset_class: equity 0/108 (decisive, zero signals), crypto 18/108 (17%)
- by_vol_regime: low 0/72, mid 18/72 (25%), high 0/72
- best_cell: ETH/USDT mid-vol, Sharpe 1.326

## Decision

**Rejected.** Zero signals on either equity symbol; the one promising
crypto mid-vol grid slice (ETH Sharpe 1.326) collapses to a full-sample
near-miss (0.538), well below the 1.0 threshold. Not a robust, generalizable
edge -- consistent with the source's own caveat that this pattern's label
is empirically contested.
