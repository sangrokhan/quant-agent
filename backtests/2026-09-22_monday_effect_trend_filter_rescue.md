# Backtest Report: Monday Effect Avoidance + SMA(100) Trend Filter (rescue of 2026-09-22-069)

**Strategy file:** `strategies/2026-09-22_monday_effect_trend_filter_rescue.py`
**Date:** 2026-09-22
**Hypothesis id:** 2026-09-22-070

## Hypothesis

Direct rescue attempt for this same cron trigger's prior rejection
2026-09-22-069 (Monday Effect avoidance, decisive Sharpe+MDD fail both
QQQ/SPY -- being long ~4/5 trading days was essentially "buy-and-hold
minus Mondays"). That report's own suggested next step: use the
Monday-avoidance filter as a SECONDARY overlay within an already-selective
trend-following entry, rather than as the sole standalone signal.
Implemented: close > SMA(trend_window) as the PRIMARY selectivity/
drawdown-control mechanism, combined with a flat-on-Mondays secondary
refinement on top. Source (Monday effect literature) same as
2026-09-22-069.

## Single-Config Validation (Step 7), trend_window=100/avoid_weekdays=(Monday,)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | true 1.109 | **false** 0.978 | 1.0 |
| Max drawdown | true 0.159 | true 0.184 | 0.25 |
| Transaction cost survival (10bps/trade) | true net Sharpe 0.644 (293 trades) | **false** net Sharpe 0.391 (292 trades) | 0.5 |
| Walk-forward (manual 4-equal-slice) | true 1.0 (4/4) | true 0.75 (3/4) | 0.75 |
| Parameter sensitivity (3-value sweep) | true 0.056 | true 0.037 | 0.5 |

## Outcome: ACCEPTED (QQQ only); REJECTED (SPY, near-miss)

**QQQ: all 5 validators pass.** The rescue works decisively: MDD drops
from the base calendar-only strategy's decisive-fail 37.4% down to a
comfortably-passing 15.9%, and Sharpe rises from 0.893 (base, fail) to
1.109 (clears threshold). Trend gate provides the real drawdown protection
the pure calendar filter lacked, and the Monday-avoidance overlay adds a
small further edge on top -- exactly the mechanism the prior rejection's
notes predicted. Parameter sensitivity is unusually strong (relative std
0.056), and walk-forward is a perfect 4/4.

**SPY: still rejected, but a near-miss** -- Sharpe 0.978 is within 2.2% of
the 1.0 threshold, and MDD/walk-forward/param-sensitivity all pass
cleanly. Only TC-survival fails decisively (net Sharpe 0.391 vs. 0.5
threshold) given the high trade count (292) -- SPY's edge here is thinner
than QQQ's and doesn't survive the 10bps/trade cost assumption as well.

**Scope**: ACCEPTED for QQQ only, consistent with this repo's convention
of scoping acceptance to the specific symbol(s) that clear all 5
validators. SPY and crypto (not separately tested at single-config level
this iteration) are out of scope for this exact config; a future loop
could revisit SPY specifically by trying a lower trade-frequency variant
(e.g. widening the trend_window further, or requiring N consecutive
non-Monday uptrend days before entry) to improve its TC-survival margin.
