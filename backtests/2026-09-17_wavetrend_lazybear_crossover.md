# Backtest report: WaveTrend [LazyBear] oscillator crossover

**Strategy file:** `strategies/2026-09-17_wavetrend_lazybear_crossover.py`

## Hypothesis

Per LazyBear's WaveTrend [WT] indicator (confirmed via GitHub-hosted exact
Pine Script source, https://github.com/bnvnvnv/fmzstrategies/blob/master/
Indicator-WaveTrend-Oscillator.md, source defaults n1=10/n2=21/obLevel1=60/
osLevel1=-60): ap=HLC3; esa=EMA(ap,n1); d=EMA(|ap-esa|,n1);
ci=(ap-esa)/(0.015*d); tci=EMA(ci,n2); wt1=tci; wt2=SMA(wt1,4). Long entry
when wt1 crosses above wt2 while wt1<osLevel1 (buy confirmation in
oversold territory, per Medium's ALFIL-studios summary); exit when wt1
crosses below wt2 while wt1>obLevel1, or max_hold_days. First WaveTrend
entry in this repo (0 prior matches).

## Grid test summary (Step 6)

`param_grid={"os_level": [-60,-50,-40], "max_hold_days": [10,20,30]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- total_cells: 108, passed_cells: 17, **pass_fraction: 15.7%**
- by_asset_class: equity 16/54; crypto 1/54
- by_vol_regime: low 7/36; mid 4/36; high 6/36
- best_cell: QQQ, low-vol regime, os_level=-40/max_hold_days=30, Sharpe 2.21
- worst_cell: ETH/USDT, mid-vol regime, Sharpe -1.38

## Single-config validators (best grid config: os_level=-40, max_hold_days=30), full sample 2019-2026

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | **FAIL** 0.705 | **FAIL** 0.533 |
| Max Drawdown (<=0.25) | **FAIL** 0.363 | pass 0.239 |
| TC survival (net Sharpe >=0.5, 5bps/trade) | pass 0.688 (27 trades) | pass 0.515 (24 trades) |
| Walk-forward (4-split manual date-split fallback) | pass 0.75 (3/4 splits) | pass 0.75 (3/4 splits) |
| Parameter sensitivity (os_level in [-30..-60], relative_std<=0.5) | pass 0.310 | pass 0.458 |

## Decision: REJECTED

Full-sample Sharpe decisively fails on both QQQ (0.70) and SPY (0.53), well
below the 1.0 threshold, despite good per-vol-regime grid cell performance
(best cell Sharpe 2.21). QQQ additionally fails max drawdown (0.363 vs
0.25 cap). The strategy's crossover-in-extreme-zone construction produces
too few trades (24-27 over 7.5 years) to be robust -- most of the grid's
apparent 15.7% pass_fraction comes from narrow per-vol-regime windows
rather than a durable full-sample edge. Crypto near-decisively rejected
(1/54 grid cells, worst cell Sharpe -1.38).
