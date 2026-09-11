# Backtest Report: LRC (Linear Regression Channel) Pullback Continuation

**Strategy file:** `strategies/2026-09-12_lrc_pullback_continuation.py` (REJECTED — kept as rejected-attempt record)
**Date:** 2026-09-12
**Source:** https://trendsandbreakouts.com/linear-regression-channel ("Practical Rules for Entries, Exits, Stops, and Filters")

## Hypothesis

Per the source's own stated practical rule set: "Trend filter: Only take longs when
the LRC slope is positive and price is above the regression line... Entry for
continuation: Enter on a pullback toward the regression line that holds...
Exit logic: ... in trends trail using the regression line."

Operationalized as: rolling least-squares regression line over `lrc_window` bars;
entry when slope>0, close>regline, and price touched/dipped to the regline within
the last `pullback_window` bars then reclaimed it; exit on close<regline, slope
flipping negative, or `max_hold_days` time-stop.

## Step 6 — Grid test summary (param x asset-class x vol-regime)

Grid: `lrc_window` in [30,50,80] x `pullback_window` in [3,5,8], symbols
equity=[QQQ,SPY] / crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3 (108 cells total).

```
total_cells: 108, passed_cells: 14, pass_fraction: 0.130
by_asset_class: equity 14/54 passed; crypto 0/54 passed (decisive reject)
by_vol_regime:  low 13/36 passed; mid 0/36 passed; high 1/36 passed
best_cell: lrc_window=80, pullback_window=8, QQQ, low-vol, Sharpe=1.91
worst_cell: lrc_window=50, pullback_window=3, QQQ, high-vol, Sharpe=-0.99
```

The pattern strongly concentrates in equity/low-vol-regime cells only; crypto and
mid/high-vol equity regimes fail decisively.

## Step 7 — Single-config validation (best grid config: lrc_window=80, pullback_window=8, slope_lag=5, max_hold_days=15)

Full 2018-01-01..2026-09-01 sample (not restricted to low-vol regime):

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe (full-sample) | 0.386 FAIL | 0.731 FAIL | >= 1.0 |
| Max Drawdown | 0.168 PASS | 0.115 PASS | <= 0.25 |
| TC survival (10bps/trade) | 0.225 FAIL | 0.407 FAIL | net Sharpe >= 0.5 |
| Walk-forward (4-split) | 0.75 PASS | 0.75 PASS | >= 0.75 |
| Param sensitivity (rel std) | 0.471 PASS | 1.252 FAIL | <= 0.5 |

## Step 8 — Decision: **REJECT**

Both QQQ and SPY fail full-sample Sharpe and post-cost survival. The grid's
"low-vol regime" edge (best cell Sharpe 1.91) does not generalize to the full
sample or to other vol regimes — the pullback-reclaim signal appears too
low-frequency/low-edge once diluted across mixed-vol conditions and trading
costs. SPY additionally fails parameter sensitivity (relative std 1.25),
indicating fragile edge dependent on exact window choice. Crypto rejected
decisively (0/54 grid cells).
