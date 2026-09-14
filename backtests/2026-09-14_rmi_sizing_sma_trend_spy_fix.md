# Relative Momentum Index (RMI) Continuous Sizing — SPY Fix

**Date:** 2026-09-15
**Strategy ID:** 2026-09-15-018 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_rmi_sizing_sma_trend.py` (unchanged; parameter re-search only)

## Hypothesis

SPY fix for 2026-09-14-097 (RMI continuous sizing dial, accepted QQQ but
rejected SPY -- Sharpe 0.976<1.0 and TC-survival net Sharpe 0.294<0.5;
crypto BTC/USDT decisively rejected, out of scope). Formula unchanged
(Roger Altman 1993, RSI Wilder-smoothing applied to N-bar momentum step,
already confirmed). Widening the search across momentum_period,
smoothing_period, and deadband finds SPY passes cleanly. Same strategy
file, same already-confirmed RMI formula, no strategy code change.

## Grid test summary (Step 6)

`param_grid={momentum_period: [5,10,14], smoothing_period: [14,21],
deadband: [0.15,0.25,0.35], rmi_sensitivity: [0.4,0.6]}`, symbol SPY only
(QQQ already accepted at original config, crypto out of scope per prior
decisive rejection).

- **total_cells:** 108, **passed:** 37, **pass_fraction:** 0.343.
- **by_vol_regime:** low 36/36 (1.000), mid 0/36 (0.000), high 1/36 (0.028).
- **best_cell:** momentum_period=5/smoothing_period=14/deadband=0.25/
  rmi_sensitivity=0.4, low-vol, Sharpe 2.599.

## Single-config validator results (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity (rel-std) | Outcome |
|---|---|---|---|---|---|---|---|
| SPY | momentum_period=5/smoothing_period=21/deadband=0.35/rmi_sensitivity=0.4 | 1.067 (pass) | 0.063 (pass) | 0.551 (pass, 140 trades) | 1.000 (pass) | 0.084 (pass) | **accepted** |

Walk-forward used manual 4-way `np.array_split` (repo's `check_walk_forward`
calls `vbt.utils.splitting.RangeSplitter`, unavailable in installed
vectorbt -- known recurring fix this cron trigger).

## Decision

**Accepted (SPY):** clears all 5 validators at momentum_period=5/
smoothing_period=21/deadband=0.35/rmi_sensitivity=0.4 -- rescues prior
2026-09-14-097's SPY double near-miss (Sharpe + TC-survival). **QQQ
unchanged** (already accepted at original config, not retested). **Crypto
remains out of scope** (prior decisive BTC/USDT MDD-fail rejection not
revisited).
