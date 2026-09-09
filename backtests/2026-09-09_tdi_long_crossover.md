# TDI (Traders Dynamic Index) Long Crossover — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_tdi_long_crossover.py`
**Outcome:** REJECTED (decisive, weak grid pass_fraction)

## Hypothesis

Per Google AI-overview synthesis (TrendSpider/XBTFX/FX Replay sources,
query "Trader's Dynamic Index TDI indicator trading strategy exact entry
exit rules"): TDI combines RSI, Bollinger Bands, and moving averages into
one oscillator with 4 components -- Green Line (RSI), Red Line (smoothed
MA of Green), Yellow Line (longer-term MA of RSI, trend bias), Blue Lines
(Bollinger Bands on RSI). Source's exact long rule: trend filter (Yellow
Line flat-to-rising or above 50) + oversold condition (Green Line below
32 OR outside lower blue band) + crossover trigger (Green crosses above
Red) => long entry. Exit: Green crosses back below Red, OR reaching the
50 midline while riding a bigger trend wave, OR stop below recent swing
low.

First TDI strategy in this repo (0 prior hits) — distinct from plain
RSI-family crossovers (Connors RSI, RSI(2)) since TDI adds a
volatility-band-on-RSI oversold trigger AND a separate longer-MA trend
bias filter, both absent from existing RSI-family strategies here.

## Grid summary (rsi_window=[8,13] x oversold_level=[32,40] x
max_hold_days=[15,25], equity=[QQQ,SPY] x crypto=[BTC/USDT,ETH/USDT],
vol_regime_splits=3, 2018-01-01 to 2026-09-01)

- total_cells: 96, passed_cells: 4, pass_fraction: **0.042**
- by_asset_class: equity 4/48 (0.083), crypto 0/48 (0.0 — decisive fail)
- by_vol_regime: low 4/32 (0.125), mid 0/32 (0.0), high 0/32 (0.0)
- best_cell: rsi_window=13/oversold_level=40/max_hold_days=15, QQQ
  low-vol regime, Sharpe 1.68
- worst_cell: rsi_window=13/oversold_level=40/max_hold_days=15, QQQ
  high-vol regime, Sharpe -1.19 (note: same param combo as best_cell —
  the identical config swings from a strong pass in low-vol to a strong
  fail in high-vol, underscoring the edge's fragility)

## Verdict: REJECTED (decisive)

Grid pass_fraction of 0.042 is comparable to the weakest results tested
this run (Falling Wedge at 0.046). The multi-condition AND-gate (trend
filter + oversold + crossover, all simultaneously required) is likely
too restrictive on daily bars, producing a sparse and fragile signal
that only works in a narrow low-vol slice of one symbol. No single-config
validator suite run given the grid's decisive weakness (per Step 7
guidance to skip full validation on a clearly-failing grid).

**Note for future loops:** the 32/68 oversold/overbought thresholds and
signal_window=2 come from the source's own default (typically applied to
lower/intraday timeframes in forex); this construction may simply be a
poor fit for daily-bar equities/crypto and would need a fundamentally
different threshold calibration (not just a parameter tweak) to be
worth revisiting.
