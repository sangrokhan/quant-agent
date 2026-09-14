# Mass Index Deviation-from-Baseline Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-166 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_mass_index_sizing_sma_trend.py` (kept as a
record of a rejected attempt — do not treat as a live strategy)

## Hypothesis

Mass Index (Donald Dorsey), reusing the formula already confirmed in this
repo's 2 prior Mass Index entries (2026-09-04-075, 2026-09-08-038, both
discrete reversal-bulge/RSI-of-Mass-Index triggers, neither accepted):
sum over `sum_window` bars of [EMA(range, ema_window) /
EMA(EMA(range, ema_window), ema_window)], a pure volatility-expansion
gauge (not directional by itself). This iteration reframes Mass Index's
own deviation from its published 25 baseline as a CONTINUOUS SIZING dial
(conviction scaler within a directional SMA(trend_window) gate): rolling
z-scored + tanh-squashed to [-1,1], deadband + leverage_cap for crypto.
First Mass Index continuous-sizing variant.

Source: reused formula from prior repo research (quantifiedstrategies.com
Mass Index formula, already confirmed in 2026-09-08-038); no new external
source this iteration.

## Grid test summary (Step 6)

`param_grid={ema_window: [9,15], sum_window: [25,40], sensitivity:
[0.4,0.6,0.8]}`, symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto),
vol_regime_splits=3.

- **total_cells:** 144, **passed:** 56, **pass_fraction:** 0.389 (notably
  lower than this cron trigger's typical ~0.45-0.52 range).
- **by_asset_class:** equity 27/72 (0.375), crypto 29/72 (0.403).
- **by_vol_regime:** low 25/48 (0.521), mid 22/48 (0.458), high 9/48
  (0.188).
- **best_cell:** QQQ, ema_window=9/sum_window=25/sensitivity=0.4, low-vol,
  Sharpe 2.607.
- **worst_cell:** QQQ, ema_window=9/sum_window=40/sensitivity=0.6,
  high-vol, Sharpe -1.232 (largest-magnitude worst_cell loss recorded this
  cron trigger).

## Single-config validator results (Step 7)

Best grid config (ema_window=9, sum_window=25, sensitivity=0.4) tested
full-sample per symbol, leverage_cap=1.0 (equity) / 0.4 (crypto):

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity (rel-std) | Outcome |
|---|---|---|---|---|---|---|
| QQQ | 0.576 (**fail**, decisive) | 0.086 (pass) | 0.289 (**fail**) | 0.750 (pass) | 0.570 (**fail**, thr 0.5) | **rejected** |
| SPY | 0.917 (**fail**, near-miss) | 0.064 (pass) | 0.517 (pass) | 1.000 (pass) | 0.178 (pass) | **rejected** |
| BTC/USDT | 0.205 (**fail**, decisive) | 0.175 (pass) | -0.037 (**fail**) | 1.000 (pass) | 0.094 (pass) | **rejected** |
| ETH/USDT | 0.167 (**fail**, decisive) | 0.279 (**fail**, borderline) | -0.036 (**fail**) | 1.000 (pass) | 0.040 (pass) | **rejected** |

## Decision

**Rejected (all 4 symbols).** SPY is the closest near-miss (Sharpe 0.917,
TC-survival actually passes) but QQQ -- the symbol that produced the
grid's best_cell -- decisively fails full-sample Sharpe AND fails
parameter-sensitivity (relative std 0.570 > 0.5 threshold), indicating the
grid's apparent QQQ edge is itself unstable across nearby sensitivity
values, not just a vol-regime artifact. Combined with this cron trigger's
lowest grid pass_fraction (0.389) and a notably large worst_cell loss
(-1.232 Sharpe), Mass Index's volatility-expansion signal does not appear
to encode a useful directional-conviction scaler when reframed as a
continuous sizing dial -- consistent with its original design purpose
(range-expansion detection for reversal-bulge timing) being a poor fit for
this cron trigger's SMA-trend-gate-plus-continuous-dial framing. No
further Mass Index variant recommended without a fundamentally different
construction (e.g. combining with an explicit directional oscillator
rather than relying on the raw volatility-expansion value alone).
