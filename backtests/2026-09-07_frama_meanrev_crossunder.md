# FRAMA Crossunder Mean-Reversion — Backtest Report

**Date:** 2026-09-07 (2nd iteration this cron trigger)
**Strategy file:** `strategies/2026-09-07_frama_meanrev_crossunder.py`
**Source:** https://www.quantifiedstrategies.com/fractal-adaptive-moving-average-frama/

## Hypothesis

The source's own SPY backtest of a plain N-day moving-average crossover
found the MEAN-REVERSION direction (buy on close crossing below the
average, sell on cross back above) consistently beat the TREND-FOLLOWING
direction across every tested period (5-200 days), e.g. period=25:
mean-reversion CAGR 8.66% vs trend-following CAGR 1.04%. This strategy
swaps in Ehlers' FRAMA (adaptive smoothing via local fractal dimension)
as the reference average, keeping the source's discovered mean-reversion
direction, hypothesizing FRAMA's trend-tracking/chop-flattening behavior
gives cleaner mean-reversion entries than a fixed-span SMA.

## Grid test (Step 6)

`param_grid`: frama_window∈{10,16,26}, max_hold_days∈{5,10}; symbols:
equity {QQQ,SPY}, crypto {BTC/USDT,ETH/USDT}; vol_regime_splits=3; period
2018-01-01..2026-09-01.

- **pass_fraction: 0.167** (12/72 cells)
- by_asset_class: equity 12/36, **crypto 0/36** (decisive crypto failure)
- by_vol_regime: low 11/24, mid 0/24, high 1/24 — edge almost entirely
  confined to the low-vol tercile
- best_cell: SPY, frama_window=10, max_hold_days=10, low-vol regime,
  Sharpe 1.80
- worst_cell: SPY, frama_window=16, max_hold_days=5, mid-vol regime,
  Sharpe -0.43

## Single-config validation (Step 7): SPY, frama_window=10, max_hold_days=10

Full period 2018-01-01..2026-09-01:

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.565 | ≥1.0 | **FAIL** |
| Max drawdown | 21.6% | ≤25% | pass |
| Transaction-cost survival (507 trades, 10bps) | net Sharpe 0.052 | ≥0.5 | **FAIL (decisive)** |
| Walk-forward (manual 4-split) | 0.75 pass_fraction (3/4 splits positive) | ≥0.75 | pass |
| Parameter sensitivity (6-point frama_window sweep) | rel std 0.377 | ≤0.5 | pass |

## Decision: **REJECT**

Full-sample Sharpe misses (0.565 vs 1.0) and transaction-cost survival
fails decisively: 507 trades over ~8.7 years (roughly 1 trade every 4
trading days) at a modest 10bps/trade cost erodes essentially the entire
gross edge (net Sharpe collapses to 0.05). The FRAMA-based mean-reversion
crossunder trades far more frequently than a fixed-span-MA mean-reversion
rule would (FRAMA tracks price tightly in trends, producing many small
crossunder/crossover flickers rather than clean regime-length signals),
which is the opposite of what the adaptive-smoothing hypothesis expected.
Grid pass_fraction (0.167) again shows the edge concentrated in the
low-vol tercile only, and crypto fails categorically (0/36).
