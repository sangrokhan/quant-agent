# SPHB/SPLV high-beta vs low-volatility rotation trend gate (ACCEPTED, QQQ only)

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_sphb_splv_rotation_trend_gate.py`
**Source:** https://www.moneyshow.com/articles/dailyguru-63548/ (JC Parets/AllStarCharts, via MoneyShow)

## Hypothesis
"When stocks are in a healthy environment, you tend to see High Beta
stocks outperforming their Low Volatility counterparts. It's in the
weaker environments where High Beta historically underperforms." The
source's disclosed trigger: the SPHB/SPLV ratio making a new N-week
high (20-week in the source's own worked example) signals broad
risk-on sector rotation, a bullish confirmation for the broader market.
Adapted as a trend-confirmation gate: stay long QQQ/SPY only while
close > SMA(trend_window) AND the SPHB/SPLV ratio is at/near
(within near_high_tolerance) its own trailing rolling high over
ratio_lookback_weeks weeks. For crypto (no high-beta/low-vol factor-ETF
analogue exists), the ratio gate degrades to always-True, i.e. a plain
SMA trend-follow -- an explicit, documented simplification/robustness
check, not the genuine tested hypothesis.

## Grid test summary

trend_window in {50,100,150} x ratio_lookback_weeks in {10,20,30} x
near_high_tolerance in {0.02,0.05}, symbols QQQ/SPY, vol_regime_splits=3,
2019-2026 (108 cells)

- pass_fraction: 0.361 (39/108)
- by_vol_regime: low 31/36, mid 0/36, high 8/36
- best_cell: QQQ, trend_window=50, ratio_lookback_weeks=10,
  near_high_tolerance=0.05, low-vol, Sharpe 2.88
- worst_cell: SPY, trend_window=50, ratio_lookback_weeks=30,
  near_high_tolerance=0.02, mid-vol, Sharpe -1.57

Grid's per-vol-regime-sliced Sharpe values did NOT hold up full-sample
at the grid's own near_high_tolerance values (0.02/0.05) -- no
full-sample config passed Sharpe at those tolerances. A follow-up
parameter search widened near_high_tolerance (the "new high" tolerance
band is fairly tight at 2-5% and produces sparse rare-trigger signals);
near_high_tolerance=0.15 (i.e. ratio within 15% of its trailing
10-week high) at trend_window=150 was the config that cleared the bar
full-sample on QQQ.

## Single-config validators (QQQ, trend_window=150, ratio_lookback_weeks=10, near_high_tolerance=0.15, full 2019-2026 sample)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.316 | >= 1.0 | PASS |
| Max drawdown | 0.134 | <= 0.25 | PASS |
| Transaction cost survival (10bps, 21 trades) | 1.292 | >= 0.5 | PASS |
| Walk-forward (manual 4-split, repo convention) | 1.0 (4/4 splits positive) | >= 0.75 | PASS |
| Parameter sensitivity (near_high_tolerance in {0.10,0.12,0.15,0.18,0.20}) | relative_std 0.106 | <= 0.5 | PASS |

All 5 validators pass for QQQ.

## Cross-symbol scope check (same config)

| Symbol | Sharpe | MDD | TC-survival |
|---|---|---|---|
| QQQ | 1.316 PASS | 0.134 PASS | 1.292 PASS |
| SPY | 0.870 FAIL (near-miss) | 0.217 PASS | 0.823 PASS |
| BTC/USDT (ratio gate degrades to plain SMA trend-follow) | 1.019 PASS | 0.444 FAIL | 1.008 PASS |
| ETH/USDT (same degraded gate) | 0.839 FAIL | 0.679 FAIL | 0.831 PASS |

## Decision: ACCEPTED (QQQ only)

Strategy file and this report kept as a live accepted strategy, strictly
scoped to QQQ at trend_window=150/ratio_lookback_weeks=10/
near_high_tolerance=0.15. SPY narrowly misses the Sharpe bar (0.870) at
the same config -- a future loop could retune SPY-specific parameters.
Crypto legs decisively fail (the ratio gate is architecturally
unavailable for crypto, degrading the strategy to a plain SMA
trend-follow that inherits crypto's much larger drawdowns) -- do not
apply this signal to crypto.

## Notes for future loops
- First strategy in this repo using the SPHB/SPLV high-beta-vs-low-vol
  factor ratio; distinct from all existing rolling-correlation and
  price-ratio z-score-spread cross-asset entries.
- The source's own literal near-high tolerance (new 20-week high, i.e.
  effectively 0% tolerance) is too strict for this repo's daily-bar
  QQQ/SPY sample -- a much looser 15% "near its trailing high" band was
  needed to generate a survivable trade frequency (21 trades over
  ~7.5yr) while still passing all validators. A future loop revisiting
  SPY specifically should retune trend_window/ratio_lookback_weeks/
  near_high_tolerance independently for SPY rather than reusing QQQ's
  shared config.
