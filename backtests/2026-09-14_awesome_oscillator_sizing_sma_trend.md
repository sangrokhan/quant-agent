# Awesome Oscillator Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-173 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_awesome_oscillator_sizing_sma_trend.py`

## Hypothesis

Awesome Oscillator (AO, Bill Williams, "Trading Chaos" 1995): AO =
SMA(median_price, fast_window) - SMA(median_price, slow_window), where
median_price = (High+Low)/2, canonical fast=5/slow=34 -- already
zero-centered by construction. This repo has 6+ prior AO entries (zero-line
crossover, saucer pattern, twin-peaks pattern, alligator-combo), ALL using
AO as a BINARY pattern/crossover ENTRY trigger. None used AO's own
continuous magnitude as a SIZING dial. This iteration reframes AO as a
CONTINUOUS SIZING dial: rolling z-scored + tanh-squashed to [-1,1], sized
within an SMA(trend_window) uptrend gate, deadband + leverage_cap for
crypto. First Awesome Oscillator continuous-sizing variant in this repo.

Source: repo's own prior confirmed formula (2026-09-04_awesome_oscillator
family); no new external source needed -- pure technique variant on an
already-confirmed canonical formula.

## Grid test summary (Step 6)

`param_grid={fast_window: [5,8], sensitivity: [0.4,0.6,0.8]}`, symbols
QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 72, **passed:** 29, **pass_fraction:** 0.403.
- **by_asset_class:** equity 18/36 (0.500), crypto 11/36 (0.306).
- **by_vol_regime:** low 21/24 (0.875), mid 8/24 (0.333), high 0/24 (0.000).
- **best_cell:** QQQ, fast_window=5/sensitivity=0.4, low-vol, Sharpe 2.889.
- **worst_cell:** QQQ, fast_window=8/sensitivity=0.8, high-vol, Sharpe
  -0.204.

Note: this is the first sizing-dial entry this cron trigger with a 0%
high-vol-regime pass rate across the whole grid.

## Single-config validator results (Step 7)

Best grid config (fast_window=5, sensitivity=0.4) tested full-sample per
symbol, leverage_cap=1.0 (equity) / 0.4 (crypto):

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity (rel-std) | Outcome |
|---|---|---|---|---|---|---|
| QQQ | 1.168 (pass) | 0.137 (pass) | 0.691 (pass) | 0.750 (pass) | 0.028 (pass) | **accepted** |
| SPY | 0.816 (**fail**) | 0.102 (pass) | 0.295 (**fail**) | 0.750 (pass) | 0.063 (pass) | **rejected** |
| BTC/USDT | 0.125 (**fail**, decisive) | 0.307 (**fail**) | -0.063 (**fail**) | 0.750 (pass) | 0.129 (pass) | **rejected** |
| ETH/USDT | 0.130 (**fail**, decisive) | 0.270 (**fail**) | -0.061 (**fail**) | 1.000 (pass) | 0.069 (pass) | **rejected** |

## Decision

**Accepted (QQQ only):** clears all 5 validators comfortably at
leverage_cap=1.0 -- AO's dual-SMA median-price momentum, reframed as a
continuous sizing dial, rescues an indicator family with 6+ prior binary-
pattern entries, none of which were previously accepted per the index.
**Rejected (SPY):** Sharpe 0.816 misses threshold and TC-survival fails
(0.295 vs 0.5) -- same recurring pattern seen across most equity sizing-dial
variants this cron trigger.
**Rejected (crypto):** BTC/USDT, ETH/USDT -- decisive Sharpe/MDD/TC-survival
failures even at leverage_cap=0.4, consistent with this cron trigger's
recurring finding that daily-bar-calibrated momentum sizing dials transfer
poorly to crypto.
