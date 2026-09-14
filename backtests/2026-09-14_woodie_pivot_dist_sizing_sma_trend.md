# Woodie Pivot Point Normalized-Distance Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-168 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_woodie_pivot_dist_sizing_sma_trend.py` (kept
as a record of a rejected attempt — do not treat as a live strategy)

## Hypothesis

Woodie's Pivot Points, reusing the double-close-weighted formula already
confirmed in this repo's prior accepted entry (2026-09-08-158, a discrete
R1-breakout trigger): PP = (H + L + 2*C) / 4, R1 = 2*PP - L, S1 = 2*PP - H
(prior-day levels). Repo has 5 prior Pivot Point family entries (classic
floor-trader, Camarilla, Woodie), all discrete breakout/bounce triggers,
none as a continuous dial. This iteration reframes today's close position
relative to the prior day's pivot, normalized by the (R1-S1) band width,
as a CONTINUOUS SIZING dial: rolling z-scored + tanh-squashed to [-1,1],
sized within an SMA(trend_window) uptrend gate, deadband + leverage_cap
for crypto. First Pivot Point continuous-sizing variant.

Source: reused formula from prior repo research (Swoopr Woodie Pivot
Points article, already confirmed in 2026-09-08-158); no new external
source this iteration.

## Grid test summary (Step 6)

`param_grid={zscore_window: [50,100,150], sensitivity: [0.4,0.6,0.8]}`,
symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 108, **passed:** 49, **pass_fraction:** 0.454.
- **by_asset_class:** equity 27/54 (0.500), crypto 22/54 (0.407).
- **by_vol_regime:** low 31/36 (0.861), mid 18/36 (0.500), high 0/36
  (0.0) — **zero passing cells in the high-vol tercile**, the sharpest
  degradation recorded so far this cron trigger.
- **best_cell:** SPY, zscore_window=150/sensitivity=0.4, low-vol, Sharpe
  2.587.
- **worst_cell:** QQQ, zscore_window=150/sensitivity=0.8, high-vol, Sharpe
  -0.314.

## Single-config validator results (Step 7)

Best grid config (zscore_window=150, sensitivity=0.4) tested full-sample
per symbol, leverage_cap=1.0 (equity) / 0.4 (crypto):

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity (rel-std) | Outcome |
|---|---|---|---|---|---|---|
| QQQ | 0.953 (**fail**, near-miss) | 0.137 (pass) | 0.044 (**fail**, decisive) | 0.750 (pass) | 0.063 (pass) | **rejected** |
| SPY | 0.936 (**fail**, near-miss) | 0.107 (pass) | -0.081 (**fail**, decisive, negative) | 0.750 (pass) | 0.051 (pass) | **rejected** |
| BTC/USDT | 0.127 (**fail**, decisive) | 0.309 (**fail**) | -0.065 (**fail**) | 0.750 (pass) | 0.212 (pass) | **rejected** |
| ETH/USDT | 0.104 (**fail**, decisive) | 0.364 (**fail**, largest MDD this cron trigger) | -0.065 (**fail**) | 1.000 (pass) | 0.223 (pass) | **rejected** |

## Decision

**Rejected (all 4 symbols).** Both equity symbols are near-misses on
Sharpe alone (0.953/0.936) but fail TC-survival decisively (0.044/-0.081 vs
0.5 threshold) — the daily-pivot-anchored dial appears to require frequent
recomputation off yesterday's H/L/C, generating enough turnover relative
to its thin edge that transaction costs erase most of the gross return.
Crypto fails decisively across the board, with ETH/USDT posting this cron
trigger's largest single MDD (0.364). The zero-pass-rate high-vol tercile
(0/36 grid cells) is the clearest signal yet that a daily-recomputed pivot
anchor is a poor base for a continuous sizing dial in volatile conditions
— the pivot itself becomes noisy relative to the day's actual range. No
further Pivot Point continuous-sizing variant recommended without an
explicit trade-frequency dampener (e.g. a much wider deadband or a
multi-day-averaged pivot anchor) to address the TC-survival failure mode.
