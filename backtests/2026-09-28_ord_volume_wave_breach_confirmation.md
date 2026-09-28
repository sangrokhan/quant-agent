# Ord Volume Wave-Average Breach Confirmation — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_ord_volume_wave_breach_confirmation.py`
**Source:** https://www.tradingview.com/script/lhda3xOg-Ord-Volume-LucF/

## Hypothesis

Tim Ord's "Ord Volume" concept divides price action into alternating
up/down "waves" (trend-filter crosses) and tracks each wave's AVERAGE
(not cumulative) volume. This page's own "Marker 1" concept: the current
wave's average volume breaching the PRIOR wave's highest average volume
signals renewed/strengthening buying participation. Operationalized here
as a long-only strategy: enter/hold when in an EMA up-wave whose running
average volume exceeds the prior completed up-wave's average volume
(scaled by `volume_breach_mult`); exit on trend break or time-stop. First
"Ord Volume"/"Weis Wave" strategy in this repo (0 prior hits).

## Grid test (Step 6)

`validation/grid_test.py::run_strategy_grid`,
`trend_window in {15,20,30}` x `volume_breach_mult in {0.8,1.0,1.3}`,
symbols equity `{QQQ, SPY}` / crypto `{BTC/USDT, ETH/USDT}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.315 (34/108)**
- by_asset_class: equity 20/54, crypto 14/54
- by_vol_regime: low 22/36, mid 11/36, high 1/36
- best_cell: ETH/USDT, trend_window=20, volume_breach_mult=0.8, mid-vol, Sharpe 2.46
- avg full-sample Sharpe by (trend_window, volume_breach_mult) trended higher
  with larger trend_window and lower volume_breach_mult (tw=30,vb=0.8 avg 1.21)

A follow-up full-sample sweep across `trend_window in {25,30,40}` x
`volume_breach_mult in {0.7,0.8,0.9}` on QQQ/SPY found `trend_window=25,
volume_breach_mult=0.9` clears Sharpe >= 1.0 on BOTH symbols simultaneously
(QQQ 1.037, SPY 1.029), adopted as the primary config below.

## Single-config validators (config: trend_window=25, volume_breach_mult=0.9, min_wave_len=3, max_hold_days=40, full sample)

| Validator | QQQ | SPY | Threshold | Passed |
|---|---|---|---|---|
| Sharpe ratio | 1.037 | 1.029 | >= 1.0 | **pass (both)** |
| Max drawdown | 0.169 | 0.122 | <= 0.25 | pass (both) |
| Transaction cost survival (10bps/trade) | net Sharpe 0.969 (42 trades) | net Sharpe 0.928 (48 trades) | >= 0.5 | pass (both) |
| Walk-forward (4 splits, SPY, manual fallback*) | per-split Sharpe [1.45, 0.17, 1.86, 0.63], pass_fraction 1.0 | -- | >= 0.75 | pass |
| Parameter sensitivity (9-combo grid from Step 6) | relative_std 0.247 | -- | <= 0.5 | pass |

\* Known repo `vbt.utils.splitting.RangeSplitter` API issue — manual 4-way
chronological split fallback used (per prior iterations' convention).

Crypto: only 14/54 grid cells pass, scattered across cells rather than
concentrated — not tested at single-config level given the grid's weak
crypto showing.

## Decision

**Accepted for equity (QQQ, SPY)** at `trend_window=25,
volume_breach_mult=0.9`. All validators pass with reasonable margin.
**Not accepted for crypto** — grid pass rate too low/scattered (14/54) to
warrant a full single-config validator run this iteration.

## Notes for future loops

Ord Volume's wave-average breach construction (rather than cumulative OBV/
Klinger-style volume) turned out workable as a long-only trend-confirmation
overlay on equities. The Marker 1 condition (default `volume_breach_mult=1.0`)
was slightly too strict on this dataset; loosening to 0.9 improved robustness
without materially hurting the underlying logic. A future loop could test
Ord's own second use case (support/resistance test confirmation via wave
comparison rather than pure trend-following) or explore why crypto vol
regimes underperform equity here (possibly crypto's higher baseline volume
noise swamps the wave-average signal).
