# Backtest Report: Bill Williams Market Facilitation Index (BW-MFI) Squat Breakout

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_bwmfi_squat_breakout.py`
**Source:** https://forex-indicators.net/bill-williams/mfi

## Hypothesis

Per the source, MFI=(High-Low)/Volume classified into 4 bar types; the
"Squat" (Pink) bar (MFI down/flat, Volume up) is called "the strongest
potential money maker of the 4 setups" -- price stalls while volume rises,
setting up a breakout. Operationalized here: after a confirmed squat bar,
enter long on a close breaking above the squat bar's high within
`breakout_expiry_bars`, gated by close > SMA(trend_window). First
Market-Facilitation-Index strategy in this repo.

## Grid Test Summary (param_grid: breakout_expiry_bars=[3,5] x
trend_sma_window=[50,100]; symbols QQQ/SPY/BTC-USDT/ETH-USDT;
vol_regime_splits=3; 2019-01-01 to 2026-09-01)

- total_cells: 48, passed: 12, **pass_fraction: 0.25**
- by_asset_class: equity 12/24, crypto **0/24**
- by_vol_regime: low 8/16, mid 3/16, high 1/16 -- edge concentrated low-vol
- best_cell: breakout_expiry_bars=3, trend_sma_window=50, QQQ, low-vol, Sharpe 2.10

## Single-Config Validators (breakout_expiry_bars=3, trend_sma_window=50,
full period 2019-2026)

| Symbol | Sharpe | MDD | TC-survival (10bps) | Walk-forward |
|---|---|---|---|---|
| QQQ | 0.976 FAIL (78 trades) | 0.148 PASS | net Sharpe 0.845 PASS | 4/4 PASS |
| SPY | 0.445 FAIL (86 trades) | 0.185 PASS | net Sharpe 0.288 FAIL | 3/4 PASS |

Swept all 4 param combos (breakout_expiry_bars x trend_sma_window) on
full-period Sharpe: QQQ ranged 0.61-0.98, SPY ranged 0.37-0.59 -- no config
reaches the 1.0 Sharpe threshold on either symbol; the grid's apparent
0.25 pass_fraction is entirely a low-vol-tercile artifact that doesn't
survive to the full sample.

## Decision: **REJECT**

QQQ near-misses at the best config (0.976 vs 1.0) but no parameter
combination clears the threshold on full-period data; SPY fails decisively.
Crypto rejected 0/24. The squat-bar breakout construction, as
parameterized here, does not produce a robust standalone edge on daily
equity/crypto bars.
