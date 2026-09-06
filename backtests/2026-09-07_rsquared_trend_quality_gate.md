# 2026-09-07: R-Squared Trend-Quality Gate + Slope-Direction Trend Following (QQQ)

## Hypothesis
Rolling R-squared of a linear regression of close vs. time measures trend
"quality" (near 1.0 = clean orderly trend, near 0 = choppy/noisy). Only
trade the regression slope's direction when R-squared exceeds a threshold
(0.8 default per source), flat otherwise -- filtering out whipsaw-prone
choppy regimes.

Source: multiple corroborating Google SERP snippets -- AlgoKing's Linear
Regression FAQ ("Use R-Squared as a trend quality filter. When R-squared
is high (>0.8), price is moving in a clear trend"), LuxAlgo's "R-squared
Trend Fit" concept, FMZ's multi-layer statistical regression strategy
using an R-squared threshold as one of its gates.

First strategy in this repo using R-squared ITSELF (not just slope/channel)
as a standalone trend-quality gate; distinct from the already-tried
negative-slope mean-reversion variant (2026-09-04-058) and the Linear
Regression Channel breakout-with-volume-confirm strategy already in this
repo.

## Strategy file
`strategies/2026-09-07_rsquared_trend_quality_gate.py`

## Grid test (Step 6)
`param_grid={"reg_window": [15, 20, 30], "r2_threshold": [0.7, 0.8, 0.9]}`,
symbols `{"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **108 total cells, 12 passed (pass_fraction = 0.111)**
- By asset class: equity 12/54, **crypto 0/54 (complete failure)**
- By vol regime: low 9/36 (best), mid 3/36, **high 0/36** (edge
  disappears entirely in high-vol regimes -- somewhat expected, since
  a clean R-squared>threshold trend fit is much harder to sustain in
  choppy/high-vol markets)
- Best cell: `reg_window=20, r2_threshold=0.7`, QQQ, low-vol regime,
  Sharpe 2.032
- Worst cell: `reg_window=30, r2_threshold=0.9`, SPY, high-vol regime,
  Sharpe -1.420

## Single-config validation (Step 7) — QQQ, `reg_window=20, r2_threshold=0.7` (grid's best cell config), full sample

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ FAIL | 0.680 | ≥ 1.0 |
| Max drawdown | ✅ PASS | 0.144 | ≤ 0.25 |
| Transaction cost survival (10bps/trade, 45 trades) | ✅ PASS | 0.592 | ≥ 0.5 |
| Walk-forward (manual 4-split fallback) | ✅ PASS | 4/4 splits positive | ≥ 0.75 |
| Parameter sensitivity (9-combo grid) | ❌ FAIL (decisive) | relative_std 1.526 | ≤ 0.5 |

## Decision: REJECTED

Full-period Sharpe misses threshold (0.68 vs 1.0), and parameter
sensitivity fails decisively (relative_std 1.53, more than 3x the
threshold) -- the strategy's apparent grid-best-cell Sharpe of 2.03 is not
robust; small changes to `reg_window`/`r2_threshold` swing performance
wildly (mean Sharpe across the 9-combo grid only 0.23). Complete crypto
failure (0/54) and complete high-vol-regime failure (0/36) further confirm
the edge is narrow and fragile, concentrated in one specific low-vol/QQQ/
reg_window=20/r2_threshold=0.7 cell rather than a genuine trend-quality
edge. Not flagged for revisit -- the parameter instability is the core
problem, not a fixable threshold choice.
