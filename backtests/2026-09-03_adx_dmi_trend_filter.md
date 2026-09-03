# Backtest Report: ADX/DMI Trend-Strength-Filtered Directional Crossover, Long-Only

**Strategy file:** `strategies/2026-09-03_adx_dmi_trend_filter.py`
**Hypothesis ID:** 2026-09-03-017
**Source:** Google search snippets (web_search intermittently failing this
cron trigger, used browser_exec Google search directly), converging across
Reddit r/algotrading, TradingView, FXNX, Fazen Capital, DXP Analytics.

## Hypothesis

Classic Wilder DMI/ADX rule: ADX(14) > 25 confirms a tradeable trend (vs
range-bound below 20-25); long entry when +DI crosses above -DI while ADX
is above the threshold; exit on -DI crossing above +DI or ADX dropping back
below threshold. First strategy in this repo to decompose trend STRENGTH
(ADX) from trend DIRECTION (+DI/-DI) as two orthogonal signals rather than
a single combined price/return/band trigger.

Long-only per SAFETY.md.

## Grid test (validation/grid_test.py::run_strategy_grid)

Grid: `adx_threshold` in {20,25,30} x `period`={14} x symbols {QQQ, SPY,
BTC/USDT, ETH/USDT} x 3 vol terciles = 36 cells, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.194** (7/36) — the weakest grid pass-rate of any
  strategy tested so far this cron trigger.
- by_asset_class: equity 7/18 (39%), crypto 0/18 (0%)
- by_vol_regime: low 5/12 (42%), mid 2/12 (17%), high 0/12 (0%)
- best_cell: QQQ, adx_threshold=20.0, low-vol regime, Sharpe 2.47 (a
  narrow-slice artifact — see full-sample result below)
- worst_cell: QQQ, adx_threshold=30.0, high-vol regime, Sharpe -2.02

## Single-config validators (best grid config: adx_threshold=20.0, period=14)

| Symbol | Sharpe | MDD | TC-adj Sharpe | Walk-fwd (4-split) |
|---|---|---|---|---|
| QQQ | 0.87 (fail, thr 1.0) | 18.3% (pass) | 0.69 (pass) | 0.75 (pass) |
| SPY | 0.44 (fail) | 18.0% (pass) | 0.21 (fail) | 0.5 (fail) |
| BTC/USDT | 0.18 (fail) | 46.4% (fail) | -0.02 (fail) | 0.75 (pass) |

Parameter sensitivity (6-point adx_threshold sweep, 15-30, on QQQ full
sample): **FAILED** — relative std 0.53 (threshold 0.5), Sharpe ranges from
0.96 (threshold=15) down to 0.17 (threshold=30), a monotonic decay as the
ADX gate gets stricter (fewer, later trend entries = less captured upside).
This is itself informative: the strategy's edge is fragile to the exact
ADX threshold chosen, not a stable property of the ADX/DMI signal.

Walk-forward used a manual 4-way date-slice fallback (vectorbt
`utils.splitting.RangeSplitter` still broken — unfixed since 2026-09-03-002).

## Decision: **REJECT**

The grid's "best cell" Sharpe of 2.47 (QQQ, low-vol tercile) was a narrow
slice artifact, consistent with the pattern already seen in 2026-09-03-009
and 2026-09-03-010 this repo — the full-sample QQQ Sharpe at the same
config is only 0.87, missing the 1.0 threshold. SPY and BTC/USDT both fail
more decisively (SPY also fails TC-survival and walk-forward; BTC/USDT
fails MDD at 46.4%). Parameter sensitivity additionally fails (rel.std
0.53) — the ADX/DMI directional-crossover signal itself does not show a
stable, threshold-robust edge on any tested symbol at full-sample scope.

Weakest grid pass-fraction (19.4%) of any strategy tested this cron
trigger, and the only one this trigger to also fail parameter sensitivity —
a clean, well-sourced negative result rather than a near-miss.
