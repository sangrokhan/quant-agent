# Chande Kroll Stop (CKSP) Normalized-Distance Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-161 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_cksp_norm_dist_sizing_sma_trend.py` (kept as a
record of a rejected attempt — do not treat as a live strategy)

## Hypothesis

Chande Kroll Stop (Tushar Chande & Stanley Kroll, 1994), reusing the
LuxAlgo/trendspider.com formula already vetted in this repo's prior CKSP
entries (2026-09-04-116, -149, 2026-09-10-063 — all binary dual-line
breakout triggers, none accepted). This iteration reframes CKSP's own
midline-distance — normalized position of Close within the [stop_short,
stop_long] band — as a CONTINUOUS SIZING dial: rolling z-scored +
tanh-squashed to [-1,1], sized within an SMA(trend_window) uptrend gate,
deadband + leverage_cap for crypto. First CKSP continuous-sizing variant.

Source: reused formula from prior repo research (no new external source
this iteration — the CKSP formula itself was already confirmed via
LuxAlgo/trendspider.com in 2026-09-10-063; this iteration is a technique
variant, not a new-formula test).

## Grid test summary (Step 6)

`param_grid={p: [10,20], atr_mult: [1.0,2.0,3.0], sensitivity:
[0.4,0.6,0.8]}`, symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto),
vol_regime_splits=3.

- **total_cells:** 216, **passed:** 111, **pass_fraction:** 0.514.
- **by_asset_class:** equity 58/108 (0.537), crypto 53/108 (0.491).
- **by_vol_regime:** low 67/72 (0.931), mid 30/72 (0.417), high 14/72
  (0.194) — heavy high-vol degradation.
- **best_cell:** QQQ, p=10/atr_mult=3.0/sensitivity=0.8, low-vol, Sharpe
  2.938.
- **worst_cell:** QQQ, p=10/atr_mult=3.0/sensitivity=0.6, high-vol, Sharpe
  -0.571.

## Single-config validator results (Step 7)

Best grid config (p=10, atr_mult=3.0, sensitivity=0.8) tested full-sample
per symbol, leverage_cap=1.0 (equity) / 0.4 (crypto):

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity (rel-std) | Outcome |
|---|---|---|---|---|---|---|
| QQQ | 0.888 (**fail**, thr 1.0, near-miss) | 0.152 (pass) | 0.438 (**fail**, thr 0.5, near-miss) | 0.750 (pass) | 0.045 (pass) | **rejected** |
| SPY | 0.979 (**fail**, thr 1.0, near-miss) | 0.068 (pass) | 0.344 (**fail**, thr 0.5) | 0.750 (pass) | 0.047 (pass) | **rejected** |
| BTC/USDT | 0.060 (**fail**, decisive) | 0.266 (**fail**) | -0.067 (**fail**) | 0.500 (**fail**) | 0.201 (pass) | **rejected** |
| ETH/USDT | 0.021 (**fail**, decisive) | 0.483 (**fail**, decisive) | -0.070 (**fail**) | 0.500 (**fail**) | 0.244 (pass) | **rejected** |

## Decision

**Rejected (all 4 symbols).** The grid's best_cell (Sharpe 2.94) was found
only in the QQQ low-vol tercile in isolation; full-sample Sharpe for the
same config drops to a near-miss 0.888-0.979 on equity (still fails
TC-survival) and collapses decisively on crypto. This is a clear example of
a grid cell that looks attractive in one narrow vol-regime slice but does
not generalize to the full-sample single-config validation — consistent
with the by_vol_regime breakdown showing pass_fraction falling from 0.931
(low-vol) to 0.194 (high-vol). Unlike the two prior binary-trigger CKSP
entries (all rejected for different reasons — breakout rule too rare /
signal too noisy), this continuous-sizing reframing does not rescue the
indicator either; CKSP's ATR-scaled stop-band appears to encode volatility
information the grid overfits to in low-vol windows rather than a durable
directional edge. No further CKSP variant recommended without a
fundamentally different construction (e.g. combining with an explicit
vol-regime gate rather than relying on the sizing dial alone).
