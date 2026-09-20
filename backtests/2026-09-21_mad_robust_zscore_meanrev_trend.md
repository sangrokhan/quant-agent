# 2026-09-21 MAD-Scaled Robust Z-Score Mean-Reversion (Trend-Gated)

**Hypothesis:** A strongly negative robust (median/MAD-based, not
mean/std-based) z-score of daily returns flags a statistical "outlier down
day" more reliably than a classical z-score (resists masking from other
recent extreme moves inflating the std); buying such outlier days, gated by
a long-term uptrend filter, should mean-revert profitably.

**Source:** https://metricgate.com/docs/mad-scaled-z-score/ ("MAD-Scaled
Z-Score: Robust Outlier Detection", May 2026) — statistical methodology
reference for the formula `z_i = (x_i - median(x)) / (1.4826 * MAD(x))`;
the trading rule (trend-gated mean-reversion entry/exit) is this iteration's
own operationalization, not from the source.

**Strategy file:** `strategies/2026-09-21_mad_robust_zscore_meanrev_trend.py`

## Step 6 — Grid test summary (entry_z: [2.5, 3.0, 3.5] x trend_window: [100, 200], SPY/QQQ/BTC/ETH, vol terciles)

- total_cells: 72, passed_cells: 29, **pass_fraction: 0.403**
- by_asset_class: equity 19/36 passed, crypto 10/36 passed (best cross-asset-class result seen this cron trigger)
- by_vol_regime: low 12/24, mid 10/24, high 7/24 (holds up even in high-vol regime, unusually)
- best_cell: entry_z=2.5, trend_window=200, SPY, mid-vol regime, Sharpe=1.93
- worst_cell: entry_z=2.5, trend_window=200, SPY, high-vol regime, Sharpe=-0.65

Promising grid breadth, but this is a per-vol-regime-slice result.

## Full-sample Sharpe sweep (SPY/QQQ, entry_z x trend_window, whole 2019-2026 sample)

SPY(2.5,100)=0.533, SPY(2.5,200)=0.660, SPY(3.0,100)=0.455, SPY(3.0,200)=0.485,
SPY(3.5,100)=0.282, SPY(3.5,200)=0.237, QQQ(2.5,100)=0.583, QQQ(2.5,200)=0.553,
QQQ(3.0,100)=0.375, QQQ(3.0,200)=0.225, QQQ(3.5,100)=0.157, QQQ(3.5,200)=0.409.

No combination clears the 1.0 Sharpe threshold on the full sample -- best is
SPY entry_z=2.5/trend_window=200 at 0.660.

## Step 7 — Single-config validators (best full-sample config: entry_z=2.5, trend_window=200, SPY, full 2019-2026 sample)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.660 | >= 1.0 |
| Max drawdown | PASS | 0.068 | <= 0.25 |
| Transaction cost survival (10bps/trade, 72 trades) | **FAIL** | net Sharpe 0.202 | >= 0.5 |
| Walk-forward (manual 4-split fallback; `RangeSplitter` broken, per repo convention) | **FAIL** | 0.5 (2/4) | >= 0.75 |
| Parameter sensitivity (entry_z sweep 2.5/3.0/3.5) | PASS | relative std 0.377 | <= 0.5 |

## Step 8 — Decision: **REJECTED**

The grid cell breakdown looked unusually promising (40% pass fraction,
holds up in both equity and crypto, and even in the high-vol tercile) but
that result is an artifact of favorable vol-regime slicing -- no
entry_z/trend_window combination clears the primary Sharpe threshold on the
full sample for either SPY or QQQ, and the best full-sample config fails
cost-survival and walk-forward too (72 trades drag heavily on a mean-Sharpe
~0.5-0.6 signal). Strategy file and this report are kept as a record per
RESEARCH_LOOP.md Step 8 (rejected attempt, not a live strategy). Worth
flagging for a future revisit: the grid's cross-asset-class/cross-vol-regime
breadth (only 3rd strategy in this whole KB with any crypto pass_fraction at
all this positive) suggests the underlying idea may have a genuine but
small edge that isn't enough on its own -- combining it as a CONTINUOUS
SIZING dial (this repo's common fix pattern for Sharpe near-misses) rather
than a binary entry/exit could be worth trying.
