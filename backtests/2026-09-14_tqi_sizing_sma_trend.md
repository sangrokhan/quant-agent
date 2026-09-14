# Trend Quality Indicator (TQI) Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-164 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_tqi_sizing_sma_trend.py` (kept as a record
of a rejected attempt — do not treat as a live strategy)

## Hypothesis

Trend Quality Indicator (TQI), reusing the TradingView open-source script
formula already confirmed in this repo's prior accepted binary-crossover
entry (2026-09-08-054): raw TQI = (regression_slope(close, reg_window) /
ATR(atr_window)) * R_squared(close, reg_window), designed to penalize
choppy/non-linear moves by weighting slope with the fit's own
goodness-of-fit. Prior entry used a binary zero-line crossover on the
smoothed TQI (accepted QQQ+SPY, rejected crypto). This iteration reframes
raw TQI itself as a CONTINUOUS SIZING dial: rolling z-scored + tanh-
squashed to [-1,1], sized within an SMA(trend_window) uptrend gate,
deadband + leverage_cap for crypto. First TQI continuous-sizing variant.

Source: reused formula from prior repo research (no new external source
this iteration — TQI formula already confirmed via TradingView open-source
script description in 2026-09-08-054; this iteration is a technique
variant, not a re-test of the same rule).

## Grid test summary (Step 6)

`param_grid={reg_window: [15,20,30], sensitivity: [0.4,0.6,0.8]}`, symbols
QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 108, **passed:** 49, **pass_fraction:** 0.454.
- **by_asset_class:** equity 25/54 (0.463), crypto 24/54 (0.444).
- **by_vol_regime:** low 33/36 (0.917), mid 11/36 (0.306), high 5/36
  (0.139) — heavy high-vol degradation, consistent pattern this cron
  trigger.
- **best_cell:** QQQ, reg_window=20/sensitivity=0.8, low-vol, Sharpe
  2.945.
- **worst_cell:** QQQ, reg_window=20/sensitivity=0.6, high-vol, Sharpe
  -0.328.

## Single-config validator results (Step 7)

Best grid config (reg_window=20, sensitivity=0.8) tested full-sample per
symbol, leverage_cap=1.0 (equity) / 0.4 (crypto):

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity (rel-std) | Outcome |
|---|---|---|---|---|---|---|
| QQQ | 0.980 (**fail**, thr 1.0, near-miss) | 0.132 (pass) | 0.738 (pass) | 1.000 (pass) | 0.039 (pass) | **rejected** |
| SPY | 0.637 (**fail**, decisive) | 0.130 (pass) | 0.313 (**fail**) | 0.750 (pass) | 0.081 (pass) | **rejected** |
| BTC/USDT | 0.164 (**fail**, decisive) | 0.306 (**fail**) | -0.045 (**fail**) | 0.750 (pass) | 0.062 (pass) | **rejected** |
| ETH/USDT | 0.201 (**fail**, decisive) | 0.255 (**fail**, borderline) | -0.030 (**fail**) | 1.000 (pass) | 0.055 (pass) | **rejected** |

## Decision

**Rejected (all 4 symbols).** QQQ is a near-miss on Sharpe alone
(0.980 vs 1.0 threshold, all other 4 validators pass comfortably) — a
candidate for a future loop's fine-tune-the-near-miss pattern (e.g. a
slightly wider reg_window or higher sensitivity might clear 1.0). SPY and
both crypto symbols fail decisively. Unlike the same indicator's binary
zero-line-crossover framing (accepted QQQ+SPY in 2026-09-08-054), the
continuous sizing-dial reframing does not clearly improve on the original
— raw (unsmoothed) TQI appears noisier as a rolling z-scored dial than the
SMA-smoothed version used for the discrete crossover, likely explaining
why QQQ now falls just short where the binary version passed.
