# Backtest Report: Elder-Ray Bull Power Bullish Divergence — Parameter Refinement Attempt (near-miss 2026-09-06-135)

**Strategy file:** `strategies/2026-09-06_elder_bull_power_bullish_divergence.py` (unchanged code)
**Outcome:** REJECTED (confirms original near-miss does not resolve into a robust edge)

## Background

2026-09-06-135 flagged this as a near-miss worth revisiting: full-sample
Sharpe missed threshold (QQQ 0.882, SPY 0.460) but grid pass_fraction was
unusually balanced across vol regimes (6/8/9 of 48 cells in
low/mid/high), suggesting a possibly genuine but under-parameterized edge.
This iteration ran a local parameter search (`ema_window` in [8,13,21],
`swing_window` in [3,5,8], `max_swing_gap` in [30,40,60], `max_hold_days`
in [10,15,25]) on QQQ to look for a config clearing Sharpe >= 1.0.

## Findings

A naive best-Sharpe search initially returned several `inf`/degenerate
results (0 trades total over the 8.7yr sample -- Sharpe is undefined/
infinite on an all-zero return series, a numerical artifact, not a real
edge). Filtering to configs with at least 30 non-zero-return days, the
best config found was `ema_window=8, swing_window=8, max_swing_gap=40,
max_hold_days=15`:

| Symbol | Trades (signal flips) | Sharpe | Max Drawdown | Net Sharpe (10bps) | Passed |
|---|---|---|---|---|---|
| QQQ | 6 | 1.483 | 0.008 | 1.406 | Nominally passes all 3 |
| SPY | 8 | 0.503 | 0.062 | 0.428 | Fails Sharpe + TC-survival |

QQQ's headline Sharpe of 1.483 is driven by only **6 trades over 8.7 years**
-- far too small a sample to be statistically meaningful (a single lucky or
unlucky trade would swing this metric drastically). A 16-combo local
parameter-sensitivity grid around this config gives
`parameter_sensitivity_relative_std = 0.635` (threshold 0.5) --
**FAILS** -- confirming the metric is fragile: nearby configs range from
Sharpe 0.69 to 1.48 (and several return zero trades entirely), with no
stable plateau of good performance. This is the signature of overfitting
to sparse data, not a real edge.

## Decision: REJECTED

The apparent QQQ "pass" at `ema_window=8/swing_window=8` is not credible:
too few trades (6) to trust the Sharpe estimate, and the parameter
sensitivity check confirms the result is not robust to small parameter
perturbations (relative_std 0.635 > 0.5 threshold, several neighboring
configs are non-tradeable with zero signals). This closes out the
2026-09-06-135 near-miss -- the underlying "Bull Power bullish divergence"
mechanism does not resolve into a statistically robust edge under further
parameter search; not recommended for further refinement attempts.
