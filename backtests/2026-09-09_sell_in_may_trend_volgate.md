# Backtest Report: Sell in May / Halloween Effect, Trend + Vol-Regime Gated

**Strategy file:** `strategies/2026-09-09_sell_in_may_trend_volgate.py`
**Date:** 2026-09-09
**Source:** Direct refinement of near-miss 2026-09-09-019 (plain Sell in May / Halloween effect)

## Hypothesis

Direct fix for near-miss 2026-09-09-019: the plain calendar-only Sell in
May strategy failed MDD (0.311/0.341) despite an excellent isolated
low-vol-tercile grid cell (Sharpe 2.14), because being long the entire
winter window with no additional filter captures full drawdown exposure
during any winter volatility spike. This iteration adds (a) close >
SMA(trend_window) and (b) trailing realized volatility below its own
rolling percentile threshold, on top of the same Nov-Apr-style calendar
window, gating out winter periods that are actually in a downtrend or
elevated-vol regime.

## Grid test summary (Step 6)

Grid: `trend_window` in [50, 100, 150], `vol_percentile_threshold` in
[0.5, 0.6, 0.7] x symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime
terciles = 108 cells, 2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.120** (13/108 cells passed)
- **By asset class:** equity 13/54, crypto 0/54
- **By vol regime:** low 10/36, mid 0/36, high 3/36
- **Best cell:** SPY, trend_window=100, vol_percentile_threshold=0.6, low-vol regime, Sharpe=1.902

## Single-config validation (Step 7): trend_window=100, vol_percentile_threshold=0.6, full sample 2018-2026

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.781 (FAIL) | 0.647 (FAIL) | >= 1.0 |
| Max drawdown | 0.143 (**PASS, fixed from 0.311**) | 0.124 (**PASS, fixed from 0.341**) | <= 0.25 |
| Net Sharpe after costs (10bps/trade) | 0.662 (PASS) | 0.503 (PASS, marginal) | >= 0.5 |
| Walk-forward pass fraction (4 slices) | 0.75 (PASS, marginal) | 0.75 (PASS, marginal) | >= 0.75 |
| Parameter sensitivity relative std | 0.139 (PASS) | 0.378 (PASS) | <= 0.5 |
| Num trades | 58 | 56 | -- |

## Comparison to plain calendar-only predecessor (2026-09-09-019)

| | Plain calendar | Trend+vol-gated |
|---|---|---|
| QQQ Sharpe | 0.414 (fail) | 0.781 (fail, improved) |
| QQQ MDD | 0.311 (**fail**) | 0.143 (**pass, fixed**) |
| SPY Sharpe | 0.334 (fail) | 0.647 (fail, improved) |
| SPY MDD | 0.341 (**fail**) | 0.124 (**pass, fixed**) |
| Validators passing | 2/5 each | 4/5 each |

## Decision

**Reject, but a clear near-miss and meaningful improvement.** The
trend+vol-regime gate fixed the predecessor's MDD failure exactly as
hypothesized (both symbols now comfortably pass MDD) and 4 of 5
validators now pass for both symbols. Sharpe remains the sole failure
(0.781 QQQ, 0.647 SPY, both below the 1.0 threshold) -- the added filters
reduce time-in-market enough to damp both drawdown and return
proportionally, similar to the pattern seen in this cron trigger's other
near-miss (HMM 3-state regime filter, 2026-09-09-014). A future iteration
could try a looser vol-percentile threshold (more time invested) or
combining the calendar window with an already-accepted trend-following
signal (e.g. HMA crossover or 52-week-high momentum) rather than a plain
SMA trend check, to recover Sharpe without reintroducing the MDD blowup.
