# Weinberg TRI ("The Range Indicator") Efficient-Travel Trend — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_weinberg_tri_efficient_travel_trend.py`
**Source:** https://www.luxalgo.com/library/indicator/the-range-indicator/

## Hypothesis

Jack Weinberg's TRI ("The Range Indicator") sets each bar's true range against
its close-to-close progress, normalizes stochastic-style over a lookback,
and smooths into a bounded 0-100 line. Low readings ("efficient travel")
are, per the source's own words, "the environment Weinberg's study
associated with trending conditions"; high readings ("churn") were read by
Weinberg as a trend-EXHAUSTION warning. Since TRI itself carries no
directional information, we gate a long entry on TRI crossing below
`low_threshold` (fresh efficient travel) AND price above a
`trend_window`-day SMA (directional trend filter). Exit on TRI crossing
back above `high_threshold` (churn returning), trend filter breaking, or a
`max_hold_days` time-stop.

## Grid test (Step 6)

`validation/grid_test.py::run_strategy_grid`,
`low_threshold in {15,20,30}` x `trend_window in {30,50,100}`,
symbols equity `{QQQ, SPY}` / crypto `{BTC/USDT, ETH/USDT}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.315 (34/108)**
- by_asset_class: equity 26/54, crypto 8/54
- by_vol_regime: low 25/36, mid 8/36, high 1/36
- best_cell: QQQ, low_threshold=15, trend_window=50, low-vol, Sharpe 2.97
- worst_cell: QQQ, low_threshold=30, trend_window=100, high-vol, Sharpe -0.53

## Single-config validators (config: low_threshold=15, trend_window=50, full sample 2019-2026)

| Validator | QQQ | SPY | Threshold | Passed |
|---|---|---|---|---|
| Sharpe ratio | 1.125 | 1.131 | >= 1.0 | **pass (both)** |
| Max drawdown | 0.178 | 0.183 | <= 0.25 | pass (both) |
| Transaction cost survival (10bps/trade) | net Sharpe 1.006 (85 trades) | net Sharpe 0.980 (74 trades) | >= 0.5 | pass (both) |
| Walk-forward (4 splits, QQQ) | per-split Sharpe [0.70, -0.28, 2.33, 1.04], pass_fraction 0.75 | -- | >= 0.75 | pass (exactly at threshold) |
| Parameter sensitivity (QQQ, 9-combo grid) | relative_std 0.137 | -- | <= 0.5 | pass |

Crypto (BTC/USDT full sample) Sharpe: 0.227 — fails, consistent with the
grid's low crypto pass rate (8/54, mostly noise).

## Decision

**Accepted for equity (QQQ, SPY)**. All validators pass, though walk-forward
passes exactly at the 0.75 threshold (3 of 4 splits positive, one split
mildly negative during a choppier sub-period) — a real but not overwhelming
margin, worth flagging for a future loop's parameter-sensitivity re-check if
more out-of-sample data becomes available. **Rejected for crypto** —
full-sample Sharpe well under 1.0 and only 8/54 grid cells pass, mostly
scattered rather than concentrated.

## Notes for future loops

TRI's stated purpose (distinguishing "efficient travel" from "churn") is
conceptually similar to the Choppiness Index already tested extensively in
this repo, but uses a genuinely different ratio construction (true-range
vs. close-to-close progress, stochastic-normalized, rather than the
Choppiness Index's ATR-sum/range-ratio). The equity result here is broadly
comparable in strength to this repo's better Choppiness-Index-gated
entries. A future loop could try combining TRI with a different directional
filter (e.g. Vortex or TSI, both already live in `strategies/`) instead of
a plain SMA, or test the churn/high-threshold side as an explicit exit-only
overlay on an existing accepted trend strategy.
