# Backtest Report: Rolling VWAP Standard-Deviation Bands Mean Reversion

**Strategy file:** `strategies/2026-09-04_vwap_bands_meanrev.py`
**Date:** 2026-09-04
**Outcome:** REJECTED (decisive, all asset classes/param combos)

## Hypothesis

Source: https://fazencapital.com/learn/en/vwap-standard-deviation-bands
(fetched via `browser_exec` after `web_search` failed with the recurring
DDGS/Yahoo TLS connection error).

Intraday VWAP standard-deviation bands (volume-weighted mean + volume-weighted
sigma) mark statistically significant price stretch from volume-consensus
fair value; a touch of the lower band, when NOT on a "trend day" (proxied
here by an elevated realized-vol regime), should mean-revert back toward
VWAP. Adapted from the source's intraday/session-based construction to a
rolling N-day analog for this repo's daily-bar dataset, reusing the
established vol-regime-gate pattern (2026-09-03-001) as the trend-day proxy.

## Grid test summary (Step 6)

Grid: `vwap_window` in {10, 20, 30} x `band_std` in {1.5, 2.0, 2.5},
symbols equity {QQQ, SPY} + crypto {BTC/USDT, ETH/USDT}, vol_regime_splits=3.

- total_cells: 108, passed_cells: 5, **pass_fraction: 0.046**
- by_asset_class: equity 5/54, crypto 0/54
- by_vol_regime: low 3/36, mid 2/36, high 0/36
- best_cell: QQQ, vwap_window=10/band_std=2.0, low-vol tercile, Sharpe 2.54
  (narrow-slice artifact — see full-sample sweep below)
- worst_cell: SPY, vwap_window=20/band_std=2.0, low-vol tercile, Sharpe -0.91

## Full-sample sweep (QQQ, all 9 param combos)

| vwap_window | band_std | trades | full-sample Sharpe |
|---|---|---|---|
| 10 | 1.5 | 25 | 0.153 |
| 10 | 2.0 | 8  | 0.403 |
| 10 | 2.5 | 0  | n/a (no trades) |
| 20 | 1.5 | 11 | 0.104 |
| 20 | 2.0 | 3  | 0.252 |
| 20 | 2.5 | 0  | n/a (no trades) |
| 30 | 1.5 | 7  | 0.460 |
| 30 | 2.0 | 3  | 0.402 |
| 30 | 2.5 | 1  | 0.604 (single trade) |

Best real (non-zero-trade) full-sample Sharpe across all tested combos is
**0.604** (30-day window, 2.5 sigma band — a single-trade result, not
robust), decisively below the 1.0 threshold. The grid's isolated best_cell
of 2.54 is a narrow low-vol-tercile artifact that does not survive full
sample evaluation (QQQ full-sample Sharpe at the same params is only 0.403).

## Single-config validators (Step 7)

Skipped remaining validator suite (walk-forward, transaction-cost, parameter
sensitivity) per Step 7 minimum-subset guidance — Sharpe already decisively
fails across the entire grid and full-sample sweep with no near-miss.

| Validator | QQQ (vwap=10, std=2.0) | SPY (same) |
|---|---|---|
| Sharpe ratio | FAIL (0.403 vs 1.0) | FAIL (0.164 vs 1.0) |
| Max drawdown | PASS (0.052 vs 0.25) | PASS (0.046 vs 0.25) |

## Decision

**Rejected.** The rolling-window daily-bar adaptation of intraday VWAP bands
produces too few trades (widening `band_std` to 2.5 eliminates trades
entirely at 10/20-day windows) and weak Sharpe even at its best full-sample
configuration. Crypto rejected decisively (0/54 grid cells). Plausible
explanation: the source's construction is fundamentally session-based
(intraday, VWAP resets daily) — a rolling multi-day window without session
resets likely dilutes the "volume consensus fair value" signal the source
relies on, and the source itself warns band touches need additional
confirmation (rejection candles, RSI divergence, Value Area alignment) that
this mechanical daily-bar adaptation does not implement.
