# Backtest Report: Sell-in-May + SMA(100) Trend Filter (rescue of 2026-09-22-067)

**Strategy file:** `strategies/2026-09-22_sell_in_may_trend_filter_rescue.py`
**Date:** 2026-09-22
**Hypothesis id:** 2026-09-22-068

## Hypothesis

Direct rescue attempt for this same cron trigger's prior rejection
2026-09-22-067 (Sell-in-May/Halloween Effect, decisive Sharpe+MDD fail on
both QQQ and SPY, no risk management within the Nov-Apr holding window).
Adds a daily-re-evaluated close > SMA(trend_window) gate on top of the
same Nov-Apr calendar window, so exposure can drop to flat mid-window on a
trend break rather than holding through the full 6 months regardless of
price action.

## Single-Config Validation (Step 7), long_start_month=11/long_end_month=4/trend_window=100

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | **false** 0.506 | **false** 0.693 | 1.0 |
| Max drawdown | true 0.227 | true 0.145 | 0.25 |
| Transaction cost survival (10bps/trade) | **false** net Sharpe 0.473 (22 trades) | true net Sharpe 0.648 (21 trades) | 0.5 |
| Walk-forward (manual 4-equal-slice) | **false** 2/4 (0.5) | **false** 2/4 (0.5) | 0.75 |
| Parameter sensitivity (3-value sweep) | true 0.135 | true 0.167 | 0.5 |

## Outcome: REJECTED (both symbols) -- rescue partially worked but insufficient

The trend gate DID fix the MDD problem that decisively failed in the base
strategy (QQQ 28.6%->22.7%, SPY 34.1%->14.5%, both now under the 0.25
threshold) -- the rescue mechanism itself works as intended for risk
control. However, Sharpe ratio still fails on both symbols (0.506 QQQ,
0.693 SPY, both well under 1.0) and walk-forward now fails too (2/4 on
both, down from the base strategy's passing 0.75/1.0) -- the more frequent
in/out toggling from the daily trend re-evaluation (22/21 trades vs. the
base's 7) increases transaction-cost drag and appears to fragment the
strategy's edge across time-splits inconsistently. Net effect: MDD problem
solved, but the underlying Sharpe edge from the Nov-Apr calendar effect
remains too weak to clear this repo's 1.0 threshold even with better risk
control -- consistent with the academic literature's own framing of this
as a modest relative-outperformance effect, not a strong absolute edge.
Unlike the turn-of-month rescue (2026-09-22-066), this rescue did not
succeed. No further rescue attempted this iteration; a future loop could
try a much longer/slower trend_window (to reduce whipsaw trade count) or
combine the calendar filter with a different risk-management mechanism
(e.g. a fixed trailing stop instead of a binary trend gate).
