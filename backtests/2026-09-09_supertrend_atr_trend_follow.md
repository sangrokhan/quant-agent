# Backtest report: SuperTrend(ATR) long-only trend follower (REJECTED — near-miss)

**Strategy file:** `strategies/2026-09-09_supertrend_atr_trend_follow.py`

## Hypothesis

Per CoinQuant's ETHUSDT backtest
(https://www.coinquant.ai/blog/supertrend-on-ethereum-6-years-of-backtest-results),
SuperTrend(atr_window, mult) flipping bullish (close > SuperTrend line) marks
a sustained trending move worth riding long; flipping bearish exits. Source's
own ETH/4H(10,3.0) numbers: +810.8% return, Sharpe 0.90 (below source's
"strong" 1.0 bar), win rate 34.4%, MDD 53.14%. First SuperTrend strategy in
this repo; tested here on DAILY bars, QQQ/SPY/BTC/ETH.

## Step 6 grid summary (run_strategy_grid)

- param_grid: `atr_window=[7,10,14]` x `mult=[2.0,3.0,4.0]`
- symbols: equity=[QQQ, SPY], crypto=[BTC/USDT, ETH/USDT]
- vol_regime_splits=3
- **total_cells=108, passed_cells=27, pass_fraction=0.25**
- by_asset_class: equity 27/54, **crypto 0/54**
- by_vol_regime: low 18/36, mid 9/36, **high 0/36**
- best_cell: atr_window=14, mult=4.0, QQQ low-vol, Sharpe=3.00
- worst_cell: atr_window=7, mult=4.0, QQQ high-vol, Sharpe=-0.92

Passes only on equity, and only in low/mid volatility regimes — fails
uniformly on crypto and on high-vol regimes for both asset classes.

## Single-config validation (best grid cell: atr_window=14, mult=4.0), full sample

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd (4-split) | Param sensitivity (rel std) |
|---|---|---|---|---|---|
| QQQ | **1.454 (pass)** | **0.256 (FAIL, thresh 0.25)** | 1.427 (pass) | 0.75 (pass) | 0.102 (pass) |
| SPY | **0.903 (FAIL, thresh 1.0)** | 0.232 (pass) | 0.862 (pass) | 1.00 (pass) | 0.195 (pass) |

Both symbols pass 4/5 validators, each with exactly one near-miss failure on
a *different* metric: QQQ misses MDD by 0.6 percentage points (0.256 vs
0.25 threshold); SPY misses Sharpe by 0.097 (0.903 vs 1.0). Everything else
(transaction-cost survival, walk-forward, parameter sensitivity) passes
comfortably on both.

## Outcome: REJECTED (near-miss)

Rejected because not all validators pass for either symbol at the primary
config, and the grid confirms the strategy only works in a narrow slice
(equity, low/mid vol) — 0% pass on crypto and 0% pass in high-vol regimes.
The near-miss nature (QQQ MDD 0.256 vs 0.25; SPY Sharpe 0.903 vs 1.0) makes
this a candidate for future refinement (e.g. a volatility-regime gate to
exclude high-vol entries entirely, or a slightly larger ATR multiplier to
reduce QQQ's drawdown) rather than a decisive rejection like the source's
own sub-1.0-Sharpe/53% MDD result on ETH -- source's own weak crypto result
foreshadowed this repo's 0/54 crypto grid outcome.
