# Backtest Report: Dorsey Inertia (RVI smoothed via rolling linear regression), Midline Crossover

**Strategy file:** `strategies/2026-09-12_dorsey_inertia_midline_cross.py` (REJECTED — kept as rejected-attempt record)
**Date:** 2026-09-12
**Source:** Donald Dorsey, "Refining the Relative Volatility Index" (Stocks & Commodities, Sep 1995), via https://www.tradingview.com/script/bzxmXFGd-Dorsey-Inertia/ and https://stonehillforex.com/dorsey-inertia-as-a-confirmation-indicator/

## Hypothesis

RVI (Dorsey's up/down-std-dev-ratio momentum indicator) smoothed with a
rolling linear-regression fit ("inertia") crossing the 50 midline signals
trend direction: "Long: Signal line crosses above the midline (50). Short:
Signal line crosses below the midline (50)." Default settings per
StonehillForex: RVIPeriod=10, AvgPeriod=14, SmoothingPeriod=20. Distinct from
prior plain-RVI strategy (2026-09-05-003, asymmetric 50/40 thresholds, no
linear-regression smoothing step).

## Step 6 — Grid test summary

Grid: `smoothing_period` in [10,20,30] x `rvi_period` in [7,10,14], symbols
equity=[QQQ,SPY] / crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3 (108 cells).

```
total_cells: 108, passed_cells: 25, pass_fraction: 0.231
by_asset_class: equity 25/54 passed; crypto 0/54 (decisive reject)
by_vol_regime:  low 18/36; mid 5/36; high 2/36
best_cell: smoothing_period=20, rvi_period=10 (source defaults), SPY, low-vol, Sharpe=2.99
worst_cell: smoothing_period=20, rvi_period=7, SPY, mid-vol, Sharpe=-0.05
```

## Step 7 — Single-config validation (default params: rvi_period=10, avg_period=14, smoothing_period=20, max_hold_days=20)

Full 2018-01-01..2026-09-01 sample:

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe (full-sample) | 0.264 FAIL | 0.549 FAIL | >= 1.0 |
| Max Drawdown | 0.313 FAIL | 0.330 FAIL | <= 0.25 |
| TC survival (10bps/trade) | 0.201 FAIL | 0.447 FAIL | net Sharpe >= 0.5 |
| Walk-forward (4-split) | 0.75 PASS | 1.00 PASS | >= 0.75 |
| Param sensitivity (rel std) | 0.302 PASS | 0.245 PASS | <= 0.5 |

## Step 8 — Decision: **REJECT**

Both QQQ and SPY fail full-sample Sharpe, max drawdown, and post-cost
survival despite passing walk-forward and parameter sensitivity. Grid's
strong low-vol-regime edge (best cell Sharpe 2.99, source's own default
params) does not generalize once the full-sample mixed-regime period is
tested — MDD blows through the 25% threshold on both symbols (0.31/0.33),
consistent with the strategy being a slow trend-persistence signal that
gets whipsawed and drawn down hard in higher-vol regimes even though it
stays net-long the right direction on average (hence walk-forward pass).
Crypto rejected decisively (0/54 grid cells).
