# Backtest Report: Bullish Meeting Lines Reversal

**Strategy file:** `strategies/2026-09-21_bullish_meeting_lines_reversal.py`
**Knowledge base id:** 2026-09-21-242

## Hypothesis

Per QuantifiedStrategies.com's "75 Types of Candlestick Patterns" list
(https://www.quantifiedstrategies.com/types-candlestick-patterns/, pattern
#54), Bullish Meeting Lines is a 2-candle bullish reversal in a downtrend:
bar1 bearish, bar2 opens with a down-gap but is a full bullish candle that
closes near bar1's close.

## Single-config validation (best grid cell: trend_lookback=10, match_tolerance=0.005, target_atr_mult=1.5)

| Symbol | Trades | Sharpe | MDD | TC-survival |
|---|---|---|---|---|
| QQQ | 106 | 0.774 (fail) | 0.063 (pass) | 0.337 (fail) |
| SPY | 80 | 0.451 (fail) | 0.031 (pass) | 0.074 (fail) |
| BTC/USDT | 40 | 0.229 (fail) | 0.127 (pass) | 0.120 (fail) |
| ETH/USDT | 28 | -0.060 (fail) | 0.214 (pass) | -0.107 (fail) |

## Grid summary (Step 6)

Grid: `trend_lookback in {10,20} x match_tolerance in {0.003,0.005,0.01} x
target_atr_mult in {1.5,2.0,3.0}`, symbols QQQ/SPY/BTC-USDT/ETH-USDT,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01, 216 cells.

- **pass_fraction: 0.236 (51/216)**
- by_asset_class: equity 51/108 (47%), crypto 0/108 (decisive fail)
- by_vol_regime: low 18/72 (25%), mid 0/72 (0%), high 33/72 (46%) --
  bimodal (works low AND high vol, fails mid-vol)
- best_cell: QQQ, high-vol regime, Sharpe 1.870

## Decision

**Rejected.** Reasonable trade counts (28-106) rule out small-sample noise.
Fails Sharpe and transaction-cost-survival full-sample on all 4 symbols
despite MDD passing comfortably everywhere. The promising bimodal
vol-regime grid slice does not survive blending into the full sample.
