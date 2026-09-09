# Backtest report: SOXX/QQQ ratio momentum regime gate on SMA trend

**Strategy file:** `strategies/2026-09-10_soxx_qqq_ratio_trend_gate.py`
**Knowledge base id:** 2026-09-10-044
**Outcome: REJECTED** (near-miss on best config; crypto 0/54, high-vol 0/36 decisive)

## Hypothesis

Per market-phase.com's SOXX/QQQ Ratio guide (visited 2026-09-10, first time
this source was read in this repo): semiconductors are a leading indicator
of risk appetite (long order lead times mean chip demand signals precede
broad economic data). Source's own scoring approach uses the ratio's 4-week
(20-trading-day) rate of change relative to a longer baseline. Tested as a
regime gate on top of a plain SMA trend-following signal: long only when
close>SMA(trend_window) AND the SOXX/QQQ ratio's roc_window-day rate of
change is positive (semis outperforming = rising risk appetite). Applied to
QQQ/SPY (the ratio's natural domain) and, as a cross-asset-class test, to
BTC/ETH.

## Grid test summary (Step 6)

`run_strategy_grid`, param_grid = trend_window∈{50,100,200} ×
roc_window∈{10,20,40}, symbols = {equity: QQQ/SPY, crypto:
BTC/USDT/ETH/USDT}, vol_regime_splits=3, 2018-01-01 to 2024-12-31.

- **total_cells:** 108
- **passed_cells:** 26
- **pass_fraction:** 0.241
- **by_asset_class:** equity 26/54; **crypto 0/54 (decisive fail)** — no semiconductor-sector analogue exists for crypto, and this cross-asset-class application of the gate found zero edge
- **by_vol_regime:** low 18/36, mid 8/36, **high 0/36 (decisive fail)**
- **best_cell:** trend_window=50, roc_window=20, QQQ, low-vol tercile, Sharpe=2.069 (single favorable slice)

## Full-sample single-config sweep (Step 7 prep)

| trend_window | roc_window | QQQ Sharpe | QQQ MDD | SPY Sharpe | SPY MDD |
|---|---|---|---|---|---|
| 100 | 10 | 0.957 | 0.166 | 0.959 | 0.130 |
| 50 | 10 | 0.863 | 0.118 | 0.949 | 0.131 |
| 200 | 10 | 0.847 | 0.188 | 0.950 | 0.119 |
| 200 | 40 | 1.093 | 0.161 | 0.824 | 0.176 |

**Best joint config (trend_window=100, roc_window=10): QQQ Sharpe=0.957,
SPY Sharpe=0.959** — both a near-miss just under the 1.0 threshold, but no
parameter combination cleared 1.0 on BOTH symbols simultaneously (the
single-symbol maxima, e.g. QQQ 1.093 at trend_window=200/roc_window=40,
paired with a failing SPY value of 0.824, so cherry-picking per-symbol
configs would not represent one deployable strategy).

## Decision

**Rejected — near-miss.** No single parameter configuration clears the 1.0
Sharpe threshold jointly on both QQQ and SPY; the closest (trend_window=100,
roc_window=10) misses by 0.04-0.05 on both. Combined with the decisive
crypto failure (0/54) and decisive high-vol-regime failure (0/36), this
does not meet the bar for acceptance, but is flagged as a near-miss worth
a future fine parameter sweep around trend_window=100/roc_window=10 (e.g.
trend_window∈{75,90,100,110,125}, roc_window∈{5,8,10,12,15}) rather than a
fundamentally broken hypothesis.
