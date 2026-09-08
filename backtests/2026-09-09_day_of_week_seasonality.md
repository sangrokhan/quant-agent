# Backtest Report: Day-of-Week / Weekend-Effect Calendar Seasonality

**Strategy file:** `strategies/2026-09-09_day_of_week_seasonality.py`
**Date:** 2026-09-09
**Source:** Google search synthesis of Investopedia/ScienceDirect/QuantifiedStrategies "day of the week effect" pages

## Hypothesis

Equity returns have historically differed systematically by day of week
(the "weekend effect": Monday returns weakest, later-week returns
relatively stronger). Mechanical rule: long only on a configurable subset
of weekdays, flat on the rest (e.g. flat Monday, long Tue-Fri). First
day-of-week (sub-week) calendar-seasonality strategy in this repo,
distinct from all month-level calendar effects already tested.

## Grid test summary (Step 6)

Grid: `long_weekdays` in [(Wed,Thu,Fri), (Tue,Wed,Thu,Fri), (Thu,Fri),
(Mon,Tue,Wed,Thu,Fri=all)] x symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3
vol-regime terciles = 48 cells, 2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.229** (11/48 cells -- highest of this cron trigger's grid results)
- **By asset class:** equity 11/24, crypto 0/24
- **By vol regime:** low 8/16, mid 3/16, high 0/16
- **Best cell:** QQQ, long_weekdays=(Tue,Wed,Thu,Fri), low-vol regime, Sharpe=3.038

## Single-config validation (Step 7): long_weekdays=(Tue,Wed,Thu,Fri) [flat Monday only], full sample 2018-2026

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.712 (FAIL) | 0.581 (FAIL) | >= 1.0 |
| Max drawdown | 0.374 (**FAIL, decisive**) | 0.374 (**FAIL, decisive**) | <= 0.25 |
| Net Sharpe after costs (10bps/trade) | 0.115 (**FAIL, decisive**) | -0.038 (**FAIL, decisive**) | >= 0.5 |
| Walk-forward pass fraction (4 slices) | 1.0 (PASS) | 1.0 (PASS) | >= 0.75 |
| Parameter sensitivity relative std | 0.421 (PASS) | 0.378 (PASS) | <= 0.5 |
| Num trades | **818** | **818** | -- |

## Decision

**Reject, decisively.** The excellent isolated low-vol-tercile grid cell
(Sharpe 3.04) is an artifact of subsample cherry-picking: full-sample
validation shows this construction generates an extremely high trade
count (818 transitions over 8.7 years -- entering/exiting the position
every single week transition day) which, combined with a per-trade cost
model (10bps), completely destroys the edge (net Sharpe collapses to
0.115 QQQ and goes NEGATIVE for SPY, -0.038). MDD also fails decisively
for both symbols (0.374, well above the 0.25 threshold) since being
flat every Monday means missing every Monday's price action but still
carrying full exposure through the volatile Tue-Fri stretch during
drawdown periods. The weekend/day-of-week effect, even if statistically
present as a return-differential in the underlying data, is not
economically tradeable at daily-bar resolution once realistic
transaction costs are applied to a strategy that necessarily re-enters
and exits every week.
