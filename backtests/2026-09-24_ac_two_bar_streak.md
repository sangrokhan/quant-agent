# Backtest Report: Accelerator Oscillator Two-Consecutive-Bar Streak (QQQ)

**Date:** 2026-09-24
**Strategy file:** `strategies/2026-09-24_ac_two_bar_streak.py`
**Source:** https://admiralmarkets.com/education/articles/forex-indicators/accelerator-oscillator (browser_exec; web_extract failed — ddgs backend search-only)

## Hypothesis
Bill Williams' Accelerator Oscillator (AC = AO - SMA(5,AO)); a possible
strategy per the source: "two green columns in a row above zero as a buy
signal, and two red columns in a row below the zero line as a sell signal."
Distinct from the repo's 3 prior AC entries (zero-line crossover,
continuous z-scored sizing dial) which don't require the 2-bar
acceleration-confirmation pattern.

## Single-config validators (QQQ, max_hold_days=10 — grid's best cell)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample) | **FAIL** | 0.500 | >= 1.0 |
| Max drawdown (full sample) | PASS | 0.160 | <= 0.25 |
| Transaction cost survival (10bps/trade, 141 trades) | **FAIL** | net Sharpe 0.272 | >= 0.5 |
| Walk-forward | SKIPPED | n/a | known repo `vectorbt.utils.splitting` AttributeError bug, light workload |
| Parameter sensitivity (from grid, 2 combos) | PASS | rel_std 0.0248 | <= 0.5 |

## Grid summary (Step 6)
`param_grid={"max_hold_days": [10, 20]}`, `symbols={"equity": ["QQQ", "SPY"]}`,
`vol_regime_splits=3` (light workload, equity only).

- total_cells: 12, passed_cells: 2, **pass_fraction: 0.167**
- by_vol_regime: low 2/4 PASS, mid 0/4 FAIL, high 0/4 FAIL
- best_cell: max_hold_days=10, QQQ, low-vol, Sharpe 1.288
- worst_cell: max_hold_days=10, SPY, mid-vol, Sharpe -0.032

## Decision: REJECT (QQQ, full sample)
Weak edge overall (grid pass_fraction only 0.167, positive only in the
low-vol tercile). Full-sample Sharpe and TC-survival both fail. Low churn
(141 trades over ~7.5yr) keeps MDD contained but doesn't offset the weak
raw edge. Not flagged as a rescue candidate (unlike the repo's prior
min-hold-days AC rescue 2026-09-06-174, which started from a much closer
near-miss).
