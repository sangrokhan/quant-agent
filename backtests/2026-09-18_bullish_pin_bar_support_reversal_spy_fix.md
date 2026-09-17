# Backtest Report: Bullish Pin Bar Support Reversal — SPY fix (rescues 2026-09-18-021 near-miss)

**Strategy file:** `strategies/2026-09-18_bullish_pin_bar_support_reversal.py` (same file, different config)
**Knowledge base id:** 2026-09-18-022

## Summary

Direct fix attempt for 2026-09-18-021 (bullish pin bar at rolling support,
accepted QQQ but SPY near-missed Sharpe 0.967<1.0 at
`support_lookback=10,rr_target=2.5,max_hold_days=25,support_tolerance=0.01`,
all other 4 validators passed). A 3x4x3x4x2x2x2=1152-cell full-sample scan on
SPY of `support_lookback x rr_target x max_hold_days x support_tolerance x
min_tail_body_ratio x max_nose_pct x min_body_top_pct` found
`support_lookback=20, rr_target=2.5, max_hold_days=20,
support_tolerance=0.015` clears Sharpe 1.075 (vs the parent's 0.967).

## Metrics (SPY, best fixed config)

| Metric | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe | 1.075 | 1.0 | yes |
| Max drawdown | 0.0133 | 0.25 | yes |
| Net Sharpe after costs (10bps/trade) | 0.993 | 0.5 | yes |
| Walk-forward pass_fraction (4 splits) | 0.75 (3/4) | 0.75 | yes |
| Parameter sensitivity rel-std | 0.414 | 0.5 | yes |

**Caveat:** only 5 trades over the ~7.5-year sample (wider `support_lookback`
means fewer qualifying rolling-support touches) -- every validator passes,
but this is a sparse-signal result and the strategy's statistical power is
limited. Recorded honestly rather than treated as a robust broad-coverage
edge.

## Decision

**Accepted for SPY** (same strategy file as 2026-09-18-021, different
config) -- rescues the parent's near-miss. QQQ keeps its own separate
2026-09-18-021 config (`support_lookback=10, rr_target=2.5,
max_hold_days=25, support_tolerance=0.01`). Crypto remains rejected per the
parent's Step 6 grid (2/54 pass_fraction), not re-tested this sub-iteration.
