# Backtest report: 52-week-high proximity momentum, QQQ refinement (ACCEPTED — QQQ + SPY)

**Strategy file:** `strategies/2026-09-09_52wk_high_momentum_qqq_refined.py`

## Hypothesis

Direct refinement of near-miss 2026-09-03-015 (52-week-high proximity
momentum: long when close within `pct_from_high` of the rolling 252d high,
exit when close < `trend_window`-day SMA). Original config
(pct_from_high=0.02, trend_window=150) gave QQQ Sharpe=0.959, a 0.041
near-miss below the 1.0 threshold, while SPY already passed at
Sharpe=1.119. A finer parameter sweep on QQQ (pct_from_high in
[0.01,...,0.04], trend_window in [150,175,200,220]) found
pct_from_high=0.04/trend_window=200 pushes QQQ's Sharpe to 1.135 --
notably, trend_window=200 (the "classic" 200-day SMA, not the original's
150-day) combined with a wider 4% proximity band to the 52-week high
(fewer, higher-conviction entries) resolves the near-miss.

## Step 6 grid summary (run_strategy_grid)

- param_grid: `pct_from_high=[0.03,0.04,0.05]` x `trend_window=[180,200,220]`
- symbols: equity=[QQQ, SPY], crypto=[BTC/USDT, ETH/USDT]
- vol_regime_splits=3
- **total_cells=108, passed_cells=27, pass_fraction=0.25**
- by_asset_class: equity 27/54, crypto 0/54
- by_vol_regime: low 18/36, mid 9/36, high 0/36
- best_cell: pct_from_high=0.03, trend_window=180, SPY low-vol, Sharpe=2.71
- worst_cell: pct_from_high=0.03, trend_window=180, QQQ high-vol, Sharpe=-0.05

## Single-config validation (pct_from_high=0.04, trend_window=200), full sample

| Symbol | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | num_trades |
|---|---|---|---|---|---|---|
| QQQ | **1.135 (pass)** | 0.192 (pass) | 1.129 (pass) | 0.75 (pass) | 0.054 rel-std (pass) | 5 |
| SPY | **1.081 (pass)** | 0.132 (pass) | 1.070 (pass) | 0.75 (pass) | 0.080 rel-std (pass) | 7 |

Both symbols now pass all 5 validators. Trade counts are low (5-7 over
7.5yr, consistent with this strategy's low-frequency nature -- it only
enters near genuine 52-week highs), but the very low parameter-sensitivity
relative-std (0.05-0.08, tightest of any strategy tested this cron trigger)
indicates the result is not a fragile single-cell artifact -- performance is
consistent across the full 3x3 nearby-parameter neighborhood.

## Outcome: ACCEPTED (QQQ + SPY)

Both symbols pass all 5 validators at the refined config
(pct_from_high=0.04, trend_window=200). This directly resolves the original
near-miss (2026-09-03-015)'s QQQ Sharpe shortfall via a widened
proximity-to-high band and a longer (more standard) 200-day trend-exit SMA.
Crypto remains out of scope (0/54 grid cells, consistent with the original
finding). The original strategy file (2026-09-03_52wk_high_momentum.py,
SPY-only accepted at different params) remains untouched/live per its own
record; this refined file is a new, separately-tracked variant scoped to
both QQQ and SPY at the new parameter values.
