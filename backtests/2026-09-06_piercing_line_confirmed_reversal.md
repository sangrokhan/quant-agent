# Piercing Line Confirmed Reversal, Downtrend-Gated, Long-Only

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_piercing_line_confirmed_reversal.py`
**Knowledge base id:** 2026-09-06-148

## Hypothesis

Per TradingView's "Candlestick Patterns" script description
(https://www.tradingview.com/scripts/hammer/): "Piercing Line requires the
close to cross above the midpoint of the prior bearish candle." Combined
with Capital.com's confirmation-candle rule (Google SERP): "Wait for the
candle after the piercing line to close. If it is green and closes higher,
this is a strong confirmation. You can enter the trade after this candle."
First 2-candle Piercing Line strategy in this repo (distinct from Bullish
Engulfing's full-body-engulfment requirement and Hammer's single-candle
wick criterion).

## Grid test (Step 6)

108 cells: `trend_window` in [20,50,100] x `max_hold_days` in [10,15,20] x
{QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol terciles.

- **Overall pass_fraction:** 0.009 (1/108) -- essentially a decisive
  rejection across the entire grid
- **by_asset_class:** equity 1/54; crypto 0/54 (decisive reject)
- **by_vol_regime:** low 0/36; mid 1/36; high 0/36
- **Best cell:** trend_window=50/max_hold_days=15, QQQ, mid-vol, Sharpe=1.19
  (single passing cell out of 108)

## Single-config validators (best-cell config, QQQ full sample)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.067 | 1.0 | **FAIL (decisive)** |
| Max drawdown | 0.064 | 0.25 | pass |
| Transaction cost survival | 0.054 | 0.5 | **FAIL (decisive)** |

**Number of trades: only 2 over the entire 7.7-year sample.**

## Decision: REJECTED (decisive)

The pattern's combined preconditions (downtrend gate + gap-down open +
midpoint cross without full engulfment + green confirmation candle closing
higher) are far too restrictive: only 2 trades occurred on QQQ over 7.7
years, and the grid's single "passing" cell (1/108) is not statistically
meaningful. This is the most decisive rejection among today's iterations --
the multi-condition AND-gate for a genuinely rare 3-bar-effective pattern
leaves essentially no signal to trade. A future loop could revisit by
dropping the confirmation-candle requirement (trading directly on the
piercing bar's own close) to raise trade frequency, at the cost of the
extra confirmation's noise-filtering value.
