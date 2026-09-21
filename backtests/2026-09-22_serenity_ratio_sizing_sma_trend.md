# Backtest Report: Serenity Ratio Continuous Sizing Dial (SMA200 Trend Gate)

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_serenity_ratio_sizing_sma_trend.py`
**Source:** https://portfoliometrics.net/metrics/serenity-ratio

## Hypothesis

Serenity Ratio = (Rp-Rf) / (Ulcer_Index * Pitfall), Pitfall = CDaR/sigma_p,
CDaR = Conditional Drawdown at Risk (CVaR taken over the drawdown
distribution rather than the return distribution) -- first CDaR-based
construction in this repo. Used to scale exposure on an SMA(200)
trend-following gate, following this repo's risk-ratio-sizing-overlay
template (Sterling, Burke, Pain, MAR/Calmar, Omega, etc).

## Step 6 — Grid test summary

Grid: `serenity_window` in {60, 90, 120}, `serenity_reference` in
{1.0, 1.5, 2.0}, symbols {QQQ, SPY, BTC/USDT, ETH/USDT}, vol_regime_splits=3
(108 cells).

- **pass_fraction: 0.333** (36/108)
- **by_asset_class:** equity 24/54; crypto 12/54
- **by_vol_regime:** low 29/36; mid 7/36; high 0/36 (decisive fail)
- **best_cell:** QQQ, low-vol, `serenity_window=60, serenity_reference=1.0`, Sharpe 2.50

## Step 7 — Single-config validators (grid-best config)

| Symbol | Sharpe | MDD | TC-survival | Param-sensitivity |
|---|---|---|---|---|
| QQQ | **FAIL** 0.803 | PASS 0.181 | PASS 0.753 | PASS 0.003 |
| SPY | **FAIL** 0.837 | PASS 0.119 | PASS 0.776 | PASS 0.035 |
| BTC/USDT | **FAIL** 0.195 | PASS 0.226 | **FAIL** -0.009 | PASS 0.011 |
| ETH/USDT | **FAIL** 0.246 | PASS 0.207 | PASS 0.029 (near-miss/weak) | PASS 0.005 |

Walk-forward skipped for all symbols (pre-existing tooling bug).

## Step 8 — Decision: REJECT (all 4 symbols)

Full-sample Sharpe fails on every symbol (best is SPY 0.837), continuing
this cron trigger's consistent pattern: risk-ratio/trend-gate sizing
overlays applied to genuinely novel indicator constructions produce
decent grid pass_fractions concentrated in low-vol regime slices, but
fall short of the 1.0 full-sample Sharpe bar. Crypto's TC-survival also
fails for BTC/USDT (near-zero net Sharpe from 1760 trades over the
sample, consistent with the hourly-bar overtrading issue seen in other
continuous-sizing-dial crypto attempts this trigger).

This closes out this cron trigger's 10th and final iteration.
