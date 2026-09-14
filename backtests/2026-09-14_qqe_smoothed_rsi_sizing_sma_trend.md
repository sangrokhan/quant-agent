# QQE Smoothed-RSI Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-165 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_qqe_smoothed_rsi_sizing_sma_trend.py`

## Hypothesis

QQE (Quantitative Qualitative Estimation), reusing howtotrade.com's
attribution already confirmed in this repo's 2 prior QQE entries
(2026-09-08-162, 2026-09-12-160, both binary crossover/confirmation
triggers, both rejected): smooths RSI with a fast EMA (RSI_MA), normally
combined with an ATR-of-RSI trailing-band ratchet construction. This
iteration deliberately isolates just the smoothed-RSI component (skipping
the trailing-band ratchet), centered around its 50 midline
(RSI_MA - 50), as a CONTINUOUS SIZING dial: rolling z-scored +
tanh-squashed to [-1,1], sized within an SMA(trend_window) uptrend gate,
deadband + leverage_cap for crypto. First QQE continuous-sizing variant.

Source: reused formula/attribution from prior repo research
(howtotrade.com QQE tutorial, already confirmed in 2026-09-08-162); no new
external source this iteration.

## Grid test summary (Step 6)

`param_grid={rsi_period: [10,14,20], sensitivity: [0.4,0.6,0.8]}`, symbols
QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 108, **passed:** 51, **pass_fraction:** 0.472.
- **by_asset_class:** equity 27/54 (0.500), crypto 24/54 (0.444).
- **by_vol_regime:** low 30/36 (0.833), mid 12/36 (0.333), high 9/36
  (0.250).
- **best_cell:** QQQ, rsi_period=14/sensitivity=0.8, low-vol, Sharpe
  2.894.
- **worst_cell:** QQQ, rsi_period=20/sensitivity=0.4, high-vol, Sharpe
  -0.296.

## Single-config validator results (Step 7)

Best grid config (rsi_period=14, sensitivity=0.8) tested full-sample per
symbol, leverage_cap=1.0 (equity) / 0.4 (crypto):

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity (rel-std) | Outcome |
|---|---|---|---|---|---|---|
| QQQ | 1.206 (pass) | 0.127 (pass) | 0.976 (pass) | 1.000 (pass) | 0.018 (pass) | **accepted** |
| SPY | 0.775 (**fail**, decisive) | 0.137 (pass) | 0.488 (**fail**, near-miss) | 0.750 (pass) | 0.073 (pass) | **rejected** |
| BTC/USDT | 0.175 (**fail**, decisive) | 0.259 (**fail**, borderline) | -0.042 (**fail**) | 1.000 (pass) | 0.074 (pass) | **rejected** |
| ETH/USDT | 0.168 (**fail**, decisive) | 0.304 (**fail**) | -0.036 (**fail**) | 1.000 (pass) | 0.077 (pass) | **rejected** |

## Decision

**Accepted (QQQ only):** all 5 validators pass with strong margins
(Sharpe 1.206, TC-survival net Sharpe 0.976) at leverage_cap=1.0.
**Rejected (SPY):** decisive Sharpe failure (0.775) with a near-miss
TC-survival (0.488 vs 0.5).
**Rejected (crypto):** BTC/USDT, ETH/USDT — decisive Sharpe/TC-survival
failures even at leverage_cap=0.4, consistent with this cron trigger's
recurring finding that RSI/momentum-family sizing dials calibrated on
daily-bar equity character transfer poorly to crypto. Notably, QQE's
simplified smoothed-RSI-only construction (no ATR-of-RSI trailing band)
performs markedly better as a continuous sizing dial on QQQ than the
original repo's 2 binary-trigger QQE entries (both rejected outright) —
worth flagging that stripping the trailing-band ratchet and using the raw
smoothed RSI directly may be the more useful framing of this indicator
family going forward.
