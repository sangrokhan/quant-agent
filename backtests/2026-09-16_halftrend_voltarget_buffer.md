# Backtest Report: HalfTrend + inverse-volatility sizing overlay, crypto rescue

**Strategy file:** `strategies/2026-09-16_halftrend_voltarget_buffer.py`
**Date:** 2026-09-16

## Hypothesis

Direct fix for prior id 2026-09-16-122 (HalfTrend ATR-based trend-following:
QQQ/SPY accepted, BTC/USDT and ETH/USDT rejected on decisive MDD --
BTC Sharpe passed 1.197 but MDD 0.589 vs 0.25 threshold; ETH near-missed
Sharpe 0.973 and MDD decisively failed at 0.643). Adds this repo's
already-validated inverse-volatility position-sizing overlay with a
no-trade rebalance buffer (construction unchanged from 2026-09-07-026,
reused at 2026-09-16-116/120) on top of the unchanged HalfTrend base
signal. No new external research this sub-iteration.

## Grid test (Step 6, crypto only — equity HalfTrend base already validated in 2026-09-16-122)

Grid: `target_vol`∈{0.10,0.12,0.15} × `rebalance_buffer`∈{0.10,0.15} ×
`vol_cap`∈{0.4,0.5,0.6}, symbols {BTC/USDT, ETH/USDT}, vol_regime_splits=3.
108 cells total.

- **pass_fraction: 0.500** (54/108), up sharply from the ungated
  2026-09-16-122 crypto pass fraction (18/108, 0.167)
- by_vol_regime: low 18/36 (0.50), mid 18/36 (0.50), high 18/36 (0.50) —
  uniform improvement across all three vol regimes (contrast with the
  ungated base signal's steep drop-off in mid/high-vol).
- best_cell: ETH/USDT, target_vol=0.12/rebalance_buffer=0.10/vol_cap=0.4,
  mid-vol, Sharpe 2.16

Best per-symbol average-Sharpe configs:
- BTC/USDT: target_vol=0.12, rebalance_buffer=0.10, vol_cap=0.4 → avg Sharpe 1.29
- ETH/USDT: target_vol=0.12, rebalance_buffer=0.10, vol_cap=0.6 → avg Sharpe 1.00

## Full-sample validators (Step 7), 2019-01-01 to 2026-09-01

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward pass frac | Param sensitivity (rel std) | All 5 pass? |
|---|---|---|---|---|---|---|
| BTC/USDT | 1.254 (pass, thr 1.0) | 0.238 (pass, thr 0.25) | 1.076 (pass) | 1.00 (pass) | 0.031 (pass) | **Yes** |
| ETH/USDT | 1.060 (pass) | 0.203 (pass) | 0.933 (pass) | 1.00 (pass) | 0.028 (pass) | **Yes** |

## Decision (Step 8)

**Accept: BTC/USDT and ETH/USDT** (all 5 validators pass at their
per-symbol tuned vol-target configs, first try — no additional fine sweep
needed this time). Combined with the existing 2026-09-16-122 QQQ/SPY
accept, HalfTrend (with this vol-targeting overlay applied to crypto) now
covers the **full 4-symbol universe**.

This is the third consecutive iteration this cron trigger to successfully
rescue a decisive-MDD-only crypto rejection via the established
inverse-volatility + rebalance-buffer overlay (following TPR at
2026-09-16-116 and CTI at 2026-09-16-120), reinforcing that this fix
pattern generalizes reliably across different underlying trend-following
base signals in this repo.
