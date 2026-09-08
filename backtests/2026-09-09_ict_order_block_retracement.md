# Backtest Report: ICT Order Block Bullish Retracement

**Strategy file:** `strategies/2026-09-09_ict_order_block_retracement.py`
**Date:** 2026-09-09
**Source:** https://journali.io/strategies/ict-order-blocks

## Hypothesis

Per Journali.io's ICT Order Blocks strategy page, an institutional "order
block" (the last opposing-color candle immediately before a strong impulsive
displacement move) marks a zone price frequently retraces into before
continuing in the displacement direction. Source's own backtest: raw OB
entries 56% WR, filtered (displacement + HTF-trend alignment + fresh OB)
61% WR, avg winner 2.1R, on ES 15-min. Operationalized on daily bars: a
bullish displacement bar (body > displacement_mult x ATR(14), close above
SMA(50)) whose immediately-preceding bearish bar is the order block; long
entry on retracement back into the OB's [low, high] range within
lookback_window bars; exit at displacement bar's high (target), OB low
(stop), or max_hold_days time-stop.

## Grid test summary (Step 6)

Grid: `displacement_mult` in [1.0, 1.5, 2.0], `lookback_window` in
[5, 10, 15] x symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles
= 108 cells, 2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.065** (7/108 cells passed)
- **By asset class:** equity 7/54 passed, **crypto 0/54 passed** (decisive crypto failure)
- **By vol regime:** low 7/36, **mid 0/36, high 0/36** (only works in calm markets)
- **Best cell:** SPY, displacement_mult=1.0, lookback_window=10, low-vol regime, Sharpe=1.774
- **Worst cell:** SPY, displacement_mult=1.0, lookback_window=5, high-vol regime, Sharpe=-0.572

## Single-config validation (Step 7): displacement_mult=1.0, lookback_window=10, full sample 2018-2026

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.075 (FAIL) | 0.304 (FAIL) | >= 1.0 |
| Max drawdown | 0.096 (PASS) | 0.082 (PASS) | <= 0.25 |
| Net Sharpe after costs (10bps/trade) | -0.080 (FAIL) | 0.064 (FAIL) | >= 0.5 |
| Walk-forward pass fraction (4 slices) | 0.25 (FAIL) | 1.0 (PASS) | >= 0.75 |
| Parameter sensitivity relative std | NaN (FAIL, near-zero mean across grid) | NaN (FAIL) | <= 0.5 |
| Num trades | 46 | 42 | -- |

## Decision

**Reject, decisively.** Full-sample Sharpe collapses far below threshold for
both symbols (0.075 QQQ, 0.304 SPY) even though the grid's best single
low-vol-tercile cell looked promising (Sharpe 1.77). The strategy's edge
is concentrated entirely in low-volatility regimes (0/36 mid-vol, 0/36
high-vol cells passed) and evaporates once transaction costs are applied
(net Sharpe negative for QQQ). Parameter sensitivity is undefined/failing
because the grid's mean Sharpe across displacement_mult/lookback_window
combinations is near zero — the daily-bar approximation of a 15-minute-chart
ICT concept (displacement + order block + retracement) does not translate
into a robust edge at this timeframe. Consistent with this repo's prior ICT
Fair Value Gap rejections (2026-09-04-095, 2026-09-08-018): ICT/smart-money
concepts implemented literally on daily bars have not produced a passing
strategy in this repo across three attempts now.
