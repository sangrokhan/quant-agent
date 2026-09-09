# Stochastic RSI + SMA-Spread + VWAP Filter — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_stochrsi_sma_vwap_filtered.py`
**Outcome:** REJECTED (decisive full-sample Sharpe fail)

## Hypothesis

Per TradingView's "Stochastic RSI Strategy (with SMA and VWAP Filters)"
by thedoggwalker (fully disclosed rule): long entry when Stochastic RSI
crosses above 30, gated by (1) a positive spread between a 9-period SMA
and a 21-period SMA (short-term momentum confirms uptrend) and (2) close
being below the VWAP (source's own stated pullback-to-value filter).
Source's risk management: fixed-tick stop/target (20/25 ticks), adapted
here to percentage-based stop (3%) / target (3.75%) since assets don't
share tick sizes, plus a max_hold_days backstop.

First Stochastic RSI (composite STOCH-of-RSI oscillator) strategy in
this repo combined with a dual-SMA-spread trend filter AND a
VWAP-relative-position filter simultaneously — distinct from plain
Stochastic Oscillator and plain RSI strategies already tested.

## Grid summary (stoch_window=[10,14] x vwap_window=[10,20] x
max_hold_days=[10,20], equity=[QQQ,SPY] x crypto=[BTC/USDT,ETH/USDT],
vol_regime_splits=3, 2018-01-01 to 2026-09-01)

- total_cells: 96, passed_cells: 7, pass_fraction: **0.073**
- by_asset_class: equity 7/48 (0.146), crypto 0/48 (0.0 — decisive fail)
- by_vol_regime: low 7/32 (0.219), mid 0/32 (0.0), high 0/32 (0.0)
- best_cell: stoch_window=14/vwap_window=10/max_hold_days=10, QQQ
  low-vol regime, Sharpe 1.73

## Full-sample validation (best grid config: stoch_window=14,
vwap_window=10, max_hold_days=10)

| Symbol | Sharpe | MDD |
|---|---|---|
| QQQ | 0.426 (FAIL, thr 1.0) | 21.0% (PASS) |
| SPY | 0.264 (FAIL, thr 1.0) | 18.5% (PASS) |

Both symbols fail full-sample Sharpe decisively — yet another instance
of this run's recurring pattern where a grid's optimistic low-vol-slice
Sharpe (1.73) does not survive full-period validation (0.42-0.26).

## Verdict: REJECTED

Both QQQ and SPY decisively fail full-sample Sharpe; crypto rejected
decisively in the grid (0/48). No further validators run given the
decisive Sharpe fail. The triple-condition entry (StochRSI cross above
30 + positive SMA spread + below VWAP) is quite restrictive and, on
daily bars, produces a signal that only works in a narrow low-vol
sub-slice, not broadly.
