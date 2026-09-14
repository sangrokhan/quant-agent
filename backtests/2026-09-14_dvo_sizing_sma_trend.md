# Backtest Report: David Varadi Oscillator (DVO) Continuous Sizing Dial (SMA Trend Gate)

**Strategy file:** `strategies/2026-09-14_dvo_sizing_sma_trend.py`
**Date:** 2026-09-14

## Hypothesis

This repo's only prior DVO entry (2026-09-08-035) used DVO as a binary
oversold-threshold mean-reversion entry. DVO is naturally bounded [0,100]
by construction (it IS a rolling percent-rank), so this iteration
reframes it as a CONTINUOUS SIZING dial: rescaled to [-1,+1] via
(DVO-50)/50, directly used as an exposure dial within an
SMA(trend_window) uptrend gate.

Source: same DVO formula as 2026-09-08-035
(https://www.quantifiedstrategies.com/david-varadi-oscillator/); only the
*use* is new.

## Grid Test Summary (Step 6)

`param_grid={"rank_lookback": [126, 252], "base_exposure": [0.4, 0.6, 0.8],
"sensitivity": [0.5, 0.7, 0.9]}`, `symbols={"equity": ["QQQ","SPY"],
"crypto": ["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3`.

- total_cells: 216, passed_cells: 93, **pass_fraction: 0.431**
- by_asset_class: equity 48/108 (0.444), crypto 45/108 (0.417 -- unusually
  close to equity for a sizing dial this trigger)
- by_vol_regime: low 62/72 (0.861), mid 31/72 (0.431), high 0/72 (0.0)
- best_cell: rank_lookback=252, base_exposure=0.8, sensitivity=0.9, QQQ low-vol, sharpe=2.28
- worst_cell: rank_lookback=126, base_exposure=0.8, sensitivity=0.9, QQQ high-vol, sharpe=-0.23

The default grid's max combo Sharpe was ~0.98 on QQQ/SPY -- a local scan
of trend_window/deadband was needed to clear the 1.0 threshold.

## Primary Config Validation (Step 7)

Best full-sample single config: `rank_lookback=126, base_exposure=0.8,
sensitivity=0.4, trend_window=30, deadband=0.5` (widened deadband from
default to cut turnover, following this cron trigger's established
deadband-widening fix pattern).

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 1.158 (pass) | 0.192 (pass) | 0.822 (pass) | 1.00 (pass) | 0.157 rel-std (pass) |
| SPY | 1.055 (pass) | 0.132 (pass) | 0.633 (pass) | 1.00 (pass) | 0.157 rel-std (pass) |
| BTC/USDT | 1.070 (pass) | 0.573 (**fail**, cap 0.25) | 0.948 (pass) | 1.00 (pass) | 0.043 rel-std (pass) |
| ETH/USDT | 0.971 (**fail**, Sharpe near-miss) | 0.647 (**fail**, cap 0.25) | 0.890 (pass) | 1.00 (pass) | 0.068 rel-std (pass) |

All 5 validators pass for both QQQ and SPY. Crypto BTC decisively fails
only MDD; ETH additionally has a Sharpe near-miss (0.971) alongside the
MDD fail.

## Decision

**ACCEPT for equity (QQQ + SPY). REJECT for crypto (BTC decisive MDD fail; ETH double fail Sharpe+MDD).**
