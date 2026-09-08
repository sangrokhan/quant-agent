# Backtest report: Choppiness Index regime gate + EMA crossover (REJECTED — insufficient sample size)

**Strategy file:** `strategies/2026-09-09_chop_regime_ema_crossover.py`

## Hypothesis

Per StrategyQuant's Codebase confirmation of the Choppiness Index (CHOP,
Bill Dreiss) formula (https://strategyquant.com/codebase/choppiness-index/)
and the widely-cited Fibonacci-derived convention (CHOP<38.2=trending,
CHOP>61.8=choppy), gating a fast/slow EMA crossover entry to only the
CHOP-trending regime should reduce whipsaw relative to an ungated
crossover. Distinct from this repo's prior CHOP entry (2026-09-04-059,
which used a static close>SMA directional filter, not a crossover).

## Step 6 grid summary (run_strategy_grid)

- param_grid: `chop_trend_thresh=[35,38.2,45]` x `ema_slow=[20,30,50]`
- symbols: equity=[QQQ, SPY], crypto=[BTC/USDT, ETH/USDT]
- vol_regime_splits=3
- **total_cells=108, passed_cells=26, pass_fraction=0.241**
- by_asset_class: equity 26/54, crypto 0/54
- by_vol_regime: low 16/36, mid 3/36, high 7/36
- best_cell: chop_trend_thresh=35, ema_slow=50, QQQ low-vol, Sharpe=2.00
- worst_cell: chop_trend_thresh=38.2, ema_slow=30, QQQ high-vol, Sharpe=-0.75

## Single-config validation (best grid cell: chop_trend_thresh=35, ema_slow=50), full sample

| Symbol | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | **num_trades** |
|---|---|---|---|---|---|---|
| QQQ | 1.414 (pass) | 0.025 (pass) | 1.399 (pass) | 1.00 (pass) | 0.348 rel-std (pass) | **3** |
| SPY | 1.264 (pass) | 0.026 (pass) | 1.244 (pass) | 1.00 (pass) | NaN (fail -- inf mean) | **3** |

## Outcome: REJECTED (insufficient sample size despite mechanical validator pass)

Both symbols mechanically pass 4-5/5 validators at the best config, but with
only **3 completed trades over 7.5 years** (2019-2026) each. This is far too
sparse a sample to draw any reliable conclusion -- a Sharpe ratio computed
from 3 trades is dominated by idiosyncratic luck, not a repeatable edge.
This is confirmed by the parameter-sensitivity sweep itself: one nearby grid
cell (chop_trend_thresh=35, ema_slow=20) produced **0 trades**, which
vectorbt's Sharpe computation turns into `inf` (zero-variance division), and
this Inf poisoned SPY's parameter-sensitivity mean/std into NaN. A
strategy whose neighboring parameter cell can produce literally zero trades
is not a robust, tradeable signal -- it is an artifact of a very narrow,
restrictive AND-gate (CHOP<35 AND bullish EMA cross, both conditions rare
simultaneously) that essentially never fires. Rejected despite the
"passing" headline numbers because trade count is a precondition for
validator results to be meaningful, and this repo's grid/validator
machinery does not currently gate on minimum trade count -- a gap worth
addressing in a future iteration (e.g. requiring num_trades>=20 before
trusting Sharpe/MDD at all).
