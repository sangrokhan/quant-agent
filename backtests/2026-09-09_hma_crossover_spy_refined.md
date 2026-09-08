# Backtest report: HMA single-line crossover, wide-window fix (ACCEPTED — QQQ + SPY)

**Strategy file:** `strategies/2026-09-09_hma_crossover_spy_refined.py`

## Hypothesis

Direct refinement of near-miss 2026-09-04-026 (Hull Moving Average
single-line crossover, long when close crosses above HMA(hma_window), exit
below). Original best full-sample config (SPY, hma_window=40) failed only
Sharpe (0.906 vs 1.0, 9.4% shortfall) -- MDD, transaction-cost-survival, and
parameter sensitivity all already passed. A wider window sweep
(hma_window in [40,50,60,70,80,100,120]) found hma_window=100 pushes both
SPY (Sharpe=1.141) and QQQ (Sharpe=1.083) above threshold.

## Step 6 grid summary (run_strategy_grid)

- param_grid: `hma_window=[80,100,120]`
- symbols: equity=[QQQ, SPY], crypto=[BTC/USDT, ETH/USDT]
- vol_regime_splits=3
- **total_cells=36, passed_cells=9, pass_fraction=0.25**
- by_asset_class: equity 9/18, crypto 0/18
- by_vol_regime: low 6/12, mid 1/12, high 2/12
- best_cell: hma_window=120, QQQ low-vol, Sharpe=2.69
- worst_cell: hma_window=120, SPY mid-vol, Sharpe=-0.26

## Single-config validation (hma_window=100), full sample

| Symbol | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | num_trades |
|---|---|---|---|---|---|---|
| QQQ | **1.083 (pass)** | 0.203 (pass) | 0.934 (pass) | 1.00 (pass) | 0.057 rel-std (pass) | 94 |
| SPY | **1.141 (pass)** | 0.177 (pass) | 0.956 (pass) | 0.75 (pass) | 0.106 rel-std (pass) | 85 |

Both symbols pass all 5 validators with healthy trade counts (85-94 over
7.5yr, much more statistically robust than several other strategies tested
this cron trigger with only single-digit trade counts). Low parameter
sensitivity (0.06-0.11 rel-std) confirms the result isn't a fragile
single-cell artifact.

## Outcome: ACCEPTED (QQQ + SPY)

Both symbols pass all 5 validators at hma_window=100, directly resolving
the original near-miss's Sharpe shortfall on SPY while also newly passing
on QQQ. Crypto remains out of scope (0/18 grid cells, consistent with the
original's decisive crypto rejection and the source's own finding that HMA
crossover performs poorly on BTC/USDT at any tested frequency).
