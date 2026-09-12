# Backtest Report: Dao Global-Trend + Local-Pullback Momentum

**Strategy file:** `strategies/2026-09-12_dao_global_local_trend_pullback.py`
**Knowledge base id:** 2026-09-12-176
**Date:** 2026-09-12

## Hypothesis

Per Tung-Lam Dao's "Momentum Strategies with L1 Filter" (Journal of
Investment Strategies 2014, arXiv:1403.4069): financial time series exhibit
a long-term "global trend" combined with short-term "local trends" that
have mean-reverting properties. This strategy implements that conceptual
decomposition using rolling OLS-slope trend estimation (a directly
implementable proxy for the paper's L1/piecewise-linear trend filter,
which requires a convex solver not available in this environment): long
entry when the global (100-bar) trend is up AND the local (15-bar) trend
has just turned from down back to up (buying the local pullback within an
established global uptrend); exit on local trend reversal, global trend
flip, or a time-stop.

## Single-config validator results (global_window=100, local_window=15)

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Param-sensitivity relative_std |
|--------|--------|-----|-------------------------|----------------------------------|
| QQQ    | 1.024 (PASS, thr 1.0) | 0.162 (PASS, thr 0.25) | 0.921 (PASS, thr 0.5, 128 trades, 5bps) | 0.241 (PASS, thr 0.5) |
| SPY    | 0.850 (FAIL, thr 1.0) | 0.082 (PASS) | -- | -- |

QQQ passes all 4 run validators, though with a narrow Sharpe margin (0.024
above threshold) -- a fragile accept, not a robust one. SPY decisively
fails Sharpe at the identical config, so acceptance scope is QQQ only.
Walk-forward not run (vectorbt.utils.splitting API broken, repo-wide known
issue).

## Grid test summary (run_strategy_grid)

`param_grid={"global_window": [80, 100], "local_window": [10, 15, 20]}`,
symbols `{"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01, 72 total cells.

- **pass_fraction: 0.25** (18/72)
- by_asset_class: equity 18/36 passed; crypto 0/36 decisively rejected.
- by_vol_regime: low 12/24, mid 6/24, high 0/24.
- Best cell: SPY low-vol, global_window=100/local_window=20, Sharpe 3.09.
- Worst cell: QQQ high-vol, global_window=100/local_window=15, Sharpe -0.95.

## Decision: ACCEPT (QQQ only, global_window=100, local_window=15)

QQQ passes Sharpe, MDD, transaction-cost-survival, and
parameter-sensitivity at the chosen config, though the Sharpe pass margin
is narrow (a fragile accept). SPY is explicitly OUT of scope (decisive
Sharpe fail at the same config). Crypto decisively rejected across the
full grid.

## Notes / caveats for future iterations

- This is a proxy implementation of Dao's conceptual global/local trend
  decomposition using rolling OLS slopes, NOT the paper's actual L1
  trend-filtering methodology (which requires a convex-optimization solver
  like cvxpy, not available in this environment). A future loop with
  cvxpy installed could revisit the paper's exact L1-filter construction
  for a potentially stronger/more faithful replication.
- The narrow Sharpe margin (1.024, only 0.024 above threshold) means this
  accept should be treated cautiously -- a future loop's parameter
  sensitivity recheck or longer out-of-sample window could easily flip it.
