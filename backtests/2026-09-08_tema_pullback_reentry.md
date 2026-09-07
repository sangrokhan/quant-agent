# TEMA Pullback Re-Entry within Confirmed Uptrend — QQQ & SPY (broad equity scope)

**Strategy file:** `strategies/2026-09-08_tema_pullback_reentry.py`
**Source(s):** https://arrowalgo.com/triple-exponential-moving-average-tema-complete-guide-algorithmic-trading/
**Knowledge base id:** 2026-09-08-056

## Hypothesis

Per arrowalgo.com's TEMA (Triple Exponential Moving Average, Patrick Mulloy)
guide "pullback re-entry" strategy: during a confirmed uptrend (price above
a slow 50-period TEMA), wait for a pullback where price touches the faster
20-period TEMA, then enter long on the next bullish candle. Captures swing
entries within a larger trend. First TEMA-specific construction in this
repo.

## Best config (from grid search)

`fast_period=15, slow_period=100, max_hold_days=10`

## Step 6 grid summary (fast_period x slow_period x max_hold_days, 2 assets x 3 vol regimes)

- total_cells: 96, passed_cells: 23, pass_fraction: 0.240
- by_asset_class: equity 23/48 passed, **crypto 0/48 passed**
- by_vol_regime: low 16/32, mid 6/32, high 1/32
- best_cell: fast_period=15, slow_period=100, max_hold_days=10, QQQ, low-vol, Sharpe 2.732
- worst_cell: fast_period=20, slow_period=50, max_hold_days=15, QQQ, high-vol, Sharpe -0.528

## Step 7 full-sample validators (best config, 2018-01-01 to 2026-09-01)

| Symbol | Sharpe | MDD | Net Sharpe (10bps) | Walk-fwd pass frac | Param sensitivity (rel std) | Verdict |
|---|---|---|---|---|---|---|
| QQQ | 1.122 (pass, thr 1.0) | 0.230 (pass, thr 0.25) | 0.887 (pass, thr 0.5) | 1.00 (pass, thr 0.75) | 0.239 (pass, thr 0.5) | **ALL PASS** |
| SPY | 1.101 (pass, thr 1.0) | 0.178 (pass, thr 0.25) | 0.727 (pass, thr 0.5) | 1.00 (pass, thr 0.75) | 0.285 (pass, thr 0.5) | **ALL PASS** |

## Decision: ACCEPT (broad equity scope — QQQ AND SPY)

Both QQQ and SPY pass every validator run — the second strategy this
session (after 2026-09-08-053 overnight-return) to generalize across both
major equity indices rather than QQQ-only. QQQ's MDD (0.230) is close to
the 0.25 cap, worth noting for future risk-management refinement, but still
passes. Moderate turnover (131/146 trades over 8.7yr) survives 10bps costs
comfortably on both symbols. Crypto rejected outright (0/48 grid cells).
Accepted for QQQ and SPY.
