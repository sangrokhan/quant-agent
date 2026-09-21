# Backtest Report: Three Stars In The South Bullish Reversal

**Strategy file:** `strategies/2026-09-21_three_stars_in_the_south_bullish_reversal.py`
**Knowledge base id:** 2026-09-21-246

## Hypothesis

Per QuantifiedStrategies.com
(https://www.quantifiedstrategies.com/three-stars-in-the-south-candlestick-pattern/),
corroborated by Bulkowski's claimed #1 reversal-performance ranking (via
search snippet from thepatternsite.com), Three Stars In The South is a
rare 3-candle bullish reversal: 3 consecutive bearish candles with
progressively shrinking, nested ranges (each candle's range fully
contained within the preceding candle's range), bar3 a small black
Marubozu.

## Signal counts (default params)

| Symbol | Trades |
|---|---|
| QQQ | 0 |
| SPY | 0 |
| BTC/USDT | 36 |
| ETH/USDT | 32 |

Crypto has an adequate sample size, unlike several other rare-pattern
rejections this cron trigger.

## Grid summary (Step 6)

Grid: `trend_lookback in {10,20} x marubozu_wick_pct in {0.005,0.01,0.02}
x target_atr_mult in {1.5,2.0,3.0}`, symbols QQQ/SPY/BTC-USDT/ETH-USDT,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01, 216 cells.

- **pass_fraction: 0.0 (0/216)** -- decisive fail
- by_asset_class: equity 0/108 (no signals), crypto 0/108
- by_vol_regime: low 0/72, mid 0/72, high 0/72
- best_cell: ETH/USDT, low-vol regime, Sharpe only 0.627

## Decision

**Rejected.** Decisive 0% grid pass fraction. Despite a claimed strong
real-world track record and an adequate crypto sample, the mechanically-
operationalized nested-inside-bar + shrinking-Marubozu construction did
not translate to a Sharpe edge in this repo's daily-bar backtest. Full
validators.py run skipped given the non-borderline result.
