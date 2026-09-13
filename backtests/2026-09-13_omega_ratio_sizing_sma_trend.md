# Omega-Ratio Dynamic Sizing SMA Trend Strategy — Backtest Report

**Date:** 2026-09-13
**Strategy file:** `strategies/2026-09-13_omega_ratio_sizing_sma_trend.py`
**KB entry:** 2026-09-13-049

## Hypothesis
Per https://en.wikipedia.org/wiki/Omega_ratio (Keating & Shadwick 2002,
browser_exec), the Omega ratio is a probability-weighted gain/loss ratio
relative to a threshold that captures the ENTIRE return distribution (all
moments), unlike Sharpe (first two moments only). This strategy scales an
SMA(200) trend gate's exposure by the underlying asset's own trailing
Omega ratio (theta=0, the Bernardo-Ledoit gain-loss-ratio special case).
First Omega-ratio-based strategy (entry or sizing) in this repo.

## Config (best from grid)
`trend_window=200, omega_window=40, omega_reference=1.0, leverage_cap=1.0`

## Single-config validator results (2019-01-01 to 2026-09-01)

| Symbol | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Trades |
|---|---|---|---|---|---|---|
| SPY | 1.028 (pass) | 0.202 (pass) | 0.994 (pass) | 0.75 (pass) | 0.020 (pass) | 22 |
| QQQ | 1.244 (pass) | 0.212 (pass) | 1.231 (pass) | 0.75 (pass) | 0.021 (pass) | 12 |
| BTC/USDT | 0.798 (fail) | 0.568 (fail) | 0.787 (pass) | 0.75 (pass) | 0.063 (pass) | 31 |

## Grid summary (72 cells: 3 omega_reference x 2 omega_window x 2 equity + 2 crypto symbols x 3 vol regimes)
- pass_fraction: 0.278 (20/72)
- by_asset_class: equity 18/36, crypto 2/36
- by_vol_regime: low 12/24, mid 8/24, high 0/24
- best_cell: SPY, omega_reference=1.0/omega_window=40, low-vol, Sharpe 2.855

## Decision
**Accepted for BOTH SPY and QQQ** — all 5 validators pass cleanly for both.
**Rejected BTC/USDT** — fails Sharpe (0.798) and MDD (0.568, badly) --
crypto's fatter tails again break a distribution-shape-based sizing
overlay, same pattern as this repo's other tail/shape-aware sizing
strategies this cron trigger.

## Source
https://en.wikipedia.org/wiki/Omega_ratio (browser_exec)
