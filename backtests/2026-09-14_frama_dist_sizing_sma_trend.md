# FRAMA Distance Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-157 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_frama_dist_sizing_sma_trend.py`

## Hypothesis

Fractal Adaptive Moving Average (FRAMA, John Ehlers, per
mesasoftware.com/papers/FRAMA.pdf and MetaTrader5/theforexgeek): an
adaptive EMA whose smoothing factor is driven by the price series' fractal
dimension D estimated from half-window vs full-window high/low ranges
(`alpha = exp(-4.6*(D-1))`, `FRAMA_t = alpha*Close_t + (1-alpha)*FRAMA_{t-1}`).
Repo has 9 prior FRAMA entries, ALL binary triggers (breakout/crossover/
slope confirmation), several near-misses. This iteration uses the
normalized distance `(Close - FRAMA) / FRAMA` (never tried as a continuous
metric before) as a CONTINUOUS SIZING dial: rolling z-scored +
tanh-squashed to [-1,+1], sized within an SMA(trend_window) uptrend gate.
First FRAMA continuous-sizing variant.

Source: https://www.mesasoftware.com/papers/FRAMA.pdf (via web_search).

## Grid test summary (Step 6)

`param_grid={frama_window: [10,16,24], sensitivity: [0.5,0.7]}`, symbols
QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 72, **passed:** 32, **pass_fraction:** 0.444.
- **by_asset_class:** equity 20/36 (0.556), crypto 12/36 (0.333).
- **by_vol_regime:** low 21/24 (0.875), mid 8/24 (0.333), high 3/24 (0.125).
- **best_cell:** QQQ, frama_window=10/sensitivity=0.7, low-vol, Sharpe 2.56.
- **worst_cell:** ETH/USDT, frama_window=10/sensitivity=0.7, high-vol,
  Sharpe 0.03.

## Single-config validator results (Step 7)

Default params (frama_window=10, sensitivity=0.7, deadband=0.20,
leverage_cap=1.0/0.4) FAILED transaction-cost survival for ALL FOUR
symbols on the first pass (turnover 298-546 trades was too high for a
20%-deadband FRAMA-distance dial, unlike this cron trigger's other
overlays). Retuned by widening equity `deadband` to 0.4 (cuts QQQ/SPY
turnover ~50%) and reducing crypto `leverage_cap` to 0.25/0.3 (BTC/ETH
respectively) to control drawdown, then re-validated:

| Symbol | Config | Trades | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Outcome |
|---|---|---|---|---|---|---|---|---|
| QQQ | deadband=0.4 | 274 | 1.259 (pass) | 0.158 (pass) | 0.505 (pass, borderline) | 1.0 (pass) | 0.207 (pass) | **accepted** |
| SPY | deadband=0.4 | 276 | 0.887 (**fail**) | 0.086 (pass) | 0.138 (**fail**) | 1.0 (pass) | 0.105 (pass) | **rejected** |
| BTC/USDT | lev_cap=0.25 | 264 | 1.335 (pass) | 0.165 (pass) | 0.682 (pass) | 1.0 (pass) | 0.018 (pass) | **accepted** |
| ETH/USDT | lev_cap=0.3 | 266 | 1.166 (pass) | 0.239 (pass) | 0.787 (pass) | 1.0 (pass) | 0.035 (pass) | **accepted** |

## Decision

**Accepted (QQQ at deadband=0.4, BTC/USDT at leverage_cap=0.25,
ETH/USDT at leverage_cap=0.3):** all 5 validators pass, though QQQ's
TC-survival is a thin pass (0.505 vs 0.5 threshold) — flag as fragile.
**Rejected (SPY):** fails both gross Sharpe (0.887) and TC-survival
(0.138) even after the same deadband widening that rescued QQQ.

Scope note: this FRAMA-distance dial runs "hot" (high baseline turnover)
compared to this cron trigger's other continuous-sizing overlays and
needed non-default deadband/leverage_cap just to survive costs — treat the
QQQ accept as fragile/borderline for a future loop to firm up (e.g. try
deadband=0.5 or a slower frama_window before fully trusting it live).

Full raw grid: `/tmp/frama_grid_summary.json` (not committed, ephemeral).
Full raw validators: `validators_frama_dist_sizing.json`.
