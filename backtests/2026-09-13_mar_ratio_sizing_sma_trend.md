# MAR-Ratio (Calmar) Dynamic Sizing SMA Trend Strategy — Backtest Report

**Date:** 2026-09-13
**Strategy file:** `strategies/2026-09-13_mar_ratio_sizing_sma_trend.py`
**KB entry:** 2026-09-13-047

## Hypothesis
Per https://www.ir-tracker.com/en/columns/advanced-strategy/drawdown-management
(browser_exec), the MAR ratio (Calmar ratio = CAGR/MaxDD) blends return and
risk into a single trailing performance-quality signal. This strategy scales
exposure on an SMA(200) trend gate by the asset's own trailing MAR ratio
(scale up when recent risk-adjusted performance is good, down when poor),
distinct from this repo's prior sizing overlays which scale purely by a
risk/dispersion measure (stddev-based vol-targeting, CVaR tail-loss).

## Config (best from grid)
`trend_window=200, mar_window=60, mar_reference=0.5, leverage_cap=1.0`

## Single-config validator results (2019-01-01 to 2026-09-01)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd pass | Param sensitivity | Trades |
|---|---|---|---|---|---|---|
| SPY | 1.222 (pass) | 0.139 (pass) | 1.172 (pass) | 0.75 (pass) | 0.114 (pass) | 28 |
| QQQ | 0.944 (**fail**, thr 1.0) | 0.189 (pass) | 0.904 (pass) | 0.75 (pass) | 0.039 (pass) | 35 |
| BTC/USDT | 1.042 (pass) | 0.396 (**fail**, thr 0.25) | 1.024 (pass) | 0.75 (pass) | 0.069 (pass) | 46 |

## Grid summary (108 cells: 3 mar_reference x 3 mar_window x 2 equity + 2 crypto symbols x 3 vol regimes)
- pass_fraction: 0.306 (33/108)
- by_asset_class: equity 27/54, crypto 6/54
- by_vol_regime: low 21/36, mid 12/36, high 0/36
- best_cell: SPY, mar_reference=0.5/mar_window=60, low-vol, Sharpe 2.864
- worst_cell: QQQ, mar_reference=1.5/mar_window=60, high-vol, Sharpe -0.818

## Decision
**Accepted for SPY only** — all 5 validators pass.
**Near-miss/rejected QQQ** — Sharpe 0.944 just under 1.0 threshold, all
other validators pass.
**Rejected BTC/USDT** — MDD 0.396 fails decisively despite passing Sharpe
and everything else; consistent with this repo's recurring finding that
crypto's fatter tail risk breaks MDD caps even when a sizing overlay
otherwise "works" on Sharpe.

## Source
- https://www.ir-tracker.com/en/columns/advanced-strategy/drawdown-management (browser_exec)
