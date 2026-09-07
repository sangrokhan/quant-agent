# Backtest Report: EMV Bullish Divergence vs. Swing Lows

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_emv_bullish_divergence_swinglow.py`
**Source:** https://arrowalgo.com/ease-of-movement-emv-complete-guide-algorithmic-trading/

## Hypothesis

Per the source's divergence strategy: "price making new lows while EMV makes
higher lows... signals exhaustion in the downtrend. Look for entry
opportunities on the long side." Distinct from the already-accepted plain
EMV zero-cross+SMA-trend strategy (2026-09-04-115) since this trades a
divergence pattern rather than an absolute zero-line level.

## Grid Test Summary (param_grid: pivot_window=[5,8] x rsi_gate=[50,60] x
max_hold_days=[15,25]; symbols QQQ/SPY/BTC-USDT/ETH-USDT; vol_regime_splits=3;
2019-01-01 to 2026-09-01)

- total_cells: 96, passed: 2, **pass_fraction: 0.021** (weak/decisive)
- by_asset_class: equity 2/48, crypto 0/48
- by_vol_regime: low 2/32, mid 0/32, high 0/32 -- narrow low-vol-only artifact
- best_cell: pivot_window=5, rsi_gate=60, max_hold_days=25, SPY, low-vol, Sharpe 1.30

## Single-Config Full-Period Check (best grid config, 2019-2026)

| Symbol | Trades | Full-period Sharpe |
|---|---|---|
| QQQ | 11 | 0.099 (decisive FAIL) |
| SPY | 7 | 0.523 (decisive FAIL) |

Sparse signal (7-11 trades over 7.7yr) and the grid's one passing low-vol
tercile does not survive to the full sample -- a narrow-slice artifact, not
a real edge. No further validators run given the decisive full-sample fail.

## Decision: **REJECT**

Weak grid pass_fraction (0.021) concentrated entirely in one low-vol
tercile; full-period Sharpe fails decisively on both QQQ and SPY; crypto
0/48. The EMV-divergence construction does not produce a usable edge on
daily equity/crypto bars with this swing-detection parameterization.
