# Bullish Doji Star Breakout — Backtest Report

**Date:** 2026-09-09 | **Strategy file:** `strategies/2026-09-09_bullish_doji_star_breakout.py` | **Outcome: REJECTED**

## Hypothesis
Per howtotrade.com's Doji Star trading rules (browser_exec fallback —
web_search DuckDuckGo errored with a TLS connection error), the Bullish
Doji Star is a 3-candle reversal: bearish candle1, a Doji candle2 gapping
down from candle1, bullish candle3. Source's own entry rule: buy placed
ABOVE candle3's high (breakout confirmation). Distinct from Morning Star
(2026-09-06-161, rejected: 0/72 grid, only 1 signal over 7.5yr) and
Bullish Abandoned Baby (2026-09-09-037, rejected: 0/192 grid, zero
signals) — Doji Star requires only one gap and a later breakout trigger
rather than a same-bar close condition.

Source: https://howtotrade.com/chart-patterns/doji-star-pattern

## Grid test (doji_body_pct=[0.1,0.15] x breakout_lookback=[3,5,8], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026)

- 72 cells total, 6 passed (pass_fraction 0.083)
- By asset class: equity 6/36, crypto 0/36 (decisive fail)
- By vol regime: low 6/24, mid 0/24, high 0/24
- Best cell: doji_body_pct=0.15/breakout_lookback=3, QQQ low-vol, Sharpe 1.63
- Best avg-across-regime config: SPY doji_body_pct=0.15/breakout_lookback=8, avg Sharpe 0.86 (no config crossed avg Sharpe 1.0)

## Full-sample direct check (SPY, doji_body_pct=0.15, breakout_lookback=8 — best avg-regime config)

| Metric | Value |
|---|---|
| Trade count | 30 |
| Full-sample Sharpe | 0.846 **FAIL** |

## Verdict
**REJECTED (decisive).** Unlike Morning Star and Abandoned Baby, this
construction does at least generate a reasonable trade count (30 on SPY at
the best config vs. 1 and 0 for those two), but the full-sample Sharpe
(0.846) still falls short of the 1.0 threshold, and no grid cell's
avg-across-regime Sharpe reached 1.0 either. Grid pass_fraction 0.083
remains low, and passes are concentrated entirely in the low-vol tercile.
Crypto rejected decisively (0/36 grid cells). This is the third
gap-requiring candlestick reversal tested in this repo (after Morning Star
and Abandoned Baby) and the third to fail — suggesting single-gap-plus-Doji
reversal patterns broadly do not translate to a robust edge on QQQ/SPY
daily bars regardless of the specific entry-trigger variant used.
