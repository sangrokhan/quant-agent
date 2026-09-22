# 2026-09-22 — Al Brooks Three-Push Wedge Reversal (short)

**Hypothesis**: Source: https://algobars.com/strategy-templates/al-brooks/brooks-wedge-reversal/
(accessed 2026-09-22, browser_exec after web_extract ddgs-backend refused
extraction). A "three-push wedge": three consecutive higher-highs, each
with a SMALLER gain than the previous (diminishing momentum), ideally
confirmed by bearish RSI divergence (RSI lower on the 3rd push than the
1st). Short entry on a bearish reversal candle at the 3rd push high, stop
above the 3rd push extreme, target the wedge base. Distinct from this
repo's existing Falling/Rising Wedge chart-pattern strategies
(2026-09-08-113, 2026-09-09-097 -- trendline-convergence range breakouts)
via the specific three-push-counting + diminishing-gain + RSI-divergence
trend-exhaustion mechanic.

**Strategy file**: `strategies/2026-09-22_brooks_wedge_reversal_short.py`

**Grid test** (`run_grid_brooks_wedge_reversal_short.py`): param_grid =
`{pivot_window: [3, 4, 6, 8], max_hold_days: [15, 25]}`, symbols =
equity(QQQ, SPY) + crypto(BTC/USDT, ETH/USDT), vol_regime_splits=3.
- total_cells=96, passed_cells=5, pass_fraction=0.052 (weakest grid result
  this cron trigger)
- by_asset_class: equity 4/48, crypto 1/48
- by_vol_regime: low 2/32, mid 2/32, high 1/32 -- scattered, no
  regime-concentration pattern this time, just uniformly weak
- best_cell: SPY pivot_window=6/max_hold_days=15, low-vol, Sharpe 1.59
  (per-tercile, isolated)

**Single-config validators** (full-sample 2019-2026, SPY,
`pivot_window=6, max_hold_days=15`):

| Metric | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 0.299 | ≥1.0 | FAIL (decisive) |
| Max drawdown | 0.028 | ≤0.25 | pass |
| TX-cost survival | 0.249 | ≥0.5 | FAIL |
| Trade count | 6 | -- | -- |

**Decision**: REJECTED. Only 6 trades over the full sample and a decisive
Sharpe/TX-cost failure. The three-push structural requirement (3
sequential higher swing highs with diminishing gains AND RSI divergence
AND a bearish confirmation candle, all in sequence) is too rare a
conjunction on daily bars, and the isolated grid pass in one narrow
low-vol cell doesn't survive full-sample scrutiny -- consistent with the
regime-concentration/small-sample artifact pattern that dominated this
cron trigger's results.
