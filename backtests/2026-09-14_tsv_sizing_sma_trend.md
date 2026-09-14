# Time Segmented Volume (TSV) Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-149
**File:** `strategies/2026-09-14_tsv_sizing_sma_trend.py`

## Hypothesis

Time Segmented Volume (TSV, Worden Brothers, TC2000): rolling sum of
volume-weighted price change, `TV_i = Volume_i * (Close_i - Close_{i-1})`,
`TSV_n = sum(TV_i for i in [n-L+1, n])`. Formula confirmed via Google
AI-overview synthesis of Investopedia/TC2000/useThinkScript (`browser_exec`).

This repo has 1 prior TSV entry (2026-09-06-165, a binary TSV-crosses-own-
signal-SMA crossover, decisively rejected). This iteration reframes TSV as
a CONTINUOUS SIZING dial: raw unbounded TSV, rolling z-scored + tanh-squashed
to [-1,+1], sized within an SMA(trend_window) uptrend gate — distinct
mechanism from the prior rejected binary crossover.

## Grid test summary (Step 6)

`param_grid={tsv_window: [8,13,21], deadband: [0.15,0.25], leverage_cap: [0.4,1.0]}`,
symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 144, **passed:** 86, **pass_fraction:** 0.597 — tied for
  best pass_fraction this cron trigger (with 2026-09-14-148 McGinley).
- **by_asset_class:** equity 40/72 (0.556), crypto 46/72 (0.639).
- **by_vol_regime:** low 48/48 (1.0, ALL low-vol cells pass), mid 26/48
  (0.542), high 12/48 (0.25).
- **best_cell:** QQQ, tsv_window=13/deadband=0.15/leverage_cap=1.0, low-vol,
  Sharpe 2.99.
- **worst_cell:** SPY, tsv_window=13/deadband=0.15/leverage_cap=1.0,
  mid-vol, Sharpe -0.21.

## Single-config validator results (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Outcome |
|---|---|---|---|---|---|---|---|
| QQQ | tw=21, db=0.25, lc=0.4 | 1.480 (pass) | pass | pass | pass | pass | **accepted** |
| SPY | tw=21, db=0.15, lc=1.0 | 1.244 (pass) | pass | **FAIL** | pass | pass | **rejected (near-miss on TC)** |
| BTC/USDT | tw=13, db=0.15, lc=0.4 | 1.435 (pass) | pass | pass | pass | pass | **accepted** |
| ETH/USDT | tw=13, db=0.15, lc=0.4 | 1.418 (pass) | pass | pass | pass | pass | **accepted** |

## Decision

**Accepted:** QQQ, BTC/USDT, ETH/USDT (all 5 validators pass at
leverage_cap=0.4).
**Rejected:** SPY (near-miss, transaction-cost survival fails; gross
Sharpe/MDD/WF/param-sensitivity all pass — a recurring pattern this cron
trigger where SPY specifically fails TC-survival while QQQ/BTC/ETH pass on
the same mechanism, candidate for a future deadband-widening follow-up
specific to SPY).

Full raw grid: `grid_result_tsv_sizing.json`. Full raw validators:
`validators_tsv_sizing.json`.
