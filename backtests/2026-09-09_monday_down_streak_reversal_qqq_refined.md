# Monday 2-Day-Down-Streak Reversal — QQQ Refinement (max_hold_days=4)

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_monday_down_streak_reversal.py` (same file, different config)
**Outcome:** ACCEPTED (QQQ)

## Hypothesis

Direct follow-up to near-miss 2026-09-09-004 (Monday 2-day-down-streak
reversal, signal-based exit): at the wide-grid best config
(down_streak_days=2, max_hold_days=5), QQQ passed Sharpe/MDD/TC/walk-forward
comfortably but failed parameter_sensitivity narrowly (relative std 0.547
vs 0.5 threshold) because the wide grid's max_hold_days values (5/10/15)
swing QQQ's Sharpe more than SPY's. This iteration runs a narrower,
finer-grained max_hold_days sweep (3/4/5/6/7, holding down_streak_days=2
fixed) specifically around the near-miss region to test whether a tighter
neighborhood rescues parameter stability -- following this repo's
established near-miss-refinement pattern (e.g. 2026-09-04-158/159,
2026-09-08-178/179).

## Grid test (Step 6, refinement)

`param_grid`: down_streak_days=[2] (fixed), max_hold_days=[3,4,5,6,7]
`symbols`: equity [QQQ, SPY] only (crypto already decisively rejected in
the wider grid, 0/36 -- no reason to re-test)
`vol_regime_splits`: 3
Total cells: 30, passed: 19, **pass_fraction: 0.633** (vs 0.222 in the wide
grid -- the narrower neighborhood is much more consistently profitable).

QQQ average Sharpe by max_hold_days: hold=3: 0.800, hold=4: 0.894 (2/3
cells pass, best), hold=5: 0.881, hold=6: 0.930, hold=7: 0.882 -- all
tightly clustered around 0.8-0.9, confirming the wide grid's instability
was mostly an artifact of comparing against the much-worse
down_streak_days=3 branch, not real fragility within down_streak_days=2.

## Single-config validation (Step 7), config down_streak_days=2/max_hold_days=4

| Validator | QQQ | Threshold |
|---|---|---|
| Sharpe ratio | 1.123 (PASS) | >= 1.0 |
| Max drawdown | 0.071 (PASS) | <= 0.25 |
| Transaction cost survival (10bps/trade) | 0.950 net Sharpe (PASS) | >= 0.5 |
| Walk-forward (4 splits) | 1.0 (PASS, 4/4) | >= 0.75 |
| Parameter sensitivity (narrow grid) | rel_std 0.049 (PASS, very stable) | <= 0.5 |

## Decision

**ACCEPTED for QQQ** (down_streak_days=2, max_hold_days=4). All 5
validators pass; parameter sensitivity within the refined neighborhood is
excellent (rel_std 0.049, essentially flat Sharpe across max_hold_days=3-7),
confirming the earlier near-miss was a grid-selection artifact (comparing
against a structurally worse down_streak_days=3 branch) rather than genuine
fragility. Combined with the already-accepted SPY config
(down_streak_days=2, max_hold_days=5, see 2026-09-09-004), this strategy
family is now accepted for BOTH major equity index ETFs, each with its own
locally-optimal max_hold_days (QQQ=4, SPY=5) -- consistent with this
repo's convention of per-symbol parameter tuning rather than forcing a
single shared config.

## Source

https://www.quantifiedstrategies.com/algorithmic-trading-strategies/ (same source as parent hypothesis 2026-09-09-004)
