# Backtest Report: Cutler's RSI Oversold-Recovery Mean Reversion

**Strategy file:** `strategies/2026-09-18_cutlers_rsi_oversold_recovery.py`
**Hypothesis id:** 2026-09-18-008
**Source:** https://www.quantifiedstrategies.com/cutlers-rsi-trading-strategy/ (Cutler's RSI, SMA-based variant of Wilder's RSI)

## Hypothesis

Cutler's RSI uses a simple moving average of gains/losses instead of
Wilder's smoothed recursive average, avoiding "Data Length Dependency" per
Cutler's own finding. Tested here as an oversold-recovery (cross above 30
from below) mean-reversion entry, gated by SMA(200) uptrend filter, exit on
overbought (70) or a max_hold_days time-stop.

## Grid Test Summary (Step 6)

Grid: `rsi_period` in {10,14,21}, `oversold_level` in {25,30,35},
`max_hold_days` in {10,20}, symbols equity {QQQ, SPY} + crypto {BTC/USDT,
ETH/USDT}, vol_regime_splits=3.

- total_cells: 216, passed_cells: 16, **pass_fraction: 0.074** (weak)
- by_asset_class: equity 14/108, crypto 2/108
- by_vol_regime: low 4/72, mid 8/72, high 4/72 (no clear regime concentration)
- best_cell: SPY high-vol, rsi_period=10/oversold_level=35/max_hold_days=20, Sharpe 2.55 (isolated slice)

## Single-Config Validation (Step 7)

Best full-sample QQQ config found (`rsi_period=21, oversold_level=30,
max_hold_days=10`) technically clears Sharpe(1.39)/MDD(0.026) thresholds
but generates only **10 trades over 8.5 years** -- far too sparse a sample
to draw a reliable conclusion (consistent with this repo's prior rejections
of similarly sparse-signal patterns, e.g. NR4/NR7). The same config on SPY
decisively fails (Sharpe -0.53, MDD 0.291).

## Decision (Step 8)

**Rejected.** Weak grid pass_fraction (0.074, one of the lower results this
cron trigger), and the only full-sample-passing QQQ config relies on a
signal too sparse (10 trades) to trust; SPY fails decisively at the same
config. Cutler's RSI's own source article states plainly "our backtests
reveal that Cutler's RSI is no improvement compared to Wilder's RSI" --
this iteration's own results corroborate that finding.
