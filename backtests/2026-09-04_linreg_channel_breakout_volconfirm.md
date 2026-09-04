# Backtest Report: Linear Regression Channel Breakout + Volume Confirm (2026-09-04)

**Hypothesis:** A rolling N-day OLS regression channel (fitted line +/- k
residual std bands); close breaking decisively above the upper band with
above-average volume confirmation signals continuation momentum strong
enough to trade; exit on reversion to the regression midline or a time-stop.
Source: Google AI-overview synthesis of PyQuantLab/TradingView/FMZ
explainers
(https://www.google.com/search?q=Linear+Regression+Channel+breakout+trading+strategy+entry+exit+rules).
Distinct from the already-rejected pure regression-slope mean-reversion idea
(id 2026-09-04-058) -- here the trade is a channel-band breakout, not a
slope-sign bet.

**Strategy file:** `strategies/2026-09-04_linreg_channel_breakout_volconfirm.py`

## Step 6 grid summary (2018-01-01 to 2026-09-01)
param_grid: channel_window in [30,40,50], band_k in [1.5,2.0]; symbols:
QQQ/SPY (equity), BTC/USDT/ETH/USDT (crypto); vol_regime_splits=3.

```
total_cells: 48, passed_cells: 3, pass_fraction: 0.0625
by_asset_class: equity 3/36, crypto 0/12
by_vol_regime: low 2/12, mid 1/12, high 0/12
best_cell: SPY, low-vol, channel_window=40/band_k=2.0 -> Sharpe 1.22
worst_cell: SPY, mid-vol, same params -> Sharpe -1.27 (same config flips
  sign entirely between vol regimes)
```

## Verdict: **REJECTED**

Decisive rejection: only 3 of 48 grid cells passed, all equity/low-mixed-vol
slices, 0/12 in crypto and 0/12 in high-vol. The single positive result
(SPY low-vol) is not robust to regime -- the exact same parameter
combination (channel_window=40, band_k=2.0) flips from Sharpe +1.22
(low-vol) to -1.27 (mid-vol) on the same symbol, indicating the "edge" is a
narrow low-vol artifact rather than a genuine breakout effect. Skipped full
Step 7 single-config validator suite per RESEARCH_LOOP.md guidance for
decisive/narrow grid failures.

Not recommending revisit with this exact construction. A future loop could
try adding an explicit vol-regime gate (only trade in low-vol) similar to
the already-accepted Gann HiLo strategy (id 2026-09-04-128) if this
indicator family is revisited.
