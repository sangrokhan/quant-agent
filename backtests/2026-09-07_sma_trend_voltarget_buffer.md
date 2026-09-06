# SMA200 Trend + Buffered Inverse-Volatility Position Sizing — Backtest Report

**Date:** 2026-09-07
**Strategy file:** `strategies/2026-09-07_sma_trend_voltarget_buffer.py`
**Source:** https://blave.org/agent/en/learn/vol_targeting (accessed 2026-09-07)

## Hypothesis

A binary SMA(trend_window) trend-following base signal (long when
close>SMA, else flat), overlaid with continuous inverse-volatility position
sizing (`scale = clip(target_vol/realized_vol, upper=vol_cap)`), plus a
no-trade rebalance buffer band (only re-size when the desired position
differs from currently-held size by more than `rebalance_buffer`), should
retain trend-following edge while damping drawdowns in high-vol regimes —
and the buffer should fix the transaction-cost-survival failure that sank
the earlier un-buffered vol-target overlay (2026-09-03-003, BTC momentum +
vol-target, rejected on MDD 47.6% and TC-survival).

## Grid test (Step 6)

`param_grid`: trend_window∈{150,200}, target_vol∈{0.20,0.30},
rebalance_buffer∈{0.10,0.15}; symbols: equity {QQQ,SPY}, crypto
{BTC/USDT,ETH/USDT}; vol_regime_splits=3; period 2018-01-01..2026-09-01.

- **pass_fraction: 0.240** (23/96 cells)
- by_asset_class: equity 23/48 passed, **crypto 0/48 passed** (decisive
  crypto failure — the buffered vol-target overlay does not rescue crypto
  regime instability)
- by_vol_regime: low 16/32, mid 7/32, **high 0/32** — edge concentrated
  entirely in low-vol regime, as expected for a trend strategy, but the
  vol-targeting overlay does NOT rescue high-vol-regime performance the
  way the source page's own risk-management framing implied it should.
- best_cell: SPY, trend_window=150, target_vol=0.3, rebalance_buffer=0.1,
  low-vol regime, Sharpe 2.47
- worst_cell: QQQ, trend_window=200, target_vol=0.3, rebalance_buffer=0.1,
  high-vol regime, Sharpe -0.25

## Single-config validation (Step 7): SPY, trend_window=150, target_vol=0.30, rebalance_buffer=0.10

Full period 2018-01-01..2026-09-01 (not vol-regime-sliced):

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.809 | ≥1.0 | **FAIL** |
| Max drawdown | 34.6% | ≤25% | **FAIL** |
| Transaction-cost survival (144 trades, 10bps) | net Sharpe 0.692 | ≥0.5 | pass |
| Walk-forward (manual 4-split, vbt.utils.splitting still broken since 2026-09-03-002) | 0.75 pass_fraction (3/4 splits positive Sharpe) | ≥0.75 | pass |
| Parameter sensitivity (6-point grid over trend_window×target_vol) | rel std 0.040 | ≤0.5 | pass |

## Decision: **REJECT**

The buffered rebalance band successfully fixed the transaction-cost problem
that sank 2026-09-03-003 (144 trades vs ~1231 previously, net Sharpe now
comfortably passes) and parameter sensitivity is very stable (rel std
0.04). However the full-sample Sharpe (0.81) and MDD (34.6%) both fail
their thresholds on the best individual grid cell's own symbol/params — the
grid's per-cell/per-regime passes are concentrated in the low-vol tercile
only and don't survive being averaged across the full sample. Crypto fails
categorically (0/48). Net: this is a directional improvement on the
transaction-cost front over the prior vol-target attempt, but the core
Sharpe/MDD edge is not there once tested across the full period rather than
per-regime-sliced cells.
