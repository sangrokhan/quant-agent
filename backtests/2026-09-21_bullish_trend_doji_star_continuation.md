# Backtest Report: Bullish Trend Doji Star Continuation

**Strategy file:** `strategies/2026-09-21_bullish_trend_doji_star_continuation.py`
**Knowledge base id:** 2026-09-21-241

## Hypothesis

Per QuantifiedStrategies.com's "75 Types of Candlestick Patterns" list
(https://www.quantifiedstrategies.com/types-candlestick-patterns/, pattern
#23), the Bullish Trend Doji Star is a 2-candle continuation pattern in an
uptrend: bar1 tall bullish, bar2 a doji gapping up from bar1. Distinct from
the already-tested Bullish Doji Star (2026-09-09-056, a 3-candle reversal
pattern with an opposite-context bar1).

## Single-config validation (best grid cell: trend_lookback=10, doji_body_pct=0.10, target_atr_mult=3.0)

| Symbol | Trades | Sharpe | MDD | TC-survival |
|---|---|---|---|---|
| QQQ | 4 | -0.220 (fail) | 0.041 (pass) | -0.272 (fail) |
| SPY | 2 | -0.240 (fail) | 0.007 (pass) | -0.315 (fail) |
| BTC/USDT | 0 | undefined (0 trades) | 0.0 | undefined |
| ETH/USDT | 0 | undefined (0 trades) | 0.0 | undefined |

## Grid summary (Step 6)

Grid: `trend_lookback in {10,20} x doji_body_pct in {0.10,0.15,0.20} x
target_atr_mult in {1.5,2.0,3.0}`, symbols QQQ/SPY/BTC-USDT/ETH-USDT,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01, 216 cells.

- **pass_fraction: 0.028 (6/216)**
- by_asset_class: equity 6/108 (6%), crypto 0/108 (decisive, zero signals)
- by_vol_regime: low 6/72, mid 0/72, high 0/72

## Decision

**Rejected.** The 5-filter conjunction (uptrend + tall-bar1 + doji-bar2 +
up-gap) is simply too rare to produce a statistically meaningful sample:
0 trades on either crypto symbol over 7+ years, and only 2-4 trades on
equity (both with negative full-sample Sharpe). The one passing grid cell
(QQQ low-vol, Sharpe 1.132) does not survive full-sample validation.
