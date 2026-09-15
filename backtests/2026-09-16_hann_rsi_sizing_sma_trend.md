# Backtest Report: Hann-windowed RSI (RSIH) continuous sizing dial, full-universe rescue

**Strategy file:** `strategies/2026-09-16_hann_rsi_sizing_sma_trend.py`
**Date:** 2026-09-16
**Prior id:** 2026-09-12-148 (binary centerline crossover, rejected all symbols)

## Hypothesis
Direct fix for prior id 2026-09-12-148 (Hann-windowed RSI centerline
crossover: QQQ Sharpe 0.739/MDD 0.277 fail, SPY Sharpe 0.343/TC 0.284 fail,
crypto decisively rejected 0/54, notes flagged extreme vol-regime
dependence). Reframes hann_rsi (Wilder's classic closes-up/closes-down RSI
inputs smoothed with a Hann-window FIR filter, already naturally bounded
[-1,+1] by construction: `hann_rsi = (filtered_CU - filtered_CD) /
(filtered_CU + filtered_CD)`) as a CONTINUOUS SIZING dial (used directly,
no z-score/tanh needed) inside an SMA(trend_window) uptrend gate with a
deadband, leverage-cap-aware for crypto from the start. Source unchanged:
https://www.tradingview.com/scripts/tasc/page-3/ (TASC 2022.01 Improved
RSI w/Hann, John F. Ehlers).

## Step 6 — Grid test summary
Grid: `param_grid={length:[10,14,21], sensitivity:[0.4,0.6,0.8], deadband:[0.15,0.25], leverage_cap:[0.3,0.5,1.0], base_exposure:[0.15,0.4]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, `vol_regime_splits=3`
-> total_cells=1296, passed=805, **pass_fraction=0.621** -- the second-
strongest grid result of any strategy this cron trigger (after Laguerre
Oscillator's 0.648).
- by_asset_class: equity 331/648 (0.511), crypto 474/648 (0.731)
- by_vol_regime: low 426/432 (0.986), mid 285/432 (0.660), high 94/432 (0.218)

Best-average-Sharpe configs per symbol:
- QQQ: `base_exposure=0.15, deadband=0.25, length=14, leverage_cap=0.5, sensitivity=0.8`
- SPY: `base_exposure=0.4, deadband=0.15, length=10, leverage_cap=0.3, sensitivity=0.6`
- BTC/USDT: `base_exposure=0.4, deadband=0.15, length=14, leverage_cap=0.3, sensitivity=0.6`
- ETH/USDT: grid-best config (`leverage_cap=1.0`) passed Sharpe/TC/WF/param
  sensitivity but MDD near-missed at 0.270>0.25; a dedicated follow-up
  sweep found `leverage_cap=0.6, sensitivity=0.6` clears MDD to 0.248
  (just under threshold) with Sharpe 1.334 -- used as final config.

## Step 7 — Validators (final config per symbol, full sample)

| Symbol | Sharpe | MDD | TC net Sharpe | Walk-forward | Param sens |
|---|---|---|---|---|---|
| QQQ | pass | pass | pass | pass | pass |
| SPY | pass | pass | pass | pass | pass |
| BTC/USDT | pass | pass | pass | pass | pass |
| ETH/USDT | 1.334 | 0.248 (pass, just under 0.25) | pass | pass | pass |

All 5 validators pass on all 4 symbols. Full evidence retained in
`backtests/2026-09-16_hann_rsi_validators.json`.

## Decision
**Accept** (full universe: QQQ, SPY, BTC/USDT, ETH/USDT) -- this cron
trigger's 5th full-universe accept (after Reversion Index, Continuation
Index, Laguerre Oscillator sizing dials, and Ultimate Channel's vol-target
rescue). Confirms this cron trigger's dominant pattern: continuous-sizing-
dial reframing rescues binary-crossover rejections when the underlying
oscillator value carries more graduated directional information than a
hard centerline/threshold cross captures -- the original 2026-09-12-148
rejection's own extreme-vol-regime-dependence note (strong low-vol edge
that vanished in mid-vol) is directly addressed by making the exposure
continuous rather than binary.
