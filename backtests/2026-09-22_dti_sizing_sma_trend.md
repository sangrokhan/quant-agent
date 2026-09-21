# Backtest Report: DTI Continuous Sizing Dial (SMA Trend Gate)

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_dti_sizing_sma_trend.py`

## Hypothesis

Reframe DTI/100 (naturally bounded [-1,+1]) as a continuous exposure-sizing
dial within an SMA(trend_window) uptrend gate, rather than the binary
zero-line-crossover entry/exit tested in 2026-09-22-023 (SPY accepted, QQQ
near-miss rejected, crypto decisively rejected). Follows this repo's
established binary-to-continuous-sizing-dial rescue pattern.

## Step 6 — Grid test summary

Grid: `trend_window` in {20, 40, 60}, `sensitivity` in {0.4, 0.6, 0.8},
symbols {QQQ, SPY, BTC/USDT, ETH/USDT}, vol_regime_splits=3 (108 cells).

- **pass_fraction: 0.417** (45/108) -- notably higher than the binary
  version's 0.278, and crypto now shows real signal (18/54 pass, vs the
  binary version's 3/54)
- **by_asset_class:** equity 27/54; crypto 18/54
- **by_vol_regime:** low 30/36; mid 14/36; high 1/36 (still decisively
  disabled in high-vol, consistent with the underlying trend-following
  signal)
- **best_cell:** QQQ, low-vol, `trend_window=60, sensitivity=0.4`, Sharpe 2.53

## Step 7 — Single-config validators

| Symbol | Config | Sharpe | MDD | TC-survival | Param-sensitivity |
|---|---|---|---|---|---|
| QQQ | trend_window=60, sensitivity=0.4 | **FAIL** 0.920 | PASS 0.121 | PASS 0.799 | PASS 0.005 |
| SPY | trend_window=60, sensitivity=0.4 | **FAIL** 0.803 | PASS 0.127 | PASS 0.622 | PASS 0.020 |
| BTC/USDT | trend_window=40, sensitivity=0.4, leverage_cap=0.5 | **FAIL** 0.166 | PASS 0.223 | **FAIL** -0.046 | PASS 0.012 |
| ETH/USDT | trend_window=40, sensitivity=0.4, leverage_cap=0.5 | **FAIL** 0.176 | PASS 0.249 (razor-thin) | **FAIL** -0.038 | PASS 0.023 |

Crypto's TC-survival failure is severe: 3309/3279 trades over the sample
(vs. equity's 58-63) because `load_crypto`'s default interval is hourly,
so the continuous dial re-weights exposure far more often intraday than
the equivalent daily-bar equity signal -- net-of-cost Sharpe goes slightly
negative.

Walk-forward skipped for all symbols (pre-existing tooling bug: installed
vectorbt's `vectorbt.utils` lacks `splitting`, not a strategy defect).

## Step 8 — Decision: REJECT (all 4 symbols)

Full-sample Sharpe fails on every symbol despite a respectable grid
pass_fraction (0.417) concentrated in low/mid-vol regime slices --
confirming the same regime-concentration pattern already seen in this
cron trigger's other near-misses (CIDI, ungated DTI). Crypto additionally
fails decisively on transaction-cost survival due to the hourly-bar
overtrading effect. No config found this iteration that clears the
full-sample Sharpe bar; the plain ungated DTI's SPY accept (2026-09-22-023)
remains the only live strategy from this indicator family this cron trigger.
