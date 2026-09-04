# Backtest Report: Turnaround Tuesday + Volume Filter (QQQ)

**Strategy file:** `strategies/2026-09-04_turnaround_tuesday_volume_filter.py`
**Hypothesis ID:** 2026-09-04-105
**Source:** https://www.quantifiedstrategies.com/volume-trading-strategy/ (targeted fix to previously-rejected 2026-09-03-018)

## Hypothesis

The plain Turnaround Tuesday day-of-week strategy (2026-09-03-018) was
rejected in this repo for a weak/unstable Sharpe (0.81 on QQQ, and an
unstable "best weekday" across the sample). QuantifiedStrategies.com's own
A/B-tested finding: gating the same Monday-close entry by whether Monday's
volume exceeds its own 25-day trailing average meaningfully improves
results (avg gain 0.81% vs 0.41%, AND lower MDD 23% vs 27%) in their SPY
backtest. This iteration applies the same volume filter to the same
day-of-week signal on this repo's data.

## Single-config validators (primary config: vol_multiplier=1.0, vol_window=20, QQQ, 2019-01-01 to 2026-09-01)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.84 | ≥ 1.0 | **FAIL** (close, up from 0.81 pre-filter) |
| Max drawdown | 0.133 | ≤ 0.25 | PASS (big improvement — was worse pre-filter) |
| Transaction cost survival (10bps/trade, 105 trades) | net Sharpe 0.63 | ≥ 0.5 | PASS |
| Walk-forward (4 contiguous splits, manual) | 4/4 splits positive Sharpe (1.0) | ≥ 0.75 | PASS |
| Parameter sensitivity (vol_multiplier×vol_window grid) | 0.259 | ≤ 0.5 | PASS |

## Step 6 grid summary (vol_multiplier∈{1.0,1.2,1.5} × vol_window∈{20,25}, SPY+QQQ+BTC/USDT+ETH/USDT, vol_regime_splits=3)

- Total cells: 72, passed: 8, **pass_fraction = 0.111**
- By asset class: equity 8/36 (22%), crypto 0/36 (0%, expected — day-of-week
  effects have no clean Mon/Tue analog on a 24/7 market, same as prior
  weekday tests in this repo).
- By vol regime: low 2/24, mid 0/24, **high 6/24** — notably, unlike most
  other strategies in this repo (which pass mostly in low-vol regimes),
  this one's edge is concentrated in HIGH-vol regimes, consistent with the
  source's own "capitulation gets washed out" speculation for why
  high-volume Mondays perform better.
- Best cell: vol_multiplier=1.0, vol_window=20, QQQ, high-vol, Sharpe 1.66.

## Decision: REJECTED (near-miss)

4 of 5 validators pass on the best config, with a large MDD improvement
(13.3% vs the original -018's failure) and a perfect 4/4 walk-forward. Only
the full-sample Sharpe (0.84) narrowly misses the 1.0 threshold — up from
0.81 pre-filter, confirming the volume filter DOES help (matches the
source's own directional finding) but not enough to clear this repo's bar
on this sample/asset. Worth a further revisit: the grid's best individual
cell (high-vol regime only, Sharpe 1.66) suggests conditioning the
strategy explicitly on being already in a high-vol regime (rather than
just a single-day volume spike) might close the remaining gap.
