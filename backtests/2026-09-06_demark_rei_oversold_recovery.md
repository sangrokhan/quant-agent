# Backtest Report: DeMark Range Expansion Index (REI) oversold-recovery

**Strategy file:** `strategies/2026-09-06_demark_rei_oversold_recovery.py`
**Date:** 2026-09-06
**Symbols tested:** QQQ, SPY (equity); BTC/USDT, ETH/USDT (crypto)
**Timeframe:** 1d

## Hypothesis

Per Enlightened Stock Trading's REI guide
(https://enlightenedstocktrading.com/range-expansion-index/) and
QuantifiedStrategies.com's REI article
(https://www.quantifiedstrategies.com/range-expansion-index/), both newly
visited this iteration, Tom DeMark's Range Expansion Index (1994) is an
arithmetically-calculated momentum oscillator (-100 to +100, overbought
above +60, oversold below -60). The source's own literal rules-based
strategy: "Entry Rule: Buy when the indicator crosses above -60 after
being oversold. Exit Rule: Sell after 100 for four consecutive days or
when REI crosses back below +60." DeMark's exact proprietary formula is
not fully disclosed free; this repo used a transparent, documented
approximation (ratio of "strong" 2-bar high/low changes to total 2-bar
high/low changes, rolling-summed over an 8-bar window) matching the
source's own plain-English description, flagged in the strategy docstring
as an operationalization rather than a literal reproduction.

## Step 6 grid summary (QQQ/SPY/BTC-USDT/ETH-USDT, rei_window in [8, 14]
x oversold_threshold in [-50, -60] x max_hold_days in [7, 10, 15],
vol_regime_splits=3)

```
total_cells: 144
passed_cells: 6
pass_fraction: 0.0417
by_asset_class: equity 6/72, crypto 0/72
by_vol_regime: low 3/48, mid 3/48, high 0/48
best_cell: rei_window=8, oversold_threshold=-50, max_hold_days=7, SPY, low-vol, sharpe=2.125
worst_cell: rei_window=8, oversold_threshold=-60, max_hold_days=10, SPY, mid-vol, sharpe=-1.047
```

## Single-config validation (best grid config: rei_window=8,
oversold_threshold=-50, max_hold_days=7; SPY full sample 2019-01-01 to
2026-09-01, 55 trades)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | -0.162 | >= 1.0 |
| Max drawdown | **FAIL** | 0.332 | <= 0.25 |
| Transaction cost survival (10bps/trade) | **FAIL** | -0.237 net Sharpe | >= 0.5 |
| Walk-forward (4 contiguous splits) | **FAIL** | 0.5 (2/4 splits positive) | >= 0.75 |
| Parameter sensitivity (12-cell SPY sweep) | **FAIL** | relative_std 9.366 | <= 0.5 |

All five validators fail decisively -- a clear reject, not a near-miss.
The grid's best_cell (Sharpe 2.125, low-vol slice) is not representative
of the full-sample performance at all; parameter sensitivity is extreme
(relative_std 9.37, meaning Sharpe swings wildly and unpredictably across
the parameter grid), consistent with the entry/exit rule being highly
sensitive to noise rather than capturing a genuine repeatable edge.

## Decision: REJECTED

Decisive failure across all five validators run. Likely explanation:
the transparent approximation used here for DeMark's proprietary REI
formula (2-bar high/low delta ratio) may not faithfully capture the
original indicator's behavior -- a future revisit, if attempted, should
look for a fuller disclosed/open-source REI implementation (e.g. a
TradingView Pine Script with the exact nested strong/weak classification
logic) rather than reusing this repo's own simplified approximation.
