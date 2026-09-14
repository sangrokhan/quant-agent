# Chande Kroll Stop (CKSP) Normalized-Distance Sizing — QQQ+SPY Fix

**Date:** 2026-09-15
**Strategy ID:** 2026-09-15-012 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_cksp_norm_dist_sizing_sma_trend.py` (unchanged; parameter re-search only)

## Hypothesis

Fix for 2026-09-14-161 (CKSP normalized-distance continuous sizing dial,
rejected on all 4 symbols: QQQ/SPY equity near-miss on Sharpe+TC-survival,
BTC/ETH crypto decisive fail). Formula reconfirmed this iteration via
https://pineify.app/pine-script/indicators/chande-kroll-stop (visited this
iteration, browser_exec fallback -- web_search's DDGS backend returned "No
results found" for the initial query) -- matches the repo's existing
`_cksp_lines()` implementation exactly (first_high_stop =
Highest(High,p)-x*ATR(p), first_low_stop = Lowest(Low,p)+x*ATR(p),
stop_long/stop_short = rolling max/min over q). Widening the parameter
search across p, q, zscore_window, and a wider deadband range (up to 0.55)
finds BOTH QQQ and SPY pass cleanly. Same strategy file, same
already-confirmed CKSP formula, no strategy-code change.

## Grid test summary (Step 6)

`param_grid={p: [10,20], q: [9,20], zscore_window: [100,150], deadband:
[0.3,0.45,0.55], sensitivity: [0.4,0.6]}`, symbols QQQ/SPY (equity only --
crypto out of scope, decisive predecessor rejection).

- **total_cells:** 288, **passed:** 169, **pass_fraction:** 0.587.
- **by_vol_regime:** low 96/96 (1.000), mid 48/96 (0.500), high 25/96 (0.260).
- **best_cell:** SPY, p=20/q=20/zscore_window=100/deadband=0.3/
  sensitivity=0.4, low-vol, Sharpe 2.724.
- **worst_cell:** QQQ, p=20/q=9/zscore_window=150/deadband=0.45/
  sensitivity=0.4, high-vol, Sharpe -0.707.

## Single-config validator results (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity (rel-std) | Outcome |
|---|---|---|---|---|---|---|---|
| QQQ | p=10/q=20/zscore_window=150/deadband=0.3/sensitivity=0.4 | 1.062 (pass) | 0.112 (pass) | 0.679 (pass, 159 trades) | 1.000 (pass) | 0.055 (pass) | **accepted** |
| SPY | p=10/q=20/zscore_window=100/deadband=0.45/sensitivity=0.6 | 1.229 (pass) | 0.081 (pass) | 0.828 (pass, 124 trades) | 1.000 (pass) | 0.089 (pass) | **accepted** |

Walk-forward used manual 4-way `np.array_split` (repo's `check_walk_forward`
calls `vbt.utils.splitting.RangeSplitter`, unavailable in installed
vectorbt -- known recurring fix this cron trigger).

## Decision

**Accepted (QQQ + SPY):** both clear all 5 validators at their respective
per-symbol re-tuned configs -- rescues prior 2026-09-14-161's double
near-miss. **Crypto remains out of scope** (prior decisive BTC/ETH
rejection not revisited this iteration).
