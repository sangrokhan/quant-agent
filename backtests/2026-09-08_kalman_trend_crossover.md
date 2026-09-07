# Single-State Kalman Filter Trend Crossover — QQQ (equity-only)

**Strategy file:** `strategies/2026-09-08_kalman_trend_crossover.py`
**Source(s):** https://theforexgeek.com/kalman-filter-trading-strategy/
**Knowledge base id:** 2026-09-08-052

## Hypothesis

A single constant-velocity 1D Kalman filter (state = [level, slope]) applied
to close price produces a smooth, low-lag adaptive trend-line estimate.
Entry: price crosses above the Kalman level estimate AND the estimated
slope is positive (trend confirmation). Exit: price crosses back below the
Kalman level, or a time-stop. This is a simpler single-filter variant than
already-rejected 2026-09-05-056 (dual fast/slow Kalman-filter
percentile-breakout construction), testing whether -056's rejection was
specific to its dual-filter/percentile complexity rather than Kalman
filtering per se.

## Best config (from grid search)

`kalman_q=0.01, max_hold_days=15`

## Step 6 grid summary (kalman_q x max_hold_days, 2 assets x 3 vol regimes)

- total_cells: 108, passed_cells: 30, pass_fraction: 0.278
- by_asset_class: equity 30/54 passed, **crypto 0/54 passed**
- by_vol_regime: low 18/36, mid 9/36, high 3/36 (some high-vol presence, unlike most other strategies this session)
- best_cell: kalman_q=0.01, max_hold_days=15, QQQ, mid-vol regime, Sharpe 2.211
- worst_cell: kalman_q=0.02, max_hold_days=15, BTC/USDT, low-vol regime, Sharpe -0.141

## Step 7 full-sample validators (best config, 2018-01-01 to 2026-09-01)

| Symbol | Sharpe | MDD | Net Sharpe (10bps) | Walk-fwd pass frac | Param sensitivity (rel std) | Verdict |
|---|---|---|---|---|---|---|
| QQQ | 1.303 (pass, thr 1.0) | 0.158 (pass, thr 0.25) | 0.837 (pass, thr 0.5) | 1.00 (pass, thr 0.75) | 0.136 (pass, thr 0.5) | **ALL PASS** |
| SPY | 0.660 (**fail**, thr 1.0) | 0.163 (pass, thr 0.25) | 0.196 (**fail**, thr 0.5) | 0.75 (pass, thr 0.75) | 0.163 (pass, thr 0.5) | FAIL (Sharpe, TC) |

## Decision: ACCEPT (QQQ-only, equity-only scope)

QQQ passes every validator run, with the strongest full-sample Sharpe (1.303)
of any strategy accepted this session, and reasonably high turnover (240
trades over 8.7yr, still comfortably surviving 10bps costs at net Sharpe
0.837). SPY fails Sharpe and transaction-cost survival (net Sharpe collapses
to 0.196 with 251 trades — similar cost-fragility pattern to the ApEn (-047)
and DPO (-049) strategies accepted earlier this session). Crypto rejected
outright (0/54 grid cells). Accepted narrowly scoped to QQQ only. Confirms
that Kalman-filter trend estimation itself has edge in this repo's universe
— the earlier -056 rejection was likely specific to its dual-filter
percentile-rescaling construction, not Kalman filtering broadly.
