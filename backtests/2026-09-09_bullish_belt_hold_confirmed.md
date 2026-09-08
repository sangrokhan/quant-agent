# Bullish Belt Hold (Confirmed Breakout Entry) — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_bullish_belt_hold_confirmed.py`
**Source:** https://www.investopedia.com/terms/b/bullishbelthold.asp

## Hypothesis

A bullish belt hold is a single-day candle: gap-down open at/below the
prior low, followed by a full-range rally to close near the high (long
white body, negligible upper/lower shadows) during a downtrend. Per
Investopedia's own explicit rule, an entry should only be taken when price
subsequently trades above the belt-hold candle's high (confirmation
breakout, not the pattern bar itself), with a stop at the pattern candle's
own midpoint. Gated here by a below-trend-SMA downtrend context per the
source's own "reliability enhanced near a support level" caveat.

## Grid test (Step 6)

`param_grid={"trend_window": [30,50,100], "max_hold_days": [10,15]}`,
symbols QQQ/SPY/BTC-USDT/ETH-USDT, `vol_regime_splits=3`, 2019-01-01 to
2026-09-01.

- **72 total cells, 0 passed (pass_fraction 0.0)** -- decisive rejection
  across every asset class and volatility regime.

## Single-config validators (trend_window=50, max_hold_days=10)

| Symbol | Trades | Sharpe (full) | MDD | TC-survival (net Sharpe) |
|---|---|---|---|---|
| QQQ | 1 | -0.556 **FAIL** | 0.064 PASS | -0.565 **FAIL** |
| SPY | 1 | -0.466 **FAIL** | 0.042 PASS | -0.477 **FAIL** |

## Decision: REJECTED

The pattern's simultaneous requirements (gap-down open, near-zero shadows
both directions, downtrend context, THEN a confirmed breakout above the
pattern high within a 5-bar window) are so restrictive that only 1 trade
fires over 7.5 years on both QQQ and SPY, and that single trade lost money
on both. 0/72 grid cells pass, confirming this isn't a small-sample
statistical fluke but a genuinely negative or non-existent edge in this
construction. Investopedia's own source material explicitly flags the
pattern as "not considered very reliable" in isolation, and this backtest
confirms that caveat empirically on daily-bar QQQ/SPY. Crypto also failed
all cells.

No further single-candle belt-hold variant recommended without a
fundamentally different confirmation/filter combination; this closes out
another candlestick-pattern angle for this repo's already-extensive
candlestick-family coverage (30+ prior entries).
