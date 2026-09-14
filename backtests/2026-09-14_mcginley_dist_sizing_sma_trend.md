# McGinley Dynamic Distance Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-148
**File:** `strategies/2026-09-14_mcginley_dist_sizing_sma_trend.py`

## Hypothesis

McGinley Dynamic (John R. McGinley, 1990): an adaptive moving average,
`MD_i = MD_{i-1} + (Close-MD_{i-1}) / (k*N*(Close/MD_{i-1})^4)`, k=0.6.
Formula confirmed via Google AI-overview synthesis of
Investopedia/Groww/Capital.com/Tradejini (`browser_exec`).

This repo has 6+ prior McGinley Dynamic entries, all binary crossover/slope
/fixed-hold triggers. This iteration measures the percentage distance of
price from its own McGinley Dynamic line `(close-MD)/MD`, rolling z-scored
+ tanh-squashed to [-1,+1], used as a sizing multiplier within an
SMA(trend_window) uptrend gate. First McGinley Dynamic continuous-sizing
variant in this repo.

## Grid test summary (Step 6)

`param_grid={md_n: [10,14,20], deadband: [0.15,0.25], leverage_cap: [0.4,1.0]}`,
symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 144, **passed:** 86, **pass_fraction:** 0.597 — best
  pass_fraction of any strategy this cron trigger so far.
- **by_asset_class:** equity 40/72 (0.556), crypto 46/72 (0.639).
- **by_vol_regime:** low 45/48 (0.938), mid 28/48 (0.583), high 13/48
  (0.271) — best high-vol showing of this trigger's sizing-dial family too.
- **best_cell:** QQQ, md_n=20/deadband=0.15/leverage_cap=1.0, low-vol,
  Sharpe 2.83.
- **worst_cell:** ETH/USDT, md_n=10/deadband=0.25/leverage_cap=0.4,
  high-vol, Sharpe -0.25.

## Single-config validator results (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Outcome |
|---|---|---|---|---|---|---|---|
| QQQ | md_n=20, db=0.25, lc=0.4 | 1.314 (pass) | pass | pass | pass | pass | **accepted** |
| SPY | md_n=20, db=0.15, lc=0.4 | 1.263 (pass) | pass | **FAIL (net Sharpe 0.179)** | pass | pass | **rejected** |
| BTC/USDT | md_n=20, db=0.15, lc=0.4 | 1.555 (pass) | pass | pass | pass | pass | **accepted** |
| ETH/USDT | md_n=14, db=0.15, lc=0.4 | 1.181 (pass) | **FAIL (0.280>0.25, near-miss)** | pass | pass | pass | rejected at lc=0.4 |
| ETH/USDT (leverage-cap recalibration) | md_n=14, db=0.15, **lc=0.3** | 1.164 (pass) | 0.197 (pass) | 0.980 (pass) | 1.0 (pass) | pass (rel_std 0.137) | **accepted** |

## Decision

**Accepted:** QQQ, BTC/USDT, ETH/USDT (ETH at leverage_cap=0.3 after a
leverage-cap-recalibration follow-up fixed the initial MDD near-miss at
leverage_cap=0.4, per this cron trigger's established recalibration
pattern, e.g. 2026-09-14-124/125).
**Rejected:** SPY (decisive transaction-cost survival fail, net Sharpe
0.179 vs 0.5 threshold, gross Sharpe/MDD/WF/param-sensitivity all pass).

Full raw grid: `grid_result_mcginley_dist_sizing.json`. Full raw validators
(leverage_cap=0.4 pass): `validators_mcginley_dist_sizing.json`; ETH
leverage_cap=0.3 recalibration run performed inline, not persisted to a
separate JSON file.
