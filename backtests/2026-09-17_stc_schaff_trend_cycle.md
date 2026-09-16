# Backtest Report: Schaff Trend Cycle (STC) Oversold/Overbought Crossover

**Strategy file:** `strategies/2026-09-17_stc_schaff_trend_cycle.py`
**Date:** 2026-09-17
**Hypothesis source:** https://howtotrade.com/indicators/schaff-trend-cycle/ (visited this iteration)

## Hypothesis

Doug Schaff's STC = 100*(MACD-%K(MACD))/(%D(MACD)-%K(MACD)), where MACD =
EMA(23) - EMA(50) and %K/%D are a 10-period Stochastic of the MACD series.
Source's own disclosed rule: signal crosses above 75 = overbought/sell,
crosses below 25 = oversold/buy. Implemented long-only: enter on upcross
through 25, exit on downcross through 75, held via hysteresis in between.

## Grid test (Step 6)

`param_grid={short_length:[15,23,30], oversold_level:[20,25,30]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- total_cells=108, passed=11 (10.2%)
- by_asset_class: equity 11/54, crypto 0/54
- by_vol_regime: low 11/36, mid 0/36, high 0/36
- best_cell: QQQ low-vol short_length=30/oversold_level=25, Sharpe=1.80

Already a low pass fraction, concentrated entirely in low-vol regimes on
equity only — a warning sign the grid-best cells don't generalize to a
full-period single config.

## Single-config validators (Step 7)

Per-symbol best-average-Sharpe-across-regimes configs, run full-period:

| Symbol | Config | Sharpe | MDD | TC net Sharpe | Walk-fwd | Param sens |
|---|---|---|---|---|---|---|
| QQQ | (30, 25) | 0.715 ❌ | 0.224 ✅ | 0.602 ✅ | 1.00 ✅ | 0.267 ✅ |
| SPY | (15, 25) | 0.458 ❌ | 0.287 ❌ | 0.272 ❌ | 1.00 ✅ | 0.148 ✅ |
| BTC/USDT | (23, 20) | 0.109 ❌ | 0.640 ❌ | -0.042 ❌ | 1.00 ✅ | 0.501 ❌ |
| ETH/USDT | (15, 30) | 0.049 ❌ | 0.764 ❌ | -0.058 ❌ | 0.50 ❌ | 0.674 ❌ |

None of the four symbols pass all 5 validators. The grid's isolated
low-vol-regime best cells do not survive full-period single-config testing
— high turnover (111-4925 trades depending on symbol) and choppy STC
whipsaws inside the 25-75 "trend formation" band (which the source itself
warns can persist for extended periods) destroy the edge outside the
cherry-picked low-vol slices.

## Decision (Step 8)

**Rejected** across all four symbols. Full disclosed rule and formula from
the source, correctly implemented, but the indicator's whipsaw-prone
behavior at daily frequency does not clear this repo's validator bar for
any symbol tested.
