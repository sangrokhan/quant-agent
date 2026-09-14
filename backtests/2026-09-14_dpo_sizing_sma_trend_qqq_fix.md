# Detrended Price Oscillator (DPO) Continuous Sizing — QQQ Fix

**Date:** 2026-09-15
**Strategy ID:** 2026-09-15-013 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_dpo_sizing_sma_trend.py` (unchanged; parameter re-search only)

## Hypothesis

QQQ fix for 2026-09-14-154 (DPO continuous sizing dial, accepted BTC/ETH
crypto but rejected QQQ decisively and SPY near-miss, both failing Sharpe
AND TC-survival at the original config). Formula reconfirmed this iteration
via https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/detrended-price-oscillator-dpo
(visited this iteration, browser_exec fallback for the original topic
search -- web_search's DDGS backend returned "No results found" for two
consecutive queries this iteration) -- matches repo's existing
`Close.shift(n/2+1) - SMA(n)` implementation exactly. Widening the search
across dpo_window (up to 30, vs original default 20) and zscore_window with
a wider deadband range (up to 0.55) finds QQQ passes cleanly. Same strategy
file, same already-confirmed DPO formula, no strategy code change.

## Grid test summary (Step 6)

`param_grid={dpo_window: [14,20,30], zscore_window: [100,150], deadband:
[0.3,0.45,0.55], sensitivity: [0.4,0.6]}`, symbols QQQ/SPY (equity only --
crypto out of scope, already accepted at the original config).

- **total_cells:** 216, **passed:** 120, **pass_fraction:** 0.556.
- **by_vol_regime:** low 72/72 (1.000), mid 34/72 (0.472), high 14/72 (0.194).
- **best_cell:** SPY, dpo_window=30/zscore_window=100/deadband=0.3/
  sensitivity=0.6, low-vol, Sharpe 2.764.
- **worst_cell:** QQQ, dpo_window=20/zscore_window=100/deadband=0.55/
  sensitivity=0.6, high-vol, Sharpe -0.916.

## Single-config validator results (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity (rel-std) | Outcome |
|---|---|---|---|---|---|---|---|
| QQQ | dpo_window=30/zscore_window=100/deadband=0.55/sensitivity=0.6 | 1.290 (pass) | 0.152 (pass) | 0.833 (pass, 144 trades) | 1.000 (pass) | 0.383 (pass) | **accepted** |
| SPY | dpo_window=30/zscore_window=150/deadband=0.45/sensitivity=0.4 | 1.223 (pass) | 0.080 (pass) | 0.466 (**fail**, 157 trades) | 1.000 (pass) | 0.204 (pass) | **rejected** |

Tried 3 additional SPY candidate configs from the grid's top rows (dpo_window=30,
various zscore_window/deadband/sensitivity combos) -- best achieved was
Sharpe 1.059/TC-survival net Sharpe 0.481 (still below 0.5 threshold), so
SPY's near-miss persists despite a widened search this iteration; recorded
as an unresolved near-miss rather than forced through.

Walk-forward used manual 4-way `np.array_split` (repo's `check_walk_forward`
calls `vbt.utils.splitting.RangeSplitter`, unavailable in installed
vectorbt -- known recurring fix this cron trigger).

## Decision

**Accepted (QQQ):** clears all 5 validators at dpo_window=30/
zscore_window=100/deadband=0.55/sensitivity=0.6 -- rescues prior
2026-09-14-154's QQQ decisive rejection.
**Still rejected (SPY):** TC-survival near-miss persists across a widened
4-config sweep (best net Sharpe 0.481 vs 0.5 threshold); a future loop
could try a lower-turnover deadband regime or a different smoothing
approach specifically for SPY.
**Unchanged (crypto):** BTC/ETH remain accepted at the original config
from 2026-09-14-154 (leverage_cap=0.4), not retested this iteration.
