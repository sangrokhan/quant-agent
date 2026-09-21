# Bearish Trend Doji Star (Short) — Backtest Report

**Date:** 2026-09-21
**Strategy file:** `strategies/2026-09-21_bearish_trend_doji_star_short.py`
**Source:** https://www.quantifiedstrategies.com/types-candlestick-patterns/ ("75 Types of Candlestick Patterns")

## Hypothesis

Per QuantifiedStrategies.com's catalog, the "Bearish Trend Doji Star" is a
2-candle continuation pattern (tall bearish candle + gap-down doji) that
signals downtrend continuation when NOT followed by a bullish
confirmation candle. First test of this pattern in this repo (0 prior KB
hits), distinct from Morning/Evening Doji Star (3-candle reversal
requiring an explicit confirmation candle).

## Feasibility check

Produces a small but usable sample: 8 trades (QQQ), 10 (SPY), 4
(BTC/USDT) at initial default parameters; loosening doji_body_ratio to
0.15-0.25 and long_body_mult to 0.3-0.5 raises QQQ to 18-46 trades.

## Grid test (Step 6)

`param_grid={"doji_body_ratio": [0.15,0.2,0.25], "long_body_mult": [0.3,0.5], "max_hold_days": [5,10]}`,
symbols `{"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2018-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.0 (0/144 cells) -- decisive fail**
- By asset class: equity 0/72, crypto 0/72
- By vol regime: low 0/48, mid 0/48, high 0/48
- Best cell: QQQ, doji_body_ratio=0.15/long_body_mult=0.3/max_hold_days=10,
  mid-vol regime, Sharpe 0.879 (still below 1.0 threshold)
- Worst cell: QQQ, doji_body_ratio=0.25/long_body_mult=0.3/max_hold_days=5,
  high-vol regime, Sharpe -2.059

## Decision: **REJECT (decisive)**

No cell across the entire 144-cell grid clears the Sharpe/MDD bar. The
"no bullish confirmation candle" continuation reading of this pattern
does not produce a systematic short-side edge on daily equity/crypto bars
at any tested parameterization. Strategy/report files kept as a record.
