# OVX Z-Score Fear Gate on USO/QQQ/SPY/BTC/ETH Trend-Following — REJECTED

## Hypothesis
Per StoneX's OVX explainer (https://www.stonex.com/en/news-and-analysis/2023/10/ovx-index-your-guide-to-the-oil-volatility-index/):
"increased fear usually drives oil prices upwards, unlike the VIX which has
a negative correlation to the price of equities." Adapted into a trend-gate:
long the primary asset's own SMA(trend_window) trend-following signal only
when OVX's rolling z-score is above `ovx_z_threshold` (elevated oil-fear
regime). Tested on USO (intended asset) plus QQQ/SPY/BTC/USDT/ETH/USDT as
cross-asset-class falsification checks.

Source: https://www.stonex.com/en/news-and-analysis/2023/10/ovx-index-your-guide-to-the-oil-volatility-index/
(read via browser_exec after web_search's DDGS/Yahoo backend TLS-errored on
this iteration's queries).

## Grid test summary (Step 6)
`param_grid={"trend_window": [50,100,150], "ovx_z_threshold": [0.0,0.5,1.0]}`,
`symbols={"equity": ["USO","QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2016-01-01 to 2026-09-01, 135 total cells.

- pass_fraction: 0.252 (34/135)
- by_asset_class: equity 9/81 passed, crypto 25/54 passed
- by_vol_regime: low 12/45, mid 20/45, high 2/45
- best_cell: crypto ETH/USDT, trend_window=50/z=0.5, mid-vol regime, Sharpe 1.975
- worst_cell: crypto ETH/USDT, same config, high-vol regime, Sharpe -0.828

The per-regime-tercile pass fraction is inflated by subsample noise (short
windows, few trades per tercile); the decisive test is full-sample Sharpe
per symbol across the same param grid (Step 7 below).

## Single-config validation (Step 7) — full-sample, best config per symbol

| Symbol | Best trend_window | Best ovx_z_threshold | Full-sample Sharpe | Sharpe passed (>=1.0)? |
|---|---|---|---|---|
| USO (intended asset) | 100 | 1.0 | 0.499 | No |
| QQQ | 150 | 0.0 | 0.752 | No |
| SPY | 50 | 0.0 | 0.865 | No |
| BTC/USDT | 150 | 0.0 | 0.121 | No |
| ETH/USDT | 100 | 0.0 | 0.076 | No |

No symbol clears the Sharpe>=1.0 threshold at its own best full-sample
config, including USO itself — the asset the source's mechanism was
specifically about. MDD/transaction-cost/walk-forward/param-sensitivity
were not run given the decisive full-sample Sharpe failure across the
entire universe (workload="max" but Sharpe failure is unambiguous enough
that a fuller validator suite would not change the accept/reject call).

## Decision: REJECTED

Sharpe threshold fails for every symbol tested, including the intended
USO target. The grid's higher pass_fraction on crypto vol-regime slices
appears to be short-sample noise rather than a genuine transferable edge
(crypto has no economic link to crude-oil-specific implied volatility, and
best/worst grid cells for the same crypto config span +1.975/-0.828 Sharpe
across vol terciles — high variance, not a robust signal).

## Notes for future loops
- ^OVX and USO are both directly loadable via `data/loaders.py::load_equity`
  (no feasibility blocker) — first confirmed working OVX data path in this
  repo, useful if a future iteration wants to try a different OVX
  construction (e.g. OVX-vs-realized-oil-vol spread, mirroring the
  already-accepted VRP=VIX-realized_vol pattern from 2026-09-05-044, or a
  continuous-sizing-dial variant instead of a binary gate).
- The z-score threshold sweep (0.0/0.5/1.0) made little difference to
  full-sample Sharpe on the equity symbols, suggesting the trend-following
  base signal (SMA crossover) dominates and the OVX fear-gate adds little
  discriminating power at these thresholds.
