# On-Balance Volume (OBV) Rate-of-Change Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-151
**File:** `strategies/2026-09-14_obv_roc_sizing_sma_trend.py`

## Hypothesis

On-Balance Volume (OBV, Joseph Granville, 1963): cumulative running total of
signed volume, `OBV_t = OBV_{t-1} + sign(Close_t-Close_{t-1})*Volume_t`.
Formula per this repo's own already-established OBV definition (8+ prior
entries).

Since raw OBV is a cumulative running total (unbounded, nonstationary over
the sample), this iteration reframes it via its own rolling RATE OF CHANGE
(diff over `roc_window` bars — the same "reframe a cumulative indicator via
its own short-horizon change" technique already validated for NVI,
2026-09-14-131), rolling z-scored and tanh-squashed to [-1,+1], used as a
sizing multiplier within an SMA(trend_window) uptrend gate. First OBV
continuous-sizing variant in this repo (8+ prior entries all binary
crossover/divergence/breakout-confirmation triggers).

## Grid test summary (Step 6)

`param_grid={roc_window: [10,20,30], deadband: [0.15,0.25], leverage_cap: [0.4,1.0]}`,
symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 144, **passed:** 86, **pass_fraction:** 0.597 — tied for
  best pass_fraction this cron trigger (with 2026-09-14-148, -149).
- **by_asset_class:** equity 41/72 (0.569), crypto 45/72 (0.625).
- **by_vol_regime:** low 43/48 (0.896), mid 32/48 (0.667, best mid-vol
  showing of this cron trigger), high 11/48 (0.229).
- **best_cell:** QQQ, roc_window=30/deadband=0.15/leverage_cap=0.4, low-vol,
  Sharpe 3.10 — highest single-cell Sharpe of any strategy this cron
  trigger so far.
- **worst_cell:** SPY, roc_window=30/deadband=0.15/leverage_cap=1.0,
  mid-vol, Sharpe -0.27.

## Single-config validator results (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Outcome |
|---|---|---|---|---|---|---|---|
| QQQ | rw=30, db=0.15, lc=0.4 | 1.624 (pass) | pass | pass | pass | pass | **accepted** |
| SPY | rw=10, db=0.15, lc=0.4 | 1.255 (pass) | pass | **FAIL** | pass | pass | **rejected (near-miss on TC)** |
| BTC/USDT | rw=30, db=0.25, lc=0.4 | 1.422 (pass) | pass | pass | pass | pass | **accepted** |
| ETH/USDT | rw=10, db=0.15, lc=0.4 | 1.231 (pass) | pass | pass | pass | pass | **accepted** |

## Decision

**Accepted:** QQQ, BTC/USDT, ETH/USDT (all 5 validators pass at
leverage_cap=0.4). QQQ's Sharpe 1.624 is the highest single-symbol Sharpe of
any accepted strategy this cron trigger.
**Rejected:** SPY (near-miss, transaction-cost survival fails; gross
Sharpe/MDD/WF/param-sensitivity all pass — the same recurring SPY-TC-
survival-near-miss pattern seen across several strategies this trigger).

Full raw grid: `grid_result_obv_roc_sizing.json`. Full raw validators:
`validators_obv_roc_sizing.json`.
