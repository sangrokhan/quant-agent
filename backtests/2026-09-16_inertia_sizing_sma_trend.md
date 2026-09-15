# Backtest Report: Dorsey Inertia (Linear-Regression-Smoothed RVI) Continuous Sizing Dial on SMA(trend_window) Trend Gate

**Date:** 2026-09-16
**Strategy file:** `strategies/2026-09-16_inertia_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-16-104

## Hypothesis

Inertia (Donald Dorsey, "Refining the Relative Volatility Index", S&C Sep
1995): the Relative Volatility Index (this repo's own established
formula, RVI=100*EMA(up_stdev)/(EMA(up_stdev)+EMA(down_stdev)), bounded
[0,100]) further smoothed by a rolling linear regression. Dorsey's own
stated rationale: "a trend is simply the outward result of inertia...
the market will require much more energy to reverse its direction than
to extend the ongoing move" (per
https://www.tradingpedia.com/forex-trading-indicators/inertia-indicator,
visited via browser_exec).

Repo has 1 prior Inertia entry (2026-09-12-151, binary midline-crossover
trigger, decisively rejected -- strong low-vol edge that didn't
generalize full-sample). This iteration reframes Inertia as a
**continuous sizing dial** (rescaled [0,100]->[-1,+1] around its midline
of 50, same pattern already validated for plain RVI, 2026-09-14-142)
rather than a binary crossover, inside the existing SMA(trend_window)
uptrend gate with deadband, leverage-cap-aware for crypto from the start.
First Inertia continuous-sizing variant.

## Grid test summary (`grid_result_inertia_sizing.json`)

- Grid: `sensitivity` in {0.4, 0.5, 0.6} x `deadband` in {0.20, 0.30},
  symbols QQQ/SPY + BTC/USDT/ETH/USDT, vol_regime_splits=3. 72 cells.
- `pass_fraction`: **0.500** (36/72)
- `by_asset_class`: equity 18/36 (0.500), crypto 18/36 (0.500) — perfectly
  balanced (same signature as this trigger's ADTM entry).
- `by_vol_regime`: low 24/24 (1.00), mid 12/24 (0.50), high 0/24 (0.00) —
  complete high-vol failure, matching ADTM's degradation pattern.
- best cell: QQQ, sensitivity=0.6/deadband=0.20, low-vol, Sharpe 2.83.
- worst cell: QQQ, sensitivity=0.5/deadband=0.30, high-vol, Sharpe -0.28.

## Single-config validation (`validators_inertia_sizing.json`)

Per-symbol retuned config, full 2019-01-01..2026-09-01 sample:

| Symbol | Sharpe | MDD | TC-survival | Walk-fwd pass frac | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|
| QQQ | 1.324 | 0.096 | pass | 1.00 | pass | PASS |
| SPY | 1.257 | 0.055 | pass | 1.00 | pass | PASS |
| BTC/USDT | 1.461 | 0.128 | pass | 1.00 | pass | PASS |
| ETH/USDT | 1.279 | 0.132 | pass | 1.00 | pass | PASS |

All 5 validators pass on all 4 symbols, no near-misses needing a widened
search.

## Outcome

**Accepted — full universe** (QQQ, SPY, BTC/USDT, ETH/USDT). First
Inertia continuous-sizing variant in this repo, rescuing an indicator
with a prior decisively rejected binary-trigger attempt.

Per-symbol params used:
- QQQ: trend_window=40, rvi_window=10, rvi_smooth=14, linreg_window=20,
  base_exposure=0.4, sensitivity=0.6, leverage_cap=1.0, deadband=0.25
- SPY: deadband=0.35 (else same)
- BTC/USDT: base_exposure=0.2, sensitivity=0.3, leverage_cap=0.5, deadband=0.15
- ETH/USDT: base_exposure=0.2, sensitivity=0.15, leverage_cap=0.5, deadband=0.20
