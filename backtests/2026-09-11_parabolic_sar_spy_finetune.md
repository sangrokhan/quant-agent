# Backtest Report: Parabolic SAR Trend-Filtered — SPY Fine-Tune (near-miss investigation)

**Date:** 2026-09-11
**Strategy file:** `strategies/2026-09-04_parabolic_sar_trend_filter.py` (reused;
already accepted for QQQ at `af_step=0.03, trend_window=200`; SPY recorded
as a near-miss at that config in 2026-09-04-042, Sharpe 0.853 vs 1.0).

## Hypothesis

Direct fix attempt for 2026-09-04-042's SPY near-miss, following the same
methodology that successfully rescued the Vortex Indicator's SPY near-miss
this trigger (2026-09-11-107): full-sample sweep `af_step` in
{0.01,0.02,0.03,0.04} x `trend_window` in {50,100,150,200} (16 combos,
wider than the original 6-combo QQQ-focused sweep) to check whether any
SPY-specific parameter combination clears Sharpe >= 1.0.

## Full-sample sweep results (SPY, 2019-01-01 to 2026-09-01)

Sorted by Sharpe descending (best first):

| af_step | trend_window | Sharpe | MDD | Sharpe pass |
|---|---|---|---|---|
| 0.03 | 50 | 0.900 | 0.170 | FAIL |
| 0.02 | 50 | 0.869 | 0.121 | FAIL |
| 0.03 | 200 | 0.853 | 0.157 | FAIL (= original near-miss config) |
| 0.02 | 200 | 0.809 | 0.153 | FAIL |
| 0.04 | 200 | 0.809 | 0.145 | FAIL |
| ... (11 more combos, all Sharpe < 0.78) | | | | FAIL |

## Decision: REJECT (SPY, all 16 combos)

Unlike the Vortex Indicator SPY near-miss (2026-09-11-107, successfully
rescued this trigger), NO parameter combination across a 16-cell
`af_step` x `trend_window` sweep clears Sharpe >= 1.0 for SPY — even the
best combo (af_step=0.03, trend_window=50, Sharpe 0.900) falls 10% short.
This is a genuine, non-fixable near-miss for SPY specifically: Parabolic
SAR's stop-and-reverse mechanism appears to suit QQQ's tech-heavy trend
character better than SPY's broader/steadier trend profile, consistent
with several other QQQ-only-accepted strategies in this repo (Vortex
originally, 52-week-high momentum, dual-EMA family) before per-symbol
fine-tuning is applied — but here fine-tuning genuinely does not close
the gap. `strategies/2026-09-04_parabolic_sar_trend_filter.py`'s live
status remains unchanged: accepted for QQQ only (af_step=0.03,
trend_window=200); SPY confirmed as a durable near-miss, not worth
revisiting again without a materially different mechanism (e.g. a
volatility-adaptive acceleration factor) rather than further grid
fine-tuning of the existing fixed-af_step design.
