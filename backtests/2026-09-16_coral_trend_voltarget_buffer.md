# Backtest Report: Coral Trend + inverse-volatility sizing overlay, crypto rescue

**Strategy file:** `strategies/2026-09-16_coral_trend_voltarget_buffer.py`
**Date:** 2026-09-16

## Hypothesis

Direct fix for prior id 2026-09-16-125 (Coral Trend color-flip trend-
following: QQQ/SPY accepted, BTC/USDT and ETH/USDT rejected -- Sharpe
passed comfortably (1.187/1.374) but MDD decisively failed (0.583/0.485,
roughly 2x threshold), a pure risk-control gap). Adds this repo's
already-validated inverse-volatility position-sizing overlay with a
no-trade rebalance buffer (construction unchanged from 2026-09-07-026,
reused at 2026-09-16-116/120/123) on top of the unchanged Coral Trend base
signal. No new external research this sub-iteration.

## Grid test (Step 6, crypto only — equity Coral Trend base already validated in 2026-09-16-125)

Grid: `target_vol`∈{0.10,0.12,0.15} × `rebalance_buffer`∈{0.10,0.15} ×
`vol_cap`∈{0.4,0.5,0.6}, symbols {BTC/USDT, ETH/USDT}, vol_regime_splits=3.
108 cells total.

- **pass_fraction: 0.759** (82/108) — the strongest vol-target rescue
  result this cron trigger (compared to TPR 0.648, CTI 0.648, HalfTrend
  0.500).
- by_vol_regime: low 36/36 (1.00), mid 32/36 (0.889), high 14/36 (0.389) —
  strong improvement across all regimes, especially mid-vol.
- best_cell: ETH/USDT, target_vol=0.15/rebalance_buffer=0.10/vol_cap=0.4,
  mid-vol, Sharpe 1.89

Both symbols converged on the SAME best-average-Sharpe config:
target_vol=0.10, rebalance_buffer=0.15, vol_cap=0.5.

## Full-sample validators (Step 7), 2019-01-01 to 2026-09-01

Shared config (sm=21, cd=0.4, target_vol=0.10, rebalance_buffer=0.15,
vol_cap=0.5):

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward pass frac | Param sensitivity (rel std) | All 5 pass? |
|---|---|---|---|---|---|---|
| BTC/USDT | 1.293 (pass, thr 1.0) | 0.176 (pass, thr 0.25) | 1.041 (pass) | 1.00 (pass) | 0.067 (pass) | **Yes** |
| ETH/USDT | 1.212 (pass) | 0.133 (pass) | 1.010 (pass) | 1.00 (pass) | 0.080 (pass) | **Yes** |

## Decision (Step 8)

**Accept: BTC/USDT and ETH/USDT** (both pass all 5 validators with a
SHARED config, first-try grid best-average-Sharpe cell, no per-symbol
fine-tune needed). Combined with the existing 2026-09-16-125 QQQ/SPY
accept, Coral Trend (with this vol-targeting overlay applied to crypto) now
covers the **full 4-symbol universe**.

This is the fourth consecutive successful rescue of a decisive-MDD-only
crypto rejection via the established inverse-volatility + rebalance-buffer
overlay this cron trigger (following TPR 2026-09-16-116, CTI 2026-09-16-120,
HalfTrend 2026-09-16-123), with the strongest grid pass_fraction of the
four — the overlay generalizes reliably and, in this case, needed no
per-symbol parameter divergence at all.
