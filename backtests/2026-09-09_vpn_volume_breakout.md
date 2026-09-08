# VPN (Volume Positive Negative) Breakout — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_vpn_volume_breakout.py`
**Outcome:** REJECTED

## Hypothesis
Per Financial Hacker's replication of Markos Katsanos' VPN indicator
(Stocks & Commodities April 2021,
https://financial-hacker.com/petra-on-programming-detecting-volume-breakouts/),
each day is classified up/down based on typical_price vs an ATR-scaled
threshold; VPN = EMA(100*(Vp-Vn)/Vtotal, 3) over a rolling period, a
volume-breakout-strength oscillator distinct from every other volume
indicator already tested in this repo. Simplified single-asset long-only
adaptation of the source's own rule: entry on VPN crossing above threshold
with rising 50d volume, RSI(5)<90, and price>SMA(30); exit on VPN crossing
below its own 30d SMA during a momentum-stall pullback, or a max_hold_days
time-stop.

## Grid test summary (period x [20,30,40], threshold x [5.0,10.0], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2018-01-01 to 2026-09-01)

- total_cells: 72, passed_cells: 9, **pass_fraction: 0.125**
- by_asset_class: equity 9/36, crypto 0/36
- by_vol_regime: low 5/24, mid 4/24, high 0/24
- best_cell: QQQ, period=20, threshold=5.0, low-vol, Sharpe 1.616

## Full-sample checks at plausible best configs

| Symbol | period | threshold | Full-sample Sharpe | Trades |
|---|---|---|---|---|
| QQQ | 20 | 5.0 | 0.344 | 18 |
| QQQ | 30 | 5.0 | 0.579 | 15 |
| QQQ | 40 | 5.0 | 0.695 | 12 |
| SPY | 20 | 5.0 | 0.503 | 16 |
| SPY | 30 | 5.0 | 0.792 | 15 |
| SPY | 40 | 5.0 | 0.460 | 11 |

Best full-sample Sharpe (SPY, period=30/threshold=5.0) is 0.792, a clear
miss vs the 1.0 threshold. Very low trade counts (11-18 trades over 8.7
years) limit statistical confidence regardless.

## Decision: REJECTED

Grid pass_fraction 0.125 (low), full-sample Sharpe fails decisively on
both equity symbols across every tested config (best 0.792); crypto
decisively rejected 0/36. Trade counts are also quite low (11-18 over the
full period), making even the best result statistically fragile. Not a
strong near-miss worth immediate revisiting, though the underlying VPN
construction itself (distinct from all prior volume indicators in this
repo) could be worth testing with a looser/simpler entry rule (dropping
some of the source's multi-condition filter stack) in a future iteration.
