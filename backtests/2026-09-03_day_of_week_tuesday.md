# Backtest report: Day-of-the-week effect (Monday close -> Tuesday close)

**Strategy file:** `strategies/2026-09-03_day_of_week_tuesday.py`
**Hypothesis:** Long only from Monday's close to Tuesday's close (weekday=1,
Python `.weekday()` convention), flat every other day of the week. Sourced
from https://www.quantifiedstrategies.com/day-of-the-week-effect/ (Oddmund
Groette): "We buy at the close on weekdays 1-5. 1 is Monday and 5 is
Friday. We exit at the close the next day." Weekday 1 (Mon->Tue) was the
best or near-best slot across S&P 500, DAX 40, OMX 30, Nifty 50, Hang Seng
in the source's 2000-Sept 2021 test.

## Grid test (validation/grid_test.py::run_strategy_grid)

`target_weekday` in {0,1,2,3,4} x QQQ/SPY/BTC-USDT/ETH-USDT x 3 vol
terciles, 60 cells, 2019-01-01 to 2026-09-01:

- **pass_fraction: 0.183** (11/60)
- by_asset_class: equity 11/30, crypto 0/30
- by_vol_regime: low 8/20, mid 1/20, high 2/20
- best_cell: QQQ, target_weekday=4 (Friday), low-vol regime, Sharpe 2.13
- worst_cell: SPY, target_weekday=2 (Wednesday), high-vol regime, Sharpe -0.46

## Full-sample Sharpe by weekday (QQQ/SPY/BTC/ETH, 2019-2026)

| symbol | Mon(0) | Tue(1) | Wed(2) | Thu(3) | Fri(4) |
|---|---|---|---|---|---|
| QQQ | 0.80 | 0.81 | 0.09 | 0.26 | 0.63 |
| SPY | 0.80 | 0.65 | -0.00 | 0.39 | 0.50 |
| BTC/USDT | 0.18 | 0.03 | 0.23 | -0.16 | 0.16 |
| ETH/USDT | 0.15 | 0.00 | 0.24 | -0.16 | 0.12 |

Notably the source's claimed "best slot" (Tuesday, weekday=1) is NOT
uniformly the best in this repo's own sample: on QQQ, Monday (0.80) is
essentially tied with Tuesday (0.81); on SPY, Monday (0.80) actually beats
Tuesday (0.65) outright.

## Standard validators (primary config: QQQ, target_weekday=1 i.e. Tuesday)

| validator | passed | value | threshold |
|---|---|---|---|
| sharpe_ratio | **FAIL** | 0.814 | 1.0 |
| max_drawdown | pass | 0.119 | 0.25 |
| transaction_cost_survival | not run (skipped after Sharpe fail; low turnover ~1/5 of days would likely survive costs, but doesn't rescue the primary Sharpe fail) | - | - |
| walk_forward | not run (skipped after Sharpe fail) | - | - |
| parameter_sensitivity | **FAIL** | rel.std 0.568 | 0.5 |

Parameter sensitivity (5-point weekday sweep on QQQ, Sharpe range
0.09-0.81) fails outright: which weekday you pick materially changes the
outcome (Sharpe 0.09 for Wednesday vs 0.81 for Tuesday) -- the "best"
weekday is not a stable property, it looks like it could be an artifact of
which specific days happened to have good/bad macro news in this sample
window, not a robust structural edge.

## Decision: REJECT

Primary config (QQQ, Tuesday) fails the Sharpe threshold outright (0.81 <
1.0) and fails parameter sensitivity (which weekday is "best" varies too
much, rel.std 0.57 > 0.5 ceiling) -- consistent with the source's own
across-index results, where the effect, while directionally real
(Monday/Tuesday slot usually strongest), is quantitatively tiny (+0.12%
avg on S&P 500) and evidently too small/fragile to clear a Sharpe>=1.0 bar
on a single-symbol daily backtest once realistic thresholds are applied.
Grid pass_fraction 0.183 is the lowest of any calendar-effect strategy
tested in this repo (turn-of-month -006 by comparison passed more broadly).
Crypto fails completely (0/30 grid cells) as expected -- no weekday
seasonality mechanism (payroll, fund rebalancing, etc.) plausibly applies
to a 24/7 market.
