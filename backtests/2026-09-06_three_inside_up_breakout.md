# Backtest Report: Three Inside Up Candlestick Breakout + Volume/RSI Filters

**Strategy file:** `strategies/2026-09-06_three_inside_up_breakout.py`
**Date:** 2026-09-06
**Hypothesis id:** 2026-09-06-182

## Hypothesis

Three Inside Up bullish reversal pattern (bearish candle -> inside bar ->
bullish breakout candle closing above the pattern high) per
QuantifiedStrategies.com's Three Inside Up guide, combined with the source's
two disclosed enhancement rules: (1) breakout must clear pattern high + 0.5x
ATR (false-breakout mitigation), and (2) breakout candle volume >= vol_mult x
20-day average volume (conviction confirmation). Also tested the source's
suggested RSI<40 oversold gate as an additional filter. Fixed 5-bar time
exit per source's own backtest convention. First 3-bar candlestick pattern
strategy in this repo.

**Source:** `https://www.quantifiedstrategies.com/three-inside-up-candlestick-pattern/`
(reached via Google search fallback after `web_search` returned no results
for the initial breakout-pattern query -- see visited_pages.jsonl).

## Step 6 grid summary

Param grid: `vol_mult in {1.0, 1.2, 1.5}` x `rsi_oversold in {40.0, 100.0}`
(100.0 effectively disables the RSI gate), fixed `atr_window=14,
breakout_atr_mult=0.5, vol_window=20, rsi_window=14, hold_bars=5`; symbols
`{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, `vol_regime_splits=3`,
2018-01-01 to 2026-09-01.

- **pass_fraction: 0.069** (5/72 cells) -- very weak
- **by_asset_class:** equity 5/36; **crypto 0/36** (decisive fail)
- **by_vol_regime:** low 2/24, mid 3/24, **high 0/24**
- **best_cell:** `vol_mult=1.0, rsi_oversold=100.0` (RSI gate disabled),
  equity/QQQ/low-vol, Sharpe 1.20 -- but this is a single narrow low-vol
  tercile slice, likely driven by very few trades given the pattern's rarity
- **worst_cell:** same params, QQQ/high-vol, Sharpe -1.18

## Step 7 single-config validators (best config: QQQ, `vol_mult=1.0,
rsi_oversold=100.0`, full sample 2018-2026-09)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | ❌ | -0.051 | ≥ 1.0 |
| max_drawdown | ✅ | 0.110 | ≤ 0.25 |
| transaction_cost_survival (10bps/trade, **9 trades total**) | ❌ | net Sharpe -0.108 | ≥ 0.5 |
| walk_forward (manual 4-equal-slice fallback) | ❌ | 2/4 splits positive Sharpe | ≥ 0.75 pass fraction |
| parameter_sensitivity (3-cell vol_mult sweep, QQQ) | ❌ | relative std 0.894 | ≤ 0.5 |

## Decision: **REJECT**

Decisive rejection, not a near-miss. Full-sample Sharpe is negative (-0.051)
and only 9 total trades occurred over the full ~8.7-year QQQ sample --
the pattern (3-bar bearish/inside/bullish-breakout-with-volume-and-ATR-
distance) is simply too rare to generate a statistically meaningful edge on
daily bars. The grid's "best cell" (Sharpe 1.20) is a low-vol-tercile
artifact built on an even smaller trade count within that regime, not a
robust finding -- confirmed by walk-forward failing (only 2/4 splits
positive) and severe parameter sensitivity (relative std 0.894, nearly 2x
the 0.5 threshold) across just 3 vol_mult values. Decisive failure on crypto
(0/36) as well. Unlike prior near-miss entries in this log, this one is not
flagged for revisiting with a tweak -- the core problem (pattern rarity ->
too few trades for a stable edge) is not fixable by adjusting the
volume/RSI/ATR filter thresholds tested here.
