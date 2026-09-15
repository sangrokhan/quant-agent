# Backtest Report: Ehlers Laguerre Oscillator continuous sizing dial, full-universe accept

**Strategy file:** `strategies/2026-09-16_laguerre_oscillator_sizing_sma_trend.py`
**Date:** 2026-09-16
**Source:** https://traders.com/Documentation/FEEDbk_docs/2025/07/TradersTips.html
(TASC July 2025 Traders' Tips, "Laguerre Filters" by John F. Ehlers, exact
disclosed EasyLanguage)

## Hypothesis
The Laguerre Oscillator is distinct from this repo's already-tested
Laguerre Filter (5-tap FIR trend-following line) and Laguerre RSI
(RSI-of-Laguerre-filtered-price): `L0 = UltimateSmoother(close, lag_length)`,
`L1 = -gamma*L0 + L0.shift(1) + gamma*L1.shift(1)` (single-stage Laguerre
recursion, gamma=0.5 per source), `RMS = sqrt(rolling_mean((L0-L1)^2,
rms_window))`, `LaguerreOsc = (L0-L1)/RMS` -- a zero-line-crossing
oscillator, roughly zero-centered but unbounded (unlike several recently-
tested Ehlers indicators). Reframed as a CONTINUOUS SIZING dial (rolling
z-score + tanh-squash to [-1,1], since not naturally bounded) inside an
SMA(trend_window) uptrend gate with a deadband, leverage-cap-aware for
crypto from the start. First Laguerre Oscillator strategy in this repo,
found via a systematic scan of the TASC Traders' Tips archive after
`web_search` returned no useful results this iteration.

## Step 6 — Grid test summary
Grid: `param_grid={lag_length:[20,30,40], sensitivity:[0.4,0.6,0.8], deadband:[0.15,0.25], leverage_cap:[0.3,0.5,1.0], base_exposure:[0.15,0.4]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, `vol_regime_splits=3`
-> total_cells=1296, passed=840, **pass_fraction=0.648** -- the strongest
grid result of any strategy tested this cron trigger (ahead of Reversion
Index's 0.607 and Continuation Index's 0.578).
- by_asset_class: equity 356/648 (0.549), crypto 484/648 (0.747)
- by_vol_regime: low 421/432 (0.975), mid 286/432 (0.662), high 133/432 (0.308)

Best-average-Sharpe configs per symbol (grid-search stage):
- QQQ: `base_exposure=0.4, deadband=0.25, lag_length=40, leverage_cap=0.5, sensitivity=0.4`
- SPY: `base_exposure=0.4, deadband=0.15, lag_length=30, leverage_cap=0.3, sensitivity=0.4`
- BTC/USDT: `base_exposure=0.4, deadband=0.25, lag_length=30, leverage_cap=0.3, sensitivity=0.4`
- ETH/USDT: `base_exposure=0.4, deadband=0.25, lag_length=40, leverage_cap=0.3, sensitivity=0.4`

## Step 7 — Validators (best config per symbol, full sample)

| Symbol | Sharpe | MDD | TC net Sharpe | Walk-forward | Param sens (relstd) |
|---|---|---|---|---|---|
| QQQ | 1.424 | 0.079 | 1.167 | 1.00 | pass |
| SPY | pass | pass | pass | pass | pass |
| BTC/USDT | pass | pass | pass | pass | pass |
| ETH/USDT | pass | pass | pass | pass | pass |

All 5 validators pass on all 4 symbols, first try -- no rescue sub-iteration
needed (unlike Reversion Index and Continuation Index this cron trigger,
which both needed an ETH/USDT leverage_cap follow-up sweep). Full evidence
retained in `backtests/2026-09-16_laguerre_oscillator_validators.json`.

## Decision
**Accept** (full universe: QQQ, SPY, BTC/USDT, ETH/USDT) -- all 5 validators
pass on all 4 symbols first try, with the strongest grid pass_fraction of
any strategy this cron trigger. Third consecutive full-universe accept this
cron trigger (after Reversion Index and Continuation Index sizing dials),
continuing the pattern that Ehlers-family oscillators adapt cleanly to this
repo's continuous-sizing-dial pattern, even when (as here) the raw value is
unbounded and needs the z-score+tanh transform rather than a direct rescale.
