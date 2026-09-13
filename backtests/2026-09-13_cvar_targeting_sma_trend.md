# CVaR-Targeting SMA Trend Strategy — Backtest Report

**Date:** 2026-09-13
**Strategy file:** `strategies/2026-09-13_cvar_targeting_sma_trend.py`
**KB entry:** 2026-09-13-045

## Hypothesis
Per Rickenberg 2019 "Tail Risk Targeting: Target VaR and CVaR Strategies"
(GARP white paper) and QuantInsti's CVaR/Expected Shortfall computation
method, dynamic position sizing that targets a constant level of tail risk
(CVaR/Expected Shortfall) rather than plain volatility (stddev) improves
risk-adjusted returns on a simple SMA(200) trend-following gate. This
isolates the sizing mechanism (CVaR-based vs. the repo's already-accepted
plain vol-targeting overlay, 2026-09-08-165) on the same entry signal.

## Config (best from grid)
`trend_window=200, cvar_window=40, target_cvar=0.02, leverage_cap=1.0`

## Single-config validator results (2019-01-01 to 2026-09-01)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd pass | Param sensitivity (rel std) | Trades |
|---|---|---|---|---|---|---|
| SPY | 1.013 (pass, thr 1.0) | 0.196 (pass, thr 0.25) | 0.976 (pass, thr 0.5) | 0.75 (pass) | 0.030 (pass, thr 0.5) | 22 |
| QQQ | 1.319 (pass) | 0.167 (pass) | 1.301 (pass) | 0.75 (pass) | 0.043 (pass) | 12 |
| BTC/USDT | 0.877 (**fail**, thr 1.0) | 0.247 (pass) | 0.851 (pass) | 0.75 (pass) | 0.029 (pass) | 31 |

## Grid summary (72 cells: 3 target_cvar x 2 cvar_window x 2 equity + 2 crypto symbols x 3 vol regimes)
- pass_fraction: 0.417 (30/72)
- by_asset_class: equity 18/36, crypto 12/36
- by_vol_regime: low 12/24, mid 18/24, high 0/24 (typical repo pattern:
  high-vol regime uniformly hard to pass, but this strategy's mid-vol
  regime performance is a notable improvement over most prior strategies
  in this repo, which usually only pass low-vol)
- best_cell: SPY, target_cvar=0.02/cvar_window=40, low-vol regime, Sharpe 2.855
- worst_cell: QQQ, target_cvar=0.015/cvar_window=40, high-vol regime, Sharpe -0.049

## Decision
**Accepted for equity (SPY, QQQ)** — all 5 validators pass for both symbols.
**Rejected for crypto (BTC/USDT)** — fails full-sample Sharpe (0.877 < 1.0)
though it passes the other 4 validators and is a near-miss, not a decisive
failure; worth revisiting with crypto-specific tuning (e.g. wider
cvar_window or lower target_cvar) in a future iteration.

## Source
- https://www.garp.org/white-paper/tail-risk-targeting (Rickenberg 2019, abstract via browser_exec)
- https://blog.quantinsti.com/cvar-expected-shortfall/ (CVaR computation method, browser_exec)
