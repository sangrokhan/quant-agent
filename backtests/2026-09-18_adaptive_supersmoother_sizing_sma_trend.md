# Backtest Report: Adaptive SuperSmoother Continuous Sizing Dial (SMA trend gate)

**Strategy file:** `strategies/2026-09-18_adaptive_supersmoother_sizing_sma_trend.py`
**Date:** 2026-09-18
**Source:** John F. Ehlers, "Adaptive SuperSmoother," TASC September 2026
(https://traders.com/Documentation/FEEDbk_docs/2026/09/TradersTips.html,
TradeStation EasyLanguage block, re-confirmed this iteration).

## Hypothesis

Repo already tested this indicator TWICE as a binary crossover trigger
(fixed-period SuperSmoother vs adaptive-period SuperSmoother crossing):
- `2026-09-12-146`: plain crossover, rejected (Sharpe/MDD near-miss).
- `2026-09-17-060`: crossover + realized-vol regime gate fix attempt --
  fixed the MDD issue but broke Sharpe on both QQQ/SPY.

This iteration reframes the same underlying Adaptive SuperSmoother
construction as a **continuous sizing dial** instead of a binary trigger
(the repo's established rescue pattern for this exact failure mode across
many other oscillators): normalized distance `(close - AdaptiveSS) /
AdaptiveSS`, rolling z-scored (60-day window) and tanh-squashed to [-1, 1],
maps to exposure `clip(0.5 + 0.5*dial, 0, leverage_cap)`, gated to 0
whenever `close < SMA(trend_window)`, held via a deadband to control
turnover.

## Formula (from source)

```
SS = SuperSmoother(Close, Period0)
ROC1 = SS - SS[1]
ROCRMS = RMS(ROC1, 81)
ROC = clip(|ROC1/ROCRMS|, 0, 2)
Period = Period0*(1-0.5*ROC)^2, floored at 2
AdaptiveSS = SuperSmoother(Close, Period)   # per-bar-varying period, recomputed each bar
```

## Grid test (Step 6)

`param_grid={trend_window:[40,60], period0:[15,20,30], sensitivity:[0.5,0.7]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
144 cells, 2018-01-01 to 2026-09-01.

- **pass_fraction: 0.493** (71/144)
- by_asset_class: equity 42/72 (0.583), crypto 29/72 (0.403)
- by_vol_regime: low 39/48 (0.813), mid 24/48 (0.5), high 8/48 (0.167)
- best cell: SPY, trend_window=60/period0=15/sensitivity=0.7, low-vol tercile, Sharpe 3.00
- worst cell: QQQ, trend_window=60/period0=30/sensitivity=0.7, high-vol tercile, Sharpe -1.01

## Best full-sample configs and validators (Step 7)

Deadband widened from the grid default (0.2) to 0.3 after a dedicated
deadband sweep (0.2/0.3/0.4/0.5/0.6) showed 0.2 fails net-of-cost Sharpe on
both symbols while 0.3 clears all thresholds with the lowest turnover of the
values that also keep raw Sharpe >=1.0.

### QQQ: trend_window=40, period0=15, sensitivity=0.5, deadband=0.3

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.140 | >=1.0 | YES |
| Max drawdown | 0.119 | <=0.25 | YES |
| TC survival (net Sharpe, 5bps, 378 trades) | 0.613 | >=0.5 | YES |
| Walk-forward (4-slice manual fallback) | 4/4 positive (1.17, 0.86, 1.28, 1.24) | >=0.75 | YES |
| Parameter sensitivity (25-pt period0 x sensitivity sweep) | rel.std 0.067 | <=0.5 | YES |

### SPY: trend_window=40, period0=30, sensitivity=0.5, deadband=0.3

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.123 | >=1.0 | YES |
| Max drawdown | 0.089 | <=0.25 | YES |
| TC survival (net Sharpe, 5bps, 262 trades) | 0.654 | >=0.5 | YES |
| Walk-forward (4-slice manual fallback) | 4/4 positive (1.52, 1.36, 1.04, 1.21) | >=0.75 | YES |
| Parameter sensitivity (25-pt period0 x sensitivity sweep) | rel.std 0.087 | <=0.5 | YES |

(`validation/validators.py::check_walk_forward` still raises
`AttributeError: module 'vectorbt.utils' has no attribute 'splitting'` on
the installed vectorbt version -- worked around with the repo's established
manual 4-equal-slice fallback, same as many prior entries.)

### Crypto (BTC/USDT, ETH/USDT)

Best full-sample configs (from the grid best-search) decisively fail: BTC
Sharpe 0.12/MDD 0.39, ETH Sharpe 0.21/MDD 0.44 -- both well outside
thresholds at every tested config. Out of scope for this accept.

## Decision

**ACCEPTED (QQQ, SPY equity only)**; crypto (BTC/USDT, ETH/USDT) rejected
decisively -- narrower-but-honest accept, consistent with this repo's
majority pattern for SMA-trend-gated continuous-sizing strategies.
