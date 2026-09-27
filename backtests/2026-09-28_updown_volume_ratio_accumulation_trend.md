# Up/down Volume Ratio Accumulation-Confirmed Trend-Following (2026-09-28)

**Hypothesis:** LuxAlgo's Up/down Volume Ratio (sum of advancing-bar volume /
sum of declining-bar volume over a rolling window, read against a fixed 1.0
balance level) confirms genuine volume-backed participation behind an
SMA-trend-gated long entry. Source: https://www.luxalgo.com/library/indicator/up-down-volume-ratio/
(read 2026-09-28 via browser_exec direct navigation).

Signal: enter long when close > SMA(trend_window) AND ratio > 1.0 AND
ratio > its own SMA(ratio_trend_len) trend line ("rising accumulation
signature" per source). Exit on trend-gate break, ratio falling below 1.0
(net distribution), or a `max_hold_days` time-stop.

## Step 6 grid summary (trend_window x {30,50,70}, ratio_window x {30,50},
ratio_trend_len x {10,20}; equity QQQ/SPY + crypto BTC/USDT,ETH/USDT;
vol_regime_splits=3; 144 cells total)

- pass_fraction: **0.368** (53/144) -- best this trigger's cycle so far
- by_asset_class: equity 33/72, crypto 20/72
- by_vol_regime: low 36/48, mid 16/48, high 1/48 (usual low-vol-tercile
  concentration, but with genuine mid-vol-tercile representation unlike
  most recent rejects)
- best_cell: trend_window=50, ratio_window=30, ratio_trend_len=10, QQQ,
  low-vol regime, Sharpe 3.09

## Step 7 full-sample validator results (best config: trend_window=50,
ratio_window=30, ratio_trend_len=10, max_hold_days=30)

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 1.42 PASS | 0.145 PASS | 1.21 PASS | 1.00 (4/4) PASS | 0.106 PASS |
| SPY | 0.63 FAIL | 0.154 PASS | 0.35 FAIL | 0.75 (3/4) PASS | 0.196 PASS |
| BTC/USDT | 0.17 FAIL | 0.41 FAIL | -0.04 FAIL | 1.00 PASS | 0.115 PASS |
| ETH/USDT | 0.17 FAIL | 0.51 FAIL | -0.03 FAIL | 1.00 PASS | 0.118 PASS |

Crypto data is 1h bars via ccxt loader (vs daily for equity), producing
4500-4900 "trades" (position flips) over the sample -- decisive churn/cost
failure, consistent with this repo's established pattern that daily-bar
signal logic applied to 1h crypto bars over-trades badly without an
explicit resampling step.

## Decision: **ACCEPT for equity (QQQ only)**; reject SPY (near-miss Sharpe
0.63/TC 0.35) and crypto (decisive Sharpe/MDD/TC fail on both BTC and ETH).

QQQ passes all 5 validators run. Kept strategy file
`strategies/2026-09-28_updown_volume_ratio_accumulation_trend.py` as a live
QQQ-only strategy; SPY/crypto config represents a rejected scope, not a
separate strategy file.
