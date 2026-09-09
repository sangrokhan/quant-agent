# ATR Channel Breakout — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_atr_channel_breakout.py`
**Outcome:** REJECTED (near-miss on both QQQ and SPY)

## Hypothesis

Per Google AI-overview synthesis (TradingCode/TradingBlox/StockGro
sources, query "ATR channel breakout strategy exact entry exit rules"): a
dynamic volatility channel from a long baseline SMA (350-day, per
TradingBlox's canonical ATR Channel Breakout System) plus an ATR-derived
band (Upper = baseline + multiplier*ATR(20), multiplier range 3-7)
triggers a long entry on a close breaking above the upper channel; exit
when price crosses back below the baseline (source's primary rule).

First TradingBlox-style ATR-Channel-breakout (SMA baseline + ATR band)
strategy in this repo — distinct from Donchian (rolling high/low, no ATR
band) and Keltner Channel (EMA baseline, tighter multiplier, mostly
mean-reversion/squeeze framing here).

## Single-config validation (best grid cell: baseline_window=350,
atr_mult=7.0, max_hold_days=60)

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 0.730 (FAIL, thr 1.0) | 26.0% (FAIL, thr 25%, borderline) | 0.707 (PASS) | 1.0/1.0 (PASS) | 0.401 (PASS) |
| SPY | 0.675 (FAIL, thr 1.0) | 20.8% (PASS) | 0.644 (PASS) | 0.75/1.0 (PASS, borderline) | 0.247 (PASS) |

Both symbols fail the Sharpe threshold (near-miss, 0.68-0.73 vs 1.0
required). QQQ additionally just breaches the max-drawdown cap (26.0% vs
25% limit).

## Grid summary (baseline_window=[100,200,350] x atr_mult=[3.0,5.0,7.0] x
max_hold_days=[60], equity=[QQQ,SPY] x crypto=[BTC/USDT,ETH/USDT],
vol_regime_splits=3, 2018-01-01 to 2026-09-01)

- total_cells: 108, passed_cells: 23, pass_fraction: 0.213
- by_asset_class: equity 23/54 (0.426), crypto 0/54 (0.0 — decisive fail)
- by_vol_regime: low 18/36 (0.500), mid 5/36 (0.139), high 0/36 (0.0)
- best_cell: baseline_window=350/atr_mult=7.0/max_hold_days=60, SPY
  low-vol regime, Sharpe 2.61
- worst_cell: baseline_window=100/atr_mult=5.0/max_hold_days=60, QQQ
  high-vol regime, Sharpe -1.04

The grid's regime-sliced best cell (Sharpe 2.61, SPY low-vol) is again
overly optimistic vs. the full-sample result (SPY full-sample Sharpe only
0.675) — the same pattern seen in this run's earlier Fibonacci Time Zone
rejection: edge concentrated in the low-vol tercile doesn't survive
full-period validation, since low-vol periods only constitute a third of
the sample. Only 22-23 trades over 8.7 years (roughly 1 every 4-5 months)
— a very low-frequency signal that's statistically thin.

## Verdict: REJECTED

Both QQQ and SPY fail full-sample Sharpe (near-miss, 0.68-0.73 vs 1.0
threshold); crypto rejected decisively (0/54 grid cells). Unlike the
accepted PVT strategy this same run, the edge here does not clear the
full-sample bar even at the grid's best-performing config — this is a
genuine near-miss, not a clean pass. Worth flagging for a future loop:
the 350-day baseline is very slow (over a year of lookback), producing
only ~2-3 trades/year; a shorter baseline_window (e.g. 100 with a wider
ATR multiplier, or combining with the already-accepted PVT/Chandelier
trend filters) might improve trade frequency and Sharpe without breaking
the volatility-channel concept.
