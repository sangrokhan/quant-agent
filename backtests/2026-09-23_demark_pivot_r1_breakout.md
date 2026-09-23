# DeMark conditional pivot R1 breakout, trend-gated (REJECTED)

**Hypothesis:** per Senzoukria's DeMark Pivots documentation
(https://senzoukria.com/indicators/demark-pivots), Tom DeMark's pivot
formula is conditional on the prior session's own close-vs-open direction
(unlike fixed Camarilla/Woodie/standard formulas). Long entry on close
breaking above yesterday's DeMark R1, gated by close>SMA(trend_window);
exit on close falling back below the day's own DeMark pivot, trend-gate
break, or a max_hold_days time-stop. First DeMark-pivot strategy in this
repo (0 prior KB hits).

Strategy file: `strategies/2026-09-23_demark_pivot_r1_breakout.py`

## Step 6 grid summary (trend_window in [100,200] x max_hold_days in [5,10], equity QQQ/SPY + crypto BTC/USDT, vol_regime_splits=3)

- total_cells: 36, passed_cells: 12, **pass_fraction: 0.333**
- by_asset_class: equity 12/24 passed, crypto 0/12 (decisive crypto fail)
- by_vol_regime: low 8/12, mid 4/12, high 0/12 — edge concentrated in low/mid-vol
- best_cell: trend_window=100, max_hold_days=5, QQQ, low-vol, Sharpe 2.361
- worst_cell: trend_window=100, max_hold_days=10, QQQ, high-vol, Sharpe -0.436

## Step 7 single-config validation (best config: trend_window=100, max_hold_days=5, full sample 2019-01-01 to 2026-09-01)

| Symbol | Trades | Sharpe | MDD | TC-survival net Sharpe | Param sensitivity (rel std) |
|---|---|---|---|---|---|
| SPY | 276 | 0.566 (FAIL) | 0.154 (PASS) | **-0.017 (FAIL, thr 0.5)** | 0.066 (PASS) |
| QQQ | 277 | 0.859 (FAIL) | 0.134 (PASS) | 0.313 (FAIL, thr 0.5) | 0.219 (PASS) |

Walk-forward not run (light workload; the decisive TC-cost failure already
disqualifies the config).

## Decision: REJECTED

The pivot's daily-bar frequency (one R1/pivot per session) generates a very
high trade count (276-277 over the sample) because the short 5-day
time-stop and daily pivot recompute churn positions constantly. Both
symbols fail full-sample Sharpe (0.57-0.86 vs 1.0 threshold) and decisively
fail net-of-cost Sharpe -- SPY's net Sharpe actually turns *negative*
(-0.017) once the ~10bps/trade cost assumption is applied to 276 trades.
The promising grid-cell Sharpes (up to 2.36) come from low-vol-tercile
subsets that don't survive transaction costs at the strategy's natural
turnover rate. Crypto fails decisively (0/12). Not accepted.
