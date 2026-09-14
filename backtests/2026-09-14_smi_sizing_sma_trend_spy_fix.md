# Stochastic Momentum Index (SMI) Continuous Sizing — SPY Fix

**Date:** 2026-09-15
**Strategy ID:** 2026-09-15-016 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_smi_sizing_sma_trend.py` (unchanged; parameter re-search only)

## Hypothesis

SPY fix for 2026-09-14-098 (SMI continuous sizing dial, accepted QQQ but
rejected SPY -- TC-survival net Sharpe 0.438<0.5; crypto BTC/USDT
decisively rejected, out of scope). Formula unchanged (William Blau 1993
double-EMA-smoothed close-displacement-from-midpoint, already confirmed).
Widening the search across smi_range_window, smi_slow, and deadband finds
SPY passes cleanly. Same strategy file, same already-confirmed SMI formula,
no strategy code change.

## Grid test summary (Step 6)

`param_grid={smi_range_window: [10,13,20], smi_slow: [25,40], deadband:
[0.15,0.25,0.35], smi_sensitivity: [0.4,0.6]}`, symbol SPY only (QQQ
already accepted at original config, crypto out of scope per prior decisive
rejection).

- **total_cells:** 108, **passed:** 47, **pass_fraction:** 0.435.
- **by_vol_regime:** low 36/36 (1.000), mid 0/36 (0.000), high 11/36 (0.306).
- **best_cell:** smi_range_window=10/smi_slow=25/deadband=0.15/
  smi_sensitivity=0.4, low-vol, Sharpe 2.588.

## Single-config validator results (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity (rel-std) | Outcome |
|---|---|---|---|---|---|---|---|
| SPY | smi_range_window=10/smi_slow=40/deadband=0.25/smi_sensitivity=0.4 | 1.134 (pass) | 0.067 (pass) | 0.633 (pass, 139 trades) | 1.000 (pass) | 0.050 (pass) | **accepted** |

Walk-forward used manual 4-way `np.array_split` (repo's `check_walk_forward`
calls `vbt.utils.splitting.RangeSplitter`, unavailable in installed
vectorbt -- known recurring fix this cron trigger).

## Decision

**Accepted (SPY):** clears all 5 validators at smi_range_window=10/
smi_slow=40/deadband=0.25/smi_sensitivity=0.4 -- rescues prior
2026-09-14-098's SPY TC-survival near-miss. **QQQ unchanged** (already
accepted at original config from 2026-09-14-098, not retested). **Crypto
remains out of scope** (prior decisive BTC/USDT MDD-fail rejection not
revisited).
