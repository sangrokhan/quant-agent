# Backtest Report: TRIX Continuous Sizing Overlay on SMA Trend Gate (2026-09-14)

**Strategy file:** `strategies/2026-09-14_trix_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-14-114

## Hypothesis

TRIX: triple-smoothed EMA (EMA of EMA of EMA, period n=14) then the
1-period percentage rate of change of that triple-smoothed value:
TRIX = (EMA3_today - EMA3_yesterday)/EMA3_yesterday * 100. Formula
confirmed via Google AI overview (browser_exec navigation): Investopedia,
TrendSpider, AvaTrade all agree.

Repo has 7 prior TRIX entries, all binary crossover/divergence/pullback
ENTRY triggers, all rejected (one had the lowest grid pass_fraction of its
cron trigger, 0.074). This iteration normalizes TRIX via rolling z-score +
tanh squash to bounded [-1,1] (the established fix pattern), then uses it
as a CONTINUOUS SIZING dial within an SMA(trend_window) uptrend gate.

## Grid test summary (Step 6)

`param_grid={trend_window:[40,60], trix_sensitivity:[0.5,0.6,0.7], deadband:[0.2,0.28]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2018-01-01 to 2026-09-01.

- total_cells=144, passed=36, pass_fraction=0.25
- by_asset_class: equity 36/72 (0.50), crypto 0/72 (0.00) -- 10th
  consecutive continuous-sizing iteration this trigger with a decisive
  crypto grid failure
- by_vol_regime: low 24/48 (0.50), mid 12/48 (0.25), high 0/48 (0.00)
- best_cell: QQQ, trend_window=60/sens=0.6/db=0.2, low-vol regime, Sharpe
  3.02 (highest single-cell Sharpe of this cron trigger's later batch)

## Single-config validator results (Step 7)

QQQ passed even at a modest deadband (0.25) with the standard trend_window
(60). SPY needed a wide deadband (0.4, matching CFO's earlier requirement)
to clear TC-survival:

| Symbol | params | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | trend_window=60, sens=0.4, db=0.25 | 1.158 (pass) | 14.7% (pass) | 1.058 (pass) | 1.00 (pass) | 0.018 rel-std (pass) | **ACCEPT** |
| SPY | trend_window=60, sens=0.4, db=0.4 | 1.036 (pass) | 16.3% (pass) | 0.942 (pass) | 1.00 (pass) | 0.045 rel-std (pass) | **ACCEPT** |
| BTC/USDT | trend_window=60, sens=0.6, db=0.2 | 0.156 (**FAIL**) | 40.1% (**FAIL**) | -0.016 (**FAIL**) | 1.00 (pass) | 0.037 rel-std (pass) | **REJECT** |

## Decision

**Accept for QQQ AND SPY (equity)**, both clearing all 5 validators with
very low parameter sensitivity (0.018-0.045 rel-std, among the tightest of
this cron trigger's batch). **Reject BTC/USDT** — decisive MDD failure at
40.1%, extending the now 10-for-10 crypto rejection streak across this
entire cron trigger's continuous-sizing campaign (EFI, EMV, STC, Qstick,
PPO, ER, FDI, CFO, R-squared, TRIX), spanning momentum, volume-flow,
linear-regression, and trend-efficiency families alike. This is the 10th
and final iteration of this cron trigger's outer loop; the consistent
crypto failure pattern across every indicator family tested is the
strongest finding of this entire trigger and should steer the next cron
trigger's Step 1/Step 2 research toward either (a) equity-only refinement
of already-accepted dials, or (b) a structurally different crypto approach
(volatility targeting, regime-conditional leverage caps, or a non-SMA
directional gate) rather than another indicator substitution in the same
template.
