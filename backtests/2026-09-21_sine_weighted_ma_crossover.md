# Sine-Weighted Moving Average Dual Crossover — Backtest Report

**Date:** 2026-09-21
**Strategy file:** `strategies/2026-09-21_sine_weighted_ma_crossover.py`
**Outcome:** ACCEPTED (QQQ only, `fast_window=10, slow_window=30, trend_window=100`)

## Hypothesis

Per Linn Software's moving-average reference
(https://www.linnsoft.com/techind/moving-averages-ma, freely available),
the Sine-Weighted Moving Average (SWMA) uses sine-shaped weighting factors
(weight_i ∝ sin(π(i+1)/(n+1))) instead of a linear triangular ramp,
producing a distinct smoothing/lag profile. This strategy tests a standard
fast/slow SWMA dual crossover, gated by a longer SMA trend filter -- the
same pattern already validated for other MA families in this repo (KAMA,
Hull, T3, ZLEMA, etc.), applied here to a genuinely novel weighting scheme
(0 prior SWMA entries).

## Grid test (Step 6)

`param_grid={"fast_window": [10,20], "slow_window": [30,50],
"trend_window": [100,150]}`, symbols `{"equity": ["QQQ","SPY"], "crypto":
["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3`, 2019-01-01 to
2026-09-01.

- **pass_fraction: 0.302** (29/96 cells) — solid, one of the stronger
  results this cron trigger.
- **by_asset_class:** equity 19/48 passed; crypto 10/48 passed.
- **by_vol_regime:** low 25/32; mid 4/32; high 0/32 — works well in
  calm/normal conditions, decisively fails high-vol regime.
- **best_cell:** `fast_window=10, slow_window=30, trend_window=150`, SPY,
  low-vol regime, Sharpe 2.91.
- **worst_cell:** `fast_window=20, slow_window=30, trend_window=100`,
  QQQ, high-vol regime, Sharpe -0.85.

Best full-sample Sharpe per symbol: QQQ **1.405** (fast=10/slow=30/trend=100),
SPY 1.041 (fast=10/slow=50/trend=150), BTC/USDT 0.264, ETH/USDT 0.307 --
crypto doesn't clear the bar on any config tested.

## Single-config validation (QQQ, `fast_window=10, slow_window=30, trend_window=100`)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.405 | ≥1.0 | **PASS** |
| Max drawdown | 0.123 | ≤0.25 | **PASS** |
| Transaction cost survival (5bps/trade, 45 trades) | net Sharpe 1.358 | ≥0.5 | **PASS** |
| Walk-forward (4 contiguous splits) | 1.0 (4/4 positive) | ≥0.75 | **PASS** |
| Parameter sensitivity (fast_window×slow_window sweep) | relative_std 0.240 | ≤0.5 | **PASS** |

All 5 validators pass cleanly, with comfortable margins on every metric.

## Decision

**Accepted for QQQ only** (`fast_window=10, slow_window=30,
trend_window=100`). All 5 validators pass with strong margins. SPY comes
close (full-sample Sharpe 1.041 at a different config) but wasn't the
grid's optimal QQQ config, and crypto shows no usable edge (best 0.307)
-- recorded here so a future loop doesn't over-trust this outside QQQ,
low/mid-vol regimes.
