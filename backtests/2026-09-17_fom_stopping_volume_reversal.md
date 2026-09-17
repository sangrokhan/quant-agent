# Backtest Report: FoM "Stopping Volume" Reversal

**Strategy file:** `strategies/2026-09-17_fom_stopping_volume_reversal.py`
**Source:** https://traders.com/documentation/feedbk_docs/2014/04/traderstips.html
(TASC April 2014 Traders' Tips, "Evidence-Based Support & Resistance" by
Melvin Dickover; TradeStation EasyLanguage credited to Doug McCrary/
TradeStation Securities; read this iteration via `browser_exec`).

## Hypothesis

Dickover's Freedom of Movement (FoM) indicator rescales the day's absolute
% price move and relative-volume z-score each to a 1-10 scale, then takes
VByM = TheVol/TheMove (high when volume is elevated but price barely moved
= "stopping volume"), and finally z-scores VByM itself into FoM. A FoM
spike (>fom_threshold std) occurring while price is in a downtrend (below
SMA(trend_window)) should signal distribution exhaustion / support forming,
marking a mean-reversion long entry. Exit on trend recovery (close crosses
back above the SMA) or a time-stop.

## Grid test summary (Step 6)

`param_grid={"fom_threshold": [1.5,2.0,2.5], "trend_window": [30,50]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, period 2019-01-01..2026-09-01.

- **total_cells:** 72, **passed_cells:** 2, **pass_fraction:** 0.028 (decisive failure)
- **by_asset_class:** equity 2/36 (0.056), crypto 0/36 (0.0)
- **by_vol_regime:** low 2/24, mid 0/24, high 0/24
- **best_cell:** fom_threshold=2.0, trend_window=50, SPY, low-vol regime, Sharpe=1.12 (isolated outlier)
- **worst_cell:** fom_threshold=2.5, trend_window=50, BTC/USDT, low-vol regime, Sharpe=-1.17

## Single-config validators — grid-best config: fom_threshold=2.0, trend_window=50

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | **FAIL** -0.056 | **FAIL** -0.337 |
| Max Drawdown (<=0.25) | **FAIL** 0.373 | **FAIL** 0.370 |
| Transaction cost survival (10bps/trade, net Sharpe>=0.5) | **FAIL** -0.109 (44 trades) | **FAIL** -0.386 (38 trades) |

Decisive rejection: all 3 core validators fail on both symbols with negative
or near-zero Sharpe -- no need to run walk-forward/parameter-sensitivity
given this magnitude of failure (per Step 7's minimum-subset guidance under
time constraints, though workload was "normal" -- the decisive failure here
makes further validation moot).

## Decision: REJECT

The "stopping volume" hypothesis does not hold on daily-bar QQQ/SPY over
2019-2026: negative Sharpe, drawdown above ceiling, and negative net-of-cost
Sharpe on both symbols. Grid pass_fraction of 0.028 (essentially noise-level)
across 72 cells confirms this is not a parameter-tuning issue. Crypto is
decisively rejected too (0/36). Strategy file kept as a record of a
rejected attempt.
