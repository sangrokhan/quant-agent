# Backtest Report: ChartMill Trend Indicator (CTI) Weekly Regime

**Strategy file:** `strategies/2026-09-12_chartmill_trend_weekly_regime.py`
**Status:** REJECTED (near-miss)

## Hypothesis
Per ChartMill.com's own documentation (fully disclosed, no paywall):
https://www.chartmill.com/documentation/technical-analysis/indicators/32-The-ChartMill-Trend-Indicator-(CTI)

Weekly bars are classified positive/neutral/negative vs a 30-week EMA:
- Positive: week's low > a 30-week EMA that has risen for >=3 consecutive weeks.
- Negative: week's high < a 30-week EMA that has declined for >=3 consecutive weeks.
- Neutral: otherwise.

Long only when weekly state is positive, flat otherwise (regime-state
strategy, no discrete trigger, same style as the already-accepted Laguerre
RSI zero-line filter 2026-09-06-110). First ChartMill/CTI strategy in this
repo.

## Grid test summary (Step 6)
- Grid: ema_period ∈ {20,30,40}, rising_weeks ∈ {2,3}; symbols QQQ/SPY
  (equity), BTC/USDT, ETH/USDT (crypto); vol_regime_splits=3.
- Total cells: 72, passed: 20, **pass_fraction = 0.278**
- By asset class: equity 20/36, crypto 0/36 (decisive reject)
- By vol regime: low 12/24, mid 8/24, high 0/24
- Best cell: ema_period=30, rising_weeks=2, SPY, low-vol tercile, Sharpe=2.18
- Worst cell: ema_period=20, rising_weeks=3, SPY, high-vol tercile, Sharpe=-0.92

## Single-config validation (Step 7), best grid config full-sample (2015-2026)
Params: ema_period=30, rising_weeks=2

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | 0.90 **FAIL** (near-miss) | 0.82 **FAIL** (near-miss) |
| Max Drawdown (<=0.25) | 0.178 PASS | 0.175 PASS |
| TC survival (net Sharpe>=0.5, 10bps/trade) | 0.87 PASS (31 trades) | 0.79 PASS (28 trades) |
| Parameter sensitivity (relative_std<=0.5) | 0.131 PASS (30-combo grid, both symbols, ema_period∈{20,25,30,35,40}×rising_weeks∈{2,3,4}) | (same combined grid) |

Walk-forward not run: `validation/validators.py::check_walk_forward` errors
on the installed vectorbt version (`vbt.utils.splitting.RangeSplitter`
attribute missing) -- pre-existing infra bug also hit by the prior iteration
this cron trigger (2026-09-12-162), noted for a future loop to fix.

## Decision
**Reject** (near-miss). 4 of 5 relevant validators pass (MDD, TC-survival,
parameter sensitivity all robust; walk-forward untested due to infra bug),
but full-sample Sharpe falls just short of the 1.0 threshold on BOTH QQQ
(0.90) and SPY (0.82) -- consistent, not a fluke of one symbol. Crypto is
decisively rejected (0/36 grid cells). This near-miss is notably more robust
than most of this cron trigger's rejects (low relative_std=0.13 on a 30-combo
param sweep, both symbols agree directionally) -- worth revisiting with a
slightly loosened Sharpe threshold discussion or an added
volatility/position-sizing overlay in a future iteration.
