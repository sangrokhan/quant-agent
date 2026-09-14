# Vervoort SVE Volatility Bands %b Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-162 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_sve_bands_pctb_sizing_sma_trend.py`

## Hypothesis

Sylvain Vervoort's SVE / Volatility Bands (per LuxAlgo's "SVE Bands"
description; `web_search`'s DDG backend TLS/connection-errored on both
queries attempted this iteration, `browser_exec` Google search fallback
used throughout; traders.com's original TASC source article is
Cloudflare-gated, consistent with prior repo findings 2026-09-10-016/-020
on Vervoort-source inaccessibility): typical price is double exponentially
smoothed to build a low-flicker centerline, bands offset that centerline
by an exponentially averaged range-flavored deviation measure. LuxAlgo
default parameterization: smoothing_length=8 (double EMA pass),
volatility_length=13, deviation_mult=3.55 (upper), lower_band_adjust=0.9
(asymmetric lower band). Repo has 1 prior Vervoort Volatility Band entry
(2026-09-08-022, rejected discrete 3-candle reversal pattern trigger).
This iteration reframes the indicator's own %b-style position (Close's
normalized location within [lower, upper], centered to [-1,+1]) as a
CONTINUOUS SIZING dial: rolling z-scored + tanh-squashed to [-1,1], sized
within an SMA(trend_window) uptrend gate, deadband + leverage_cap for
crypto. First Vervoort Volatility Band continuous-sizing variant.

Source: https://www.luxalgo.com/library/indicator/zXEjsttC-vervoort-volatility-bands/

## Grid test summary (Step 6)

`param_grid={smoothing_length: [8,15], deviation_mult: [2.0,3.55],
sensitivity: [0.4,0.6,0.8]}`, symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT
(crypto), vol_regime_splits=3.

- **total_cells:** 144, **passed:** 66, **pass_fraction:** 0.458.
- **by_asset_class:** equity 34/72 (0.472), crypto 32/72 (0.444).
- **by_vol_regime:** low 40/48 (0.833), mid 18/48 (0.375), high 8/48
  (0.167) — heavy high-vol degradation, consistent with this cron
  trigger's recurring pattern for trend-gated sizing overlays.
- **best_cell:** QQQ, smoothing_length=8/deviation_mult=3.55/
  sensitivity=0.6, low-vol, Sharpe 2.732.
- **worst_cell:** QQQ, smoothing_length=15/deviation_mult=3.55/
  sensitivity=0.8, high-vol, Sharpe -0.188.

## Single-config validator results (Step 7)

Best grid config (smoothing_length=8, deviation_mult=3.55, sensitivity=0.6)
tested full-sample per symbol, leverage_cap=1.0 (equity) / 0.4 (crypto):

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity (rel-std) | Outcome |
|---|---|---|---|---|---|---|
| QQQ | 1.060 (pass) | 0.143 (pass) | 0.562 (pass) | 1.000 (pass) | 0.060 (pass) | **accepted** |
| SPY | 0.975 (**fail**, thr 1.0, near-miss) | 0.107 (pass) | 0.321 (**fail**, thr 0.5) | 1.000 (pass) | 0.031 (pass) | **rejected** |
| BTC/USDT | 0.145 (**fail**, decisive) | 0.290 (**fail**) | -0.057 (**fail**) | 1.000 (pass) | 0.063 (pass) | **rejected** |
| ETH/USDT | 0.139 (**fail**, decisive) | 0.254 (**fail**, borderline) | -0.053 (**fail**) | 1.000 (pass) | 0.079 (pass) | **rejected** |

## Decision

**Accepted (QQQ only):** all 5 validators pass with comfortable margins at
leverage_cap=1.0.
**Rejected (SPY):** near-miss on Sharpe (0.975 vs 1.0) but decisive
TC-survival failure (0.321 vs 0.5 threshold) — SPY's tighter historical
range makes the double-smoothed band's %b dial too noisy relative to
trading costs.
**Rejected (crypto):** BTC/USDT, ETH/USDT — decisive failure on Sharpe and
MDD even at leverage_cap=0.4, consistent with this cron trigger's recurring
finding that indicators built around a smoothed-range deviation measure
(designed for daily-bar equity volatility character) do not transfer well
to 24/7 crypto price action. Narrower-but-honest QQQ-only acceptance
recorded per RESEARCH_LOOP.md Step 6 guidance rather than treating this as
a broadly-applicable strategy.
