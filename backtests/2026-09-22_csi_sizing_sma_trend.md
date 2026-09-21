# Backtest Report: CSI Continuous Sizing Dial

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_csi_sizing_sma_trend.py`

## Hypothesis

Direct fix attempt for prior rejection 2026-09-22-026 (CSI discrete
percentile-rank regime gate, failed Sharpe on all 4 symbols): reframe CSI's
own rolling z-score (tanh-squashed) as a continuous exposure dial within an
SMA(trend_window) uptrend gate, instead of a binary gate/no-gate switch.

## Step 6 — Grid test summary

Grid: `trend_window` in {20, 40, 60}, `sensitivity` in {0.3, 0.5, 0.7},
symbols {QQQ, SPY, BTC/USDT, ETH/USDT}, vol_regime_splits=3 (108 cells).

- **pass_fraction: 0.500** (54/108) -- highest of this cron trigger's 3 CSI
  attempts and this iteration's 3 DTI attempts
- **by_asset_class:** equity 24/54; crypto 30/54 (crypto now the STRONGER
  side, unusual for this repo)
- **by_vol_regime:** low 35/36 (nearly universal); mid 16/36; high 3/36
- **best_cell:** QQQ, low-vol, `trend_window=60, sensitivity=0.5`, Sharpe 3.12

## Step 7 — Single-config validators

| Symbol | Sharpe | MDD | TC-survival | Param-sensitivity |
|---|---|---|---|---|
| QQQ | **FAIL** 0.700 | PASS 0.149 | PASS 0.580 | PASS 0.064 |
| SPY | **FAIL** 0.729 | PASS 0.139 | PASS 0.531 | PASS 0.045 |
| BTC/USDT | **FAIL** 0.277 | PASS 0.126 | **FAIL** -0.034 | PASS 0.005 |
| ETH/USDT | **FAIL** 0.309 | PASS 0.185 | **FAIL** -0.015 | PASS 0.014 |

Crypto's TC-survival failure persists (hourly-bar overtrading: 3000+
trades from the continuous dial re-weighting every hour). Equity is a
clean near-miss on Sharpe (0.70-0.73), better than the discrete-gate
version's 0.63-0.88 spread but still short of 1.0.

Walk-forward skipped for all symbols (pre-existing tooling bug).

## Step 8 — Decision: REJECT (all 4 symbols)

Despite the highest grid pass_fraction of any CSI/DTI variant tested this
cron trigger (0.500), full-sample Sharpe still falls short on every symbol.
The continuous-sizing-dial reframing improved MDD and TC-survival broadly
but did not close the Sharpe gap. This CSI indicator family (both discrete
regime-gate and continuous-sizing-dial variants) is now considered
exhausted for this cron trigger without a genuinely new mechanism (e.g. a
faster-timeframe crypto data source to fix the hourly-bar overtrading
problem, which is out of scope for data/loaders.py's current OHLCV-only
design).
