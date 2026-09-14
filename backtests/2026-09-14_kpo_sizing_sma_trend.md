# Kase Peak Oscillator (KPO) Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-169 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_kpo_sizing_sma_trend.py`

## Hypothesis

Kase Peak Oscillator (KPO, Cynthia Kase), reusing the formula already
confirmed in this repo's 2 prior KPO entries (2026-09-08-010,
2026-09-09-057, both binary zero-line/peak-out crossover triggers, neither
accepted): a volatility-normalized ratio of the maximum recent directional
move (over a short_cycle..long_cycle band) to a rolling volatility
normalizer (SMA of stdev of log returns), differencing the "up" leg minus
"down" leg — already zero-centered by construction. This iteration
reframes KPO's own value as a CONTINUOUS SIZING dial: rolling z-scored +
tanh-squashed to [-1,1], sized within an SMA(trend_window) uptrend gate,
deadband + leverage_cap for crypto. First Kase Peak Oscillator
continuous-sizing variant.

Source: reused formula from prior repo research (Mladen's MQL4 port on
prorealcode.com forum, already confirmed in 2026-09-09-057); no new
external source this iteration.

## Grid test summary (Step 6)

`param_grid={long_cycle: [20,30], sensitivity: [0.4,0.6,0.8]}`, symbols
QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 72, **passed:** 35, **pass_fraction:** 0.486.
- **by_asset_class:** equity 21/36 (0.583), crypto 14/36 (0.389).
- **by_vol_regime:** low 20/24 (0.833), mid 8/24 (0.333), high 7/24
  (0.292).
- **best_cell:** QQQ, long_cycle=20/sensitivity=0.8, low-vol, Sharpe
  2.722.
- **worst_cell:** SPY, long_cycle=20/sensitivity=0.8, mid-vol, Sharpe
  -0.203 (mildest worst_cell loss this cron trigger).

## Single-config validator results (Step 7)

Best grid config (long_cycle=20, sensitivity=0.8) tested full-sample per
symbol, leverage_cap=1.0 (equity) / 0.4 (crypto):

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity (rel-std) | Outcome |
|---|---|---|---|---|---|---|
| QQQ | 1.166 (pass) | 0.130 (pass) | 0.858 (pass) | 1.000 (pass) | 0.038 (pass) | **accepted** |
| SPY | 1.017 (pass) | 0.078 (pass) | 0.588 (pass) | 1.000 (pass) | 0.041 (pass) | **accepted** |
| BTC/USDT | 0.213 (**fail**, decisive) | 0.252 (**fail**, borderline) | -0.042 (**fail**) | 1.000 (pass) | 0.028 (pass) | **rejected** |
| ETH/USDT | 0.217 (**fail**, decisive) | 0.264 (**fail**, borderline) | -0.033 (**fail**) | 1.000 (pass) | 0.031 (pass) | **rejected** |

## Decision

**Accepted (QQQ + SPY):** both equity symbols clear all 5 validators
comfortably at leverage_cap=1.0 — KPO's volatility-normalized
max-directional-move construction, when reframed as a continuous sizing
dial rather than a discrete crossover, decisively rescues an indicator
family whose 2 prior binary-trigger entries were both rejected.
**Rejected (crypto):** BTC/USDT, ETH/USDT — decisive Sharpe/TC-survival
failures with borderline MDD failures on both symbols even at
leverage_cap=0.4, consistent with this cron trigger's recurring finding
that daily-bar-calibrated volatility-normalized momentum measures transfer
poorly to crypto. This is one of the stronger equity results this cron
trigger (paired QQQ+SPY acceptance, not just one symbol), worth noting for
future loops as a positive precedent for volatility-normalized max-move
oscillators as sizing dials.
