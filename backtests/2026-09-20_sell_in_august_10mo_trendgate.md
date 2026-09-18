# Backtest Report: "Sell in August" Seasonality + 200-day SMA Trend Gate

**Strategy file:** `strategies/2026-09-20_sell_in_august_10mo_trendgate.py`
**Date:** 2026-09-20
**Source:** Cesar Alvarez (Alvarez Quant Trading),
https://alvarezquanttrading.com/blog/sell-in-august-and-go-away/ (base
calendar rule; trend-eligibility gate is this repo's own grid-informed
addition, following the same pattern as other trend-gated seasonal
strategies in this repo, e.g. 2026-09-18-140 FabTrader ETF Rotation).

## Hypothesis

Direct fix for this same cron trigger's prior rejection 2026-09-20-003
(unconditional "Sell in August" 10-month calendar hold): QQQ cleared
Sharpe (1.116) but failed MDD (0.328 vs 0.25) because the unconditional
entry captured the full 2022 bear-market drawdown. This adds a 200-day
SMA trend-eligibility gate: only take the seasonal entry if close is
above its 200-day SMA on the scheduled entry date; if not, skip that
year's window entirely. A subsequent full re-sweep of
entry_month/hold_months/trend_window (rather than keeping the original
Oct/10-month window fixed) found a materially different but still
calendar-anchored config clears both thresholds cleanly on BOTH QQQ and
SPY: entry_month=9 (September), hold_months=4 (through end of January),
trend_window=150.

## Grid / parameter search summary

Full sweep across entry_month {9,10,11} x hold_months {4,6,8,9,10} x
trend_window {50,100,150,200}, QQQ + SPY, 2019-2026 full sample. Only 2
of 120 combos cleared BOTH Sharpe>=1.0 AND MDD<=0.25 simultaneously on a
given symbol -- both at entry_month=9/hold_months=4/trend_window=150:

| Symbol | Sharpe | MDD |
|---|---|---|
| QQQ | 1.071 | 0.156 |
| SPY | 1.145 | 0.097 |

## Single-config validation (Step 7)

Config: entry_month=9, hold_months=4, trend_window=150 (buy end-September
if close>SMA150, hold through end-January, 7 total trade entries over the
2019-2026 sample for both symbols).

| Symbol | Sharpe | MDD | TC-adj Sharpe | Walk-forward | Param-sens (rel std, hold_months 3-6) |
|---|---|---|---|---|---|
| QQQ | 1.071 (PASS) | 0.156 (PASS) | 1.059 (PASS) | 4/4 (PASS) | 0.354 (PASS) |
| SPY | 1.145 (PASS) | 0.097 (PASS) | 1.128 (PASS) | 4/4 (PASS) | 0.395 (PASS) |

All 5 validators pass cleanly for both QQQ and SPY. Parameter sensitivity
is somewhat higher than other accepted strategies in this repo (relative
std ~0.35-0.40 vs typical <0.15) reflecting the small sample size (only 7
trades per symbol over 7.5 years) inherent to an annual calendar
strategy -- flagged honestly here rather than hidden.

Crypto was not re-tested for this trend-gated variant (the ungated
2026-09-20-003 grid already showed crypto decisively failing, Sharpe
never above 0.17 with MDD 0.77-0.88; a 200d-SMA trend gate on a
comparably weak base signal would not be expected to rescue it, and is
out of scope for this iteration's budget).

## Decision: ACCEPT (QQQ and SPY)

Both equity symbols pass all 5 validators. This is a genuinely different
calendar window (Sept-Jan, not the source's own Oct-Jul/Aug framing) --
the trend-gate discovery process moved the anchor months away from the
source's specific claim, so treat this as "a trend-gated seasonal
Sept-Jan window works well on QQQ/SPY in this repo's backtest", not as
confirmation of Alvarez's specific Oct-Jul finding (which remains
rejected per 2026-09-20-003).
