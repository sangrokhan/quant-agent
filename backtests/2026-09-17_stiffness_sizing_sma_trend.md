# Stiffness Indicator Continuous Sizing Dial — Backtest Report

**Date:** 2026-09-17
**Strategy file:** `strategies/2026-09-17_stiffness_sizing_sma_trend.py`
**Hypothesis:** Stiffness Indicator (Markos Katsanos, Nov 2018 Stocks &
Commodities) — counts how often price closes above a volatility-adjusted
moving-average floor over a rolling window, a naturally bounded [0,100]
measure of trend persistence/strength. Used directly (already bounded, no
z-score needed) as a continuous sizing dial within an SMA(trend_window)
uptrend gate + deadband. First Stiffness Indicator strategy in this repo.

**Source:** https://mkatsanos.com/stiffness-indicator (original author's
site, exact AmiBroker source code, read via browser_exec this iteration).

## Step 6 grid summary (432 cells: trend_window x{30,40,50}, stiffness_period
x{40,60,80}, sensitivity x{0.5,0.7}, deadband x{0.15,0.20}, 2 equity + 2
crypto symbols, vol_regime_splits=3)

- Overall pass_fraction: **0.3542** (153/432)
- By asset class: equity 108/216 (0.500); crypto 45/216 (0.208)
- By vol regime: low 96/144 (0.667); mid 57/144 (0.396); high **0/144
  (0.0)** — fifth consecutive entry this cron trigger with this categorical
  high-vol-regime failure pattern (VPT 2026-09-17-104, LWMA 2026-09-17-105,
  Pivot Point SuperTrend 2026-09-17-106, HA Smoothed 2026-09-17-108, now
  Stiffness).
- Best cell: ETH/USDT, trend_window=40/stiffness_period=40/sensitivity=0.5/
  deadband=0.15, mid-vol regime, Sharpe 2.51.
- Worst cell: QQQ, trend_window=50/stiffness_period=40/sensitivity=0.7/
  deadband=0.2, high-vol regime, Sharpe -0.83.

Best-per-symbol config (by pass_fraction then avg Sharpe):
- QQQ: trend_window=30/stiffness_period=80/sensitivity=0.5/deadband=0.20 → pass_frac 0.667, avg Sharpe 1.078
- SPY: trend_window=40/stiffness_period=80/sensitivity=0.5/deadband=0.15 → pass_frac 0.333, avg Sharpe 1.114
- BTC/USDT: trend_window=50/stiffness_period=80/sensitivity=0.5/deadband=0.20 → pass_frac 0.667, avg Sharpe 1.201
- ETH/USDT: trend_window=40/stiffness_period=80/sensitivity=0.5/deadband=0.15 → pass_frac 0.0, avg Sharpe 1.222 (best config specifically for ETH)

## Step 7 single-config validators (best-per-symbol config; crypto retuned
to leverage_cap=0.3, base_exposure=0.15)

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | All pass? |
|---|---|---|---|---|---|---|
| QQQ | 1.048 (pass) | 0.179 (pass) | 0.771 (pass) | 0.75 (pass) | 0.026 rel-std (pass) | **YES** |
| SPY | 1.066 (pass) | 0.106 (pass) | 0.710 (pass) | 1.0 (pass) | 0.012 rel-std (pass) | **YES** |
| BTC/USDT | 0.215 (fail) | 0.167 (pass) | -0.056 (fail) | 0.75 (pass) | 0.012 rel-std (pass) | NO — decisive |
| ETH/USDT | 0.210 (fail) | 0.123 (pass) | -0.055 (fail) | 1.0 (pass) | 0.016 rel-std (pass) | NO — decisive |

## Decision

**Accepted: QQQ and SPY (equity).** All 5 validators pass at the
grid-optimal per-symbol config for both.

**Rejected: BTC/USDT and ETH/USDT (crypto).** Decisive Sharpe and
transaction-cost-survival failure even after the standard leverage-cap
retune — very high turnover (3254-3952 trades over the sample), driven by
crypto's higher-frequency volatility triggering frequent threshold-crossing
events in the underlying `close > MA2` calculation that Stiffness counts.
This matches the same "turnover doesn't scale down with leverage cap"
pattern already observed for Pivot Point SuperTrend (2026-09-17-106) and HA
Smoothed (2026-09-17-108) this cron trigger.

**Cron-trigger-wide meta-finding (now confirmed across 5 distinct
indicator families):** every continuous-sizing-dial strategy tested this
cron trigger (VPT, LWMA, Pivot Point SuperTrend, HA Smoothed, Stiffness)
shows a categorical 0/144 or 0/192 high-realized-vol-regime grid-cell
failure rate, regardless of the underlying indicator's economic logic. This
strongly suggests the shared mechanic (z-score/tanh-or-bounded dial +
SMA-trend-gate + fixed deadband, tested against a fixed 10bps/trade
transaction-cost model) is itself intrinsically vulnerable to high-vol
whipsaw, independent of indicator choice. A dedicated future iteration
should investigate this as a standalone finding (e.g. does an explicit
high-vol-regime exposure cap/exclusion, rather than continued per-indicator
retunes, generalize as a fix across the whole family) rather than
continuing to discover it piecemeal per new indicator.
