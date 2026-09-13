# Downside-Deviation (Semi-Variance) Sizing SMA Trend Strategy — Backtest Report

**Date:** 2026-09-13
**Strategy file:** `strategies/2026-09-13_downside_deviation_sizing_sma_trend.py`
**KB entry:** 2026-09-13-048

## Hypothesis
Per https://urbandigistore.com/blog/stop-loss-position-sizing-sortino-deviation
(browser_exec), downside deviation (semi-variance) only penalizes returns
below a target threshold (0), unlike symmetric stddev. Sizing an SMA(200)
trend-following gate's exposure by target_downside_dev/rolling_downside_dev
should give steadier upside-skewed assets a larger allocation than
symmetric vol-targeting.

## Config (best from grid)
`trend_window=200, dd_window=40, target_downside_dev=0.015, leverage_cap=1.0`

## Single-config validator results (2019-01-01 to 2026-09-01)

| Symbol | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Trades |
|---|---|---|---|---|---|---|
| SPY | 0.989 (**fail**, thr 1.0) | 0.208 (pass) | 0.955 (pass) | 0.75 (pass) | 0.027 (pass) | 22 |
| QQQ | 1.226 (pass) | 0.213 (pass) | 1.213 (pass) | 0.75 (pass) | 0.040 (pass) | 12 |
| BTC/USDT | 0.784 (**fail**) | 0.475 (**fail**) | 0.772 (pass) | 0.75 (pass) | 0.050 (pass) | 31 |

## Grid summary (72 cells: 3 target_downside_dev x 2 dd_window x 2 equity + 2 crypto symbols x 3 vol regimes)
- pass_fraction: 0.403 (29/72)
- by_asset_class: equity 18/36, crypto 11/36
- by_vol_regime: low 13/24, mid 16/24, high 0/24
- best_cell: SPY, target_downside_dev=0.015/dd_window=40, low-vol, Sharpe 2.854

## Decision
**Accepted for QQQ only** — all 5 validators pass.
**Near-miss/rejected SPY** — Sharpe 0.989 just under 1.0, all else passes.
**Rejected BTC/USDT** — fails both Sharpe and MDD decisively; same crypto
fat-tail pattern as the repo's other tail-aware sizing overlays.

## Source
https://urbandigistore.com/blog/stop-loss-position-sizing-sortino-deviation (browser_exec)
